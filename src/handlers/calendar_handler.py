"""HTTP request handler for the missionary lunch calendar."""
from datetime import date
from urllib.parse import parse_qs, urlparse

from core.logger import LOGGER
from core.utils import build_calendar_payload
from handlers.default import DefaultHandler
from settings import DAYS, MAX_APP_PROFILES, MAX_OCCURRENCES, MAX_SLOTS


class CalendarHandler(DefaultHandler):
    """HTTP request handler for the calendar API."""

    STORE = None
    DEV = False

    _STATIC_ROUTES = {
        "/": ("index.html", "text/html; charset=utf-8"),
        "/styles.css": ("styles.css", "text/css; charset=utf-8"),
        "/script.js": ("script.js", "application/javascript; charset=utf-8"),
        "/favicon.svg": ("favicon.svg", "image/svg+xml"),
    }

    def do_GET(self):  # pylint: disable=invalid-name
        """Handle GET requests for the calendar API."""
        parsed = urlparse(self.path)

        if parsed.path in self._STATIC_ROUTES:
            filename, content_type = self._STATIC_ROUTES[parsed.path]
            self.send_static(filename, content_type)
            return

        if parsed.path == "/api/config":
            self.send_json(200, {"dev": self.DEV})
            return

        if parsed.path == "/api/settings":
            self._handle_get_settings()
            return

        if parsed.path != "/api/calendar":
            self.send_json(404, {"status": "error", "error": "Not found"})
            return

        self._handle_get_calendar(parsed)

    def do_POST(self):  # pylint: disable=invalid-name,too-many-return-statements
        """Handle POST requests to update calendar entries."""
        parsed = urlparse(self.path)
        if parsed.path == "/api/settings":
            self._handle_post_settings()
            return
        if parsed.path != "/api/calendar":
            self.send_json(404, {"status": "error", "error": "Not found"})
            return

        self._handle_post_calendar()

    def _handle_get_settings(self):
        """Handle GET /api/settings."""
        user_id = self.get_user_id()
        if not user_id:
            self.send_json(401, {"status": "error", "error": "User not authenticated"})
            return
        settings = self.STORE.load_settings(user_id)
        LOGGER.info("GET /api/settings user_id=%s", user_id)
        self.send_json(200, {"status": "ok", "settings": settings})

    def _handle_post_settings(self):
        """Handle POST /api/settings."""
        user_id, data = self._require_authenticated_json()
        if user_id is None:
            return
        ward = str(data.get("ward", "")).strip()
        settings = self.STORE.load_settings(user_id)
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
        self.STORE.save_settings(user_id, settings)
        LOGGER.info("POST /api/settings user_id=%s ward=%r", user_id, ward)
        self.send_json(200, {"status": "ok", "settings": settings})

    def _handle_get_calendar(self, parsed):
        """Handle GET /api/calendar."""
        user_id = self.get_user_id()
        if not user_id:
            self.send_json(401, {"status": "error", "error": "User not authenticated"})
            return

        query = parse_qs(parsed.query)
        try:
            year = int(query.get("year", [str(date.today().year)])[0])
            month = int(query.get("month", [str(date.today().month)])[0])
            profile = int(query.get("profile", ["1"])[0])
        except ValueError:
            LOGGER.warning("GET /api/calendar invalid month/year query=%s", parsed.query)
            self.send_json(400, {"status": "error", "error": "Invalid month/year"})
            return

        if month < 1 or month > 12:
            LOGGER.warning("GET /api/calendar invalid month=%s year=%s", month, year)
            self.send_json(400, {"status": "error", "error": "Month must be between 1 and 12"})
            return

        if profile < 1 or profile > MAX_APP_PROFILES:
            LOGGER.warning("GET /api/calendar invalid profile=%s", profile)
            self.send_json(
                400,
                {"status": "error", "error": f"profile must be between 1 and {MAX_APP_PROFILES}"},
            )
            return

        entries = self.STORE.load_entries(user_id, profile)
        LOGGER.info(
            "GET /api/calendar user_id=%s year=%s month=%s profile=%s",
            user_id, year, month, profile,
        )
        self.send_json(200, build_calendar_payload(year, month, entries))

    def _handle_post_calendar(self):  # pylint: disable=too-many-return-statements
        """Handle POST /api/calendar."""
        user_id, data = self._require_authenticated_json()
        if user_id is None:
            LOGGER.warning("POST /api/calendar invalid json or unauthenticated")
            return

        day_of_week = str(data.get("day_of_week", "")).strip()
        occurrence = data.get("occurrence")
        slot = data.get("slot", 1)
        name = str(data.get("name", "")).strip()
        profile = data.get("profile", 1)

        if day_of_week not in DAYS:
            LOGGER.warning("POST /api/calendar invalid day_of_week=%s", day_of_week)
            self.send_json(400, {"status": "error", "error": "Invalid day_of_week"})
            return

        if day_of_week == "Monday":
            LOGGER.warning(
                "POST /api/calendar rejected monday occurrence=%s slot=%s",
                occurrence, slot,
            )
            self.send_json(400, {"status": "error", "error": "Monday is fixed to PDAY"})
            return

        if not isinstance(occurrence, int) or occurrence < 1 or occurrence > MAX_OCCURRENCES:
            LOGGER.warning(
                "POST /api/calendar invalid occurrence=%s day_of_week=%s",
                occurrence, day_of_week,
            )
            self.send_json(400, {"status": "error", "error": "occurrence must be between 1 and 5"})
            return

        if not isinstance(slot, int) or slot < 1 or slot > MAX_SLOTS:
            LOGGER.warning(
                "POST /api/calendar invalid slot=%s day_of_week=%s occurrence=%s",
                slot, day_of_week, occurrence,
            )
            self.send_json(400, {"status": "error", "error": "slot must be between 1 and 2"})
            return

        if not isinstance(profile, int) or profile < 1 or profile > MAX_APP_PROFILES:
            LOGGER.warning("POST /api/calendar invalid profile=%s", profile)
            self.send_json(
                400,
                {"status": "error", "error": f"profile must be between 1 and {MAX_APP_PROFILES}"},
            )
            return

        entries = self.STORE.load_entries(user_id, profile)
        base_key = f"{occurrence}:{day_of_week}"
        key = f"{base_key}:{slot}"
        if name:
            entries[key] = name
        else:
            entries.pop(key, None)
        # Migrate legacy key once any slot is edited.
        entries.pop(base_key, None)
        self.STORE.save_entries(user_id, entries, profile)
        LOGGER.info(
            "POST /api/calendar user_id=%s saved occurrence=%s day_of_week=%s slot=%s"
            " has_name=%s profile=%s",
            user_id,
            occurrence,
            day_of_week,
            slot,
            bool(name),
            profile,
        )

        self.send_json(
            200,
            {
                "status": "ok",
                "saved": {
                    "occurrence": occurrence,
                    "day_of_week": day_of_week,
                    "slot": slot,
                    "name": name,
                    "profile": profile,
                },
            },
        )
