"""Storage backends for the missionary lunch calendar application."""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BAPTISMAL_PROGRAM = [
    {"item": "Hino Inicial", "assignee": ""},
    {"item": "Oração Inicial", "assignee": ""},
    {"item": "Seleção Musical", "assignee": ""},
    {"item": "Testemunhos", "assignee": ""},
    {"item": "Hino Final", "assignee": ""},
    {"item": "Oração Final", "assignee": ""},
]


def _str_val(val, default=""):
    """Return a stripped string for simple text fields."""
    return str(val).strip() if isinstance(val, (str, int, float)) else default


def _sanitize_baptismal_plan(data):
    """Return a sanitized copy of a baptismal plan document."""
    if not isinstance(data, dict):
        return {}

    def _sanitize_candidate(candidate):
        if not isinstance(candidate, dict):
            return None
        return {
            "id": _str_val(candidate.get("id")),
            "fullName": _str_val(candidate.get("fullName")),
            "birthDate": _str_val(candidate.get("birthDate")),
            "candidateType": _str_val(candidate.get("candidateType")),
            "interviewCompleted": bool(candidate.get("interviewCompleted")),
        }

    def _sanitize_ordinance(ordinance):
        if not isinstance(ordinance, dict):
            return None
        return {
            "candidateId": _str_val(ordinance.get("candidateId")),
            "baptizerName": _str_val(ordinance.get("baptizerName")),
            "baptizerPriesthood": _str_val(ordinance.get("baptizerPriesthood")),
            "confirmationBy": _str_val(ordinance.get("confirmationBy")),
        }

    def _sanitize_witness(witness):
        if not isinstance(witness, dict):
            return None
        return {
            "candidateId": _str_val(witness.get("candidateId")),
            "witness1": _str_val(witness.get("witness1")),
            "witness2": _str_val(witness.get("witness2")),
        }

    def _sanitize_program_item(item):
        if not isinstance(item, dict):
            return None
        return {
            "item": _str_val(item.get("item")),
            "assignee": _str_val(item.get("assignee")),
        }

    def _sanitize_talk(talk):
        if not isinstance(talk, dict):
            return None
        return {
            "id": _str_val(talk.get("id")),
            "talkPerson": _str_val(talk.get("talkPerson")),
            "talkTheme": _str_val(talk.get("talkTheme")),
        }

    plan = {
        "serviceDate": _str_val(data.get("serviceDate")),
        "serviceTime": _str_val(data.get("serviceTime")),
        "ward": _str_val(data.get("ward")),
        "location": _str_val(data.get("location")),
        "conductingLeader": _str_val(data.get("conductingLeader")),
        "status": _str_val(data.get("status", "Draft")),
        "candidates": [],
        "ordinances": [],
        "witnesses": [],
        "program": [],
        "talks": [],
        "notes": _str_val(data.get("notes")),
    }
    for candidate in data.get("candidates", []):
        sanitized = _sanitize_candidate(candidate)
        if sanitized is not None:
            plan["candidates"].append(sanitized)
    for ordinance in data.get("ordinances", []):
        sanitized = _sanitize_ordinance(ordinance)
        if sanitized is not None:
            plan["ordinances"].append(sanitized)
    for witness in data.get("witnesses", []):
        sanitized = _sanitize_witness(witness)
        if sanitized is not None:
            plan["witnesses"].append(sanitized)
    for item in data.get("program", []):
        sanitized = _sanitize_program_item(item)
        if sanitized is not None:
            plan["program"].append(sanitized)
    for talk in data.get("talks", []):
        sanitized = _sanitize_talk(talk)
        if sanitized is not None:
            plan["talks"].append(sanitized)
    return plan


def _new_plan_skeleton():
    """Return a fresh baptismal plan dict with defaults."""
    return {
        "serviceDate": "",
        "serviceTime": "",
        "ward": "",
        "location": "",
        "conductingLeader": "",
        "status": "Draft",
        "candidates": [],
        "ordinances": [],
        "witnesses": [],
        "program": [dict(item) for item in DEFAULT_BAPTISMAL_PROGRAM],
        "talks": [],
        "notes": "",
    }


class JsonFileStore:
    """File-based JSON store for local/development use.

    Data is stored in a single JSON file using the same document schema as
    FirestoreStore so that the two backends remain interchangeable:

        {
          "<user_id>": {
            "entries":   { "<occurrence>:<day>:<slot>": "<name>", ... },
            "entries_2": { ... },
            "settings":  { "ward": "...", ... }
          }
        }
    """

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

    def _sanitize_settings(self, settings):
        """Return a sanitized copy of a settings dict, allowing string and int values."""
        if not isinstance(settings, dict):
            return {}
        clean = {}
        for key, value in settings.items():
            if isinstance(key, str) and isinstance(value, (str, int)):
                clean[key] = value
        return clean

    def _entries_field(self, profile):
        """Return the document field name for the given profile (mirrors FirestoreStore)."""
        return "entries" if profile == 1 else f"entries_{profile}"

    def _get_user_doc(self, raw, user_id):
        user_doc = raw.get(user_id, {})
        return user_doc if isinstance(user_doc, dict) else {}

    def load_entries(self, user_id, profile=1):
        """Load and return the calendar entries dict for the given user ID and profile."""
        raw = self._read_raw()
        user_doc = self._get_user_doc(raw, user_id)
        field = self._entries_field(profile)
        return self._sanitize_entries(user_doc.get(field, {}))

    def save_entries(self, user_id, entries, profile=1):
        """Persist the calendar entries dict for the given user ID and profile."""
        raw = self._read_raw()
        if not isinstance(raw.get(user_id), dict):
            raw[user_id] = {}
        field = self._entries_field(profile)
        raw[user_id][field] = self._sanitize_entries(entries)
        self.path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    def load_settings(self, user_id):
        """Load and return the settings dict for the given user ID."""
        raw = self._read_raw()
        user_doc = self._get_user_doc(raw, user_id)
        return self._sanitize_settings(user_doc.get("settings", {}))

    def save_settings(self, user_id, settings):
        """Persist the settings dict for the given user ID."""
        raw = self._read_raw()
        if not isinstance(raw.get(user_id), dict):
            raw[user_id] = {}
        raw[user_id]["settings"] = self._sanitize_settings(settings)
        self.path.write_text(json.dumps(raw, indent=2), encoding="utf-8")


class FirestoreStore:
    """Cloud Firestore-backed store for production use."""

    def __init__(self, collection):
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
        self._collection_name = collection
        self._client = self._build_client()

    def _build_client(self):
        project_id = "mission-leader-assistant"
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

    def _sanitize_settings(self, settings):
        """Return a sanitized copy of a settings dict, allowing string and int values."""
        if not isinstance(settings, dict):
            return {}
        clean = {}
        for key, value in settings.items():
            if isinstance(key, str) and isinstance(value, (str, int)):
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
        return self._sanitize_settings(settings)

    def save_settings(self, user_id, settings):
        """Persist the settings dict for the given user ID."""
        # merge=["settings"] resets the field to the provided value instead of deep-merging.
        clean = self._sanitize_settings(settings)
        self._doc_ref(user_id).set({"settings": clean}, merge=["settings"])


def create_store(dev=False, data_file="calendar_data.json", collection="calendar_entries"):
    """Create and return the appropriate store backend based on the dev flag."""
    if dev:
        return JsonFileStore(data_file)
    return FirestoreStore(collection)


class BaptismalPlanJsonStore:
    """File-based JSON store for baptismal plans (local/development use).

    Data is stored using the same document schema as BaptismalPlanFirestoreStore:

        {
          "<user_id>": {
            "plans": {
              "<plan_id>": { ...plan fields... }
            }
          }
        }
    """

    def __init__(self, data_file):
        base, _, ext = data_file.rpartition(".")
        if base:
            plan_file = f"{base}_baptismal_plans.{ext}"
        else:
            plan_file = f"{data_file}_baptismal_plans"
        self.path = Path.cwd() / plan_file

    def _read_raw(self):
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return raw if isinstance(raw, dict) else {}

    def _write_raw(self, data):
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _get_plans_map(self, raw, user_id):
        user_doc = raw.get(user_id, {})
        if not isinstance(user_doc, dict):
            return {}
        plans_map = user_doc.get("plans", {})
        return plans_map if isinstance(plans_map, dict) else {}

    def list_plans(self, user_id):
        """Return list of plan summaries ordered by serviceDate descending."""
        raw = self._read_raw()
        plans_map = self._get_plans_map(raw, user_id)
        summaries = []
        for plan_id, plan_data in plans_map.items():
            if not isinstance(plan_data, dict):
                continue
            candidates = plan_data.get("candidates", [])
            names = [c.get("fullName", "") for c in candidates if isinstance(c, dict)]
            summaries.append({
                "id": plan_id,
                "serviceDate": plan_data.get("serviceDate", ""),
                "candidates": names,
                "status": plan_data.get("status", "Draft"),
            })
        summaries.sort(key=lambda p: p.get("serviceDate", ""), reverse=True)
        return summaries

    def get_plan(self, user_id, plan_id):
        """Return full plan data or None if not found."""
        raw = self._read_raw()
        plan = self._get_plans_map(raw, user_id).get(plan_id)
        return plan if isinstance(plan, dict) else None

    def create_plan(self, user_id):
        """Create a new plan and return (plan_id, plan_data)."""
        raw = self._read_raw()
        if not isinstance(raw.get(user_id), dict):
            raw[user_id] = {}
        if not isinstance(raw[user_id].get("plans"), dict):
            raw[user_id]["plans"] = {}
        plan_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        plan = _new_plan_skeleton()
        plan["id"] = plan_id
        plan["createdAt"] = now
        plan["updatedAt"] = now
        raw[user_id]["plans"][plan_id] = plan
        self._write_raw(raw)
        return plan_id, plan

    def update_plan(self, user_id, plan_id, plan_data):
        """Update an existing plan. Returns updated plan or None if not found."""
        raw = self._read_raw()
        plans_map = self._get_plans_map(raw, user_id)
        existing = plans_map.get(plan_id)
        if not isinstance(existing, dict):
            return None
        now = datetime.now(timezone.utc).isoformat()
        plan = _sanitize_baptismal_plan(plan_data)
        plan["id"] = plan_id
        plan["createdAt"] = existing.get("createdAt", now)
        plan["updatedAt"] = now
        if not isinstance(raw.get(user_id), dict):
            raw[user_id] = {}
        if not isinstance(raw[user_id].get("plans"), dict):
            raw[user_id]["plans"] = {}
        raw[user_id]["plans"][plan_id] = plan
        self._write_raw(raw)
        return plan

    def delete_plan(self, user_id, plan_id):
        """Delete a plan. Returns True if deleted, False if not found."""
        raw = self._read_raw()
        plans_map = self._get_plans_map(raw, user_id)
        if plan_id not in plans_map:
            return False
        del plans_map[plan_id]
        if isinstance(raw.get(user_id), dict):
            raw[user_id]["plans"] = plans_map
        self._write_raw(raw)
        return True


class BaptismalPlanFirestoreStore:
    """Cloud Firestore-backed store for baptismal plans."""

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
        self._client = self._build_client()

    def _build_client(self):
        project_id = "mission-leader-assistant"
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
                raise RuntimeError(
                    "GOOGLE_APPLICATION_CREDENTIALS_JSON is not valid JSON"
                ) from exc
            credentials = self._service_account.Credentials.from_service_account_info(
                service_account_info
            )
            resolved_project_id = project_id or service_account_info.get("project_id")
            return self._firestore.Client(
                project=resolved_project_id, credentials=credentials
            )
        return self._firestore.Client(project=project_id)

    def _doc_ref(self, user_id):
        return self._client.collection("baptismal_plan_entries").document(user_id)

    def _read_plans_map(self, user_id):
        snapshot = self._doc_ref(user_id).get()
        if not snapshot.exists:
            return {}
        payload = snapshot.to_dict() or {}
        plans_map = payload.get("plans", {})
        return plans_map if isinstance(plans_map, dict) else {}

    def list_plans(self, user_id):
        """Return list of plan summaries ordered by serviceDate descending."""
        plans_map = self._read_plans_map(user_id)
        summaries = []
        for plan_id, plan_data in plans_map.items():
            if not isinstance(plan_data, dict):
                continue
            candidates = plan_data.get("candidates", [])
            names = [c.get("fullName", "") for c in candidates if isinstance(c, dict)]
            summaries.append({
                "id": plan_id,
                "serviceDate": plan_data.get("serviceDate", ""),
                "candidates": names,
                "status": plan_data.get("status", "Draft"),
            })
        summaries.sort(key=lambda p: p.get("serviceDate", ""), reverse=True)
        return summaries

    def get_plan(self, user_id, plan_id):
        """Return full plan data or None if not found."""
        plans_map = self._read_plans_map(user_id)
        plan = plans_map.get(plan_id)
        return plan if isinstance(plan, dict) else None

    def create_plan(self, user_id):
        """Create a new plan and return (plan_id, plan_data)."""
        plans_map = self._read_plans_map(user_id)
        plan_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        plan = _new_plan_skeleton()
        plan["id"] = plan_id
        plan["createdAt"] = now
        plan["updatedAt"] = now
        plans_map[plan_id] = plan
        self._doc_ref(user_id).set({"plans": plans_map}, merge=True)
        return plan_id, plan

    def update_plan(self, user_id, plan_id, plan_data):
        """Update an existing plan. Returns updated plan or None if not found."""
        plans_map = self._read_plans_map(user_id)
        existing = plans_map.get(plan_id)
        if not isinstance(existing, dict):
            return None
        now = datetime.now(timezone.utc).isoformat()
        plan = _sanitize_baptismal_plan(plan_data)
        plan["id"] = plan_id
        plan["createdAt"] = existing.get("createdAt", now)
        plan["updatedAt"] = now
        plans_map[plan_id] = plan
        self._doc_ref(user_id).set({"plans": plans_map}, merge=True)
        return plan

    def delete_plan(self, user_id, plan_id):
        """Delete a plan. Returns True if deleted, False if not found."""
        plans_map = self._read_plans_map(user_id)
        if plan_id not in plans_map:
            return False
        del plans_map[plan_id]
        self._doc_ref(user_id).set({"plans": plans_map})
        return True


def create_baptismal_plan_store(dev=False, data_file="calendar_data.json"):
    """Create and return the appropriate baptismal plan store backend."""
    if dev:
        return BaptismalPlanJsonStore(data_file)
    return BaptismalPlanFirestoreStore()
