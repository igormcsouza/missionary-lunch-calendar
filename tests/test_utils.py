"""Tests for calendar utility functions."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from core.utils import (  # noqa: E402  # pylint: disable=wrong-import-position
    DAYS,
    MAX_DISPLAY_WEEKS,
    MAX_OCCURRENCES,
    MAX_SLOTS,
    build_calendar_payload,
    build_day_lookup,
    get_cell_names,
)


class TestGetCellNames(unittest.TestCase):
    """Tests for get_cell_names utility."""

    def test_no_occurrence_returns_empty(self):
        """get_cell_names with no occurrence returns empty strings."""
        result = get_cell_names({}, None, "Tuesday")
        self.assertEqual(result, {"first": "", "second": ""})

    def test_returns_slot_values(self):
        """get_cell_names returns first and second slot for a given cell."""
        entries = {"1:Tuesday:1": "Alice", "1:Tuesday:2": "Bob"}
        result = get_cell_names(entries, 1, "Tuesday")
        self.assertEqual(result["first"], "Alice")
        self.assertEqual(result["second"], "Bob")

    def test_backward_compat_legacy_key(self):
        """get_cell_names falls back to bare legacy key when slot keys are absent."""
        entries = {"1:Tuesday": "LegacyName"}
        result = get_cell_names(entries, 1, "Tuesday")
        self.assertEqual(result["first"], "LegacyName")
        self.assertEqual(result["second"], "")

    def test_missing_entry_returns_empty_strings(self):
        """get_cell_names returns empty strings when no entry exists for the cell."""
        result = get_cell_names({}, 1, "Tuesday")
        self.assertEqual(result, {"first": "", "second": ""})


class TestBuildDayLookup(unittest.TestCase):
    """Tests for build_day_lookup utility."""

    def test_march_2025_starts_on_saturday(self):
        """1 March 2025 is a Saturday (occurrence 1)."""
        lookup = build_day_lookup(2025, 3)
        entry = lookup.get((1, "Saturday"))
        self.assertIsNotNone(entry)
        self.assertEqual(entry["day_number"], 1)
        self.assertEqual(entry["occurrence"], 1)

    def test_non_existent_day_not_in_lookup(self):
        """Days that don't exist in the month are absent from the lookup."""
        lookup = build_day_lookup(2025, 3)
        # Week 1 Monday doesn't exist (March starts on Saturday).
        self.assertIsNone(lookup.get((1, "Monday")))


class TestBuildCalendarPayload(unittest.TestCase):
    """Tests for build_calendar_payload utility."""

    def test_march_2025_has_correct_structure(self):
        """March 2025 payload contains 6 week rows with 7 cells each."""
        payload = build_calendar_payload(2025, 3, {})
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["month"], 3)
        self.assertEqual(payload["year"], 2025)
        self.assertEqual(len(payload["weeks"]), MAX_DISPLAY_WEEKS)
        for week in payload["weeks"]:
            self.assertEqual(len(week["cells"]), len(DAYS))

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

    def test_empty_entries_returns_empty_names(self):
        """Cells with no entry have empty name strings."""
        payload = build_calendar_payload(2025, 3, {})
        tuesday = next(
            c
            for week in payload["weeks"]
            for c in week["cells"]
            if c["day_of_week"] == "Tuesday" and c["occurrence"] == 1
        )
        self.assertEqual(tuesday["name"], "")
        self.assertEqual(tuesday["names"], {"first": "", "second": ""})


class TestConstants(unittest.TestCase):
    """Tests for module-level constants."""

    def test_days_has_seven_entries(self):
        """DAYS contains exactly 7 day names starting with Monday."""
        self.assertEqual(len(DAYS), 7)
        self.assertEqual(DAYS[0], "Monday")
        self.assertEqual(DAYS[-1], "Sunday")

    def test_max_slots_is_two(self):
        """MAX_SLOTS is 2."""
        self.assertEqual(MAX_SLOTS, 2)

    def test_max_occurrences_is_five(self):
        """MAX_OCCURRENCES is 5."""
        self.assertEqual(MAX_OCCURRENCES, 5)


if __name__ == "__main__":
    unittest.main()
