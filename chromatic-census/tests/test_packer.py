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
