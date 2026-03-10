"""HTTP request handler for the missionary lunch calendar."""
import json
import logging
from datetime import date
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from core.utils import DAYS, MAX_OCCURRENCES, MAX_SLOTS, build_calendar_payload
from settings import MAX_APP_PROFILES, handle_get_settings, handle_post_settings

LOGGER = logging.getLogger("calendar_api")


class CalendarHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the calendar API."""

    STORE = None
    LOGGED_USER_IDS = set()

    def get_user_id(self):
        """Extract and return the authenticated user ID from request headers."""
        user_id = self.headers.get("X-User-Id", "").strip()
        if not user_id:
            return None
        if user_id not in self.LOGGED_USER_IDS:
            self.LOGGED_USER_IDS.add(user_id)
            LOGGER.info("Authenticated user uid=%s", user_id)
        return user_id

    def send_json(self, status_code, payload):
        """Serialize payload as JSON and send an HTTP response."""
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_index(self):
        """Serve the index.html file."""
        index_path = Path(__file__).parent.parent / "htmls" / "index.html"
        if not index_path.exists():
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"index.html not found in current directory")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(index_path.read_bytes())

    def do_GET(self):  # pylint: disable=invalid-name
        """Handle GET requests for the calendar API."""
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_index()
            return

        if parsed.path == "/api/settings":
            handle_get_settings(self)
            return

        if parsed.path != "/api/calendar":
            self.send_json(404, {"status": "error", "error": "Not found"})
            return

        self._handle_get_calendar(parsed)

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

    def do_POST(self):  # pylint: disable=invalid-name,too-many-return-statements
        """Handle POST requests to update calendar entries."""
        parsed = urlparse(self.path)
        if parsed.path == "/api/settings":
            handle_post_settings(self)
            return
        if parsed.path != "/api/calendar":
            self.send_json(404, {"status": "error", "error": "Not found"})
            return

        user_id = self.get_user_id()
        if not user_id:
            self.send_json(401, {"status": "error", "error": "User not authenticated"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)

        try:
            data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except json.JSONDecodeError:
            LOGGER.warning("POST /api/calendar invalid json")
            self.send_json(400, {"status": "error", "error": "Invalid JSON"})
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

    def log_message(self, _fmt, *args):  # pylint: disable=arguments-differ
        """Suppress default HTTP server console logging."""
