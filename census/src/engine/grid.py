"""CIELAB grid generation.

Generates candidate points in CIELAB space for the packing algorithm.
Processing is organized by L* slice for cache locality and natural
checkpointing boundaries.
"""

import numpy as np


class GridGenerator:
    """Generates the CIELAB candidate point grid."""

    def __init__(self, config):
        """
        Args:
            config: Dict with keys L_min, L_max, L_step, a_min, a_max, a_step,
                    b_min, b_max, b_step.
        """
        self.L_min = config["L_min"]
        self.L_max = config["L_max"]
        self.L_step = config["L_step"]
        self.a_min = config["a_min"]
        self.a_max = config["a_max"]
        self.a_step = config["a_step"]
        self.b_min = config["b_min"]
        self.b_max = config["b_max"]
        self.b_step = config["b_step"]

        self._L_values = np.arange(self.L_min, self.L_max + self.L_step / 2, self.L_step)
        self._a_values = np.arange(self.a_min, self.a_max + self.a_step / 2, self.a_step)
        self._b_values = np.arange(self.b_min, self.b_max + self.b_step / 2, self.b_step)

    def get_L_values(self):
        """Return array of all L* values to process."""
        return self._L_values

    def total_slices(self):
        """Number of L* slices."""
        return len(self._L_values)

    def points_per_slice(self):
        """Number of candidate points per L* slice (before gamut filtering)."""
        return len(self._a_values) * len(self._b_values)

    def estimate_total_points(self):
        """Rough total candidate points across all slices."""
        return self.total_slices() * self.points_per_slice()

    def generate_slice(self, L_value):
        """Generate all candidate (L*, a*, b*) points for a single L* value.

        Args:
            L_value: The L* lightness value for this slice.

        Returns:
            Tuple of (L, a, b) arrays, each of shape (N,) where
            N = num_a_steps * num_b_steps.
        """
        a_grid, b_grid = np.meshgrid(self._a_values, self._b_values, indexing="ij")
        a_flat = a_grid.ravel()
        b_flat = b_grid.ravel()
        L_flat = np.full_like(a_flat, L_value)
        return L_flat, a_flat, b_flat
