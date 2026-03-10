"""Storage backends for the missionary lunch calendar application."""
import json
import os
from pathlib import Path


class JsonFileStore:
    """File-based JSON store for local/development use."""
    def __init__(self, data_file):
        self.path = Path.cwd() / data_file
        base, _, ext = data_file.rpartition(".")
        settings_file = f"{base}_settings.{ext}" if base else f"{data_file}_settings"
        self.settings_path = Path.cwd() / settings_file

    def _read_raw(self):
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(raw, dict):
            return {}
        return raw

    def _sanitize_entries(self, entries):
        if not isinstance(entries, dict):
            return {}
        clean = {}
        for key, value in entries.items():
            if isinstance(key, str) and isinstance(value, str):
                clean[key] = value
        return clean

    def _is_legacy_entries_shape(self, raw):
        return all(isinstance(k, str) and isinstance(v, str) for k, v in raw.items())

    def _sanitize_users_map(self, raw):
        users_map = {}
        for user_id, entries in raw.items():
            if not isinstance(user_id, str):
                continue
            users_map[user_id] = self._sanitize_entries(entries)
        return users_map

    def load_entries(self, user_id, profile=1):
        """Load and return the calendar entries dict for the given user ID and profile."""
        raw = self._read_raw()
        if not raw:
            return {}
        if self._is_legacy_entries_shape(raw):
            return self._sanitize_entries(raw) if profile == 1 else {}

        users_map = self._sanitize_users_map(raw)
        all_entries = users_map.get(user_id, {})
        if profile == 1:
            # Profile-1 entry keys always start with an occurrence digit (1–5).
            return {k: v for k, v in all_entries.items() if k[:1].isdigit()}
        prefix = f"p{profile}:"
        return {k[len(prefix):]: v for k, v in all_entries.items() if k.startswith(prefix)}

    def save_entries(self, user_id, entries, profile=1):
        """Persist the calendar entries dict for the given user ID and profile."""
        raw = self._read_raw()
        users_map = {}
        if raw and not self._is_legacy_entries_shape(raw):
            users_map = self._sanitize_users_map(raw)

        all_entries = users_map.get(user_id, {})
        clean = self._sanitize_entries(entries)
        if profile == 1:
            # Keep profile 2+ entries (keys that do not start with a digit), replace profile-1.
            other = {k: v for k, v in all_entries.items() if not k[:1].isdigit()}
            users_map[user_id] = {**other, **clean}
        else:
            prefix = f"p{profile}:"
            other = {k: v for k, v in all_entries.items() if not k.startswith(prefix)}
            users_map[user_id] = {**other, **{f"{prefix}{k}": v for k, v in clean.items()}}
        self.path.write_text(json.dumps(users_map, indent=2), encoding="utf-8")

    def load_settings(self, user_id):
        """Load and return the settings dict for the given user ID."""
        if not self.settings_path.exists():
            return {}
        try:
            raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(raw, dict):
            return {}
        return self._sanitize_entries(raw.get(user_id, {}))

    def save_settings(self, user_id, settings):
        """Persist the settings dict for the given user ID."""
        existing = {}
        if self.settings_path.exists():
            try:
                raw = json.loads(self.settings_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    existing = raw
            except json.JSONDecodeError:
                pass
        existing[user_id] = self._sanitize_entries(settings)
        self.settings_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


class FirestoreStore:
    """Cloud Firestore-backed store for production use."""

    def __init__(self):
        try:
            from google.cloud import firestore  # pylint: disable=import-outside-toplevel
            from google.oauth2 import service_account  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise RuntimeError(
                "google-cloud-firestore is required for non-dev mode. "
                "Install dependencies and configure Google credentials."
            ) from exc

        self._firestore = firestore
        self._service_account = service_account
        self._collection_name = os.environ.get("FIRESTORE_COLLECTION", "calendar_entries")
        self._client = self._build_client()

    def _build_client(self):
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        credentials_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip()
        if (
            (credentials_json.startswith("'") and credentials_json.endswith("'"))
            or (credentials_json.startswith('"') and credentials_json.endswith('"'))
        ):
            credentials_json = credentials_json[1:-1]

        if credentials_json:
            try:
                service_account_info = json.loads(credentials_json)
            except json.JSONDecodeError as exc:
                raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS_JSON is not valid JSON") from exc

            credentials = self._service_account.Credentials.from_service_account_info(
                service_account_info
            )
            resolved_project_id = project_id or service_account_info.get("project_id")
            return self._firestore.Client(project=resolved_project_id, credentials=credentials)

        return self._firestore.Client(project=project_id)

    def _sanitize_entries(self, entries):
        if not isinstance(entries, dict):
            return {}
        clean = {}
        for key, value in entries.items():
            if isinstance(key, str) and isinstance(value, str):
                clean[key] = value
        return clean

    def _doc_ref(self, user_id):
        return self._client.collection(self._collection_name).document(user_id)

    def _entries_field(self, profile):
        """Return the Firestore document field name for the given profile."""
        return "entries" if profile == 1 else f"entries_{profile}"

    def load_entries(self, user_id, profile=1):
        """Load and return the calendar entries dict for the given user ID and profile."""
        snapshot = self._doc_ref(user_id).get()
        if not snapshot.exists:
            return {}
        payload = snapshot.to_dict() or {}
        entries = payload.get(self._entries_field(profile), {})
        return self._sanitize_entries(entries)

    def save_entries(self, user_id, entries, profile=1):
        """Persist the calendar entries dict for the given user ID and profile."""
        clean_entries = self._sanitize_entries(entries)
        field = self._entries_field(profile)
        # merge=[field] resets the entire field to the provided value instead of
        # deep-merging, so removed or cleared entries are actually deleted.
        self._doc_ref(user_id).set({field: clean_entries}, merge=[field])

    def load_settings(self, user_id):
        """Load and return the settings dict for the given user ID."""
        snapshot = self._doc_ref(user_id).get()
        if not snapshot.exists:
            return {}
        payload = snapshot.to_dict() or {}
        settings = payload.get("settings", {})
        return self._sanitize_entries(settings)

    def save_settings(self, user_id, settings):
        """Persist the settings dict for the given user ID."""
        # merge=["settings"] resets the field to the provided value instead of deep-merging.
        clean = self._sanitize_entries(settings)
        self._doc_ref(user_id).set({"settings": clean}, merge=["settings"])


def create_store(dev=False, data_file="calendar_data.json"):
    """Create and return the appropriate store backend based on the dev flag."""
    if dev:
        return JsonFileStore(data_file)
    return FirestoreStore()
