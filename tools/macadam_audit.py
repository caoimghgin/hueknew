#!/usr/bin/env python3
"""Audit census seeds against the Rösch–MacAdam optimal color boundary.

The Rösch–MacAdam solid defines the absolute boundary of physically
realizable surface colors under a given illuminant. Any seed outside
this boundary cannot correspond to a real color.

This script:
1. Computes the optimal color boundary at each L* level
2. Tests all census seeds against it
3. Reports how many seeds are invalid (outside the boundary)
"""

import csv
import sys
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# CIE 1931 2° color matching functions (5nm, 380–780nm)
# Source: CIE 015:2004, Table 1
# ---------------------------------------------------------------------------
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

# D65 illuminant SPD at 5nm intervals (380–780nm), CIE standard
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

# D65 white point
D65_WHITE_X = 95.047
D65_WHITE_Y = 100.000
D65_WHITE_Z = 108.883

N_WAVELENGTHS = len(D65_SPD)  # 81 wavelengths (380–780nm at 5nm)


# ---------------------------------------------------------------------------
# CIELAB conversion
# ---------------------------------------------------------------------------
_DELTA = 6.0 / 29.0
_DELTA_SQ = _DELTA ** 2
_DELTA_CU = _DELTA ** 3

def _f(t):
    result = np.empty_like(t, dtype=np.float64)
    mask = t > _DELTA_CU
    result[mask] = np.cbrt(t[mask])
    result[~mask] = t[~mask] / (3.0 * _DELTA_SQ) + 4.0 / 29.0
    return result

def xyz_to_lab(X, Y, Z):
    fx = _f(np.asarray(X, dtype=np.float64) / D65_WHITE_X)
    fy = _f(np.asarray(Y, dtype=np.float64) / D65_WHITE_Y)
    fz = _f(np.asarray(Z, dtype=np.float64) / D65_WHITE_Z)
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return L, a, b


# ---------------------------------------------------------------------------
# Precompute wavelength-weighted tristimulus contributions
# Each wavelength contributes: E(λ) * x̄(λ), E(λ) * ȳ(λ), E(λ) * z̄(λ)
# ---------------------------------------------------------------------------
xbar = CIE_1931_2DEG[:, 1]
ybar = CIE_1931_2DEG[:, 2]
zbar = CIE_1931_2DEG[:, 3]

# Weighted contributions per wavelength (what R=1 at that wavelength adds)
# Normalize so that Y of the perfect white (R=1 everywhere) = 100
k = 100.0 / np.sum(D65_SPD * ybar)
wx = k * D65_SPD * xbar  # X contribution per wavelength
wy = k * D65_SPD * ybar  # Y contribution per wavelength
wz = k * D65_SPD * zbar  # Z contribution per wavelength

# Total XYZ for the perfect reflector (should be ≈ D65 white point)
X_white = np.sum(wx)
Y_white = np.sum(wy)
Z_white = np.sum(wz)
print(f"White point check: X={X_white:.3f} Y={Y_white:.3f} Z={Z_white:.3f}")
print(f"Expected:          X={D65_WHITE_X:.3f} Y={D65_WHITE_Y:.3f} Z={D65_WHITE_Z:.3f}")


# ---------------------------------------------------------------------------
# Compute Rösch–MacAdam optimal color boundary
#
# An optimal color has reflectance R(λ) ∈ {0, 1} with at most two
# transitions. There are two types:
#   Band:  R=1 for λ ∈ [λ₁, λ₂], else 0
#   Notch: R=0 for λ ∈ [λ₁, λ₂], else 1
#
# For each (λ₁, λ₂) pair, compute XYZ → Lab.
# At each L* level, the convex hull of achievable (a*, b*) = the boundary.
# ---------------------------------------------------------------------------
def compute_optimal_colors():
    """Compute all optimal colors (band and notch types).

    Returns arrays of (L, a, b) for all optimal color spectra.
    """
    n = N_WAVELENGTHS

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

    # Add the two extremes
    # Pure black (R=0 everywhere)
    all_L.append(0.0)
    all_a.append(0.0)
    all_b.append(0.0)

    # Pure white (R=1 everywhere)
    L_w, a_w, b_w = xyz_to_lab(X_white, Y_white, Z_white)
    all_L.append(float(L_w))
    all_a.append(float(a_w))
    all_b.append(float(b_w))

    return np.array(all_L), np.array(all_a), np.array(all_b)


def build_boundary_at_L_levels(opt_L, opt_a, opt_b, L_levels, tolerance=0.5):
    """For each L* level, find the convex hull of optimal colors in a*b* space.

    Returns a dict: L_level -> convex hull polygon (Nx2 array of a*, b*).
    """
    from scipy.spatial import ConvexHull

    boundaries = {}
    for L_target in L_levels:
        mask = np.abs(opt_L - L_target) < tolerance
        if np.sum(mask) < 3:
            # Too few points — widen tolerance
            mask = np.abs(opt_L - L_target) < tolerance * 3
        if np.sum(mask) < 3:
            continue

        points = np.column_stack((opt_a[mask], opt_b[mask]))
        try:
            hull = ConvexHull(points)
            hull_pts = points[hull.vertices]
            boundaries[L_target] = hull_pts
        except Exception:
            continue

    return boundaries


def point_in_polygon(px, py, polygon):
    """Ray-casting point-in-polygon test (vectorized)."""
    n = len(polygon)
    inside = np.zeros(len(px), dtype=bool)

    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]

        # Check if ray from (px, py) rightward crosses edge (i, j)
        cond = ((yi > py) != (yj > py)) & \
               (px < (xj - xi) * (py - yi) / (yj - yi + 1e-30) + xi)
        inside = inside ^ cond
        j = i

    return inside


def main():
    print("=" * 60)
    print("Rösch–MacAdam Optimal Color Boundary Audit")
    print("=" * 60)

    # Step 1: Compute all optimal colors
    print("\nStep 1: Computing optimal color boundary...")
    opt_L, opt_a, opt_b = compute_optimal_colors()
    print(f"  Generated {len(opt_L):,} optimal color spectra")
    print(f"  L* range: [{opt_L.min():.1f}, {opt_L.max():.1f}]")
    print(f"  a* range: [{opt_a.min():.1f}, {opt_a.max():.1f}]")
    print(f"  b* range: [{opt_b.min():.1f}, {opt_b.max():.1f}]")

    # Step 2: Build convex hull boundaries at each L* level
    print("\nStep 2: Building convex hull boundaries at each L* level...")
    L_levels = np.arange(0, 101, 1.0)  # every 1 L* unit
    boundaries = build_boundary_at_L_levels(opt_L, opt_a, opt_b, L_levels, tolerance=0.5)
    print(f"  Built boundaries for {len(boundaries)} L* levels")

    # Step 3: Load census seeds
    data_dir = Path(__file__).parent.parent / "data"

    for tier_name, filename in [
        ("Obvious (ΔE=5.0)", "obvious.csv"),
        ("Acceptability (ΔE=2.0)", "acceptability.csv"),
        ("JND (ΔE=1.0)", "jnd.csv"),
    ]:
        csv_path = data_dir / filename
        if not csv_path.exists():
            print(f"\n  Skipping {tier_name}: {filename} not found")
            continue

        print(f"\n{'=' * 60}")
        print(f"Auditing: {tier_name}")
        print(f"{'=' * 60}")

        L_vals, a_vals, b_vals = [], [], []
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                L_vals.append(float(row["L"]))
                a_vals.append(float(row["a"]))
                b_vals.append(float(row["b"]))

        L_arr = np.array(L_vals)
        a_arr = np.array(a_vals)
        b_arr = np.array(b_vals)
        total = len(L_arr)
        print(f"  Total seeds: {total:,}")

        # Step 4: Test each seed against its L*-level boundary
        valid = np.ones(total, dtype=bool)  # assume valid until proven otherwise
        no_boundary = 0

        for L_target, hull_pts in boundaries.items():
            # Find seeds at this L* level (within 0.5)
            mask = np.abs(L_arr - L_target) < 0.5
            if not np.any(mask):
                continue

            idx = np.where(mask)[0]
            inside = point_in_polygon(a_arr[idx], b_arr[idx], hull_pts)
            valid[idx[~inside]] = False

        # Seeds at L* levels without a boundary (shouldn't happen much)
        for i in range(total):
            L_rounded = round(L_arr[i])
            if L_rounded not in boundaries:
                no_boundary += 1

        invalid = np.sum(~valid)
        print(f"  Valid seeds:   {total - invalid:,} ({100 * (total - invalid) / total:.1f}%)")
        print(f"  INVALID seeds: {invalid:,} ({100 * invalid / total:.1f}%)")
        if no_boundary > 0:
            print(f"  (No boundary data for {no_boundary} seeds)")

        # Breakdown by L* range
        print(f"\n  Breakdown by L* range:")
        print(f"  {'L* range':<15} {'Total':>8} {'Invalid':>8} {'%':>7}")
        print(f"  {'-'*42}")
        for lo, hi, label in [
            (0, 5, "0–5"),
            (5, 10, "5–10"),
            (10, 20, "10–20"),
            (20, 40, "20–40"),
            (40, 60, "40–60"),
            (60, 80, "60–80"),
            (80, 90, "80–90"),
            (90, 95, "90–95"),
            (95, 100, "95–100"),
            (100, 101, "100"),
        ]:
            mask = (L_arr >= lo) & (L_arr < hi)
            n = np.sum(mask)
            if n == 0:
                continue
            inv = np.sum(mask & ~valid)
            print(f"  {label:<15} {n:>8,} {inv:>8,} {100 * inv / n:>6.1f}%")

        # Max chroma at extreme L* levels
        print(f"\n  Max chroma (sqrt(a²+b²)) at extreme L* levels:")
        for L_target in [0, 5, 10, 90, 95, 100]:
            mask = np.abs(L_arr - L_target) < 1.0
            if np.any(mask):
                chroma = np.sqrt(a_arr[mask]**2 + b_arr[mask]**2)
                print(f"    L*≈{L_target:>3}: max chroma = {chroma.max():.1f}"
                      f"  (n={np.sum(mask):,})")

                # What does the boundary say?
                if L_target in boundaries:
                    hull = boundaries[L_target]
                    hull_chroma = np.sqrt(hull[:, 0]**2 + hull[:, 1]**2)
                    print(f"           boundary max chroma = {hull_chroma.max():.1f}")


if __name__ == "__main__":
    main()
