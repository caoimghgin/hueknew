"""Checkpoint management for crash-resilient multi-week runs.

Saves packer state to disk at regular intervals and on shutdown signals.
Uses atomic writes (write to temp, then rename) for crash safety.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages saving and loading of packer state checkpoints."""

    MAX_CHECKPOINTS = 3  # Keep the last N checkpoints, delete older ones

    def __init__(self, checkpoint_dir, interval_seconds=300):
        """
        Args:
            checkpoint_dir: Directory for checkpoint files.
            interval_seconds: Minimum seconds between auto-saves.
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.interval_seconds = interval_seconds
        self._last_save_time = 0

    def should_save(self):
        """Check if enough time has elapsed since the last save."""
        return (time.time() - self._last_save_time) >= self.interval_seconds

    def save(self, state):
        """Save a checkpoint to disk.

        Args:
            state: Dict with packer state (tier_counts, current_slice, etc.)

        Returns:
            Path to the saved checkpoint file.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"checkpoint_{timestamp}.json"
        filepath = self.checkpoint_dir / filename
        tmp_path = filepath.with_suffix(".tmp")

        checkpoint = {
            "version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": state,
        }

        # Atomic write: write to temp file, then rename
        with open(tmp_path, "w") as f:
            json.dump(checkpoint, f, indent=2, default=str)

        os.rename(tmp_path, filepath)
        self._last_save_time = time.time()

        logger.info(f"Checkpoint saved: {filepath}")

        # Clean up old checkpoints
        self._cleanup()

        return filepath

    def load_latest(self):
        """Load the most recent checkpoint.

        Returns:
            State dict, or None if no checkpoint found.
        """
        checkpoints = sorted(
            self.checkpoint_dir.glob("checkpoint_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for cp_path in checkpoints:
            try:
                with open(cp_path) as f:
                    checkpoint = json.load(f)
                logger.info(f"Loaded checkpoint: {cp_path}")
                return checkpoint.get("state", checkpoint)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Corrupt checkpoint {cp_path}: {e}")
                continue

        return None

    def _cleanup(self):
        """Remove old checkpoints, keeping only the most recent MAX_CHECKPOINTS."""
        checkpoints = sorted(
            self.checkpoint_dir.glob("checkpoint_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for old_cp in checkpoints[self.MAX_CHECKPOINTS:]:
            try:
                old_cp.unlink()
                logger.debug(f"Removed old checkpoint: {old_cp}")
            except OSError:
                pass
