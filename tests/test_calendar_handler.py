"""Tests for CalendarHandler HTTP endpoints (calendar and settings APIs)."""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from core.store import JsonFileStore  # noqa: E402  # pylint: disable=wrong-import-position
from handlers.calendar_handler import CalendarHandler  # noqa: E402  # pylint: disable=wrong-import-position


def _make_handler(method, path, body=None, headers=None):
    """Return a CalendarHandler instance wired to in-memory streams."""
    raw_headers = {"X-User-Id": "testuser"}
    if headers:
        raw_headers.update(headers)

    body_bytes = json.dumps(body).encode() if body else b""
    if body_bytes:
        raw_headers["Content-Length"] = str(len(body_bytes))

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


class TestCalendarHandlerGetCalendar(unittest.TestCase):
    """Tests for GET /api/calendar."""

    def setUp(self):
        self._fd, self._tmp = tempfile.mkstemp(suffix=".json")
        os.close(self._fd)
        CalendarHandler.STORE = JsonFileStore(self._tmp)
        CalendarHandler.LOGGED_USER_IDS.clear()

    def tearDown(self):
        if os.path.exists(self._tmp):
            os.unlink(self._tmp)

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

    def test_get_config_returns_dev_false_by_default(self):
        """GET /api/config returns dev=False when DEV is not set."""
        CalendarHandler.DEV = False
        handler, wfile = _make_handler("GET", "/api/config")
        handler.do_GET()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 200)
        self.assertIs(payload["dev"], False)

    def test_get_config_returns_dev_true_when_set(self):
        """GET /api/config returns dev=True when DEV is set to True."""
        CalendarHandler.DEV = True
        handler, wfile = _make_handler("GET", "/api/config")
        handler.do_GET()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 200)
        self.assertIs(payload["dev"], True)
        CalendarHandler.DEV = False  # restore


class TestCalendarHandlerPostCalendar(unittest.TestCase):
    """Tests for POST /api/calendar."""

    def setUp(self):
        self._fd, self._tmp = tempfile.mkstemp(suffix=".json")
        os.close(self._fd)
        CalendarHandler.STORE = JsonFileStore(self._tmp)
        CalendarHandler.LOGGED_USER_IDS.clear()

    def tearDown(self):
        if os.path.exists(self._tmp):
            os.unlink(self._tmp)

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


class TestCalendarHandlerGetSettings(unittest.TestCase):
    """Tests for GET /api/settings via CalendarHandler."""

    def setUp(self):
        self._fd, self._tmp = tempfile.mkstemp(suffix=".json")
        os.close(self._fd)
        CalendarHandler.STORE = JsonFileStore(self._tmp)
        CalendarHandler.LOGGED_USER_IDS.clear()

    def tearDown(self):
        if os.path.exists(self._tmp):
            os.unlink(self._tmp)

    def test_returns_empty_settings_for_new_user(self):
        """GET /api/settings returns an empty dict for a user with no stored settings."""
        handler, wfile = _make_handler("GET", "/api/settings")
        handler.do_GET()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["settings"], {})

    def test_returns_stored_settings(self):
        """GET /api/settings returns previously saved settings."""
        CalendarHandler.STORE.save_settings("testuser", {"ward": "Westside"})
        handler, wfile = _make_handler("GET", "/api/settings")
        handler.do_GET()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 200)
        self.assertEqual(payload["settings"]["ward"], "Westside")

    def test_missing_user_id_returns_401(self):
        """GET /api/settings without X-User-Id returns 401."""
        handler, wfile = _make_handler("GET", "/api/settings", headers={"X-User-Id": ""})
        handler.do_GET()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 401)
        self.assertEqual(payload["status"], "error")


class TestCalendarHandlerPostSettings(unittest.TestCase):
    """Tests for POST /api/settings via CalendarHandler."""

    def setUp(self):
        self._fd, self._tmp = tempfile.mkstemp(suffix=".json")
        os.close(self._fd)
        CalendarHandler.STORE = JsonFileStore(self._tmp)
        CalendarHandler.LOGGED_USER_IDS.clear()

    def tearDown(self):
        if os.path.exists(self._tmp):
            os.unlink(self._tmp)

    def test_saves_ward(self):
        """POST /api/settings persists the ward and returns it."""
        handler, wfile = _make_handler("POST", "/api/settings", body={"ward": "Northfield"})
        handler.do_POST()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 200)
        self.assertEqual(payload["settings"]["ward"], "Northfield")

    def test_clears_ward_with_empty_string(self):
        """POST /api/settings with an empty ward removes the key."""
        CalendarHandler.STORE.save_settings("testuser", {"ward": "Northfield"})
        handler, wfile = _make_handler("POST", "/api/settings", body={"ward": ""})
        handler.do_POST()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 200)
        self.assertNotIn("ward", payload["settings"])

    def test_saves_profile_title(self):
        """POST /api/settings saves a per-profile title field."""
        handler, wfile = _make_handler(
            "POST", "/api/settings", body={"slot_1_title": "Elders"}
        )
        handler.do_POST()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 200)
        self.assertEqual(payload["settings"]["slot_1_title"], "Elders")

    def test_missing_user_id_returns_401(self):
        """POST /api/settings without X-User-Id returns 401."""
        handler, wfile = _make_handler(
            "POST", "/api/settings", body={"ward": "X"}, headers={"X-User-Id": ""}
        )
        handler.do_POST()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 401)
        self.assertEqual(payload["status"], "error")

    def test_invalid_json_returns_400(self):
        """POST /api/settings with invalid JSON returns 400."""
        handler, wfile = _make_handler("POST", "/api/settings")
        handler.rfile = io.BytesIO(b"notjson")
        handler.headers["Content-Length"] = "7"
        handler.do_POST()
        status, payload = _parse_response(wfile)
        self.assertEqual(status, 400)
        self.assertEqual(payload["status"], "error")


if __name__ == "__main__":
    unittest.main()
