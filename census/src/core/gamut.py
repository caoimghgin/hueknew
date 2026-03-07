"""Human visual gamut validation.

Determines whether L*a*b* coordinates correspond to real, physically
realizable surface colors by checking against:
1. The CIE 1931 chromaticity diagram boundary (spectral locus + purple line)
2. The Rösch–MacAdam optimal color solid (luminance-dependent gamut boundary)

The spectral locus check ensures chromaticity is physically possible.
The MacAdam check ensures that chromaticity is achievable at the given
lightness — the gamut narrows to a point at L*=0 (black) and L*=100 (white).
"""

import numpy as np

from .cielab import lab_to_xyz, xyz_to_chromaticity, lab_to_srgb_hex
from .spectral_data import get_cached_spectral_locus, get_cached_macadam_boundaries


class GamutValidator:
    """Validates whether L*a*b* coordinates fall within the human visual gamut."""

    def __init__(self, tolerance=0.001):
        self.tolerance = tolerance
        self._polygon = get_cached_spectral_locus()
        self._macadam = get_cached_macadam_boundaries()

    def is_in_gamut(self, L, a, b):
        """Test whether L*a*b* points are within the human visual gamut.

        Applies both the 2D spectral locus check (chromaticity) and the 3D
        Rösch–MacAdam optimal color boundary (lightness-dependent).

        Args:
            L, a, b: Arrays of L*a*b* coordinates.

        Returns:
            Boolean array — True for points within the gamut.
        """
        L = np.asarray(L, dtype=np.float64)
        a = np.asarray(a, dtype=np.float64)
        b = np.asarray(b, dtype=np.float64)

        # Step 1: L*a*b* -> XYZ
        X, Y, Z = lab_to_xyz(L, a, b)

        # Step 2: Non-negativity check (negative tristimulus = imaginary color)
        non_neg = (X >= -self.tolerance) & (Y >= -self.tolerance) & (Z >= -self.tolerance)

        # Step 3: Convert to chromaticity (x, y)
        x, y = xyz_to_chromaticity(X, Y, Z)

        # Step 4: Point-in-polygon test against spectral locus
        in_locus = self._points_in_polygon(x, y)

        # Step 5: Exclude pure black (L*=0 is valid but X=Y=Z=0 has no chromaticity)
        # Black is in-gamut by convention
        is_black = (X + Y + Z) < 1e-10
        in_locus = in_locus | is_black

        # Step 6: Rösch–MacAdam optimal color boundary check
        # The gamut narrows at extreme lightness — not all chromaticities
        # are achievable at all L* levels. Test each point against the
        # convex hull of optimal colors at its L* level.
        in_macadam = self._check_macadam(L, a, b)

        return non_neg & in_locus & in_macadam

    def _check_macadam(self, L, a, b):
        """Test points against the Rösch–MacAdam boundary at their L* level.

        For each point, finds the nearest integer L* level and tests whether
        (a*, b*) falls inside the convex hull of optimal colors at that level.
        """
        result = np.ones(L.shape, dtype=bool)

        # Points on or very near the neutral axis are always valid (grays).
        # Ray-casting can fail for points on hull vertices/edges, and
        # achromatic colors are physically realizable at every L* level.
        chroma = np.sqrt(a**2 + b**2)
        is_neutral = chroma < 1.0

        # Group points by their nearest integer L* level
        L_rounded = np.clip(np.round(L).astype(int), 0, 100)

        for L_level, hull_pts in self._macadam.items():
            mask = (L_rounded == L_level) & ~is_neutral
            if not np.any(mask):
                continue

            idx = np.where(mask)[0]
            inside = self._points_in_polygon_ab(a[idx], b[idx], hull_pts)
            result[idx] = inside

        return result

    @staticmethod
    def _points_in_polygon_ab(px, py, polygon):
        """Ray-casting point-in-polygon for a*b* coordinates."""
        px = np.asarray(px, dtype=np.float64)
        py = np.asarray(py, dtype=np.float64)
        n = len(polygon)
        inside = np.zeros(px.shape, dtype=bool)

        j = n - 1
        for i in range(n):
            xi, yi = polygon[i, 0], polygon[i, 1]
            xj, yj = polygon[j, 0], polygon[j, 1]

            cond1 = (yi > py) != (yj > py)
            if np.any(cond1):
                slope = (xj - xi) / (yj - yi)
                x_intersect = xi + slope * (py - yi)
                crosses = cond1 & (px < x_intersect)
                inside ^= crosses

            j = i

        return inside

    def filter_valid(self, L, a, b):
        """Return only in-gamut points.

        Args:
            L, a, b: Arrays of L*a*b* coordinates.

        Returns:
            Tuple of (L, a, b) arrays containing only valid points,
            plus the boolean mask.
        """
        mask = self.is_in_gamut(L, a, b)
        return L[mask], a[mask], b[mask], mask

    def _points_in_polygon(self, x, y):
        """Vectorized ray-casting point-in-polygon test.

        Tests whether each (x, y) point is inside the spectral locus polygon.
        Uses the ray casting algorithm: cast a horizontal ray from each point
        and count crossings with polygon edges. Odd crossings = inside.
        """
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)

        poly = self._polygon
        n = len(poly)
        inside = np.zeros(x.shape, dtype=bool)

        # Iterate over polygon edges
        j = n - 1
        for i in range(n):
            xi, yi = poly[i, 0], poly[i, 1]
            xj, yj = poly[j, 0], poly[j, 1]

            # Check if the horizontal ray from (px, py) crosses edge (i, j)
            cond1 = (yi > y) != (yj > y)
            if np.any(cond1):
                # Compute x-coordinate of intersection
                slope = (xj - xi) / (yj - yi)
                x_intersect = xi + slope * (y - yi)
                crosses = cond1 & (x < x_intersect)
                inside ^= crosses

            j = i

        return inside
