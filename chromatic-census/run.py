#!/usr/bin/env python3
"""Chromatic Census — Main entry point.

Usage:
    python run.py --mode coarse      # Quick validation run (~2 minutes)
    python run.py --mode fine         # Full census (~10 minutes)
    python run.py --mode superfine   # Convergence test (~37 minutes)
    python run.py --mode ultrafine   # Deep convergence (~5-10 hours)
    python run.py --resume            # Resume from last checkpoint
    python run.py --status            # Print current status
    python run.py --dashboard-only    # Run dashboard without engine
    python run.py --estimate          # Quick volume-integration estimate
"""

import argparse
import json
import logging
import signal
import sys
import threading
import time
from pathlib import Path

import yaml


def parse_args():
    parser = argparse.ArgumentParser(description="Chromatic Census")
    parser.add_argument("--mode", choices=["coarse", "fine", "superfine", "ultrafine"], default="fine",
                        help="Grid resolution (default: fine)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from the latest checkpoint")
    parser.add_argument("--status", action="store_true",
                        help="Print current status and exit")
    parser.add_argument("--dashboard-only", action="store_true",
                        help="Run the dashboard without starting the engine")
    parser.add_argument("--no-dashboard", action="store_true",
                        help="Run the engine without the dashboard")
    parser.add_argument("--estimate", action="store_true",
                        help="Run quick volume-integration estimate and exit")
    parser.add_argument("--config", default="config.yaml",
                        help="Config file path (default: config.yaml)")
    return parser.parse_args()


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def apply_coarse_overrides(config):
    """Override grid steps to coarse resolution for quick validation."""
    config["grid"]["L_step"] = 1.0
    config["grid"]["a_step"] = 2.0
    config["grid"]["b_step"] = 2.0
    return config


def apply_superfine_overrides(config):
    """Override grid steps to superfine resolution for convergence testing."""
    config["grid"]["L_step"] = 0.125
    config["grid"]["a_step"] = 0.25
    config["grid"]["b_step"] = 0.25
    return config


def apply_ultrafine_overrides(config):
    """Override grid steps to ultrafine resolution for deep convergence testing."""
    config["grid"]["L_step"] = 0.0625
    config["grid"]["a_step"] = 0.125
    config["grid"]["b_step"] = 0.125
    return config


def setup_logging(config):
    level = getattr(logging, config.get("reporting", {}).get("log_level", "INFO"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def print_status(config):
    """Print current status from status.json."""
    status_file = Path(config["reporting"]["status_file"])
    if not status_file.exists():
        print("No status file found. Census has not been started.")
        return

    with open(status_file) as f:
        status = json.load(f)

    print(f"\nChromatic Census — Status")
    print(f"{'='*50}")
    print(f"State: {status.get('state', 'unknown')}")
    print(f"Progress: {status.get('progress_pct', 0):.1f}%")
    print(f"Slice: {status.get('current_slice', 0) + 1}/{status.get('total_slices', 0)}")
    print(f"L*: {status.get('current_L_value', 0):.2f}")

    seeds = status.get("seeds", {})
    print(f"\nSeeds Found:")
    for tier, count in sorted(seeds.items()):
        print(f"  {tier}: {count:,}")

    elapsed = status.get("elapsed_seconds", 0)
    eta = status.get("eta_seconds", 0)
    print(f"\nElapsed: {_format_duration(elapsed)}")
    print(f"ETA: {_format_duration(eta)}")
    print(f"Rate: {status.get('rate_points_per_sec', 0):,.0f} pts/sec")
    print(f"Memory: {status.get('memory_mb', 0):.0f} MB")


def run_estimate(config):
    """Run quick volume-integration estimate."""
    from src.core.gamut import GamutValidator
    from src.engine.estimator import VolumeEstimator

    logger = logging.getLogger(__name__)
    gamut = GamutValidator()
    estimator = VolumeEstimator()

    print("\nChromatic Census — Volume Integration Estimate")
    print(f"{'='*50}")
    print("(Approximate — the greedy packer gives exact counts)\n")

    for threshold in config["packing"]["thresholds"]:
        name = threshold["name"]
        delta_e = threshold["delta_e"]
        logger.info(f"Estimating for {name} (ΔE={delta_e})...")
        count = estimator.estimate_count(delta_e, gamut, config["grid"])
        print(f"  {name} (ΔE={delta_e}): ~{count:,} colors")


def run_engine(config, args):
    """Run the census engine with optional dashboard."""
    from src.core.gamut import GamutValidator
    from src.engine.grid import GridGenerator
    from src.engine.packer import GreedyPacker
    from src.persistence.checkpoint import CheckpointManager
    from src.persistence.results import ResultsDatabase
    from src.reporting.progress import ProgressTracker
    from src.reporting.snapshots import SnapshotGenerator

    logger = logging.getLogger(__name__)

    # Initialize components
    gamut = GamutValidator(config["gamut"].get("boundary_tolerance", 0.001))
    grid = GridGenerator(config["grid"])
    packer = GreedyPacker(config, gamut)

    checkpoint_dir = Path(config["persistence"]["checkpoint_dir"])
    checkpoint_mgr = CheckpointManager(checkpoint_dir, config["persistence"]["checkpoint_interval"])

    db_path = Path(config["persistence"]["results_db"])
    results_db = ResultsDatabase(db_path)
    results_db.ensure_thresholds(config["packing"]["thresholds"])
    results_db.log_event("start", {"mode": args.mode, "resume": args.resume})

    status_file = Path(config["reporting"]["status_file"])
    progress = ProgressTracker(grid.total_slices(), status_file, results_db)

    snapshot_gen = SnapshotGenerator(
        Path(config["reporting"]["snapshot_dir"]),
        config["reporting"]["snapshot_interval"],
    )

    # Resume from checkpoint if requested
    resume_from = 0
    if args.resume:
        state = checkpoint_mgr.load_latest()
        if state:
            packer.restore_state(state)
            resume_from = state.get("current_slice", 0)
            progress.add_log_entry("resumed", f"from slice {resume_from}")
            logger.info(f"Resumed from checkpoint at slice {resume_from}")
        else:
            logger.info("No checkpoint found, starting fresh")

    # Start dashboard in background thread
    if not args.no_dashboard and config.get("dashboard", {}).get("enabled", True):
        from src.dashboard.server import run_dashboard
        dash_config = config.get("dashboard", {})
        dashboard_thread = threading.Thread(
            target=run_dashboard,
            kwargs={
                "host": dash_config.get("host", "0.0.0.0"),
                "port": dash_config.get("port", 8084),
                "status_file": str(status_file),
                "db_path": str(db_path),
            },
            daemon=True,
        )
        dashboard_thread.start()
        logger.info(f"Dashboard running on http://{dash_config.get('host', '0.0.0.0')}:{dash_config.get('port', 8084)}")

    # Signal handlers for graceful shutdown
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        packer.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Write initial status
    progress.add_log_entry("started", f"mode={args.mode}")
    progress.write_status()

    logger.info(
        f"Starting census: {grid.total_slices()} slices, "
        f"~{grid.estimate_total_points():,} candidate points"
    )

    # Slice callback — called after each L* slice completes
    def on_slice_complete(result):
        # Update progress
        progress.update(result)
        progress.print_console()
        progress.write_status()

        # Insert seeds into database
        results_db.insert_seeds_batch(result.seeds)
        results_db.complete_slice(
            result.slice_id, result.L_value, result.valid_points,
            result.seeds_per_tier, result.duration_seconds,
        )

        # Checkpoint
        if checkpoint_mgr.should_save():
            checkpoint_mgr.save(packer.get_state())
            progress.record_checkpoint()
            progress.add_log_entry("checkpoint", f"slice {result.slice_id}")
            results_db.log_event("checkpoint", packer.get_state())

        # Snapshot
        if snapshot_gen.should_generate():
            snapshot_gen.generate(progress, results_db)
            progress.add_log_entry("snapshot", f"slice {result.slice_id}")

    # Run the packer
    try:
        result = packer.pack_all(
            grid=grid,
            resume_from=resume_from,
            slice_callback=on_slice_complete,
        )
    except Exception as e:
        logger.error(f"Engine error: {e}", exc_info=True)
        checkpoint_mgr.save(packer.get_state())
        results_db.log_event("error", {"message": str(e)})
        raise
    finally:
        # Final checkpoint
        checkpoint_mgr.save(packer.get_state())
        results_db.log_event("stopped", packer.get_state())

    if result.get("completed"):
        logger.info("Census complete!")
        progress.add_log_entry("finished", f"Total: {packer.get_tier_counts()}")
        progress.write_finished()
        results_db.log_event("finished", packer.get_tier_counts())

        # Print final results
        print(f"\n{'='*60}")
        print("CHROMATIC CENSUS — FINAL RESULTS")
        print(f"{'='*60}")
        for tier_name, count in sorted(packer.get_tier_counts().items()):
            print(f"  {tier_name}: {count:,} distinguishable colors")
        print(f"{'='*60}")
    else:
        logger.info("Census paused. Use --resume to continue.")

    results_db.close()


def run_dashboard_only(config):
    """Run just the dashboard server (no engine)."""
    from src.dashboard.server import run_dashboard
    dash_config = config.get("dashboard", {})
    status_file = config["reporting"]["status_file"]
    db_path = config["persistence"]["results_db"]
    print(f"Dashboard running on http://0.0.0.0:{dash_config.get('port', 8084)}")
    run_dashboard(
        host=dash_config.get("host", "0.0.0.0"),
        port=dash_config.get("port", 8084),
        status_file=status_file,
        db_path=db_path,
    )


def _format_duration(seconds):
    if seconds <= 0:
        return "--"
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def main():
    args = parse_args()
    config = load_config(args.config)
    setup_logging(config)

    if args.mode == "coarse":
        config = apply_coarse_overrides(config)
    elif args.mode == "superfine":
        config = apply_superfine_overrides(config)
    elif args.mode == "ultrafine":
        config = apply_ultrafine_overrides(config)

    if args.status:
        print_status(config)
    elif args.estimate:
        run_estimate(config)
    elif args.dashboard_only:
        run_dashboard_only(config)
    else:
        run_engine(config, args)


if __name__ == "__main__":
    main()
