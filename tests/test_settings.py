"""Tests for the settings module (global configuration constants)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from settings import (  # noqa: E402  # pylint: disable=wrong-import-position
    DATA_FILE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    MAX_APP_PROFILES,
)


class TestSettingsConstants(unittest.TestCase):
    """Tests for the configuration constants exported from settings.py."""

    def test_default_host(self):
        """DEFAULT_HOST is the all-interfaces bind address."""
        self.assertEqual(DEFAULT_HOST, "0.0.0.0")

    def test_default_port(self):
        """DEFAULT_PORT is a valid TCP port number."""
        self.assertIsInstance(DEFAULT_PORT, int)
        self.assertGreater(DEFAULT_PORT, 0)
        self.assertLessEqual(DEFAULT_PORT, 65535)

    def test_data_file_is_json(self):
        """DATA_FILE ends with .json."""
        self.assertTrue(DATA_FILE.endswith(".json"))

    def test_max_app_profiles_is_two(self):
        """MAX_APP_PROFILES is 2."""
        self.assertEqual(MAX_APP_PROFILES, 2)


if __name__ == "__main__":
    unittest.main()
