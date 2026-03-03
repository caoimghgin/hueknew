"""Gap-filling optimization for converging seed counts.

Instead of running progressively finer grids (exponential cost, diminishing
returns), this engine loads existing seeds from a completed census run and
systematically searches for positions where new seeds can be inserted —
the "gaps" in the packing.

Strategy:
  1. Load all seeds per tier from the results database.
  2. Build a global KD-tree per tier.
  3. Sweep candidate points (offset grid, then random probes).
  4. For each candidate, fast nearest-neighbor check → exact ΔE2000 if needed.
  5. Greedily insert confirmed gap seeds, rebuild tree, repeat.
  6. Converge when a full pass adds zero new seeds.
"""

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from ..core.cielab import lab_to_srgb_hex
from ..core.delta_e import delta_e_2000
from ..core.gamut import GamutValidator

logger = logging.getLogger(__name__)

# Conservative Euclidean overestimate for ΔE2000 search.
# ΔE2000 can exceed CIELAB Euclidean by up to ~1.5× (near neutral axis
# at mid-lightness due to the G factor). 6.0 is the safe search radius
# for the largest threshold (ΔE=5.0).
SEARCH_RADIUS = 6.0

# If the nearest existing seed is within this factor × threshold in
# Euclidean distance, the point is certainly covered (ΔE2000 < threshold).
# Factor of 0.3 is very conservative: ΔE2000 would need to be >3.3×
# Euclidean to miss, which doesn't happen in practice.
SAFE_SKIP_FACTOR = 0.3


@dataclass
class TierConfig:
    """Configuration for a single perceptual tier."""
    name: str
    delta_e: float
    threshold_id: int  # From the source database


@dataclass
class GapFillResult:
    """Results from a gap-filling pass."""
    tier_name: str
    existing_seeds: int
    new_seeds: int
    total_seeds: int
    candidates_checked: int
    candidates_skipped: int  # Eliminated by Euclidean pre-filter
    candidates_verified: int  # Needed full ΔE2000 check
    duration_seconds: float


@dataclass
class SliceProgress:
    """Progress update for a single L* slice."""
    slice_id: int
    L_value: float
    total_slices: int
    new_seeds_per_tier: dict  # tier_name -> count this slice
    cumulative_new_per_tier: dict  # tier_name -> running total
    duration_seconds: float
    candidates_in_slice: int


class GapFiller:
    """Finds and fills gaps in an existing seed packing.

    Loads seeds from a completed census database, builds spatial indices,
    and systematically searches for positions where new seeds can be
    inserted to tighten the packing toward the theoretical limit.
    """

    def __init__(self, config, gamut_validator, seed_db_path):
        """
        Args:
            config: Full configuration dict.
            gamut_validator: GamutValidator instance.
            seed_db_path: Path to the source SQLite database with existing seeds.
        """
        self.gamut = gamut_validator
        self.config = config
        self.seed_db_path = Path(seed_db_path)

        if not self.seed_db_path.exists():
            raise FileNotFoundError(f"Seed database not found: {self.seed_db_path}")

        # Will be populated by load_seeds()
        self.tiers = []  # List of TierConfig
        self.tier_seeds = {}  # tier_name -> Nx3 float64 array
        self.tier_trees = {}  # tier_name -> cKDTree
        self.tier_new_seeds = {}  # tier_name -> list of [L, a, b]

        self._running = True

    def stop(self):
        """Signal the gap-filler to stop after the current slice."""
        self._running = False

    def load_seeds(self):
        """Load existing seeds from the database and build per-tier arrays.

        Returns:
            Dict of {tier_name: seed_count} for loaded seeds.
        """
        logger.info(f"Loading seeds from {self.seed_db_path}")
        conn = sqlite3.connect(str(self.seed_db_path), timeout=30)
        conn.row_factory = sqlite3.Row

        # Load threshold definitions
        rows = conn.execute(
            "SELECT id, name, delta_e FROM thresholds ORDER BY delta_e"
        ).fetchall()

        self.tiers = []
        for row in rows:
            self.tiers.append(TierConfig(
                name=row["name"],
                delta_e=row["delta_e"],
                threshold_id=row["id"],
            ))

        # Load seeds per tier
        counts = {}
        for tier in self.tiers:
            rows = conn.execute(
                "SELECT L, a, b FROM seeds WHERE threshold_id = ? ORDER BY L",
                (tier.threshold_id,),
            ).fetchall()

            if rows:
                seeds = np.array(
                    [(r["L"], r["a"], r["b"]) for r in rows],
                    dtype=np.float64,
                )
            else:
                seeds = np.empty((0, 3), dtype=np.float64)

            self.tier_seeds[tier.name] = seeds
            self.tier_new_seeds[tier.name] = []
            counts[tier.name] = len(seeds)
            logger.info(f"  {tier.name} (ΔE={tier.delta_e}): {len(seeds):,} seeds loaded")

        conn.close()
        return counts

    def build_trees(self):
        """Build KD-trees for each tier's seed set."""
        for tier in self.tiers:
            seeds = self.tier_seeds[tier.name]
            if len(seeds) > 0:
                self.tier_trees[tier.name] = cKDTree(seeds)
                logger.info(
                    f"  {tier.name}: KD-tree built ({len(seeds):,} points)"
                )
            else:
                self.tier_trees[tier.name] = None
                logger.warning(f"  {tier.name}: No seeds — skipping tree")

    def _rebuild_tier_tree(self, tier_name):
        """Rebuild a tier's KD-tree after adding new seeds."""
        new = self.tier_new_seeds[tier_name]
        if not new:
            return

        new_arr = np.array(new, dtype=np.float64).reshape(-1, 3)
        existing = self.tier_seeds[tier_name]

        if len(existing) > 0:
            combined = np.vstack([existing, new_arr])
        else:
            combined = new_arr

        self.tier_seeds[tier_name] = combined
        self.tier_trees[tier_name] = cKDTree(combined)
        self.tier_new_seeds[tier_name] = []

    def _check_candidate(self, point, tier):
        """Check if a candidate point is a valid new seed for a tier.

        Args:
            point: (L, a, b) array.
            tier: TierConfig.

        Returns:
            True if the point is a valid gap (farther than tier.delta_e
            from all existing seeds in ΔE2000).
        """
        tree = self.tier_trees[tier.name]
        if tree is None:
            return True  # No existing seeds — everything is a gap

        # Query all existing seeds within Euclidean search radius
        neighbor_idx = tree.query_ball_point(point, SEARCH_RADIUS)

        if len(neighbor_idx) == 0:
            return True  # No seeds within search radius — definite gap

        # Compute exact ΔE2000 to all neighbors
        neighbor_idx = np.array(neighbor_idx, dtype=np.intp)
        seeds = self.tier_seeds[tier.name]
        n_L = seeds[neighbor_idx, 0]
        n_a = seeds[neighbor_idx, 1]
        n_b = seeds[neighbor_idx, 2]

        distances = delta_e_2000(
            point[0], point[1], point[2],
            n_L, n_a, n_b,
        )

        return np.all(distances > tier.delta_e)

    def fill_gaps_grid(self, L_step, a_step, b_step,
                       L_offset=0.0, a_offset=0.0, b_offset=0.0,
                       slice_callback=None):
        """Sweep a grid looking for gaps in all tiers' packings.

        Args:
            L_step, a_step, b_step: Grid resolution.
            L_offset, a_offset, b_offset: Grid offset from origin.
            slice_callback: Optional callback(SliceProgress) per slice.

        Returns:
            List of GapFillResult, one per tier.
        """
        start_time = time.time()

        # Generate L* values for sweep
        L_min, L_max = 0.0, 100.0
        L_values = np.arange(L_min + L_offset, L_max + L_step / 2, L_step)
        L_values = L_values[L_values <= L_max]
        total_slices = len(L_values)

        # a*/b* candidate values
        a_min, b_min = -128.0, -128.0
        a_max, b_max = 127.0, 127.0
        a_values = np.arange(a_min + a_offset, a_max + a_step / 2, a_step)
        b_values = np.arange(b_min + b_offset, b_max + b_step / 2, b_step)
        a_values = a_values[a_values <= a_max]
        b_values = b_values[b_values <= b_max]

        logger.info(
            f"Gap-fill grid sweep: {total_slices} slices, "
            f"{len(a_values)}×{len(b_values)} per slice, "
            f"offset=({L_offset}, {a_offset}, {b_offset})"
        )

        # Per-tier tracking
        tier_stats = {t.name: {
            "new": 0, "checked": 0, "skipped": 0, "verified": 0,
        } for t in self.tiers}

        cumulative_new = {t.name: 0 for t in self.tiers}

        for si, L_val in enumerate(L_values):
            if not self._running:
                logger.info(f"Gap-filler stopped at slice {si}")
                break

            slice_start = time.time()

            # Generate candidate grid for this slice
            aa, bb = np.meshgrid(a_values, b_values, indexing="ij")
            a_flat = aa.ravel()
            b_flat = bb.ravel()
            L_flat = np.full_like(a_flat, L_val)

            # Gamut filter
            L_valid, a_valid, b_valid, mask = self.gamut.filter_valid(
                L_flat, a_flat, b_flat,
            )
            n_valid = len(L_valid)

            if n_valid == 0:
                continue

            candidates = np.column_stack([L_valid, a_valid, b_valid])

            # Process each tier
            slice_new = {t.name: 0 for t in self.tiers}

            for tier in self.tiers:
                tree = self.tier_trees[tier.name]
                if tree is None:
                    continue

                stats = tier_stats[tier.name]

                # Batch nearest-neighbor query for fast pre-filtering
                nn_dist, _ = tree.query(candidates)

                # Split candidates into categories
                safe_skip_dist = tier.delta_e * SAFE_SKIP_FACTOR
                definitely_skip = nn_dist <= safe_skip_dist
                possibly_gap = ~definitely_skip

                stats["skipped"] += int(definitely_skip.sum())
                stats["checked"] += n_valid

                # For possibly-gap candidates, do full ΔE2000 check
                gap_indices = np.where(possibly_gap)[0]
                stats["verified"] += len(gap_indices)

                # Track new seeds for greedy packing within this slice
                new_seed_positions = []

                for idx in gap_indices:
                    if not self._running:
                        break

                    point = candidates[idx]

                    # Check against existing seeds
                    if not self._check_candidate(point, tier):
                        continue

                    # Also check against new seeds added in this slice
                    if new_seed_positions:
                        new_arr = np.array(new_seed_positions, dtype=np.float64)
                        new_dists = delta_e_2000(
                            point[0], point[1], point[2],
                            new_arr[:, 0], new_arr[:, 1], new_arr[:, 2],
                        )
                        if np.any(new_dists <= tier.delta_e):
                            continue

                    # Confirmed gap — new seed!
                    new_seed_positions.append([point[0], point[1], point[2]])
                    self.tier_new_seeds[tier.name].append(
                        [float(point[0]), float(point[1]), float(point[2])]
                    )
                    stats["new"] += 1
                    slice_new[tier.name] += 1
                    cumulative_new[tier.name] += 1

                # Rebuild tree if we found new seeds (so next slices see them)
                if new_seed_positions:
                    self._rebuild_tier_tree(tier.name)

            slice_dur = time.time() - slice_start

            if slice_callback:
                slice_callback(SliceProgress(
                    slice_id=si,
                    L_value=L_val,
                    total_slices=total_slices,
                    new_seeds_per_tier=slice_new,
                    cumulative_new_per_tier=dict(cumulative_new),
                    duration_seconds=slice_dur,
                    candidates_in_slice=n_valid,
                ))

            # Log progress periodically
            if si % 100 == 0 or si == total_slices - 1:
                elapsed = time.time() - start_time
                new_summary = " · ".join(
                    f"{t.name}: +{cumulative_new[t.name]:,}" for t in self.tiers
                )
                logger.info(
                    f"  Slice {si + 1}/{total_slices} L*={L_val:.4f} "
                    f"({elapsed:.0f}s) — {new_summary}"
                )

        # Compile results
        total_elapsed = time.time() - start_time
        results = []
        for tier in self.tiers:
            s = tier_stats[tier.name]
            results.append(GapFillResult(
                tier_name=tier.name,
                existing_seeds=len(self.tier_seeds[tier.name]) - s["new"],
                new_seeds=s["new"],
                total_seeds=len(self.tier_seeds[tier.name]),
                candidates_checked=s["checked"],
                candidates_skipped=s["skipped"],
                candidates_verified=s["verified"],
                duration_seconds=total_elapsed,
            ))

        return results

    def fill_gaps_random(self, n_probes=10_000_000, batch_size=100_000,
                         slice_callback=None):
        """Random probing pass to find remaining gaps.

        Generates random in-gamut points and checks each against existing
        seeds. More effective at finding irregular gaps that grid sweeps miss.

        Args:
            n_probes: Total number of random points to generate.
            batch_size: Points generated per batch.
            slice_callback: Optional callback(SliceProgress) per batch.

        Returns:
            List of GapFillResult, one per tier.
        """
        start_time = time.time()
        n_batches = (n_probes + batch_size - 1) // batch_size

        logger.info(
            f"Gap-fill random probing: {n_probes:,} probes in "
            f"{n_batches} batches of {batch_size:,}"
        )

        rng = np.random.default_rng(seed=42)
        tier_stats = {t.name: {
            "new": 0, "checked": 0, "skipped": 0, "verified": 0,
        } for t in self.tiers}
        cumulative_new = {t.name: 0 for t in self.tiers}

        for bi in range(n_batches):
            if not self._running:
                break

            batch_start = time.time()

            # Generate random CIELAB points
            L_rand = rng.uniform(0.0, 100.0, size=batch_size)
            a_rand = rng.uniform(-128.0, 127.0, size=batch_size)
            b_rand = rng.uniform(-128.0, 127.0, size=batch_size)

            # Gamut filter
            L_valid, a_valid, b_valid, mask = self.gamut.filter_valid(
                L_rand, a_rand, b_rand,
            )
            n_valid = len(L_valid)

            if n_valid == 0:
                continue

            candidates = np.column_stack([L_valid, a_valid, b_valid])

            batch_new = {t.name: 0 for t in self.tiers}

            for tier in self.tiers:
                tree = self.tier_trees[tier.name]
                if tree is None:
                    continue

                stats = tier_stats[tier.name]
                stats["checked"] += n_valid

                # Batch nearest-neighbor pre-filter
                nn_dist, _ = tree.query(candidates)
                safe_skip_dist = tier.delta_e * SAFE_SKIP_FACTOR
                possibly_gap = nn_dist > safe_skip_dist
                stats["skipped"] += int((~possibly_gap).sum())

                gap_indices = np.where(possibly_gap)[0]
                stats["verified"] += len(gap_indices)

                new_seed_positions = []

                for idx in gap_indices:
                    if not self._running:
                        break

                    point = candidates[idx]

                    if not self._check_candidate(point, tier):
                        continue

                    if new_seed_positions:
                        new_arr = np.array(new_seed_positions, dtype=np.float64)
                        new_dists = delta_e_2000(
                            point[0], point[1], point[2],
                            new_arr[:, 0], new_arr[:, 1], new_arr[:, 2],
                        )
                        if np.any(new_dists <= tier.delta_e):
                            continue

                    new_seed_positions.append([point[0], point[1], point[2]])
                    self.tier_new_seeds[tier.name].append(
                        [float(point[0]), float(point[1]), float(point[2])]
                    )
                    stats["new"] += 1
                    batch_new[tier.name] += 1
                    cumulative_new[tier.name] += 1

                if new_seed_positions:
                    self._rebuild_tier_tree(tier.name)

            batch_dur = time.time() - batch_start

            if slice_callback:
                slice_callback(SliceProgress(
                    slice_id=bi,
                    L_value=0.0,
                    total_slices=n_batches,
                    new_seeds_per_tier=batch_new,
                    cumulative_new_per_tier=dict(cumulative_new),
                    duration_seconds=batch_dur,
                    candidates_in_slice=n_valid,
                ))

            if bi % 10 == 0 or bi == n_batches - 1:
                elapsed = time.time() - start_time
                new_summary = " · ".join(
                    f"{t.name}: +{cumulative_new[t.name]:,}" for t in self.tiers
                )
                logger.info(
                    f"  Batch {bi + 1}/{n_batches} ({elapsed:.0f}s) — {new_summary}"
                )

        total_elapsed = time.time() - start_time
        results = []
        for tier in self.tiers:
            s = tier_stats[tier.name]
            results.append(GapFillResult(
                tier_name=tier.name,
                existing_seeds=len(self.tier_seeds[tier.name]) - s["new"],
                new_seeds=s["new"],
                total_seeds=len(self.tier_seeds[tier.name]),
                candidates_checked=s["checked"],
                candidates_skipped=s["skipped"],
                candidates_verified=s["verified"],
                duration_seconds=total_elapsed,
            ))

        return results

    def get_new_seeds(self):
        """Return all new seeds found across all tiers.

        Returns:
            List of dicts with L, a, b, hex, tier keys.
        """
        all_seeds = []
        for tier in self.tiers:
            for pos in self.tier_new_seeds[tier.name]:
                L, a, b = pos
                all_seeds.append({
                    "L": L, "a": a, "b": b,
                    "hex": lab_to_srgb_hex(L, a, b),
                    "tier": tier.name,
                    "slice_id": -1,  # Gap-fill seeds don't belong to a specific slice
                })
        return all_seeds

    def get_tier_counts(self):
        """Return current total seed counts per tier."""
        return {t.name: len(self.tier_seeds[t.name]) for t in self.tiers}

    def get_tier_new_counts(self):
        """Return new seed counts per tier (from gap-filling only)."""
        return {t.name: len(self.tier_new_seeds[t.name]) for t in self.tiers}
