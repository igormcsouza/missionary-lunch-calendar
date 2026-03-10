"""API-level tests for the calendar HTTP server."""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from core.store import JsonFileStore  # noqa: E402  # pylint: disable=wrong-import-position
from core.utils import build_calendar_payload  # noqa: E402  # pylint: disable=wrong-import-position
from handlers.calendar_handler import CalendarHandler  # noqa: E402  # pylint: disable=wrong-import-position


def _make_handler(method, path, body=None, headers=None):
    """Return a CalendarHandler instance wired to in-memory streams."""
    raw_headers = {"X-User-Id": "testuser"}
    if headers:
        raw_headers.update(headers)

    body_bytes = json.dumps(body).encode() if body else b""
    if body_bytes:
        raw_headers["Content-Length"] = str(len(body_bytes))

    # rfile contains only the body; headers are passed separately.
    rfile = io.BytesIO(body_bytes)
    wfile = io.BytesIO()

    handler = CalendarHandler.__new__(CalendarHandler)
    handler.rfile = rfile
    handler.wfile = wfile
    handler.headers = raw_headers
    handler.path = path
    handler.requestline = f"{method} {path} HTTP/1.1"
    handler.request_version = "HTTP/1.1"
    handler.server = type("FakeServer", (), {"server_name": "localhost", "server_port": 5001})()
    handler.client_address = ("127.0.0.1", 9999)
    return handler, wfile


def _parse_response(wfile):
    """Parse raw HTTP response bytes into (status_code, payload_dict)."""
    wfile.seek(0)
    raw = wfile.read().decode("utf-8", errors="replace")
    lines = raw.split("\r\n")
    status_code = int(lines[0].split(" ")[1])
    body_start = raw.find("\r\n\r\n") + 4
    payload = json.loads(raw[body_start:])
    return status_code, payload


class TestCalendarAPIGetCalendar(unittest.TestCase):
    """Tests for GET /api/calendar."""

    def setUp(self):
        self._fd, self._tmp = tempfile.mkstemp(suffix=".json")
        os.close(self._fd)
        CalendarHandler.STORE = JsonFileStore(self._tmp)
        CalendarHandler.LOGGED_USER_IDS.clear()

    def tearDown(self):
        for path in (self._tmp, self._tmp.replace(".json", "_settings.json")):
            if os.path.exists(path):
                os.unlink(path)

    def test_get_calendar_returns_ok(self):
        """GET /api/calendar with valid params returns a 200 with weekly data."""
        handler, wfile = _make_handler("GET", "/api/calendar?year=2025&month=3")
        handler.do_GET()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["month"], 3)
        self.assertEqual(payload["year"], 2025)
        self.assertIn("weeks", payload)

    def test_get_calendar_missing_user_id_returns_401(self):
        """GET /api/calendar without X-User-Id returns 401."""
        handler, wfile = _make_handler(
            "GET", "/api/calendar?year=2025&month=3", headers={"X-User-Id": ""}
        )
        handler.do_GET()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 401)
        self.assertEqual(payload["status"], "error")

    def test_get_calendar_invalid_month_returns_400(self):
        """GET /api/calendar with month=13 returns 400."""
        handler, wfile = _make_handler("GET", "/api/calendar?year=2025&month=13")
        handler.do_GET()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 400)
        self.assertEqual(payload["status"], "error")

    def test_get_calendar_invalid_profile_returns_400(self):
        """GET /api/calendar with an out-of-range profile returns 400."""
        handler, wfile = _make_handler("GET", "/api/calendar?year=2025&month=3&profile=99")
        handler.do_GET()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 400)
        self.assertEqual(payload["status"], "error")

    def test_get_unknown_path_returns_404(self):
        """GET on an unknown path returns 404."""
        handler, wfile = _make_handler("GET", "/api/unknown")
        handler.do_GET()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 404)
        self.assertEqual(payload["status"], "error")


class TestCalendarAPIPostCalendar(unittest.TestCase):
    """Tests for POST /api/calendar."""

    def setUp(self):
        self._fd, self._tmp = tempfile.mkstemp(suffix=".json")
        os.close(self._fd)
        CalendarHandler.STORE = JsonFileStore(self._tmp)
        CalendarHandler.LOGGED_USER_IDS.clear()

    def tearDown(self):
        for path in (self._tmp, self._tmp.replace(".json", "_settings.json")):
            if os.path.exists(path):
                os.unlink(path)

    def test_post_calendar_saves_entry(self):
        """POST /api/calendar persists a new name and returns it."""
        body = {"day_of_week": "Tuesday", "occurrence": 1, "slot": 1, "name": "Alice", "profile": 1}
        handler, wfile = _make_handler("POST", "/api/calendar", body=body)
        handler.do_POST()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["saved"]["name"], "Alice")

    def test_post_calendar_monday_returns_400(self):
        """POST /api/calendar for Monday is rejected."""
        body = {"day_of_week": "Monday", "occurrence": 1, "slot": 1, "name": "Bob", "profile": 1}
        handler, wfile = _make_handler("POST", "/api/calendar", body=body)
        handler.do_POST()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 400)
        self.assertIn("Monday", payload["error"])

    def test_post_calendar_invalid_day_returns_400(self):
        """POST /api/calendar with an unrecognised day returns 400."""
        body = {"day_of_week": "Funday", "occurrence": 1, "slot": 1, "name": "Carol", "profile": 1}
        handler, wfile = _make_handler("POST", "/api/calendar", body=body)
        handler.do_POST()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 400)
        self.assertEqual(payload["status"], "error")

    def test_post_calendar_invalid_occurrence_returns_400(self):
        """POST /api/calendar with occurrence=0 returns 400."""
        body = {"day_of_week": "Tuesday", "occurrence": 0, "slot": 1, "name": "Dave", "profile": 1}
        handler, wfile = _make_handler("POST", "/api/calendar", body=body)
        handler.do_POST()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 400)
        self.assertEqual(payload["status"], "error")

    def test_post_calendar_invalid_slot_returns_400(self):
        """POST /api/calendar with slot=3 returns 400."""
        body = {"day_of_week": "Tuesday", "occurrence": 1, "slot": 3, "name": "Eve", "profile": 1}
        handler, wfile = _make_handler("POST", "/api/calendar", body=body)
        handler.do_POST()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 400)
        self.assertEqual(payload["status"], "error")

    def test_post_calendar_clear_entry(self):
        """POST /api/calendar with an empty name clears the stored entry."""
        body_save = {
            "day_of_week": "Wednesday",
            "occurrence": 2,
            "slot": 1,
            "name": "Frank",
            "profile": 1,
        }
        handler, _ = _make_handler("POST", "/api/calendar", body=body_save)
        handler.do_POST()

        body_clear = {
            "day_of_week": "Wednesday",
            "occurrence": 2,
            "slot": 1,
            "name": "",
            "profile": 1,
        }
        handler2, wfile2 = _make_handler("POST", "/api/calendar", body=body_clear)
        handler2.do_POST()
        status, payload = _parse_response(wfile2)
        self.assertEqual(status, 200)
        self.assertEqual(payload["saved"]["name"], "")

    def test_post_calendar_missing_user_id_returns_401(self):
        """POST /api/calendar without X-User-Id returns 401."""
        body = {"day_of_week": "Tuesday", "occurrence": 1, "slot": 1, "name": "Grace", "profile": 1}
        handler, wfile = _make_handler(
            "POST", "/api/calendar", body=body, headers={"X-User-Id": ""}
        )
        handler.do_POST()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 401)
        self.assertEqual(payload["status"], "error")

    def test_post_unknown_path_returns_404(self):
        """POST on an unknown path returns 404."""
        handler, wfile = _make_handler("POST", "/api/unknown")
        handler.do_POST()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 404)
        self.assertEqual(payload["status"], "error")


class TestCalendarAPISettings(unittest.TestCase):
    """Tests for GET and POST /api/settings."""

    def setUp(self):
        self._fd, self._tmp = tempfile.mkstemp(suffix=".json")
        os.close(self._fd)
        CalendarHandler.STORE = JsonFileStore(self._tmp)
        CalendarHandler.LOGGED_USER_IDS.clear()

    def tearDown(self):
        for path in (self._tmp, self._tmp.replace(".json", "_settings.json")):
            if os.path.exists(path):
                os.unlink(path)

    def test_get_settings_returns_ok(self):
        """GET /api/settings returns 200 with a settings dict."""
        handler, wfile = _make_handler("GET", "/api/settings")
        handler.do_GET()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("settings", payload)

    def test_post_settings_saves_ward(self):
        """POST /api/settings persists the ward field."""
        body = {"ward": "Sunridge"}
        handler, wfile = _make_handler("POST", "/api/settings", body=body)
        handler.do_POST()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 200)
        self.assertEqual(payload["settings"]["ward"], "Sunridge")

    def test_post_settings_clears_ward(self):
        """POST /api/settings with an empty ward removes the key."""
        body_save = {"ward": "Lakeside"}
        handler, _ = _make_handler("POST", "/api/settings", body=body_save)
        handler.do_POST()

        body_clear = {"ward": ""}
        handler2, wfile2 = _make_handler("POST", "/api/settings", body=body_clear)
        handler2.do_POST()
        status, payload = _parse_response(wfile2)
        self.assertEqual(status, 200)
        self.assertNotIn("ward", payload["settings"])

    def test_get_settings_missing_user_id_returns_401(self):
        """GET /api/settings without X-User-Id returns 401."""
        handler, wfile = _make_handler("GET", "/api/settings", headers={"X-User-Id": ""})
        handler.do_GET()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 401)
        self.assertEqual(payload["status"], "error")


class TestBuildCalendarPayload(unittest.TestCase):
    """Unit tests for build_calendar_payload helper."""

    def test_march_2025_has_correct_structure(self):
        """March 2025 payload contains 6 week rows with 7 cells each."""
        payload = build_calendar_payload(2025, 3, {})
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["month"], 3)
        self.assertEqual(len(payload["weeks"]), 6)
        for week in payload["weeks"]:
            self.assertEqual(len(week["cells"]), 7)

    def test_monday_cells_are_fixed_pday(self):
        """Monday cells always show PDAY and are not editable."""
        payload = build_calendar_payload(2025, 3, {})
        for week in payload["weeks"]:
            monday = next(c for c in week["cells"] if c["day_of_week"] == "Monday")
            self.assertEqual(monday["name"], "PDAY")
            self.assertFalse(monday["editable"])

    def test_stored_entry_appears_in_payload(self):
        """An entry saved to the store is reflected in the calendar payload."""
        entries = {"1:Tuesday:1": "Helen"}
        payload = build_calendar_payload(2025, 3, entries)
        first_tuesday = next(
            c
            for week in payload["weeks"]
            for c in week["cells"]
            if c["day_of_week"] == "Tuesday" and c["occurrence"] == 1
        )
        self.assertEqual(first_tuesday["names"]["first"], "Helen")


if __name__ == "__main__":
    unittest.main()
