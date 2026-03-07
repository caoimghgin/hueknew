"""CIE 1931 2-degree standard observer data and D65 illuminant reference values.

All data is hardcoded from published CIE standards to avoid file I/O at import time.
Includes Rösch–MacAdam optimal color boundary computation.
"""

import numpy as np

# CIE D65 standard illuminant reference white point (2-degree observer)
D65_WHITE_X = 95.047
D65_WHITE_Y = 100.000
D65_WHITE_Z = 108.883

# CIE D65 illuminant spectral power distribution at 5nm intervals (380–780nm)
# Source: CIE 015:2004
D65_SPD = np.array([
    49.9755, 52.3118, 54.6482, 68.7015, 82.7549,
    87.1204, 91.486,  92.4589, 93.4318, 90.057,
    86.6823, 95.7736, 104.865, 110.936, 117.008,
    117.41,  117.812, 116.336, 114.861, 115.392,
    115.923, 112.367, 108.811, 109.082, 109.354,
    108.578, 107.802, 106.296, 104.79,  106.239,
    107.689, 106.047, 104.405, 104.225, 104.046,
    102.023, 100.0,   98.1671, 96.3342, 96.0611,
    95.788,  92.2368, 88.6856, 89.3459, 90.0062,
    89.8026, 89.5991, 88.6489, 87.6987, 85.4936,
    83.2886, 83.4939, 83.6992, 81.863,  80.0268,
    80.1207, 80.2146, 81.2462, 82.2778, 80.281,
    78.2842, 74.0027, 69.7213, 70.6652, 71.6091,
    72.979,  74.349,  67.9765, 61.604,  65.7448,
    69.8856, 72.4863, 75.087,  69.3398, 63.5927,
    55.0054, 46.4182, 56.6118, 66.8054, 65.0941,
    63.3828,
])

# CIE 1931 2-degree standard observer color matching functions (5nm intervals)
# Columns: wavelength (nm), x_bar, y_bar, z_bar
# Source: CIE 015:2004, Table 1
CIE_1931_2DEG = np.array([
    [380, 0.001368, 0.000039, 0.006450],
    [385, 0.002236, 0.000064, 0.010550],
    [390, 0.004243, 0.000120, 0.020050],
    [395, 0.007650, 0.000217, 0.036210],
    [400, 0.014310, 0.000396, 0.067850],
    [405, 0.023190, 0.000640, 0.110200],
    [410, 0.043510, 0.001210, 0.207400],
    [415, 0.077630, 0.002180, 0.371300],
    [420, 0.134380, 0.004000, 0.645600],
    [425, 0.214770, 0.007300, 1.039050],
    [430, 0.283900, 0.011600, 1.385600],
    [435, 0.328500, 0.016840, 1.622960],
    [440, 0.348280, 0.023000, 1.747060],
    [445, 0.348060, 0.029800, 1.782600],
    [450, 0.336200, 0.038000, 1.772110],
    [455, 0.318700, 0.048000, 1.744100],
    [460, 0.290800, 0.060000, 1.669200],
    [465, 0.251100, 0.073900, 1.528100],
    [470, 0.195360, 0.090980, 1.287640],
    [475, 0.142100, 0.112600, 1.041900],
    [480, 0.095640, 0.139020, 0.812950],
    [485, 0.058010, 0.169300, 0.616200],
    [490, 0.032010, 0.208020, 0.465180],
    [495, 0.014700, 0.258600, 0.353300],
    [500, 0.004900, 0.323000, 0.272000],
    [505, 0.002400, 0.407300, 0.212300],
    [510, 0.009300, 0.503000, 0.158200],
    [515, 0.029100, 0.608200, 0.111700],
    [520, 0.063270, 0.710000, 0.078250],
    [525, 0.109600, 0.793200, 0.057250],
    [530, 0.165500, 0.862000, 0.042160],
    [535, 0.225750, 0.914850, 0.029840],
    [540, 0.290400, 0.954000, 0.020300],
    [545, 0.359700, 0.980300, 0.013400],
    [550, 0.433450, 0.994950, 0.008750],
    [555, 0.512050, 1.000110, 0.005750],
    [560, 0.594500, 0.995000, 0.003900],
    [565, 0.678400, 0.978600, 0.002750],
    [570, 0.762100, 0.952000, 0.002100],
    [575, 0.842500, 0.915400, 0.001800],
    [580, 0.916300, 0.870000, 0.001650],
    [585, 0.978600, 0.816300, 0.001400],
    [590, 1.026300, 0.757000, 0.001100],
    [595, 1.056700, 0.694900, 0.001000],
    [600, 1.062200, 0.631000, 0.000800],
    [605, 1.045600, 0.566800, 0.000600],
    [610, 1.002600, 0.503000, 0.000340],
    [615, 0.938400, 0.441200, 0.000240],
    [620, 0.854450, 0.381000, 0.000190],
    [625, 0.751400, 0.321000, 0.000100],
    [630, 0.642400, 0.265000, 0.000050],
    [635, 0.541900, 0.217000, 0.000030],
    [640, 0.447900, 0.175000, 0.000020],
    [645, 0.360800, 0.138200, 0.000010],
    [650, 0.283500, 0.107000, 0.000000],
    [655, 0.218700, 0.081600, 0.000000],
    [660, 0.164900, 0.061000, 0.000000],
    [665, 0.121200, 0.044580, 0.000000],
    [670, 0.087400, 0.032000, 0.000000],
    [675, 0.063600, 0.023200, 0.000000],
    [680, 0.046770, 0.017000, 0.000000],
    [685, 0.032900, 0.011920, 0.000000],
    [690, 0.022700, 0.008210, 0.000000],
    [695, 0.015840, 0.005723, 0.000000],
    [700, 0.011359, 0.004102, 0.000000],
    [705, 0.008111, 0.002929, 0.000000],
    [710, 0.005790, 0.002091, 0.000000],
    [715, 0.004109, 0.001484, 0.000000],
    [720, 0.002899, 0.001047, 0.000000],
    [725, 0.002049, 0.000740, 0.000000],
    [730, 0.001440, 0.000520, 0.000000],
    [735, 0.001000, 0.000361, 0.000000],
    [740, 0.000690, 0.000249, 0.000000],
    [745, 0.000476, 0.000172, 0.000000],
    [750, 0.000332, 0.000120, 0.000000],
    [755, 0.000235, 0.000085, 0.000000],
    [760, 0.000166, 0.000060, 0.000000],
    [765, 0.000117, 0.000042, 0.000000],
    [770, 0.000083, 0.000030, 0.000000],
    [775, 0.000059, 0.000021, 0.000000],
    [780, 0.000042, 0.000015, 0.000000],
])


def get_spectral_locus_polygon():
    """Compute the CIE 1931 chromaticity diagram boundary (spectral locus + purple line).

    Returns an Nx2 array of (x, y) chromaticity coordinates forming a closed polygon.
    The spectral locus runs from 380nm to 780nm, and the purple line closes it.
    """
    x_bar = CIE_1931_2DEG[:, 1]
    y_bar = CIE_1931_2DEG[:, 2]
    z_bar = CIE_1931_2DEG[:, 3]

    total = x_bar + y_bar + z_bar
    # Avoid division by zero at wavelength extremes
    mask = total > 1e-10
    x = np.zeros_like(x_bar)
    y = np.zeros_like(y_bar)
    x[mask] = x_bar[mask] / total[mask]
    y[mask] = y_bar[mask] / total[mask]

    # Keep only valid points (where total > threshold)
    valid = mask & (y > 1e-10)
    polygon = np.column_stack([x[valid], y[valid]])

    # The polygon is already ordered by wavelength (spectral locus).
    # Close the polygon by connecting 780nm back to 380nm (the purple line).
    # numpy's polygon operations handle the closure.
    return polygon


# Pre-compute at import time
_SPECTRAL_LOCUS_POLYGON = None


def get_cached_spectral_locus():
    """Get the cached spectral locus polygon, computing it once on first call."""
    global _SPECTRAL_LOCUS_POLYGON
    if _SPECTRAL_LOCUS_POLYGON is None:
        _SPECTRAL_LOCUS_POLYGON = get_spectral_locus_polygon()
    return _SPECTRAL_LOCUS_POLYGON


# ---------------------------------------------------------------------------
# Rösch–MacAdam optimal color boundary
#
# The optimal color solid defines the absolute boundary of physically
# realizable surface colors under a given illuminant. An optimal color has
# reflectance R(λ) ∈ {0, 1} with at most two transitions:
#   Band:  R=1 for λ ∈ [λ₁, λ₂], else 0
#   Notch: R=0 for λ ∈ [λ₁, λ₂], else 1
#
# For each (λ₁, λ₂) pair, we compute XYZ → L*a*b*. At each L* level, the
# convex hull of achievable (a*, b*) coordinates defines the gamut boundary.
# ---------------------------------------------------------------------------

def _compute_optimal_colors():
    """Compute all optimal color spectra (band + notch types).

    Returns arrays of (L, a, b) for all optimal colors under D65.
    """
    from .cielab import xyz_to_lab

    xbar = CIE_1931_2DEG[:, 1]
    ybar = CIE_1931_2DEG[:, 2]
    zbar = CIE_1931_2DEG[:, 3]
    n = len(xbar)

    # Normalize so Y of perfect white = 100
    k = 100.0 / np.sum(D65_SPD * ybar)
    wx = k * D65_SPD * xbar
    wy = k * D65_SPD * ybar
    wz = k * D65_SPD * zbar

    X_white = np.sum(wx)
    Y_white = np.sum(wy)
    Z_white = np.sum(wz)

    # Cumulative sums for fast band integral computation
    cum_wx = np.concatenate(([0], np.cumsum(wx)))
    cum_wy = np.concatenate(([0], np.cumsum(wy)))
    cum_wz = np.concatenate(([0], np.cumsum(wz)))

    all_L, all_a, all_b = [], [], []

    for i in range(n):
        for j in range(i, n):
            # Band type: R=1 for wavelengths i through j
            X_band = cum_wx[j + 1] - cum_wx[i]
            Y_band = cum_wy[j + 1] - cum_wy[i]
            Z_band = cum_wz[j + 1] - cum_wz[i]

            if Y_band > 0:
                L, a, b = xyz_to_lab(X_band, Y_band, Z_band)
                all_L.append(float(L))
                all_a.append(float(a))
                all_b.append(float(b))

            # Notch type: R=1 everywhere EXCEPT wavelengths i through j
            X_notch = X_white - X_band
            Y_notch = Y_white - Y_band
            Z_notch = Z_white - Z_band

            if Y_notch > 0:
                L, a, b = xyz_to_lab(X_notch, Y_notch, Z_notch)
                all_L.append(float(L))
                all_a.append(float(a))
                all_b.append(float(b))

    # Add extremes: pure black and pure white
    all_L.append(0.0); all_a.append(0.0); all_b.append(0.0)
    L_w, a_w, b_w = xyz_to_lab(X_white, Y_white, Z_white)
    all_L.append(float(L_w)); all_a.append(float(a_w)); all_b.append(float(b_w))

    return np.array(all_L), np.array(all_a), np.array(all_b)


def _build_macadam_boundaries(opt_L, opt_a, opt_b):
    """Build convex hull boundaries at integer L* levels.

    Returns a dict: L_level (int) -> convex hull polygon (Nx2 array).
    """
    from scipy.spatial import ConvexHull

    boundaries = {}
    for L_target in range(0, 101):
        # Collect optimal colors near this L* level
        tolerance = 0.5
        mask = np.abs(opt_L - L_target) < tolerance
        if np.sum(mask) < 3:
            mask = np.abs(opt_L - L_target) < tolerance * 3
        if np.sum(mask) < 3:
            continue

        points = np.column_stack((opt_a[mask], opt_b[mask]))
        try:
            hull = ConvexHull(points)
            boundaries[L_target] = points[hull.vertices]
        except Exception:
            continue

    return boundaries


# Cache for the MacAdam boundary lookup table
_MACADAM_BOUNDARIES = None


def get_cached_macadam_boundaries():
    """Get the cached Rösch–MacAdam boundary polygons, computing once on first call.

    Returns:
        Dict mapping integer L* (0–100) to Nx2 arrays of (a*, b*) hull vertices.
    """
    global _MACADAM_BOUNDARIES
    if _MACADAM_BOUNDARIES is None:
        opt_L, opt_a, opt_b = _compute_optimal_colors()
        _MACADAM_BOUNDARIES = _build_macadam_boundaries(opt_L, opt_a, opt_b)
    return _MACADAM_BOUNDARIES
