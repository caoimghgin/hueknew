#!/usr/bin/env python3
"""
Compute gamut volumes in CIELAB space via Monte Carlo sampling.

Two measurements:
1. sRGB and Adobe RGB volume as % of the MacAdam solid (Lab volume)
2. sRGB and Adobe RGB volume as % of the MacAdam solid (perceptual count)

For Lab volume: uniformly sample the Lab bounding box, classify each point.
For MacAdam membership: use KD-tree of our 269K JND seeds as a proxy —
if a random Lab point is within ΔE76 ≈ 1.5 of any seed, it's "inside."
"""

import csv
import time
from pathlib import Path

import numpy as np
from scipy.spatial import KDTree

# --- Color math (vectorized) ---

def lab_to_xyz_vec(Lab):
    """Lab (Nx3) → XYZ (Nx3), D65."""
    L, a, b = Lab[:, 0], Lab[:, 1], Lab[:, 2]
    fy = (L + 16) / 116
    fx = a / 500 + fy
    fz = fy - b / 200

    delta = 6 / 29
    def finv(t):
        out = np.where(t > delta, t ** 3, 3 * delta**2 * (t - 4 / 29))
        return out

    X = 0.95047 * finv(fx)
    Y = 1.00000 * finv(fy)
    Z = 1.08883 * finv(fz)
    return np.column_stack([X, Y, Z])


def xyz_in_gamut(XYZ, mat, tol=1e-6):
    """Check if XYZ points are inside an RGB gamut. Returns bool array."""
    rgb = XYZ @ np.array(mat).T  # (N, 3)
    return np.all((rgb >= -tol) & (rgb <= 1 + tol), axis=1)


# sRGB: XYZ → linear sRGB
SRGB_MAT = [
    [ 3.2404542, -1.5371385, -0.4985314],
    [-0.9692660,  1.8760108,  0.0415560],
    [ 0.0556434, -0.2040259,  1.0572252],
]

# Adobe RGB (1998): XYZ → linear Adobe RGB
ADOBE_MAT = [
    [ 2.0413690, -0.5649464, -0.3446944],
    [-0.9692660,  1.8760108,  0.0415560],
    [ 0.0134474, -0.1183897,  1.0154096],
]


def main():
    # --- Load JND seeds for MacAdam proxy ---
    print("Loading JND seeds...")
    seeds = []
    csv_path = str(Path(__file__).parent.parent / "data" / "jnd.csv")
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            seeds.append([float(row["L"]), float(row["a"]), float(row["b"])])
    seeds = np.array(seeds)
    print(f"  {len(seeds):,} seeds loaded")

    print("Building KD-tree...")
    tree = KDTree(seeds)

    # --- Monte Carlo sampling ---
    N = 5_000_000
    print(f"\nSampling {N:,} random points in Lab bounding box...")
    rng = np.random.default_rng(42)

    # Sample: L in [0, 100], a in [-128, 128], b in [-128, 128]
    L_rand = rng.uniform(0, 100, N)
    a_rand = rng.uniform(-128, 128, N)
    b_rand = rng.uniform(-128, 128, N)
    Lab_rand = np.column_stack([L_rand, a_rand, b_rand])

    # Convert to XYZ
    print("Converting Lab → XYZ...")
    XYZ_rand = lab_to_xyz_vec(Lab_rand)

    # Check RGB gamuts
    print("Checking sRGB membership...")
    t0 = time.time()
    in_srgb = xyz_in_gamut(XYZ_rand, SRGB_MAT)
    print(f"  done in {time.time()-t0:.1f}s")

    print("Checking Adobe RGB membership...")
    t0 = time.time()
    in_adobe = xyz_in_gamut(XYZ_rand, ADOBE_MAT)
    print(f"  done in {time.time()-t0:.1f}s")

    # Check MacAdam solid membership via KD-tree proximity
    # Seeds are packed at CIEDE2000 ΔE≈1.0. In Lab Euclidean space,
    # the effective spacing varies but ~1.0-2.0. A threshold of 1.5
    # gives good coverage without bleeding outside the solid.
    print("Checking MacAdam solid membership (KD-tree)...")
    t0 = time.time()
    distances, _ = tree.query(Lab_rand)
    print(f"  done in {time.time()-t0:.1f}s")

    # Try multiple thresholds to check sensitivity
    for threshold in [1.0, 1.25, 1.5, 2.0]:
        in_macadam = distances <= threshold
        n_mac = np.sum(in_macadam)
        n_srgb_mac = np.sum(in_srgb & in_macadam)
        n_adobe_mac = np.sum(in_adobe & in_macadam)

        # Lab bounding box volume = 100 × 256 × 256 = 6,553,600
        bbox_vol = 100 * 256 * 256
        mac_vol = bbox_vol * (n_mac / N)
        srgb_vol = bbox_vol * (np.sum(in_srgb) / N)
        adobe_vol = bbox_vol * (np.sum(in_adobe) / N)

        print(f"\n=== Threshold ΔE76 ≤ {threshold} ===")
        print(f"  MacAdam solid:  {n_mac:>9,} hits → volume ≈ {mac_vol:>12,.0f} Lab³")
        print(f"  sRGB total:     {np.sum(in_srgb):>9,} hits → volume ≈ {srgb_vol:>12,.0f} Lab³")
        print(f"  Adobe RGB total:{np.sum(in_adobe):>9,} hits → volume ≈ {adobe_vol:>12,.0f} Lab³")
        print(f"  sRGB ∩ MacAdam: {n_srgb_mac:>9,}")
        print(f"  Adobe ∩ MacAdam:{n_adobe_mac:>9,}")
        if n_mac > 0:
            print(f"  sRGB as % of MacAdam (Lab vol):     {100*n_srgb_mac/n_mac:.1f}%")
            print(f"  Adobe RGB as % of MacAdam (Lab vol): {100*n_adobe_mac/n_mac:.1f}%")
            print(f"  Adobe / sRGB volume ratio:           {n_adobe_mac/n_srgb_mac:.2f}x")

    # Also report the raw gamut volumes without MacAdam constraint
    print(f"\n=== Raw gamut volumes (no MacAdam constraint) ===")
    n_s = np.sum(in_srgb)
    n_a = np.sum(in_adobe)
    print(f"  sRGB volume:     {bbox_vol * n_s / N:>12,.0f} Lab³  ({n_s:,} hits)")
    print(f"  Adobe RGB volume:{bbox_vol * n_a / N:>12,.0f} Lab³  ({n_a:,} hits)")
    print(f"  Adobe / sRGB:    {n_a / n_s:.3f}x")


if __name__ == "__main__":
    main()
