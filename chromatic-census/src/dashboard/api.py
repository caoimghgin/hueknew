"""Dashboard JSON API endpoints.

All endpoints are read-only — they read status.json from disk and
query the SQLite results database.
"""

import json
import logging
import sqlite3
from pathlib import Path

from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# These are set by server.py at startup
STATUS_FILE = None
DB_PATH = None


def _read_status():
    """Read the current status.json file."""
    if STATUS_FILE is None or not Path(STATUS_FILE).exists():
        return {"state": "not_started"}
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Error reading status file: {e}")
        return {"state": "error", "message": str(e)}


def _query_db(query, params=(), limit=None):
    """Run a read-only query against the results database."""
    if DB_PATH is None or not Path(DB_PATH).exists():
        return []
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5)
        conn.row_factory = sqlite3.Row
        if limit:
            query += f" LIMIT {int(limit)}"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.warning(f"Database query error: {e}")
        return []


async def get_status(request):
    """Return current census status."""
    return JSONResponse(_read_status())


async def get_slices(request):
    """Return per-slice summary data for charts."""
    slices = _query_db("""
        SELECT s.slice_id, s.L_value, s.valid_points, s.seeds_found,
               s.density, s.duration_seconds, t.name as tier_name, t.delta_e
        FROM slices s
        JOIN thresholds t ON t.id = s.threshold_id
        ORDER BY s.slice_id, t.delta_e
    """)
    return JSONResponse(slices)


async def get_recent_seeds(request):
    """Return most recently discovered seeds (for 'color of the moment')."""
    seeds = _query_db("""
        SELECT s.L, s.a, s.b, s.hex_srgb, s.slice_id,
               t.name as tier_name, s.discovered_at
        FROM seeds s
        JOIN thresholds t ON t.id = s.threshold_id
        ORDER BY s.id DESC
    """, limit=20)
    return JSONResponse(seeds)


async def health_check(request):
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "service": "census"})
