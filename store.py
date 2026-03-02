import json
import os
from pathlib import Path


class JsonFileStore:
    def __init__(self, data_file):
        self.path = Path.cwd() / data_file

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

    def load_entries(self, user_id):
        raw = self._read_raw()
        if not raw:
            return {}
        if self._is_legacy_entries_shape(raw):
            return self._sanitize_entries(raw)

        users_map = self._sanitize_users_map(raw)
        return users_map.get(user_id, {})

    def save_entries(self, user_id, entries):
        raw = self._read_raw()
        users_map = {}
        if raw and not self._is_legacy_entries_shape(raw):
            users_map = self._sanitize_users_map(raw)

        users_map[user_id] = self._sanitize_entries(entries)
        self.path.write_text(json.dumps(users_map, indent=2), encoding="utf-8")


class FirestoreStore:
    def __init__(self):
        try:
            from google.cloud import firestore
            from google.oauth2 import service_account
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

            credentials = self._service_account.Credentials.from_service_account_info(service_account_info)
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

    def load_entries(self, user_id):
        snapshot = self._doc_ref(user_id).get()
        if not snapshot.exists:
            return {}
        payload = snapshot.to_dict() or {}
        entries = payload.get("entries", {})
        return self._sanitize_entries(entries)

    def save_entries(self, user_id, entries):
        clean_entries = self._sanitize_entries(entries)
        self._doc_ref(user_id).set({"entries": clean_entries}, merge=True)


def create_store(dev=False, data_file="calendar_data.json"):
    if dev:
        return JsonFileStore(data_file)
    return FirestoreStore()
