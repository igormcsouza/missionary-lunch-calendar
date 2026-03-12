"""HTTP server for the missionary lunch calendar application."""
import argparse
import logging
from http.server import HTTPServer

from core.logger import LOGGER
from core.store import create_store
from handlers.calendar_handler import CalendarHandler
from settings import DATA_FILE, DEFAULT_HOST, DEFAULT_PORT


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
    server = HTTPServer((args.host, args.port), CalendarHandler)
    LOGGER.info("Running at http://%s:%s", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
