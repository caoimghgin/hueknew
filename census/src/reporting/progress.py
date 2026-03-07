"""Progress tracking and status file writing.

Writes status.json for the dashboard to read, and prints formatted
console output for log monitoring.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks census progress and writes status for the dashboard."""

    def __init__(self, total_slices, status_file, results_db=None):
        """
        Args:
            total_slices: Total number of L* slices.
            status_file: Path to write status.json.
            results_db: Optional ResultsDatabase for querying slice data.
        """
        self.total_slices = total_slices
        self.status_file = Path(status_file)
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.results_db = results_db

        self.start_time = time.time()
        self.current_slice = 0
        self.current_L_value = 0.0
        self.tier_counts = {}
        self.total_valid_points = 0
        self.total_points_processed = 0
        self.completed_slices = []
        self.last_checkpoint_time = None
        self.run_log = []

        # Rate tracking (rolling window)
        self._rate_history = []
        self._last_rate_time = time.time()
        self._last_rate_points = 0

    def update(self, slice_result):
        """Update progress after a slice completes.

        Args:
            slice_result: SliceResult from the packer.
        """
        self.current_slice = slice_result.slice_id
        self.current_L_value = slice_result.L_value
        self.total_valid_points += slice_result.valid_points
        self.total_points_processed += slice_result.points_processed

        # Update tier counts
        for tier_name, count in slice_result.seeds_per_tier.items():
            self.tier_counts[tier_name] = self.tier_counts.get(tier_name, 0) + count

        # Track slice completion
        self.completed_slices.append({
            "slice_id": slice_result.slice_id,
            "L_value": slice_result.L_value,
            "valid_points": slice_result.valid_points,
            "seeds": slice_result.seeds_per_tier,
            "duration": slice_result.duration_seconds,
        })

        # Update rate
        now = time.time()
        elapsed_since_last = now - self._last_rate_time
        if elapsed_since_last > 0:
            points_since_last = self.total_points_processed - self._last_rate_points
            rate = points_since_last / elapsed_since_last
            self._rate_history.append(rate)
            if len(self._rate_history) > 20:
                self._rate_history = self._rate_history[-20:]
            self._last_rate_time = now
            self._last_rate_points = self.total_points_processed

    def record_checkpoint(self):
        """Note that a checkpoint was saved."""
        self.last_checkpoint_time = time.time()

    def add_log_entry(self, event, details=""):
        """Add an entry to the in-memory run log."""
        self.run_log.append({
            "event": event,
            "time": datetime.now(timezone.utc).isoformat(),
            "details": details,
        })
        if len(self.run_log) > 100:
            self.run_log = self.run_log[-100:]

    def compute_eta(self):
        """Estimate time remaining based on completed slices."""
        if self.current_slice == 0:
            return 0
        elapsed = time.time() - self.start_time
        slices_done = self.current_slice + 1
        rate = slices_done / elapsed
        remaining = self.total_slices - slices_done
        return remaining / rate if rate > 0 else 0

    def get_rate(self):
        """Get current processing rate (points/sec)."""
        if not self._rate_history:
            return 0.0
        return sum(self._rate_history) / len(self._rate_history)

    def write_status(self):
        """Write status.json for the dashboard to read."""
        elapsed = time.time() - self.start_time
        eta = self.compute_eta()
        progress_pct = ((self.current_slice + 1) / self.total_slices * 100) if self.total_slices > 0 else 0

        # System resources
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        disk_usage_mb = self._get_output_disk_usage()

        status = {
            "state": "running",
            "started_at": datetime.fromtimestamp(self.start_time, tz=timezone.utc).isoformat(),
            "elapsed_seconds": elapsed,
            "current_slice": self.current_slice,
            "current_L_value": self.current_L_value,
            "total_slices": self.total_slices,
            "progress_pct": round(progress_pct, 1),
            "eta_seconds": eta,
            "seeds": self.tier_counts,
            "rate_points_per_sec": round(self.get_rate(), 1),
            "total_valid_points": self.total_valid_points,
            "total_points_processed": self.total_points_processed,
            "memory_mb": round(memory_mb, 1),
            "disk_usage_mb": round(disk_usage_mb, 1),
            "last_checkpoint": (
                datetime.fromtimestamp(self.last_checkpoint_time, tz=timezone.utc).isoformat()
                if self.last_checkpoint_time else None
            ),
            "completed_slices": self.completed_slices[-50:],
            "run_log": self.run_log[-20:],
        }

        # Atomic write
        tmp_path = self.status_file.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(status, f, indent=2, default=str)
        os.rename(tmp_path, self.status_file)

    def write_finished(self):
        """Write final status indicating completion."""
        self.write_status()
        # Re-read and update state
        with open(self.status_file) as f:
            status = json.load(f)
        status["state"] = "finished"
        tmp_path = self.status_file.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(status, f, indent=2, default=str)
        os.rename(tmp_path, self.status_file)

    def print_console(self):
        """Print formatted progress to console/log."""
        elapsed = time.time() - self.start_time
        eta = self.compute_eta()

        lines = [
            f"[Chromatic Census] L*={self.current_L_value:.2f} | "
            f"Slice {self.current_slice + 1}/{self.total_slices} | "
            f"Progress: {(self.current_slice + 1) / self.total_slices * 100:.1f}%",
        ]

        for tier_name, count in sorted(self.tier_counts.items()):
            lines.append(f"  {tier_name}: {count:,} seeds")

        lines.append(
            f"  Rate: {self.get_rate():,.0f} pts/sec | "
            f"ETA: {self._format_duration(eta)}"
        )

        logger.info("\n".join(lines))

    def _get_output_disk_usage(self):
        """Get total size of output directory in MB."""
        output_dir = self.status_file.parent
        total = 0
        for f in output_dir.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total / (1024 * 1024)

    @staticmethod
    def _format_duration(seconds):
        """Format seconds as human-readable duration."""
        if seconds <= 0:
            return "calculating..."
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
