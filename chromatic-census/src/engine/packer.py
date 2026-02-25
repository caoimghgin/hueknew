"""Greedy JND sphere-packing algorithm.

The computational heart of Chromatic Census. Packs non-overlapping
ΔE2000 neighborhoods into the human visual gamut at three threshold
tiers simultaneously.
"""

import time
import logging
from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import cKDTree

from ..core.delta_e import delta_e_2000
from ..core.gamut import GamutValidator
from ..core.cielab import lab_to_srgb_hex
from .grid import GridGenerator
from .spatial import SpatialIndex

logger = logging.getLogger(__name__)


@dataclass
class TierState:
    """Tracking state for a single perceptual threshold tier."""
    name: str
    delta_e: float
    description: str = ""
    claimed: np.ndarray = field(default=None, repr=False)
    seed_count: int = 0
    # Most recent seed for "color of the moment" display
    last_seed: dict = field(default_factory=dict)


@dataclass
class SliceResult:
    """Results from packing a single L* slice."""
    slice_id: int
    L_value: float
    valid_points: int
    seeds_per_tier: dict  # tier_name -> count
    seeds: list  # list of seed dicts with L,a,b,hex,tier info
    duration_seconds: float
    points_processed: int
    # Per-tier seed positions for the ghost buffer {tier_name: Nx3 ndarray}
    tier_seed_positions: dict = field(default=None, repr=False)


class GreedyPacker:
    """Multi-threshold greedy sphere-packing in CIELAB space."""

    def __init__(self, config, gamut_validator):
        """
        Args:
            config: Full configuration dict (needs 'packing', 'delta_e', 'grid' sections).
            gamut_validator: GamutValidator instance.
        """
        self.gamut = gamut_validator
        self.packing_config = config["packing"]
        self.delta_e_config = config.get("delta_e", {})
        self.grid_config = config["grid"]

        self.kdtree_radius = self.packing_config["kdtree_radius"]
        self.rebuild_interval = self.packing_config["kdtree_rebuild_interval"]

        # Initialize tier states
        self.tiers = []
        for t in self.packing_config["thresholds"]:
            self.tiers.append(TierState(
                name=t["name"],
                delta_e=t["delta_e"],
                description=t.get("description", ""),
            ))

        # Overall tracking
        self.current_slice = 0
        self.total_points_processed = 0
        self.total_valid_points = 0
        self.start_time = None
        self._running = True

        # Ghost seed buffer for cross-slice deduplication.
        # List of (L_value, {tier_name: Nx3 ndarray}) tuples — per-tier
        # seed positions from recently completed slices. Each tier only
        # checks against ghost seeds that were actually seeds at that tier,
        # preventing over-suppression from denser tiers' seeds.
        self._ghost_buffer = []

    def stop(self):
        """Signal the packer to stop after the current slice."""
        self._running = False

    def get_tier_counts(self):
        """Return current seed counts per tier."""
        return {t.name: t.seed_count for t in self.tiers}

    def get_last_seeds(self):
        """Return the most recent seed from each tier."""
        return {t.name: t.last_seed for t in self.tiers if t.last_seed}

    def _gather_ghost_seeds(self, L_current):
        """Gather per-tier seed positions from recent slices within KD-tree radius.

        Returns:
            Dict of {tier_name: Nx3 float64 array} with ghost seeds per tier.
        """
        per_tier = {t.name: [] for t in self.tiers}
        for L_val, tier_seeds in self._ghost_buffer:
            if abs(L_current - L_val) <= self.kdtree_radius:
                for tier_name, seeds in tier_seeds.items():
                    if len(seeds) > 0:
                        per_tier[tier_name].append(seeds)

        result = {}
        for tier_name, arrays in per_tier.items():
            if arrays:
                result[tier_name] = np.vstack(arrays)
            else:
                result[tier_name] = np.empty((0, 3), dtype=np.float64)
        return result

    def _prune_ghost_buffer(self, L_current):
        """Remove ghost buffer entries too far behind the current slice."""
        self._ghost_buffer = [
            (L_val, tier_seeds) for L_val, tier_seeds in self._ghost_buffer
            if L_current - L_val <= self.kdtree_radius
        ]

    def pack_slice(self, slice_id, L_value, L_arr, a_arr, b_arr,
                   ghost_seeds=None, progress_callback=None):
        """Pack a single L* slice across all threshold tiers.

        Args:
            slice_id: Index of this L* slice.
            L_value: The L* lightness value.
            L_arr, a_arr, b_arr: Arrays of valid (in-gamut) points for this slice.
            ghost_seeds: Optional dict of {tier_name: Nx3 array} with per-tier
                seed positions from adjacent slices. Each tier is only checked
                against ghost seeds that were actually seeds at that tier.
            progress_callback: Optional callback(points_processed, total) for progress.

        Returns:
            SliceResult with per-tier seed counts and seed data.
        """
        start = time.time()
        n_points = len(L_arr)

        if n_points == 0:
            return SliceResult(
                slice_id=slice_id,
                L_value=L_value,
                valid_points=0,
                seeds_per_tier={t.name: 0 for t in self.tiers},
                seeds=[],
                duration_seconds=0.0,
                points_processed=0,
            )

        # Stack points for KD-tree: Nx3
        points = np.column_stack([L_arr, a_arr, b_arr])

        # Build spatial index for local candidates
        spatial = SpatialIndex(
            points,
            radius=self.kdtree_radius,
            rebuild_interval=self.rebuild_interval,
        )

        # Build per-tier read-only KD-trees for ghost seeds
        ghost_trees = {}    # tier_name -> cKDTree
        ghost_points = {}   # tier_name -> Nx3 ndarray
        if ghost_seeds is not None:
            for tier_name, ghost_arr in ghost_seeds.items():
                if len(ghost_arr) > 0:
                    ghost_points[tier_name] = np.asarray(ghost_arr, dtype=np.float64)
                    ghost_trees[tier_name] = cKDTree(ghost_points[tier_name])

        # Per-tier claimed bitmaps for this slice
        tier_claimed = [np.zeros(n_points, dtype=bool) for _ in self.tiers]
        tier_slice_counts = [0] * len(self.tiers)
        slice_seeds = []
        # Collect seed positions per tier for the ghost buffer
        tier_seed_collectors = {t.name: [] for t in self.tiers}

        # Iterate through points — skip any already claimed at tier 0 (JND, smallest)
        points_processed = 0
        for idx in range(n_points):
            if not self._running:
                break

            # Skip if already claimed at the finest tier (JND)
            if tier_claimed[0][idx]:
                continue

            # Skip if deleted in spatial index
            if spatial.is_deleted(idx):
                continue

            point = points[idx]
            L_p, a_p, b_p = point[0], point[1], point[2]

            # Check ghost seeds for suppression — each tier against its own ghosts
            ghost_suppresses = [False] * len(self.tiers)
            for ti, tier in enumerate(self.tiers):
                if tier.name in ghost_trees:
                    g_idx = ghost_trees[tier.name].query_ball_point(
                        point, self.kdtree_radius)
                    if len(g_idx) > 0:
                        g_idx = np.array(g_idx, dtype=np.intp)
                        gp = ghost_points[tier.name]
                        g_L = gp[g_idx, 0]
                        g_a = gp[g_idx, 1]
                        g_b = gp[g_idx, 2]
                        g_dist = delta_e_2000(L_p, a_p, b_p, g_L, g_a, g_b)
                        if np.any(g_dist <= tier.delta_e):
                            ghost_suppresses[ti] = True

            # Query local KD-tree for neighbors
            neighbor_indices = spatial.query_neighbors(point)

            if len(neighbor_indices) == 0:
                # No local neighbors — check ghost suppression per-tier
                for ti, tier in enumerate(self.tiers):
                    if tier_claimed[ti][idx]:
                        continue
                    if ghost_suppresses[ti]:
                        tier_claimed[ti][idx] = True  # Claimed by ghost, not a seed
                    else:
                        tier_claimed[ti][idx] = True
                        tier_slice_counts[ti] += 1
                        tier.seed_count += 1
                        seed_info = {
                            "L": float(L_p), "a": float(a_p), "b": float(b_p),
                            "slice_id": slice_id, "tier": tier.name,
                            "hex": lab_to_srgb_hex(L_p, a_p, b_p),
                        }
                        slice_seeds.append(seed_info)
                        tier.last_seed = seed_info
                        tier_seed_collectors[tier.name].append([L_p, a_p, b_p])
                continue

            # Compute exact ΔE2000 to all local neighbors
            n_L = points[neighbor_indices, 0]
            n_a = points[neighbor_indices, 1]
            n_b = points[neighbor_indices, 2]
            distances = delta_e_2000(L_p, a_p, b_p, n_L, n_a, n_b)

            # Process each tier
            for ti, tier in enumerate(self.tiers):
                if tier_claimed[ti][idx]:
                    continue

                if ghost_suppresses[ti]:
                    # Ghost seed covers this point — claim it and local
                    # neighbors within threshold, but do NOT count as a seed
                    tier_claimed[ti][idx] = True
                    within = distances <= tier.delta_e
                    tier_claimed[ti][neighbor_indices[within]] = True
                    continue

                # This point is unclaimed at this tier — it becomes a seed
                tier_claimed[ti][idx] = True
                tier_slice_counts[ti] += 1
                tier.seed_count += 1

                seed_info = {
                    "L": float(L_p), "a": float(a_p), "b": float(b_p),
                    "slice_id": slice_id, "tier": tier.name,
                    "hex": lab_to_srgb_hex(L_p, a_p, b_p),
                }
                slice_seeds.append(seed_info)
                tier.last_seed = seed_info
                tier_seed_collectors[tier.name].append([L_p, a_p, b_p])

                # Claim all neighbors within this tier's threshold
                within = distances <= tier.delta_e
                claim_indices = neighbor_indices[within]
                tier_claimed[ti][claim_indices] = True

            # Mark JND-claimed neighbors as deleted in spatial index
            # (only need to track finest tier for the outer loop skip)
            jnd_within = distances <= self.tiers[0].delta_e
            spatial.mark_deleted(neighbor_indices[jnd_within])

            points_processed += 1
            if progress_callback and points_processed % 1000 == 0:
                progress_callback(points_processed, n_points)

            # Note: we do NOT rebuild the KD-tree mid-slice. Rebuilding
            # would remap indices and invalidate the outer loop's idx and
            # the claimed bitmaps. Lazy deletion (filtering deleted points
            # from query results) is sufficient for per-slice trees which
            # are small enough that degraded query performance is negligible.

        duration = time.time() - start

        # Convert per-tier seed positions to arrays for the ghost buffer
        tier_seeds = {}
        for tier_name, positions in tier_seed_collectors.items():
            if positions:
                tier_seeds[tier_name] = np.array(positions, dtype=np.float64).reshape(-1, 3)
            else:
                tier_seeds[tier_name] = np.empty((0, 3), dtype=np.float64)

        result = SliceResult(
            slice_id=slice_id,
            L_value=L_value,
            valid_points=n_points,
            seeds_per_tier={t.name: tier_slice_counts[i] for i, t in enumerate(self.tiers)},
            seeds=slice_seeds,
            duration_seconds=duration,
            points_processed=points_processed,
            tier_seed_positions=tier_seeds,
        )
        return result

    def pack_all(self, grid, resume_from=0, slice_callback=None):
        """Run packing across all L* slices.

        Args:
            grid: GridGenerator instance.
            resume_from: L* slice index to resume from (0 for fresh start).
            slice_callback: Optional callback(SliceResult) called after each slice.

        Returns:
            Dict with final results.
        """
        self.start_time = time.time()
        L_values = grid.get_L_values()

        logger.info(
            f"Starting packing: {len(L_values)} L* slices, "
            f"thresholds: {[t.delta_e for t in self.tiers]}"
        )

        for slice_id in range(resume_from, len(L_values)):
            if not self._running:
                logger.info(f"Packer stopped at slice {slice_id}")
                break

            L_value = L_values[slice_id]
            self.current_slice = slice_id

            # Generate candidate points for this slice
            L_arr, a_arr, b_arr = grid.generate_slice(L_value)

            # Filter to gamut
            L_valid, a_valid, b_valid, mask = self.gamut.filter_valid(L_arr, a_arr, b_arr)
            self.total_valid_points += len(L_valid)

            # Gather per-tier ghost seeds from recent slices
            ghost_seeds = self._gather_ghost_seeds(L_value)
            n_ghosts = sum(len(v) for v in ghost_seeds.values())

            logger.info(
                f"Slice {slice_id}/{len(L_values)} L*={L_value:.2f}: "
                f"{len(L_valid)}/{len(L_arr)} in-gamut points, "
                f"{n_ghosts} ghost seeds"
            )

            # Pack this slice with ghost awareness
            result = self.pack_slice(
                slice_id, L_value, L_valid, a_valid, b_valid,
                ghost_seeds=ghost_seeds,
            )
            self.total_points_processed += result.points_processed

            # Add this slice's per-tier seeds to the ghost buffer
            if result.tier_seed_positions is not None:
                has_seeds = any(len(v) > 0 for v in result.tier_seed_positions.values())
                if has_seeds:
                    self._ghost_buffer.append((L_value, result.tier_seed_positions))

            # Prune old entries from the ghost buffer
            self._prune_ghost_buffer(L_value)

            logger.info(
                f"  Seeds: {result.seeds_per_tier} in {result.duration_seconds:.1f}s"
            )

            if slice_callback:
                slice_callback(result)

        elapsed = time.time() - self.start_time
        return {
            "completed": not self._running or slice_id >= len(L_values) - 1,
            "slices_processed": self.current_slice + 1,
            "total_slices": len(L_values),
            "tier_counts": self.get_tier_counts(),
            "total_valid_points": self.total_valid_points,
            "elapsed_seconds": elapsed,
        }

    def get_state(self):
        """Get current state for checkpointing."""
        # Serialize ghost buffer: convert per-tier numpy arrays to lists for JSON
        ghost_buffer_serialized = []
        for L_val, tier_seeds in self._ghost_buffer:
            tier_dict = {name: seeds.tolist() for name, seeds in tier_seeds.items()}
            ghost_buffer_serialized.append((L_val, tier_dict))

        return {
            "current_slice": self.current_slice,
            "tier_counts": self.get_tier_counts(),
            "total_points_processed": self.total_points_processed,
            "total_valid_points": self.total_valid_points,
            "elapsed_seconds": time.time() - self.start_time if self.start_time else 0,
            "ghost_buffer": ghost_buffer_serialized,
        }

    def restore_state(self, state):
        """Restore packer state from a checkpoint."""
        self.current_slice = state.get("current_slice", 0)
        self.total_points_processed = state.get("total_points_processed", 0)
        self.total_valid_points = state.get("total_valid_points", 0)

        tier_counts = state.get("tier_counts", {})
        for tier in self.tiers:
            if tier.name in tier_counts:
                tier.seed_count = tier_counts[tier.name]

        # Restore per-tier ghost buffer
        ghost_data = state.get("ghost_buffer", [])
        self._ghost_buffer = []
        for L_val, tier_dict in ghost_data:
            restored = {name: np.array(seeds, dtype=np.float64)
                       for name, seeds in tier_dict.items()}
            self._ghost_buffer.append((L_val, restored))

    def is_complete(self):
        """Check if all slices have been processed."""
        grid = GridGenerator(self.grid_config)
        return self.current_slice >= grid.total_slices() - 1
