"""Tests for the storage backends."""
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(__file__))
from store import JsonFileStore, FirestoreStore  # noqa: E402  # pylint: disable=wrong-import-position


class TestJsonFileStoreClearEntry(unittest.TestCase):
    """Tests that JsonFileStore correctly persists entry deletions."""

    def setUp(self):
        fd, self.tmp = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        self.store = JsonFileStore(self.tmp)

    def tearDown(self):
        for path in (self.tmp, self.tmp.replace(".json", "_settings.json")):
            if os.path.exists(path):
                os.unlink(path)

    def test_clear_only_entry_profile1(self):
        """Clearing the last entry for profile 1 removes it from storage."""
        self.store.save_entries("user1", {"1:Friday:1": "John"}, profile=1)
        entries = self.store.load_entries("user1", profile=1)
        self.assertEqual(entries, {"1:Friday:1": "John"})

        # Simulate app.py clearing the entry.
        entries.pop("1:Friday:1", None)
        self.store.save_entries("user1", entries, profile=1)

        self.assertEqual(self.store.load_entries("user1", profile=1), {})

    def test_clear_one_of_two_entries_profile1(self):
        """Clearing one entry removes only that entry, leaving others intact."""
        self.store.save_entries(
            "user1",
            {"1:Friday:1": "John", "1:Tuesday:1": "Bob"},
            profile=1,
        )
        entries = self.store.load_entries("user1", profile=1)
        entries.pop("1:Friday:1", None)
        self.store.save_entries("user1", entries, profile=1)

        result = self.store.load_entries("user1", profile=1)
        self.assertNotIn("1:Friday:1", result)
        self.assertEqual(result.get("1:Tuesday:1"), "Bob")

    def test_clear_entry_preserves_profile2(self):
        """Clearing a profile-1 entry does not affect profile-2 entries."""
        self.store.save_entries("user1", {"1:Friday:1": "John"}, profile=1)
        self.store.save_entries("user1", {"1:Saturday:1": "Anna"}, profile=2)

        entries = self.store.load_entries("user1", profile=1)
        entries.pop("1:Friday:1", None)
        self.store.save_entries("user1", entries, profile=1)

        self.assertEqual(self.store.load_entries("user1", profile=1), {})
        self.assertEqual(
            self.store.load_entries("user1", profile=2), {"1:Saturday:1": "Anna"}
        )

    def test_clear_settings(self):
        """Clearing all settings removes them from storage."""
        self.store.save_settings("user1", {"ward": "TestWard"})
        settings = self.store.load_settings("user1")
        settings.pop("ward", None)
        self.store.save_settings("user1", settings)
        self.assertEqual(self.store.load_settings("user1"), {})


class TestFirestoreStoreClearEntry(unittest.TestCase):
    """Tests that FirestoreStore calls Firestore with field-path merge so that
    entries are fully replaced (not deep-merged) when emptying a field."""

    def _make_store(self):
        """Create a FirestoreStore with a fully-mocked Firestore client."""
        with patch("store.FirestoreStore._build_client") as mock_build:
            mock_client = MagicMock()
            mock_build.return_value = mock_client
            # Patch the imports inside __init__
            firestore_mod = MagicMock()
            sa_mod = MagicMock()
            with patch.dict(
                "sys.modules",
                {
                    "google.cloud": MagicMock(),
                    "google.cloud.firestore": firestore_mod,
                    "google.oauth2": MagicMock(),
                    "google.oauth2.service_account": sa_mod,
                },
            ):
                store = FirestoreStore.__new__(FirestoreStore)
                store._firestore = firestore_mod  # pylint: disable=protected-access
                store._service_account = sa_mod  # pylint: disable=protected-access
                store._collection_name = "calendar_entries"  # pylint: disable=protected-access
                store._client = mock_client  # pylint: disable=protected-access
        return store, mock_client

    def _doc_ref(self, mock_client):
        return mock_client.collection.return_value.document.return_value

    def test_save_entries_uses_field_path_merge_not_bool_merge(self):
        """save_entries must use merge=[field] so that the field is replaced,
        not deep-merged.  merge=True would silently preserve deleted entries."""
        store, mock_client = self._make_store()
        doc_ref = self._doc_ref(mock_client)

        store.save_entries("user1", {"1:Friday:1": "John"}, profile=1)

        doc_ref.set.assert_called_once_with(
            {"entries": {"1:Friday:1": "John"}}, merge=["entries"]
        )

    def test_save_entries_empty_clears_field(self):
        """save_entries with an empty dict must pass merge=['entries'] so
        Firestore replaces (not merges) the field, actually clearing it."""
        store, mock_client = self._make_store()
        doc_ref = self._doc_ref(mock_client)

        store.save_entries("user1", {}, profile=1)

        doc_ref.set.assert_called_once_with({"entries": {}}, merge=["entries"])

    def test_save_entries_profile2_uses_field_path_merge(self):
        """save_entries for profile 2 uses the correct field name in the merge list."""
        store, mock_client = self._make_store()
        doc_ref = self._doc_ref(mock_client)

        store.save_entries("user1", {"1:Saturday:1": "Anna"}, profile=2)

        doc_ref.set.assert_called_once_with(
            {"entries_2": {"1:Saturday:1": "Anna"}}, merge=["entries_2"]
        )

    def test_save_settings_uses_field_path_merge(self):
        """save_settings must use merge=['settings'] so the settings field is
        replaced, not deep-merged."""
        store, mock_client = self._make_store()
        doc_ref = self._doc_ref(mock_client)

        store.save_settings("user1", {"ward": "TestWard"})

        doc_ref.set.assert_called_once_with(
            {"settings": {"ward": "TestWard"}}, merge=["settings"]
        )

    def test_save_settings_empty_clears_field(self):
        """save_settings with an empty dict must pass merge=['settings'] so the
        field is replaced (cleared) rather than deep-merged (no-op)."""
        store, mock_client = self._make_store()
        doc_ref = self._doc_ref(mock_client)

        store.save_settings("user1", {})

        doc_ref.set.assert_called_once_with({"settings": {}}, merge=["settings"])


if __name__ == "__main__":
    unittest.main()
