"""HTTP request handler extension for the Baptismal Plan feature."""
import re
from urllib.parse import urlparse

from core.logger import LOGGER
from handlers.calendar_handler import CalendarHandler

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

_BP_PREFIX = "/api/baptismal-plans"


def _valid_plan_id(plan_id):
    """Return True when plan_id looks like a lower-case UUID."""
    return bool(_UUID_RE.match(plan_id))


class BaptismalPlanHandler(CalendarHandler):
    """Extends CalendarHandler with Baptismal Plan API routes."""

    PLAN_STORE = None

    # ── routing ──────────────────────────────────────────────────────────────

    def do_GET(self):  # pylint: disable=invalid-name
        """Handle GET requests, delegating baptismal-plan routes."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == _BP_PREFIX:
            self._handle_list_plans()
            return

        if path.startswith(_BP_PREFIX + "/"):
            plan_id = path[len(_BP_PREFIX) + 1:]
            if _valid_plan_id(plan_id):
                self._handle_get_plan(plan_id)
            else:
                self.send_json(400, {"status": "error", "error": "Invalid plan ID"})
            return

        super().do_GET()

    def do_POST(self):  # pylint: disable=invalid-name
        """Handle POST requests, delegating baptismal-plan routes."""
        parsed = urlparse(self.path)
        if parsed.path == _BP_PREFIX:
            self._handle_create_plan()
            return
        super().do_POST()

    def do_PUT(self):  # pylint: disable=invalid-name
        """Handle PUT requests for baptismal-plan updates."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith(_BP_PREFIX + "/"):
            plan_id = path[len(_BP_PREFIX) + 1:]
            if _valid_plan_id(plan_id):
                self._handle_update_plan(plan_id)
            else:
                self.send_json(400, {"status": "error", "error": "Invalid plan ID"})
            return

        self.send_json(404, {"status": "error", "error": "Not found"})

    # ── handlers ─────────────────────────────────────────────────────────────

    def _handle_list_plans(self):
        """Handle GET /api/baptismal-plans."""
        user_id = self.get_user_id()
        if not user_id:
            self.send_json(401, {"status": "error", "error": "User not authenticated"})
            return
        plans = self.PLAN_STORE.list_plans(user_id)
        LOGGER.info("GET /api/baptismal-plans user_id=%s count=%d", user_id, len(plans))
        self.send_json(200, {"status": "ok", "plans": plans})

    def _handle_get_plan(self, plan_id):
        """Handle GET /api/baptismal-plans/{planId}."""
        user_id = self.get_user_id()
        if not user_id:
            self.send_json(401, {"status": "error", "error": "User not authenticated"})
            return
        plan = self.PLAN_STORE.get_plan(user_id, plan_id)
        if plan is None:
            self.send_json(404, {"status": "error", "error": "Plan not found"})
            return
        LOGGER.info("GET /api/baptismal-plans/%s user_id=%s", plan_id, user_id)
        self.send_json(200, {"status": "ok", "plan": plan})

    def _handle_create_plan(self):
        """Handle POST /api/baptismal-plans."""
        user_id = self.get_user_id()
        if not user_id:
            self.send_json(401, {"status": "error", "error": "User not authenticated"})
            return
        plan_id, plan = self.PLAN_STORE.create_plan(user_id)
        LOGGER.info("POST /api/baptismal-plans user_id=%s plan_id=%s", user_id, plan_id)
        self.send_json(201, {"status": "ok", "plan": plan})

    def _handle_update_plan(self, plan_id):
        """Handle PUT /api/baptismal-plans/{planId}."""
        user_id, data = self._require_authenticated_json()
        if user_id is None:
            return

        plan = self.PLAN_STORE.update_plan(user_id, plan_id, data)
        if plan is None:
            self.send_json(404, {"status": "error", "error": "Plan not found"})
            return

        LOGGER.info("PUT /api/baptismal-plans/%s user_id=%s", plan_id, user_id)
        self.send_json(200, {"status": "ok", "plan": plan})
