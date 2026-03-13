"""HTTP server for the missionary lunch calendar application."""
import argparse
import logging
from http.server import HTTPServer

from core.logger import LOGGER
from core.store import create_baptismal_plan_store, create_store
from handlers.baptismal_plan_handler import BaptismalPlanHandler
from handlers.calendar_handler import CalendarHandler
from settings import DATA_FILE, DEFAULT_HOST, DEFAULT_PORT


class AppHandler(BaptismalPlanHandler, CalendarHandler):
    """Combined HTTP handler routing both baptismal-plan and calendar API requests.

    Python's MRO (AppHandler → BaptismalPlanHandler → CalendarHandler → DefaultHandler)
    ensures that ``do_GET`` and ``do_POST`` in ``BaptismalPlanHandler`` are resolved first.
    When a route is not matched there, the cooperative ``super().do_GET()`` / ``super().do_POST()``
    call delegates to ``CalendarHandler``, which handles calendar and settings routes.
    """


def main():
    """Parse arguments, configure logging, and start the HTTP server."""
    parser = argparse.ArgumentParser(description="Run the missionary lunch calendar server.")
    parser.add_argument(
        "--host", default=DEFAULT_HOST,
        help=f"Host interface to bind (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})",
    )
    parser.add_argument("--dev", action="store_true", help="Enable development mode")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    CalendarHandler.STORE = create_store(
        dev=args.dev, data_file=DATA_FILE, collection="calendar_entries"
    )
    CalendarHandler.DEV = args.dev
    BaptismalPlanHandler.PLAN_STORE = create_baptismal_plan_store(
        dev=args.dev, data_file=DATA_FILE
    )
    server = HTTPServer((args.host, args.port), AppHandler)
    LOGGER.info("Running at http://%s:%s", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
