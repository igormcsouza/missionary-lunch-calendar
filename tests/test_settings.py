"""Tests for settings HTTP handler functions."""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from core.store import JsonFileStore  # noqa: E402  # pylint: disable=wrong-import-position
from settings import (  # noqa: E402  # pylint: disable=wrong-import-position
    MAX_APP_PROFILES,
    handle_get_settings,
    handle_post_settings,
)


def _make_mock_handler(user_id="testuser", body=None, store=None):
    """Build a minimal mock handler compatible with the settings functions."""
    body_bytes = json.dumps(body).encode() if body else b""
    headers = {"X-User-Id": user_id}
    if body_bytes:
        headers["Content-Length"] = str(len(body_bytes))

    wfile = io.BytesIO()

    class MockHandler:  # pylint: disable=too-few-public-methods
        """Minimal mock that satisfies the settings handler interface."""
        STORE = store

        def __init__(self):
            self.headers = headers
            self.rfile = io.BytesIO(body_bytes)
            self.wfile = wfile
            self._response = None

        def get_user_id(self):
            uid = self.headers.get("X-User-Id", "").strip()
            return uid if uid else None

        def send_json(self, status_code, payload):
            body_enc = json.dumps(payload).encode("utf-8")
            self.wfile.write(
                f"HTTP/1.1 {status_code}\r\nContent-Length: {len(body_enc)}\r\n\r\n".encode()
            )
            self.wfile.write(body_enc)

    return MockHandler(), wfile


def _parse_wfile(wfile):
    wfile.seek(0)
    raw = wfile.read().decode("utf-8")
    first_line = raw.split("\r\n")[0]
    status_code = int(first_line.split(" ")[1])
    body_start = raw.find("\r\n\r\n") + 4
    return status_code, json.loads(raw[body_start:])


class TestHandleGetSettings(unittest.TestCase):
    """Unit tests for handle_get_settings."""

    def setUp(self):
        self._fd, self._tmp = tempfile.mkstemp(suffix=".json")
        os.close(self._fd)
        self._store = JsonFileStore(self._tmp)

    def tearDown(self):
        for path in (self._tmp, self._tmp.replace(".json", "_settings.json")):
            if os.path.exists(path):
                os.unlink(path)

    def test_returns_empty_settings_for_new_user(self):
        """handle_get_settings returns an empty dict for a user with no stored settings."""
        handler, wfile = _make_mock_handler(store=self._store)
        handle_get_settings(handler)
        status, payload = _parse_wfile(wfile)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["settings"], {})

    def test_returns_stored_settings(self):
        """handle_get_settings returns previously saved settings."""
        self._store.save_settings("testuser", {"ward": "Westside"})
        handler, wfile = _make_mock_handler(store=self._store)
        handle_get_settings(handler)
        status, payload = _parse_wfile(wfile)
        self.assertEqual(status, 200)
        self.assertEqual(payload["settings"]["ward"], "Westside")

    def test_missing_user_id_returns_401(self):
        """handle_get_settings returns 401 when no user ID is present."""
        handler, wfile = _make_mock_handler(user_id="", store=self._store)
        handle_get_settings(handler)
        status, payload = _parse_wfile(wfile)
        self.assertEqual(status, 401)
        self.assertEqual(payload["status"], "error")


class TestHandlePostSettings(unittest.TestCase):
    """Unit tests for handle_post_settings."""

    def setUp(self):
        self._fd, self._tmp = tempfile.mkstemp(suffix=".json")
        os.close(self._fd)
        self._store = JsonFileStore(self._tmp)

    def tearDown(self):
        for path in (self._tmp, self._tmp.replace(".json", "_settings.json")):
            if os.path.exists(path):
                os.unlink(path)

    def test_saves_ward(self):
        """handle_post_settings persists the ward and returns it."""
        handler, wfile = _make_mock_handler(body={"ward": "Northfield"}, store=self._store)
        handle_post_settings(handler)
        status, payload = _parse_wfile(wfile)
        self.assertEqual(status, 200)
        self.assertEqual(payload["settings"]["ward"], "Northfield")

    def test_clears_ward_with_empty_string(self):
        """handle_post_settings removes the ward key when an empty string is sent."""
        self._store.save_settings("testuser", {"ward": "Northfield"})
        handler, wfile = _make_mock_handler(body={"ward": ""}, store=self._store)
        handle_post_settings(handler)
        status, payload = _parse_wfile(wfile)
        self.assertEqual(status, 200)
        self.assertNotIn("ward", payload["settings"])

    def test_saves_profile_title(self):
        """handle_post_settings saves a per-profile title field."""
        handler, wfile = _make_mock_handler(
            body={"slot_1_title": "Elders"}, store=self._store
        )
        handle_post_settings(handler)
        status, payload = _parse_wfile(wfile)
        self.assertEqual(status, 200)
        self.assertEqual(payload["settings"]["slot_1_title"], "Elders")

    def test_missing_user_id_returns_401(self):
        """handle_post_settings returns 401 when no user ID is present."""
        handler, wfile = _make_mock_handler(user_id="", body={"ward": "X"}, store=self._store)
        handle_post_settings(handler)
        status, payload = _parse_wfile(wfile)
        self.assertEqual(status, 401)
        self.assertEqual(payload["status"], "error")

    def test_invalid_json_returns_400(self):
        """handle_post_settings returns 400 for invalid JSON body."""
        # Override rfile with raw invalid bytes
        class BadHandler:  # pylint: disable=too-few-public-methods
            """Mock handler that returns invalid JSON from rfile."""
            STORE = self._store
            headers = {"X-User-Id": "testuser", "Content-Length": "5"}
            rfile = io.BytesIO(b"notjs")
            wfile = io.BytesIO()

            def get_user_id(self):
                return "testuser"

            def send_json(self, status_code, payload):
                body_enc = json.dumps(payload).encode("utf-8")
                self.wfile.write(
                    f"HTTP/1.1 {status_code}\r\nContent-Length: {len(body_enc)}\r\n\r\n".encode()
                )
                self.wfile.write(body_enc)

        h = BadHandler()
        handle_post_settings(h)
        h.wfile.seek(0)
        raw = h.wfile.read().decode()
        first_line = raw.split("\r\n")[0]
        status_code = int(first_line.split(" ")[1])
        self.assertEqual(status_code, 400)


class TestMaxAppProfiles(unittest.TestCase):
    """Tests for the MAX_APP_PROFILES constant in settings."""

    def test_max_app_profiles_is_two(self):
        """MAX_APP_PROFILES is 2."""
        self.assertEqual(MAX_APP_PROFILES, 2)


if __name__ == "__main__":
    unittest.main()
