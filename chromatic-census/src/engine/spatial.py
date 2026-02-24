"""KD-tree spatial indexing for efficient neighbor search.

Wraps scipy.spatial.cKDTree with lazy deletion and periodic rebuilds
to avoid the cost of rebuilding the tree on every point removal.
"""

import numpy as np
from scipy.spatial import cKDTree


class SpatialIndex:
    """KD-tree with lazy deletion for neighbor queries in CIELAB space."""

    def __init__(self, points, radius=6.0, rebuild_interval=10000):
        """
        Args:
            points: Nx3 array of (L*, a*, b*) coordinates.
            radius: Euclidean search radius (conservative overestimate of
                    the largest ΔE2000 threshold).
            rebuild_interval: Rebuild the tree after this many deletions.
        """
        self._points = np.asarray(points, dtype=np.float64)
        self._radius = radius
        self._rebuild_interval = rebuild_interval
        self._deleted = np.zeros(len(self._points), dtype=bool)
        self._delete_count = 0
        self._tree = cKDTree(self._points)

    def query_neighbors(self, point):
        """Find all points within the Euclidean radius of the given point.

        Args:
            point: 1D array of (L*, a*, b*).

        Returns:
            Array of indices into the original points array. Deleted
            points are excluded.
        """
        indices = self._tree.query_ball_point(point, self._radius)
        indices = np.array(indices, dtype=np.intp)
        if len(indices) == 0:
            return indices
        # Filter out deleted points
        mask = ~self._deleted[indices]
        return indices[mask]

    def mark_deleted(self, indices):
        """Mark points as deleted (they remain in the tree but are skipped).

        Args:
            indices: Array of point indices to mark as deleted.
        """
        indices = np.asarray(indices, dtype=np.intp)
        newly_deleted = ~self._deleted[indices]
        self._deleted[indices] = True
        self._delete_count += int(newly_deleted.sum())

    def is_deleted(self, index):
        """Check if a single point has been deleted."""
        return self._deleted[index]

    def needs_rebuild(self):
        """Check if the tree should be rebuilt based on deletion count."""
        return self._delete_count >= self._rebuild_interval

    def rebuild(self):
        """Rebuild the KD-tree with only non-deleted points.

        Returns a mapping from new indices to original indices.
        """
        alive_mask = ~self._deleted
        alive_indices = np.where(alive_mask)[0]

        if len(alive_indices) == 0:
            return np.array([], dtype=np.intp)

        self._points = self._points[alive_mask]
        self._deleted = np.zeros(len(self._points), dtype=bool)
        self._delete_count = 0
        self._tree = cKDTree(self._points)

        return alive_indices

    def get_point(self, index):
        """Get the L*a*b* coordinates of a point by index."""
        return self._points[index]

    def __len__(self):
        """Number of non-deleted points."""
        return len(self._points) - int(self._deleted.sum())
