"""SQLite results database for storing census output.

Uses WAL mode for concurrent read access from the dashboard while
the engine writes. Batch inserts for performance.
"""

import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class ResultsDatabase:
    """SQLite database for census results."""

    def __init__(self, db_path):
        """
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), timeout=30)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self.init_schema()

    def init_schema(self):
        """Create tables if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS thresholds (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                delta_e REAL NOT NULL,
                description TEXT
            );

            CREATE TABLE IF NOT EXISTS seeds (
                id INTEGER PRIMARY KEY,
                L REAL NOT NULL,
                a REAL NOT NULL,
                b REAL NOT NULL,
                hex_srgb TEXT,
                slice_id INTEGER,
                threshold_id INTEGER REFERENCES thresholds(id),
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_seeds_threshold ON seeds(threshold_id);
            CREATE INDEX IF NOT EXISTS idx_seeds_slice ON seeds(slice_id, threshold_id);
            CREATE INDEX IF NOT EXISTS idx_seeds_discovered ON seeds(discovered_at DESC);

            CREATE TABLE IF NOT EXISTS slices (
                slice_id INTEGER,
                threshold_id INTEGER REFERENCES thresholds(id),
                L_value REAL,
                valid_points INTEGER,
                seeds_found INTEGER,
                density REAL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                PRIMARY KEY (slice_id, threshold_id)
            );

            CREATE TABLE IF NOT EXISTS run_log (
                id INTEGER PRIMARY KEY,
                event TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            );
        """)
        self._conn.commit()

    def ensure_thresholds(self, thresholds):
        """Insert threshold definitions if not already present.

        Args:
            thresholds: List of dicts with 'name', 'delta_e', 'description'.
        """
        for t in thresholds:
            self._conn.execute(
                "INSERT OR IGNORE INTO thresholds (name, delta_e, description) VALUES (?, ?, ?)",
                (t["name"], t["delta_e"], t.get("description", "")),
            )
        self._conn.commit()

    def get_threshold_id(self, name):
        """Get the threshold ID for a given tier name."""
        row = self._conn.execute(
            "SELECT id FROM thresholds WHERE name = ?", (name,)
        ).fetchone()
        return row["id"] if row else None

    def insert_seeds_batch(self, seeds):
        """Insert a batch of seed records.

        Args:
            seeds: List of dicts with keys: L, a, b, hex, slice_id, tier.
        """
        if not seeds:
            return

        rows = []
        for s in seeds:
            tid = self.get_threshold_id(s["tier"])
            if tid is None:
                continue
            rows.append((s["L"], s["a"], s["b"], s.get("hex", ""), s["slice_id"], tid))

        self._conn.executemany(
            "INSERT INTO seeds (L, a, b, hex_srgb, slice_id, threshold_id) VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        self._conn.commit()

    def complete_slice(self, slice_id, L_value, valid_points, seeds_per_tier, duration_seconds):
        """Record completion of a slice across all tiers.

        Args:
            slice_id: Index of the completed slice.
            L_value: The L* value of this slice.
            valid_points: Number of in-gamut points in the slice.
            seeds_per_tier: Dict of tier_name -> seed count.
            duration_seconds: Time taken to process the slice.
        """
        now = datetime.now(timezone.utc).isoformat()
        for tier_name, seed_count in seeds_per_tier.items():
            tid = self.get_threshold_id(tier_name)
            if tid is None:
                continue
            density = seed_count / valid_points if valid_points > 0 else 0.0
            self._conn.execute(
                """INSERT OR REPLACE INTO slices
                   (slice_id, threshold_id, L_value, valid_points, seeds_found, density,
                    completed_at, duration_seconds)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (slice_id, tid, L_value, valid_points, seed_count, density, now, duration_seconds),
            )
        self._conn.commit()

    def log_event(self, event, details=None):
        """Write an entry to the run log.

        Args:
            event: Event type string (e.g. 'start', 'checkpoint', 'finish').
            details: Optional dict of additional details.
        """
        self._conn.execute(
            "INSERT INTO run_log (event, details) VALUES (?, ?)",
            (event, json.dumps(details, default=str) if details else None),
        )
        self._conn.commit()

    def get_tier_counts(self):
        """Get current total seed counts per tier."""
        rows = self._conn.execute("""
            SELECT t.name, COUNT(s.id) as count
            FROM thresholds t
            LEFT JOIN seeds s ON s.threshold_id = t.id
            GROUP BY t.name
        """).fetchall()
        return {row["name"]: row["count"] for row in rows}

    def get_slice_summary(self):
        """Get per-slice summary data for all tiers."""
        rows = self._conn.execute("""
            SELECT s.slice_id, s.L_value, s.valid_points, s.seeds_found,
                   s.density, s.duration_seconds, t.name as tier_name, t.delta_e
            FROM slices s
            JOIN thresholds t ON t.id = s.threshold_id
            ORDER BY s.slice_id, t.delta_e
        """).fetchall()
        return [dict(row) for row in rows]

    def get_recent_seeds(self, limit=10):
        """Get the most recently discovered seeds across all tiers."""
        rows = self._conn.execute("""
            SELECT s.L, s.a, s.b, s.hex_srgb, s.slice_id,
                   t.name as tier_name, s.discovered_at
            FROM seeds s
            JOIN thresholds t ON t.id = s.threshold_id
            ORDER BY s.id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(row) for row in rows]

    def get_run_log(self, limit=50):
        """Get recent run log entries."""
        rows = self._conn.execute(
            "SELECT event, timestamp, details FROM run_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self):
        """Close the database connection."""
        self._conn.close()
