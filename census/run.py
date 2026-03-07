#!/usr/bin/env python3
"""Chromatic Census — Main entry point.

Usage:
    python run.py --mode coarse      # Quick validation run (~2 minutes)
    python run.py --mode fine         # Full census (~10 minutes)
    python run.py --mode superfine   # Convergence test (~37 minutes)
    python run.py --mode ultrafine   # Deep convergence (~5-10 hours)
    python run.py --mode hyperfine   # Convergence limit (~32 hours)
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
    parser.add_argument("--mode", choices=["coarse", "fine", "superfine", "ultrafine", "hyperfine", "gapfill"], default="fine",
                        help="Grid resolution or 'gapfill' for gap-filling optimization")
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
    parser.add_argument("--seed-db", default=None,
                        help="Path to seed database for gap-fill mode")
    parser.add_argument("--random-probes", type=int, default=50_000_000,
                        help="Number of random probes for gap-fill cleanup (default: 50M)")
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


def apply_hyperfine_overrides(config):
    """Override grid steps to hyperfine resolution for convergence limit."""
    config["grid"]["L_step"] = 0.03125
    config["grid"]["a_step"] = 0.0625
    config["grid"]["b_step"] = 0.0625
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

        # Export CSVs to data/
        from src.core.cielab import lab_to_srgb_hex, is_in_srgb_gamut
        export_dir = Path(__file__).resolve().parent.parent / "data"
        export_dir.mkdir(parents=True, exist_ok=True)
        tier_filenames = {"jnd": "jnd.csv", "acceptability": "acceptability.csv", "obvious": "obvious.csv"}
        all_seeds = results_db.get_all_seeds()
        for tier_name, seeds in all_seeds.items():
            if tier_name not in tier_filenames:
                continue
            srgb_mask = is_in_srgb_gamut(seeds[:, 0], seeds[:, 1], seeds[:, 2])
            csv_path = export_dir / tier_filenames[tier_name]
            with open(csv_path, "w") as f:
                f.write("id,L,a,b,hex_srgb,in_srgb\n")
                for i, ((L, a, b), in_s) in enumerate(zip(seeds, srgb_mask), 1):
                    hex_color = lab_to_srgb_hex(L, a, b)
                    f.write(f"{i},{L},{a},{b},{hex_color},{int(in_s)}\n")
            print(f"  Exported {len(seeds):,} {tier_name} seeds → {csv_path}")
    else:
        logger.info("Census paused. Use --resume to continue.")

    results_db.close()


def run_gapfill(config, args):
    """Run gap-filling optimization on an existing seed database."""
    from src.core.gamut import GamutValidator
    from src.engine.gap_filler import GapFiller
    from src.persistence.results import ResultsDatabase

    logger = logging.getLogger(__name__)

    # Determine source database
    seed_db = args.seed_db
    if seed_db is None:
        seed_db = config["persistence"]["results_db"]
        logger.info(f"No --seed-db specified, using {seed_db}")

    seed_db = Path(seed_db)
    if not seed_db.exists():
        print(f"Error: Seed database not found: {seed_db}")
        sys.exit(1)

    gamut = GamutValidator(config["gamut"].get("boundary_tolerance", 0.001))

    # Create gap-filler
    gapfill = GapFiller(config, gamut, seed_db)
    existing_counts = gapfill.load_seeds()
    gapfill.build_trees()

    print(f"\n{'='*60}")
    print("CHROMATIC CENSUS — GAP-FILL OPTIMIZATION")
    print(f"{'='*60}")
    print(f"Source database: {seed_db}")
    print(f"Existing seeds:")
    for name, count in existing_counts.items():
        print(f"  {name}: {count:,}")

    # Set up output database
    output_db_path = Path(config["persistence"]["results_db"])
    results_db = ResultsDatabase(output_db_path)
    results_db.ensure_thresholds(config["packing"]["thresholds"])
    results_db.log_event("gapfill_start", {
        "seed_db": str(seed_db),
        "existing_counts": existing_counts,
    })

    # Start dashboard in background
    status_file = Path(config["reporting"]["status_file"])
    if config.get("dashboard", {}).get("enabled", True):
        from src.dashboard.server import run_dashboard
        dash_config = config.get("dashboard", {})
        dashboard_thread = threading.Thread(
            target=run_dashboard,
            kwargs={
                "host": dash_config.get("host", "0.0.0.0"),
                "port": dash_config.get("port", 8084),
                "status_file": str(status_file),
                "db_path": str(output_db_path),
            },
            daemon=True,
        )
        dashboard_thread.start()

    # Signal handler
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, stopping gap-filler...")
        gapfill.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Progress callback
    last_status_write = [0.0]

    def on_slice(progress):
        now = time.time()
        if now - last_status_write[0] >= 5.0:
            # Write status.json for dashboard
            total_counts = gapfill.get_tier_counts()
            status = {
                "state": "gap-filling",
                "current_slice": progress.slice_id,
                "current_L_value": progress.L_value,
                "total_slices": progress.total_slices,
                "progress_pct": (progress.slice_id + 1) / progress.total_slices * 100,
                "seeds": total_counts,
                "new_seeds": progress.cumulative_new_per_tier,
            }
            try:
                import json
                with open(status_file, "w") as f:
                    json.dump(status, f, indent=2)
            except Exception:
                pass
            last_status_write[0] = now

    # --- PASS 1: Offset grid sweep ---
    # Use ultrafine resolution, shifted by half a step
    L_step = 0.0625
    a_step = 0.125
    b_step = 0.125

    print(f"\n--- Pass 1: Offset grid sweep ---")
    print(f"Grid: L* step {L_step}, a*/b* step {a_step}")
    print(f"Offset: half-step ({L_step/2}, {a_step/2}, {b_step/2})")

    grid_results = gapfill.fill_gaps_grid(
        L_step=L_step,
        a_step=a_step,
        b_step=b_step,
        L_offset=L_step / 2,
        a_offset=a_step / 2,
        b_offset=b_step / 2,
        slice_callback=on_slice,
    )

    print(f"\nPass 1 results:")
    for r in grid_results:
        print(
            f"  {r.tier_name}: +{r.new_seeds:,} new seeds "
            f"({r.total_seeds:,} total) "
            f"[{r.candidates_skipped:,} skipped, "
            f"{r.candidates_verified:,} verified]"
        )

    # Save grid-pass seeds to database
    grid_new_seeds = gapfill.get_new_seeds()
    if grid_new_seeds:
        results_db.insert_seeds_batch(grid_new_seeds)
        results_db.log_event("gapfill_grid_pass", {
            t.name: r.new_seeds for t, r in zip(gapfill.tiers, grid_results)
        })

    # --- PASS 2: Random probing ---
    if args.random_probes > 0 and gapfill._running:
        print(f"\n--- Pass 2: Random probing ({args.random_probes:,} probes) ---")

        random_results = gapfill.fill_gaps_random(
            n_probes=args.random_probes,
            batch_size=500_000,
            slice_callback=on_slice,
        )

        print(f"\nPass 2 results:")
        for r in random_results:
            print(
                f"  {r.tier_name}: +{r.new_seeds:,} new seeds "
                f"({r.total_seeds:,} total)"
            )

        random_new_seeds = gapfill.get_new_seeds()
        if random_new_seeds:
            results_db.insert_seeds_batch(random_new_seeds)
            results_db.log_event("gapfill_random_pass", {
                t.name: r.new_seeds for t, r in zip(gapfill.tiers, random_results)
            })

    # --- Final results ---
    final_counts = gapfill.get_tier_counts()

    print(f"\n{'='*60}")
    print("GAP-FILL OPTIMIZATION — FINAL RESULTS")
    print(f"{'='*60}")
    for name, count in final_counts.items():
        existing = existing_counts.get(name, 0)
        added = count - existing
        pct = (added / existing * 100) if existing > 0 else 0
        print(f"  {name}: {count:,}  (+{added:,}, +{pct:.1f}%)")
    print(f"{'='*60}")

    results_db.log_event("gapfill_finished", final_counts)

    # Persist all new seeds to database
    all_new = gapfill.get_new_seeds()
    if all_new:
        results_db.insert_seeds_batch(all_new)
        logger.info(f"Persisted {len(all_new):,} new seeds to database")

    results_db.close()

    # Export CSVs with all seeds (original + gap-filled)
    export_dir = Path(__file__).resolve().parent.parent / "data"
    export_dir.mkdir(parents=True, exist_ok=True)
    tier_filenames = {"jnd": "jnd.csv", "acceptability": "acceptability.csv", "obvious": "obvious.csv"}
    all_tier_seeds = gapfill.get_all_seeds()
    from src.core.cielab import lab_to_srgb_hex, is_in_srgb_gamut
    for tier in gapfill.tiers:
        seeds = all_tier_seeds[tier.name]
        srgb_mask = is_in_srgb_gamut(seeds[:, 0], seeds[:, 1], seeds[:, 2])
        csv_path = export_dir / tier_filenames[tier.name]
        with open(csv_path, "w") as f:
            f.write("id,L,a,b,hex_srgb,in_srgb\n")
            for i, ((L, a, b), in_s) in enumerate(zip(seeds, srgb_mask), 1):
                hex_color = lab_to_srgb_hex(L, a, b)
                f.write(f"{i},{L},{a},{b},{hex_color},{int(in_s)}\n")
        print(f"  Exported {len(seeds):,} {tier.name} seeds → {csv_path}")

    # Write final status
    import json
    status = {
        "state": "finished",
        "seeds": final_counts,
        "existing_seeds": existing_counts,
        "new_seeds": {k: final_counts[k] - existing_counts.get(k, 0)
                      for k in final_counts},
    }
    with open(status_file, "w") as f:
        json.dump(status, f, indent=2)


def _import_csvs_to_db(db_path):
    """Import pre-computed CSVs into a SQLite database for the dashboard.

    Called automatically when --dashboard-only is run without a results.sqlite.
    """
    import csv
    import sqlite3

    data_dir = Path(__file__).resolve().parent.parent / "data"
    tier_map = {
        "jnd": ("JND", 1.0),
        "acceptability": ("acceptability", 2.0),
        "obvious": ("obvious", 5.0),
    }

    csv_files = {name: data_dir / f"{name}.csv" for name in tier_map}
    if not any(f.exists() for f in csv_files.values()):
        return False

    print("Importing CSV data into dashboard database...")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
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
        CREATE INDEX IF NOT EXISTS idx_seeds_threshold_L ON seeds(threshold_id, L);
    """)

    for tier_key, (tier_name, delta_e) in tier_map.items():
        conn.execute(
            "INSERT OR IGNORE INTO thresholds (name, delta_e) VALUES (?, ?)",
            (tier_name, delta_e),
        )
    conn.commit()

    for tier_key, (tier_name, delta_e) in tier_map.items():
        csv_path = csv_files[tier_key]
        if not csv_path.exists():
            continue
        tid = conn.execute(
            "SELECT id FROM thresholds WHERE name = ?", (tier_name,)
        ).fetchone()[0]
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            batch = [
                (float(r["L"]), float(r["a"]), float(r["b"]), r["hex_srgb"], tid)
                for r in reader
            ]
        conn.executemany(
            "INSERT INTO seeds (L, a, b, hex_srgb, threshold_id) VALUES (?, ?, ?, ?, ?)",
            batch,
        )
        print(f"  {tier_name}: {len(batch):,} seeds imported")

    conn.commit()
    conn.close()
    return True


def run_dashboard_only(config):
    """Run just the dashboard server (no engine)."""
    from src.dashboard.server import run_dashboard
    dash_config = config.get("dashboard", {})
    status_file = config["reporting"]["status_file"]
    db_path = config["persistence"]["results_db"]

    # Auto-import CSVs if no database exists
    if not Path(db_path).exists():
        if _import_csvs_to_db(db_path):
            # Write a status file so the dashboard shows results
            import json
            status = {"state": "finished", "seeds": {}}
            Path(status_file).parent.mkdir(parents=True, exist_ok=True)
            with open(status_file, "w") as f:
                json.dump(status, f)

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
    elif args.mode == "hyperfine":
        config = apply_hyperfine_overrides(config)

    if args.status:
        print_status(config)
    elif args.estimate:
        run_estimate(config)
    elif args.dashboard_only:
        run_dashboard_only(config)
    elif args.mode == "gapfill":
        run_gapfill(config, args)
    else:
        run_engine(config, args)


if __name__ == "__main__":
    main()
