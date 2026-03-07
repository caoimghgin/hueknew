"""Fast volume-integration estimator for sanity-checking.

Provides a quick approximation of how many distinguishable colors fit
in the human visual gamut by estimating local ΔE2000 neighborhood
volumes and integrating across the gamut. This is the "fancier hand-waving"
that the greedy packer is designed to replace — but it's useful for
early validation.
"""

import numpy as np

from ..core.gamut import GamutValidator
from ..core.delta_e import delta_e_2000


class VolumeEstimator:
    """Estimates distinguishable color counts via volume integration."""

    def estimate_count(self, threshold, gamut_validator, grid_config):
        """Estimate the number of distinguishable colors at a given ΔE2000 threshold.

        Samples the CIELAB gamut on a coarse grid and estimates local
        packing density by computing the ΔE2000 "volume" around each point.

        Args:
            threshold: ΔE2000 threshold (e.g. 1.0, 2.0, 5.0).
            gamut_validator: GamutValidator instance.
            grid_config: Grid configuration dict.

        Returns:
            Estimated count of distinguishable colors.
        """
        # Use a coarse sampling grid for speed
        L_vals = np.arange(
            grid_config["L_min"],
            grid_config["L_max"] + 0.5,
            2.0
        )
        a_vals = np.arange(grid_config["a_min"], grid_config["a_max"] + 0.5, 4.0)
        b_vals = np.arange(grid_config["b_min"], grid_config["b_max"] + 0.5, 4.0)

        total_volume = 0.0
        total_local_volumes = 0.0
        sample_count = 0

        for L in L_vals:
            a_grid, b_grid = np.meshgrid(a_vals, b_vals, indexing="ij")
            a_flat = a_grid.ravel()
            b_flat = b_grid.ravel()
            L_flat = np.full_like(a_flat, L)

            mask = gamut_validator.is_in_gamut(L_flat, a_flat, b_flat)
            valid_count = mask.sum()
            if valid_count == 0:
                continue

            total_volume += valid_count

            # Sample a subset to estimate local ΔE2000 density
            L_v = L_flat[mask]
            a_v = a_flat[mask]
            b_v = b_flat[mask]

            # For a subset of points, compute the local ΔE2000 neighborhood size
            n_samples = min(50, len(L_v))
            indices = np.linspace(0, len(L_v) - 1, n_samples, dtype=int)

            for idx in indices:
                # Compute ΔE2000 to a small perturbation in each axis
                # to estimate the local Jacobian
                eps = threshold / 2.0
                dL = delta_e_2000(L_v[idx], a_v[idx], b_v[idx],
                                  L_v[idx] + eps, a_v[idx], b_v[idx])
                da = delta_e_2000(L_v[idx], a_v[idx], b_v[idx],
                                  L_v[idx], a_v[idx] + eps, b_v[idx])
                db = delta_e_2000(L_v[idx], a_v[idx], b_v[idx],
                                  L_v[idx], a_v[idx], b_v[idx] + eps)

                # Effective CIELAB radius that corresponds to the ΔE threshold
                # in each direction
                r_L = eps * threshold / max(float(dL), 1e-10)
                r_a = eps * threshold / max(float(da), 1e-10)
                r_b = eps * threshold / max(float(db), 1e-10)

                # Volume of the local ΔE2000 ellipsoid in CIELAB coordinates
                local_vol = (4.0 / 3.0) * np.pi * r_L * r_a * r_b
                total_local_volumes += local_vol
                sample_count += 1

        if sample_count == 0:
            return 0

        # Average local ellipsoid volume
        avg_local_volume = total_local_volumes / sample_count

        # Total gamut volume in CIELAB coordinate units
        # Each grid cell has volume = L_step * a_step * b_step
        cell_volume = 2.0 * 4.0 * 4.0  # coarse grid steps
        gamut_volume = total_volume * cell_volume

        # Sphere packing efficiency ~64% for random packing in 3D
        packing_efficiency = 0.64
        estimated_count = int(gamut_volume * packing_efficiency / avg_local_volume)

        return estimated_count
