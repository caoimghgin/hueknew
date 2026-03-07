#!/usr/bin/env python3
"""Count neighbors within ΔE 1.5 for every sRGB JND seed, rank by most.

Usage (inside Docker):
    docker run --rm \
        -v /path/to/output:/data/output \
        chromatic-census python analysis/neighbor_density.py

Or via docker exec:
    docker exec -w /app chromatic-census python analysis/neighbor_density.py
"""

import os
import sqlite3
import sys
import time

os.chdir("/app")
sys.path.insert(0, "/app")

import numpy as np
from scipy.spatial import cKDTree

from src.core.cielab import is_in_srgb_gamut
from src.core.delta_e import delta_e_2000

DB_PATH = "/data/output/results.sqlite"
THRESHOLD = 1.5
EUCLIDEAN_RADIUS = 4.0  # Conservative overestimate for ΔE2000 ≤ 1.5


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Get JND threshold id
    tid = conn.execute("SELECT id FROM thresholds WHERE name='JND'").fetchone()[0]

    # Load all JND seeds
    all_seeds = conn.execute(
        "SELECT id, L, a, b, hex_srgb FROM seeds WHERE threshold_id=? ORDER BY id",
        (tid,),
    ).fetchall()

    L_all = np.array([s["L"] for s in all_seeds])
    a_all = np.array([s["a"] for s in all_seeds])
    b_all = np.array([s["b"] for s in all_seeds])

    # Filter to sRGB
    mask = is_in_srgb_gamut(L_all, a_all, b_all)
    srgb_idx = np.where(mask)[0]
    n = len(srgb_idx)
    print(f"sRGB JND seeds: {n:,}", file=sys.stderr)

    L = L_all[srgb_idx]
    a = a_all[srgb_idx]
    b = b_all[srgb_idx]
    ids = [all_seeds[i]["id"] for i in srgb_idx]
    hexes = [all_seeds[i]["hex_srgb"] for i in srgb_idx]

    tree = cKDTree(np.column_stack([L, a, b]))

    t0 = time.monotonic()
    counts = np.zeros(n, dtype=int)

    for i in range(n):
        cand_idx = tree.query_ball_point([L[i], a[i], b[i]], EUCLIDEAN_RADIUS)
        cand_idx = [j for j in cand_idx if j != i]
        if not cand_idx:
            continue
        cand = np.array(cand_idx)
        de = delta_e_2000(L[i], a[i], b[i], L[cand], a[cand], b[cand])
        counts[i] = int(np.sum(de < THRESHOLD))

        if (i + 1) % 10000 == 0:
            elapsed = time.monotonic() - t0
            print(f"  {i+1:,}/{n:,} ({elapsed:.1f}s)", file=sys.stderr)

    elapsed = time.monotonic() - t0
    print(f"Done in {elapsed:.1f}s", file=sys.stderr)

    # Sort by count descending
    ranked = np.argsort(counts)[::-1]

    # Print top 50
    print(f"{'rank':>5} {'id':>8} {'hex':>9} {'L*':>7} {'a*':>7} {'b*':>7} {'neighbors':>10}")
    print("-" * 62)
    for r in range(50):
        i = ranked[r]
        print(f"{r+1:>5} {ids[i]:>8} {hexes[i]:>9} {L[i]:>7.2f} {a[i]:>7.2f} {b[i]:>7.2f} {counts[i]:>10}")

    # Summary stats
    print(f"\n--- Summary (ΔE < {THRESHOLD}) ---")
    print(f"Min neighbors:    {counts.min()}")
    print(f"Max neighbors:    {counts.max()}")
    print(f"Mean neighbors:   {counts.mean():.1f}")
    print(f"Median neighbors: {np.median(counts):.1f}")
    print(f"Seeds with 0:     {np.sum(counts == 0):,}")

    conn.close()


if __name__ == "__main__":
    main()
