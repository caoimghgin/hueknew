"""Periodic snapshot generation for hourly progress reports."""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class SnapshotGenerator:
    """Generates periodic progress snapshots."""

    def __init__(self, snapshot_dir, interval_seconds=3600):
        """
        Args:
            snapshot_dir: Directory for snapshot files.
            interval_seconds: Minimum seconds between snapshots.
        """
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.interval_seconds = interval_seconds
        self._last_snapshot_time = 0

    def should_generate(self):
        """Check if enough time has elapsed for a new snapshot."""
        return (time.time() - self._last_snapshot_time) >= self.interval_seconds

    def generate(self, progress_tracker, results_db=None):
        """Generate a snapshot report.

        Args:
            progress_tracker: ProgressTracker with current state.
            results_db: Optional ResultsDatabase for detailed queries.

        Returns:
            Path to the generated snapshot directory.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        snap_dir = self.snapshot_dir / f"snapshot_{timestamp}"
        snap_dir.mkdir(parents=True, exist_ok=True)

        # Summary JSON
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "progress_pct": round(
                (progress_tracker.current_slice + 1) / progress_tracker.total_slices * 100, 1
            ) if progress_tracker.total_slices > 0 else 0,
            "current_slice": progress_tracker.current_slice,
            "total_slices": progress_tracker.total_slices,
            "tier_counts": progress_tracker.tier_counts,
            "elapsed_seconds": time.time() - progress_tracker.start_time,
            "eta_seconds": progress_tracker.compute_eta(),
            "rate_points_per_sec": progress_tracker.get_rate(),
            "total_valid_points": progress_tracker.total_valid_points,
        }

        # Add per-slice data if database available
        if results_db:
            summary["slice_data"] = results_db.get_slice_summary()

        with open(snap_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)

        self._last_snapshot_time = time.time()
        logger.info(f"Snapshot generated: {snap_dir}")

        return snap_dir
