import argparse
import json
import logging
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5001
INDEX_FILE = "index.html"
DATA_FILE = "calendar_data.json"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MAX_DISPLAY_WEEKS = 6
MAX_OCCURRENCES = 5
MAX_SLOTS = 2
LOGGER = logging.getLogger("calendar_api")


def load_entries():
    path = Path.cwd() / DATA_FILE
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    if not isinstance(raw, dict):
        return {}

    entries = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, str):
            entries[key] = value
    return entries


def get_cell_names(entries, occurrence, day_of_week):
    if not occurrence:
        return {"first": "", "second": ""}

    base_key = f"{occurrence}:{day_of_week}"
    first = entries.get(f"{base_key}:1", "")
    second = entries.get(f"{base_key}:2", "")

    # Backward compatibility for old single-value data.
    if not first and not second:
        first = entries.get(base_key, "")

    return {"first": first, "second": second}


def save_entries(entries):
    path = Path.cwd() / DATA_FILE
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def build_day_lookup(year, month):
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
    def send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_index(self):
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

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_index()
            return

        if parsed.path != "/api/calendar":
            self.send_json(404, {"status": "error", "error": "Not found"})
            return

        query = parse_qs(parsed.query)
        try:
            year = int(query.get("year", [str(date.today().year)])[0])
            month = int(query.get("month", [str(date.today().month)])[0])
        except ValueError:
            LOGGER.warning("GET /api/calendar invalid month/year query=%s", parsed.query)
            self.send_json(400, {"status": "error", "error": "Invalid month/year"})
            return

        if month < 1 or month > 12:
            LOGGER.warning("GET /api/calendar invalid month=%s year=%s", month, year)
            self.send_json(400, {"status": "error", "error": "Month must be between 1 and 12"})
            return

        entries = load_entries()
        LOGGER.info("GET /api/calendar year=%s month=%s", year, month)
        self.send_json(200, build_calendar_payload(year, month, entries))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/calendar":
            self.send_json(404, {"status": "error", "error": "Not found"})
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

        if day_of_week not in DAYS:
            LOGGER.warning("POST /api/calendar invalid day_of_week=%s", day_of_week)
            self.send_json(400, {"status": "error", "error": "Invalid day_of_week"})
            return

        if day_of_week == "Monday":
            LOGGER.warning("POST /api/calendar rejected monday occurrence=%s slot=%s", occurrence, slot)
            self.send_json(400, {"status": "error", "error": "Monday is fixed to PDAY"})
            return

        if not isinstance(occurrence, int) or occurrence < 1 or occurrence > MAX_OCCURRENCES:
            LOGGER.warning("POST /api/calendar invalid occurrence=%s day_of_week=%s", occurrence, day_of_week)
            self.send_json(400, {"status": "error", "error": "occurrence must be between 1 and 5"})
            return

        if not isinstance(slot, int) or slot < 1 or slot > MAX_SLOTS:
            LOGGER.warning("POST /api/calendar invalid slot=%s day_of_week=%s occurrence=%s", slot, day_of_week, occurrence)
            self.send_json(400, {"status": "error", "error": "slot must be between 1 and 2"})
            return

        entries = load_entries()
        base_key = f"{occurrence}:{day_of_week}"
        key = f"{base_key}:{slot}"
        if name:
            entries[key] = name
        else:
            entries.pop(key, None)
        # Migrate legacy key once any slot is edited.
        entries.pop(base_key, None)
        save_entries(entries)
        LOGGER.info(
            "POST /api/calendar saved occurrence=%s day_of_week=%s slot=%s has_name=%s",
            occurrence,
            day_of_week,
            slot,
            bool(name),
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
                },
            },
        )

    def log_message(self, fmt, *args):
        return


def main():
    parser = argparse.ArgumentParser(description="Run the missionary lunch calendar server.")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host interface to bind (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port to listen on (default: {DEFAULT_PORT})")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
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
