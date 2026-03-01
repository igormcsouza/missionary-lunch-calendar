import json
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PORT = 5001
INDEX_FILE = "index.html"
DATA_FILE = "calendar_data.json"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MAX_DISPLAY_WEEKS = 6
MAX_OCCURRENCES = 5


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

    return {str(k): str(v) for k, v in raw.items()}


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
            key = f"{occurrence}:{day_name}" if occurrence else None
            if day_name == "Monday":
                name = "PDAY"
                editable = False
            else:
                name = entries.get(key, "") if key else ""
                editable = True

            cells.append(
                {
                    "week_number": week_number,
                    "day_of_week": day_name,
                    "day_number": day_number,
                    "occurrence": occurrence,
                    "name": name,
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
            self.send_json(400, {"status": "error", "error": "Invalid month/year"})
            return

        if month < 1 or month > 12:
            self.send_json(400, {"status": "error", "error": "Month must be between 1 and 12"})
            return

        entries = load_entries()
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
            self.send_json(400, {"status": "error", "error": "Invalid JSON"})
            return

        day_of_week = str(data.get("day_of_week", "")).strip()
        occurrence = data.get("occurrence")
        name = str(data.get("name", "")).strip()

        if day_of_week not in DAYS:
            self.send_json(400, {"status": "error", "error": "Invalid day_of_week"})
            return

        if day_of_week == "Monday":
            self.send_json(400, {"status": "error", "error": "Monday is fixed to PDAY"})
            return

        if not isinstance(occurrence, int) or occurrence < 1 or occurrence > MAX_OCCURRENCES:
            self.send_json(400, {"status": "error", "error": "occurrence must be between 1 and 5"})
            return

        entries = load_entries()
        key = f"{occurrence}:{day_of_week}"
        if name:
            entries[key] = name
        else:
            entries.pop(key, None)
        save_entries(entries)

        self.send_json(
            200,
            {
                "status": "ok",
                "saved": {
                    "occurrence": occurrence,
                    "day_of_week": day_of_week,
                    "name": name,
                },
            },
        )

    def log_message(self, fmt, *args):
        return


def main():
    server = HTTPServer(("0.0.0.0", PORT), CalendarHandler)
    print(f"Listening on http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
