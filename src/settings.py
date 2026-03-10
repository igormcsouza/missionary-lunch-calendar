"""Settings-related HTTP request handlers for the missionary lunch calendar."""
import json
import logging


MAX_APP_PROFILES = 2

LOGGER = logging.getLogger("calendar_api")


def handle_get_settings(handler):
    """Handle GET /api/settings."""
    user_id = handler.get_user_id()
    if not user_id:
        handler.send_json(401, {"status": "error", "error": "User not authenticated"})
        return
    settings = handler.STORE.load_settings(user_id)
    LOGGER.info("GET /api/settings user_id=%s", user_id)
    handler.send_json(200, {"status": "ok", "settings": settings})


def handle_post_settings(handler):
    """Handle POST /api/settings."""
    user_id = handler.get_user_id()
    if not user_id:
        handler.send_json(401, {"status": "error", "error": "User not authenticated"})
        return
    content_length = int(handler.headers.get("Content-Length", "0"))
    raw_body = handler.rfile.read(content_length)
    try:
        data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except json.JSONDecodeError:
        handler.send_json(400, {"status": "error", "error": "Invalid JSON"})
        return
    ward = str(data.get("ward", "")).strip()
    settings = handler.STORE.load_settings(user_id)
    if ward:
        settings["ward"] = ward
    else:
        settings.pop("ward", None)
    # Per-profile title and subtitle (only update if key is present in request).
    for app_profile in range(1, MAX_APP_PROFILES + 1):
        for field in ("title", "subtitle"):
            key = f"slot_{app_profile}_{field}"
            if key in data:
                value = str(data[key]).strip()
                if value:
                    settings[key] = value
                else:
                    settings.pop(key, None)
    handler.STORE.save_settings(user_id, settings)
    LOGGER.info("POST /api/settings user_id=%s ward=%r", user_id, ward)
    handler.send_json(200, {"status": "ok", "settings": settings})
