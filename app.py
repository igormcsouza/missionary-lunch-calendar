"""HTTP server for the missionary lunch calendar application."""
import argparse
import json
import logging
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from store import create_store


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5001
INDEX_FILE = "index.html"
DATA_FILE = "calendar_data.json"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MAX_DISPLAY_WEEKS = 6
MAX_OCCURRENCES = 5
MAX_SLOTS = 2
MAX_APP_PROFILES = 2
LOGGER = logging.getLogger("calendar_api")
STORE = create_store(dev=True, data_file=DATA_FILE)
LOGGED_USER_IDS = set()


def load_entries(user_id, profile=1):
    """Load calendar entries for the given user ID and profile."""
    return STORE.load_entries(user_id, profile)


def load_settings(user_id):
    """Load settings for the given user ID."""
    return STORE.load_settings(user_id)


def save_settings(user_id, settings):
    """Persist settings for the given user ID."""
    STORE.save_settings(user_id, settings)


def get_cell_names(entries, occurrence, day_of_week):
    """Return the first and second slot names for a calendar cell."""
    if not occurrence:
        return {"first": "", "second": ""}

    base_key = f"{occurrence}:{day_of_week}"
    first = entries.get(f"{base_key}:1", "")
    second = entries.get(f"{base_key}:2", "")

    # Backward compatibility for old single-value data.
    if not first and not second:
        first = entries.get(base_key, "")

    return {"first": first, "second": second}


def save_entries(user_id, entries, profile=1):
    """Persist calendar entries for the given user ID and profile."""
    STORE.save_entries(user_id, entries, profile)


def build_day_lookup(year, month):
    """Build a mapping of (week_number, day_name) to day metadata for a month."""
    day_lookup = {}
    week_number = 1
    day = 1
    occurrence_by_day = {day_name: 0 for day_name in DAYS}

    while True:
        try:
            current = date(year, month, day)
        except ValueError:
            break

        day_name = DAYS[current.weekday()]
        occurrence_by_day[day_name] += 1
        day_lookup[(week_number, day_name)] = {
            "day_number": day,
            "occurrence": occurrence_by_day[day_name],
        }

        if day_name == "Sunday":
            week_number += 1
        day += 1

    return day_lookup


def build_calendar_payload(year, month, entries):
    """Construct the full calendar JSON payload for the given month."""
    day_lookup = build_day_lookup(year, month)
    weeks = []
    for week_number in range(1, MAX_DISPLAY_WEEKS + 1):
        cells = []
        for day_name in DAYS:
            day_data = day_lookup.get((week_number, day_name))
            day_number = day_data["day_number"] if day_data else None
            occurrence = day_data["occurrence"] if day_data else None
            if day_name == "Monday":
                names = {"first": "PDAY", "second": ""}
                editable = False
            else:
                names = get_cell_names(entries, occurrence, day_name)
                editable = True

            cells.append(
                {
                    "week_number": week_number,
                    "day_of_week": day_name,
                    "day_number": day_number,
                    "occurrence": occurrence,
                    "name": names["first"],
                    "names": names,
                    "editable": editable,
                }
            )

        weeks.append({"week_number": week_number, "cells": cells})

    return {
        "status": "ok",
        "month": month,
        "year": year,
        "weeks": weeks,
    }


class CalendarHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the calendar API."""

    def get_user_id(self):
        """Extract and return the authenticated user ID from request headers."""
        user_id = self.headers.get("X-User-Id", "").strip()
        if not user_id:
            return None
        if user_id not in LOGGED_USER_IDS:
            LOGGED_USER_IDS.add(user_id)
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
        index_path = Path.cwd() / INDEX_FILE
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
            self._handle_get_settings()
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

        entries = load_entries(user_id, profile)
        LOGGER.info(
            "GET /api/calendar user_id=%s year=%s month=%s profile=%s",
            user_id, year, month, profile,
        )
        self.send_json(200, build_calendar_payload(year, month, entries))

    def _handle_get_settings(self):
        """Handle GET /api/settings."""
        user_id = self.get_user_id()
        if not user_id:
            self.send_json(401, {"status": "error", "error": "User not authenticated"})
            return
        settings = load_settings(user_id)
        LOGGER.info("GET /api/settings user_id=%s", user_id)
        self.send_json(200, {"status": "ok", "settings": settings})

    def _handle_post_settings(self):
        """Handle POST /api/settings."""
        user_id = self.get_user_id()
        if not user_id:
            self.send_json(401, {"status": "error", "error": "User not authenticated"})
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        try:
            data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except json.JSONDecodeError:
            self.send_json(400, {"status": "error", "error": "Invalid JSON"})
            return
        ward = str(data.get("ward", "")).strip()
        settings = load_settings(user_id)
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
        save_settings(user_id, settings)
        LOGGER.info("POST /api/settings user_id=%s ward=%r", user_id, ward)
        self.send_json(200, {"status": "ok", "settings": settings})

    def do_POST(self):  # pylint: disable=invalid-name,too-many-return-statements
        """Handle POST requests to update calendar entries."""
        parsed = urlparse(self.path)
        if parsed.path == "/api/settings":
            self._handle_post_settings()
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

        entries = load_entries(user_id, profile)
        base_key = f"{occurrence}:{day_of_week}"
        key = f"{base_key}:{slot}"
        if name:
            entries[key] = name
        else:
            entries.pop(key, None)
        # Migrate legacy key once any slot is edited.
        entries.pop(base_key, None)
        save_entries(user_id, entries, profile)
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


def main():
    """Parse arguments, configure logging, and start the HTTP server."""
    global STORE  # pylint: disable=global-statement

    parser = argparse.ArgumentParser(description="Run the missionary lunch calendar server.")
    parser.add_argument(
        "--host", default=DEFAULT_HOST,
        help=f"Host interface to bind (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})",
    )
    parser.add_argument("--dev", action="store_true", help="Enable development mode")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    STORE = create_store(dev=args.dev, data_file=DATA_FILE)
    server = HTTPServer((args.host, args.port), CalendarHandler)
    LOGGER.info("Running at http://%s:%s", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
