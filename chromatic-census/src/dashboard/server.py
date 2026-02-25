"""Dashboard web server using Starlette + uvicorn.

Serves the HTML dashboard page and JSON API endpoints.
Follows the same pattern as Oracle and Chronicle.
"""

import logging

import uvicorn
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.routing import Route

from . import api
from .page import render_dashboard_html
from .jnd_audit_page import render_jnd_audit_html

logger = logging.getLogger(__name__)


async def dashboard_page(request):
    """Serve the main dashboard HTML page."""
    return HTMLResponse(render_dashboard_html())


async def jnd_audit_page(request):
    """Serve the JND Visual Audit HTML page."""
    return HTMLResponse(render_jnd_audit_html())


def create_app(status_file=None, db_path=None):
    """Create the Starlette application.

    Args:
        status_file: Path to status.json (read by API endpoints).
        db_path: Path to the SQLite results database.
    """
    # Configure API module with file paths
    api.STATUS_FILE = status_file
    api.DB_PATH = db_path

    app = Starlette(
        debug=False,
        routes=[
            Route("/", endpoint=dashboard_page),
            Route("/jnd-audit", endpoint=jnd_audit_page),
            Route("/health", endpoint=api.health_check),
            Route("/api/status", endpoint=api.get_status),
            Route("/api/slices", endpoint=api.get_slices),
            Route("/api/recent-seeds", endpoint=api.get_recent_seeds),
            Route("/api/jnd-audit/seed", endpoint=api.get_jnd_audit_seed),
            Route("/api/jnd-audit/neighbors", endpoint=api.get_jnd_audit_neighbors),
            Route("/api/jnd-audit/gaps", endpoint=api.get_jnd_audit_gaps),
        ],
    )

    return app


def run_dashboard(host="0.0.0.0", port=8084, status_file=None, db_path=None):
    """Run the dashboard server (blocking).

    Intended to be called from a daemon thread.

    Args:
        host: Bind address.
        port: Bind port.
        status_file: Path to status.json.
        db_path: Path to SQLite database.
    """
    app = create_app(status_file=status_file, db_path=db_path)
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    logger.info(f"Dashboard starting on http://{host}:{port}")
    server.run()
