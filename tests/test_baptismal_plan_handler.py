"""Tests for the BaptismalPlanHandler API routes."""
import json
import os
import sys
import unittest
from io import BytesIO
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from handlers.baptismal_plan_handler import BaptismalPlanHandler  # noqa: E402  # pylint: disable=wrong-import-position


def _make_handler(method, path, user_id=None, body=None):
    """Create a BaptismalPlanHandler with a fake request context."""
    mock_request = MagicMock()
    mock_request.makefile.return_value = BytesIO(b"")

    handler = BaptismalPlanHandler.__new__(BaptismalPlanHandler)
    handler.command = method
    handler.path = path
    handler.headers = {}
    if user_id:
        handler.headers["X-User-Id"] = user_id

    raw = b""
    if body is not None:
        raw = json.dumps(body).encode()
    handler.headers["Content-Length"] = str(len(raw))
    handler.rfile = BytesIO(raw)

    handler.response_code = None
    handler.response_body = None

    def fake_send_json(code, payload):
        handler.response_code = code
        handler.response_body = payload

    handler.send_json = fake_send_json

    def fake_get_user_id():
        return handler.headers.get("X-User-Id")

    handler.get_user_id = fake_get_user_id
    return handler


class TestBaptismalPlanHandlerListPlans(unittest.TestCase):
    """Tests for GET /api/baptismal-plans."""

    def setUp(self):
        self.mock_store = MagicMock()
        BaptismalPlanHandler.PLAN_STORE = self.mock_store

    def test_list_plans_returns_ok(self):
        """GET /api/baptismal-plans returns 200 with the list of plan summaries."""
        self.mock_store.list_plans.return_value = []
        handler = _make_handler("GET", "/api/baptismal-plans", user_id="uid1")
        handler.do_GET()
        self.assertEqual(handler.response_code, 200)
        self.assertEqual(handler.response_body["status"], "ok")
        self.assertEqual(handler.response_body["plans"], [])

    def test_list_plans_missing_user_returns_401(self):
        """GET /api/baptismal-plans without X-User-Id returns 401."""
        handler = _make_handler("GET", "/api/baptismal-plans")
        handler.do_GET()
        self.assertEqual(handler.response_code, 401)


class TestBaptismalPlanHandlerGetPlan(unittest.TestCase):
    """Tests for GET /api/baptismal-plans/{planId}."""

    def setUp(self):
        self.mock_store = MagicMock()
        BaptismalPlanHandler.PLAN_STORE = self.mock_store

    def test_get_plan_returns_plan(self):
        """GET /api/baptismal-plans/{id} returns the matching plan document."""
        plan_id = "8f778763-14f5-405e-9abe-fb885dac5ff4"
        self.mock_store.get_plan.return_value = {"id": plan_id, "status": "Draft"}
        handler = _make_handler("GET", f"/api/baptismal-plans/{plan_id}", user_id="uid1")
        handler.do_GET()
        self.assertEqual(handler.response_code, 200)
        self.assertEqual(handler.response_body["plan"]["id"], plan_id)

    def test_get_plan_not_found_returns_404(self):
        """GET /api/baptismal-plans/{id} returns 404 when the plan does not exist."""
        plan_id = "8f778763-14f5-405e-9abe-fb885dac5ff4"
        self.mock_store.get_plan.return_value = None
        handler = _make_handler("GET", f"/api/baptismal-plans/{plan_id}", user_id="uid1")
        handler.do_GET()
        self.assertEqual(handler.response_code, 404)

    def test_get_plan_invalid_id_returns_400(self):
        """GET /api/baptismal-plans/{id} returns 400 for a non-UUID plan ID."""
        handler = _make_handler("GET", "/api/baptismal-plans/not-a-uuid", user_id="uid1")
        handler.do_GET()
        self.assertEqual(handler.response_code, 400)

    def test_get_plan_missing_user_returns_401(self):
        """GET /api/baptismal-plans/{id} without X-User-Id returns 401."""
        plan_id = "8f778763-14f5-405e-9abe-fb885dac5ff4"
        handler = _make_handler("GET", f"/api/baptismal-plans/{plan_id}")
        handler.do_GET()
        self.assertEqual(handler.response_code, 401)


class TestBaptismalPlanHandlerCreatePlan(unittest.TestCase):
    """Tests for POST /api/baptismal-plans."""

    def setUp(self):
        self.mock_store = MagicMock()
        BaptismalPlanHandler.PLAN_STORE = self.mock_store

    def test_create_plan_returns_201(self):
        """POST /api/baptismal-plans creates a new plan and returns 201."""
        plan_id = "8f778763-14f5-405e-9abe-fb885dac5ff4"
        plan_data = {"id": plan_id, "status": "Draft"}
        self.mock_store.create_plan.return_value = (plan_id, plan_data)
        handler = _make_handler("POST", "/api/baptismal-plans", user_id="uid1", body={})
        handler.do_POST()
        self.assertEqual(handler.response_code, 201)
        self.assertEqual(handler.response_body["plan"]["id"], plan_id)

    def test_create_plan_missing_user_returns_401(self):
        """POST /api/baptismal-plans without X-User-Id returns 401."""
        handler = _make_handler("POST", "/api/baptismal-plans", body={})
        handler.do_POST()
        self.assertEqual(handler.response_code, 401)


class TestBaptismalPlanHandlerUpdatePlan(unittest.TestCase):
    """Tests for PUT /api/baptismal-plans/{planId}."""

    def setUp(self):
        self.mock_store = MagicMock()
        BaptismalPlanHandler.PLAN_STORE = self.mock_store

    def test_update_plan_returns_ok(self):
        """PUT /api/baptismal-plans/{id} persists changes and returns the updated plan."""
        plan_id = "8f778763-14f5-405e-9abe-fb885dac5ff4"
        updated_plan = {"id": plan_id, "status": "Scheduled", "serviceDate": "2026-03-23"}
        self.mock_store.update_plan.return_value = updated_plan
        handler = _make_handler(
            "PUT", f"/api/baptismal-plans/{plan_id}",
            user_id="uid1",
            body={"serviceDate": "2026-03-23", "status": "Scheduled"},
        )
        handler.do_PUT()
        self.assertEqual(handler.response_code, 200)
        self.assertEqual(handler.response_body["plan"]["status"], "Scheduled")

    def test_update_plan_not_found_returns_404(self):
        """PUT /api/baptismal-plans/{id} returns 404 when the plan does not exist."""
        plan_id = "8f778763-14f5-405e-9abe-fb885dac5ff4"
        self.mock_store.update_plan.return_value = None
        handler = _make_handler(
            "PUT", f"/api/baptismal-plans/{plan_id}", user_id="uid1", body={}
        )
        handler.do_PUT()
        self.assertEqual(handler.response_code, 404)

    def test_update_plan_invalid_id_returns_400(self):
        """PUT /api/baptismal-plans/{id} returns 400 for a non-UUID plan ID."""
        handler = _make_handler("PUT", "/api/baptismal-plans/bad-id", user_id="uid1", body={})
        handler.do_PUT()
        self.assertEqual(handler.response_code, 400)

    def test_update_plan_missing_user_returns_401(self):
        """PUT /api/baptismal-plans/{id} without X-User-Id returns 401."""
        plan_id = "8f778763-14f5-405e-9abe-fb885dac5ff4"
        handler = _make_handler("PUT", f"/api/baptismal-plans/{plan_id}", body={})
        handler.do_PUT()
        self.assertEqual(handler.response_code, 401)

    def test_update_plan_invalid_json_returns_400(self):
        """PUT /api/baptismal-plans/{id} with an invalid JSON body returns 400."""
        plan_id = "8f778763-14f5-405e-9abe-fb885dac5ff4"
        handler = _make_handler("PUT", f"/api/baptismal-plans/{plan_id}", user_id="uid1")
        # Override with invalid JSON body
        invalid_body = b"not json"
        handler.headers["Content-Length"] = str(len(invalid_body))
        handler.rfile = BytesIO(invalid_body)
        handler.do_PUT()
        self.assertEqual(handler.response_code, 400)

    def test_put_unknown_path_returns_404(self):
        """PUT on an unknown path returns 404."""
        handler = _make_handler("PUT", "/api/unknown-route", user_id="uid1")
        handler.do_PUT()
        self.assertEqual(handler.response_code, 404)
