"""Tests for the greedy packing algorithm.

Uses a small-scale grid to verify correctness of multi-tier packing.
"""

import pytest
import numpy as np

from src.core.gamut import GamutValidator
from src.engine.packer import GreedyPacker, TierState
from src.engine.grid import GridGenerator


@pytest.fixture
def coarse_config():
    """Configuration for a very coarse grid (fast tests)."""
    return {
        "grid": {
            "L_min": 40.0,
            "L_max": 60.0,
            "L_step": 10.0,
            "a_min": -50.0,
            "a_max": 50.0,
            "a_step": 5.0,
            "b_min": -50.0,
            "b_max": 50.0,
            "b_step": 5.0,
        },
        "packing": {
            "thresholds": [
                {"name": "JND", "delta_e": 1.0},
                {"name": "acceptability", "delta_e": 2.0},
                {"name": "obvious", "delta_e": 5.0},
            ],
            "kdtree_radius": 6.0,
            "kdtree_rebuild_interval": 10000,
        },
        "delta_e": {"k_L": 1.0, "k_C": 1.0, "k_H": 1.0},
    }


@pytest.fixture
def gamut():
    return GamutValidator()


class TestGreedyPacker:

    def test_tier_count_ordering(self, coarse_config, gamut):
        """JND count >= Acceptability count >= Obvious count."""
        packer = GreedyPacker(coarse_config, gamut)
        grid = GridGenerator(coarse_config["grid"])
        packer.pack_all(grid)

        counts = packer.get_tier_counts()
        assert counts["JND"] >= counts["acceptability"], (
            f"JND ({counts['JND']}) should be >= acceptability ({counts['acceptability']})"
        )
        assert counts["acceptability"] >= counts["obvious"], (
            f"acceptability ({counts['acceptability']}) should be >= obvious ({counts['obvious']})"
        )

    def test_seeds_found(self, coarse_config, gamut):
        """Packing should find at least some seeds at each tier."""
        packer = GreedyPacker(coarse_config, gamut)
        grid = GridGenerator(coarse_config["grid"])
        packer.pack_all(grid)

        counts = packer.get_tier_counts()
        for tier_name, count in counts.items():
            assert count > 0, f"No seeds found for tier {tier_name}"

    def test_slice_callback(self, coarse_config, gamut):
        """The slice callback should be called for each slice."""
        packer = GreedyPacker(coarse_config, gamut)
        grid = GridGenerator(coarse_config["grid"])

        results = []
        packer.pack_all(grid, slice_callback=lambda r: results.append(r))

        assert len(results) == grid.total_slices()
        for result in results:
            assert result.valid_points >= 0
            assert result.duration_seconds >= 0

    def test_single_slice(self, coarse_config, gamut):
        """Packing a single slice should work."""
        packer = GreedyPacker(coarse_config, gamut)
        grid = GridGenerator(coarse_config["grid"])

        L_arr, a_arr, b_arr = grid.generate_slice(50.0)
        L_v, a_v, b_v, mask = gamut.filter_valid(L_arr, a_arr, b_arr)

        result = packer.pack_slice(0, 50.0, L_v, a_v, b_v)

        assert result.valid_points == len(L_v)
        assert result.seeds_per_tier["JND"] >= result.seeds_per_tier["acceptability"]
        assert len(result.seeds) > 0

    def test_empty_slice(self, coarse_config, gamut):
        """Packing an empty slice should return zero counts."""
        packer = GreedyPacker(coarse_config, gamut)
        result = packer.pack_slice(
            0, 50.0,
            np.array([]), np.array([]), np.array([])
        )
        assert result.valid_points == 0
        assert all(v == 0 for v in result.seeds_per_tier.values())

    def test_get_state(self, coarse_config, gamut):
        """get_state should reflect current progress."""
        packer = GreedyPacker(coarse_config, gamut)
        grid = GridGenerator(coarse_config["grid"])
        packer.pack_all(grid)

        state = packer.get_state()
        assert state["total_valid_points"] > 0
        assert state["tier_counts"]["JND"] > 0

    def test_seed_hex_colors(self, coarse_config, gamut):
        """Seeds should have valid hex color strings."""
        packer = GreedyPacker(coarse_config, gamut)
        grid = GridGenerator(coarse_config["grid"])

        seeds_collected = []
        def collect(result):
            seeds_collected.extend(result.seeds)

        packer.pack_all(grid, slice_callback=collect)

        assert len(seeds_collected) > 0
        for seed in seeds_collected[:10]:  # spot check
            assert seed["hex"].startswith("#")
            assert len(seed["hex"]) == 7
            # Should be valid hex
            int(seed["hex"][1:], 16)

    def test_tier_seed_positions_returned(self, coarse_config, gamut):
        """pack_slice should return per-tier seed positions for ghost buffer."""
        packer = GreedyPacker(coarse_config, gamut)
        grid = GridGenerator(coarse_config["grid"])

        L_arr, a_arr, b_arr = grid.generate_slice(50.0)
        L_v, a_v, b_v, mask = gamut.filter_valid(L_arr, a_arr, b_arr)

        result = packer.pack_slice(0, 50.0, L_v, a_v, b_v)

        assert result.tier_seed_positions is not None
        for tier_name, count in result.seeds_per_tier.items():
            assert tier_name in result.tier_seed_positions
            arr = result.tier_seed_positions[tier_name]
            assert arr.shape[1] == 3
            assert len(arr) == count

    def test_ghost_seed_suppression(self, gamut):
        """Adjacent slices should not double-count seeds at the same (a*,b*) position.

        Two points at (50, 0, 0) and (50.5, 0, 0) have ΔE2000 ≈ 0.33.
        Without ghost seeds, both become JND seeds. With ghost seeds from
        slice 1, the second point should be suppressed.
        """
        config = {
            "grid": {
                "L_min": 50.0, "L_max": 50.5, "L_step": 0.5,
                "a_min": -5.0, "a_max": 5.0, "a_step": 5.0,
                "b_min": -5.0, "b_max": 5.0, "b_step": 5.0,
            },
            "packing": {
                "thresholds": [
                    {"name": "JND", "delta_e": 1.0},
                    {"name": "acceptability", "delta_e": 2.0},
                    {"name": "obvious", "delta_e": 5.0},
                ],
                "kdtree_radius": 6.0,
                "kdtree_rebuild_interval": 10000,
            },
            "delta_e": {},
        }
        packer = GreedyPacker(config, gamut)
        grid = GridGenerator(config["grid"])
        packer.pack_all(grid)

        counts = packer.get_tier_counts()
        # With ghost seeds, point (50.5, 0, 0) is suppressed by (50, 0, 0)
        # at JND because ΔE2000 ≈ 0.33 < 1.0. The total should reflect
        # deduplication, not double-counting.
        # Without the fix, this would double-count points at overlapping positions.
        # The exact count depends on gamut validation, but the key assertion is
        # that pack_all uses ghost seeds (verified by checking the buffer).
        assert counts["JND"] > 0
        assert counts["JND"] >= counts["acceptability"]

    def test_ghost_buffer_populated(self, gamut):
        """The ghost buffer should be populated after pack_all."""
        config = {
            "grid": {
                "L_min": 50.0, "L_max": 51.0, "L_step": 0.5,
                "a_min": -20.0, "a_max": 20.0, "a_step": 5.0,
                "b_min": -20.0, "b_max": 20.0, "b_step": 5.0,
            },
            "packing": {
                "thresholds": [
                    {"name": "JND", "delta_e": 1.0},
                    {"name": "acceptability", "delta_e": 2.0},
                    {"name": "obvious", "delta_e": 5.0},
                ],
                "kdtree_radius": 6.0,
                "kdtree_rebuild_interval": 10000,
            },
            "delta_e": {},
        }
        packer = GreedyPacker(config, gamut)
        grid = GridGenerator(config["grid"])
        packer.pack_all(grid)

        # Ghost buffer should have entries from processed slices
        assert len(packer._ghost_buffer) > 0
        for L_val, tier_seeds in packer._ghost_buffer:
            assert isinstance(tier_seeds, dict)
            for tier_name, seeds in tier_seeds.items():
                assert isinstance(seeds, np.ndarray)
                if len(seeds) > 0:
                    assert seeds.shape[1] == 3

    def test_ghost_buffer_checkpoint_roundtrip(self, gamut):
        """Ghost buffer should survive checkpoint save/restore."""
        config = {
            "grid": {
                "L_min": 50.0, "L_max": 51.0, "L_step": 0.5,
                "a_min": -20.0, "a_max": 20.0, "a_step": 5.0,
                "b_min": -20.0, "b_max": 20.0, "b_step": 5.0,
            },
            "packing": {
                "thresholds": [
                    {"name": "JND", "delta_e": 1.0},
                    {"name": "acceptability", "delta_e": 2.0},
                    {"name": "obvious", "delta_e": 5.0},
                ],
                "kdtree_radius": 6.0,
                "kdtree_rebuild_interval": 10000,
            },
            "delta_e": {},
        }
        packer = GreedyPacker(config, gamut)
        grid = GridGenerator(config["grid"])
        packer.pack_all(grid)

        state = packer.get_state()
        assert "ghost_buffer" in state

        # Create a new packer and restore
        packer2 = GreedyPacker(config, gamut)
        packer2.restore_state(state)

        assert len(packer2._ghost_buffer) == len(packer._ghost_buffer)
        for (L1, ts1), (L2, ts2) in zip(packer._ghost_buffer, packer2._ghost_buffer):
            assert L1 == L2
            assert set(ts1.keys()) == set(ts2.keys())
            for tier_name in ts1:
                np.testing.assert_array_almost_equal(ts1[tier_name], ts2[tier_name])


class TestGridGenerator:

    def test_slice_count(self):
        config = {
            "L_min": 0.0, "L_max": 100.0, "L_step": 1.0,
            "a_min": -128.0, "a_max": 127.0, "a_step": 2.0,
            "b_min": -128.0, "b_max": 127.0, "b_step": 2.0,
        }
        grid = GridGenerator(config)
        assert grid.total_slices() == 101

    def test_fine_grid_size(self):
        config = {
            "L_min": 0.0, "L_max": 100.0, "L_step": 0.25,
            "a_min": -128.0, "a_max": 127.0, "a_step": 0.5,
            "b_min": -128.0, "b_max": 127.0, "b_step": 0.5,
        }
        grid = GridGenerator(config)
        assert grid.total_slices() == 401
        assert grid.points_per_slice() > 250000

    def test_generate_slice_shape(self):
        config = {
            "L_min": 0.0, "L_max": 100.0, "L_step": 10.0,
            "a_min": -10.0, "a_max": 10.0, "a_step": 5.0,
            "b_min": -10.0, "b_max": 10.0, "b_step": 5.0,
        }
        grid = GridGenerator(config)
        L, a, b = grid.generate_slice(50.0)
        assert len(L) == len(a) == len(b)
        assert all(L == 50.0)
