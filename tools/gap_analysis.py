"""Gap Analysis: Do sRGB gamut holes create false gaps in the JND chain walk?

Question
--------
When walking through sRGB JND seeds by ΔE2000, adjacent steps are often
~2 ΔE apart (roughly 2 JND). Could a color that was *filtered out* as
non-sRGB have fit between those steps — making the gap an artifact of
gamut limitation rather than a true packing boundary?

Method
------
For a given chain-walk triple (prev, ref, next), query ALL JND seeds in
the database (including non-sRGB) and check whether any fall "between"
adjacent pairs — i.e., within ΔE < threshold of both the reference and
its neighbor.

Usage
-----
    docker exec -w /app chromatic-census python analysis/gap_analysis.py

Or with custom coordinates:
    docker exec -w /app chromatic-census python analysis/gap_analysis.py \
        --ref 61.0 -9.5 -28.0 \
        --left 60.0 -8.0 -32.5 \
        --right 59.5 -9.5 -32.0
"""
import argparse
import os
import sqlite3
import sys

import numpy as np

os.chdir("/app")
sys.path.insert(0, "/app")

from src.core.cielab import is_in_srgb_gamut
from src.core.delta_e import delta_e_2000


def analyze_gap(conn, tid, ref_Lab, left_Lab, right_Lab, L_window=4.0):
    """Analyze the gap between a chain-walk triple.

    Returns a dict with full results.
    """
    ref_L, ref_a, ref_b = ref_Lab
    left_L, left_a, left_b = left_Lab
    right_L, right_a, right_b = right_Lab

    # ΔE between ref and its neighbors
    de_ref_left = float(delta_e_2000(ref_L, ref_a, ref_b,
                                     np.array([left_L]), np.array([left_a]), np.array([left_b]))[0])
    de_ref_right = float(delta_e_2000(ref_L, ref_a, ref_b,
                                      np.array([right_L]), np.array([right_a]), np.array([right_b]))[0])

    # Query ALL JND seeds in an L* window
    L_min = min(ref_L, left_L, right_L) - L_window
    L_max = max(ref_L, left_L, right_L) + L_window
    rows = conn.execute(
        "SELECT id, L, a, b, hex_srgb FROM seeds WHERE threshold_id = ? AND L BETWEEN ? AND ?",
        (tid, L_min, L_max)
    ).fetchall()

    L_arr = np.array([r["L"] for r in rows])
    a_arr = np.array([r["a"] for r in rows])
    b_arr = np.array([r["b"] for r in rows])
    srgb_mask = is_in_srgb_gamut(L_arr, a_arr, b_arr)

    de_from_ref = delta_e_2000(ref_L, ref_a, ref_b, L_arr, a_arr, b_arr)

    results = {
        "ref": {"L": ref_L, "a": ref_a, "b": ref_b},
        "left": {"L": left_L, "a": left_a, "b": left_b},
        "right": {"L": right_L, "a": right_a, "b": right_b},
        "de_ref_left": de_ref_left,
        "de_ref_right": de_ref_right,
        "window": {
            "total_seeds": len(rows),
            "srgb": int(np.sum(srgb_mask)),
            "non_srgb": int(len(rows) - np.sum(srgb_mask)),
        },
        "gaps": {},
    }

    for label, neighbor_Lab, de_threshold in [
        ("left", left_Lab, de_ref_left),
        ("right", right_Lab, de_ref_right),
    ]:
        nL, na, nb = neighbor_Lab
        de_from_neighbor = delta_e_2000(nL, na, nb, L_arr, a_arr, b_arr)

        between = ((de_from_ref < de_threshold) &
                   (de_from_neighbor < de_threshold) &
                   (de_from_ref > 0.01))

        between_srgb = between & srgb_mask
        between_non_srgb = between & ~srgb_mask

        seeds_between = []
        for i in np.where(between)[0]:
            r = rows[i]
            seeds_between.append({
                "L": r["L"], "a": r["a"], "b": r["b"],
                "hex": r["hex_srgb"],
                "de_ref": round(float(de_from_ref[i]), 4),
                "de_neighbor": round(float(de_from_neighbor[i]), 4),
                "in_srgb": bool(srgb_mask[i]),
            })

        results["gaps"][label] = {
            "de_threshold": round(de_threshold, 4),
            "total_between": int(np.sum(between)),
            "srgb_between": int(np.sum(between_srgb)),
            "non_srgb_between": int(np.sum(between_non_srgb)),
            "seeds": sorted(seeds_between, key=lambda s: s["de_ref"]),
        }

    return results


def print_results(results):
    """Pretty-print gap analysis results."""
    ref = results["ref"]
    left = results["left"]
    right = results["right"]

    print("=" * 70)
    print("GAP ANALYSIS — sRGB Gamut Holes in JND Chain Walk")
    print("=" * 70)
    print()
    print(f"  Reference:  L*={ref['L']:.1f}, a*={ref['a']:.1f}, b*={ref['b']:.1f}")
    print(f"  Left (prev): L*={left['L']:.1f}, a*={left['a']:.1f}, b*={left['b']:.1f}  "
          f"(ΔE={results['de_ref_left']:.3f})")
    print(f"  Right (next): L*={right['L']:.1f}, a*={right['a']:.1f}, b*={right['b']:.1f}  "
          f"(ΔE={results['de_ref_right']:.3f})")
    print()

    w = results["window"]
    print(f"  Search window: {w['total_seeds']:,} JND seeds")
    print(f"    sRGB:     {w['srgb']:,} ({100*w['srgb']/w['total_seeds']:.1f}%)")
    print(f"    non-sRGB: {w['non_srgb']:,} ({100*w['non_srgb']/w['total_seeds']:.1f}%)")
    print()

    for label in ["left", "right"]:
        gap = results["gaps"][label]
        direction = "prev" if label == "left" else "next"
        print(f"  Gap: ref ↔ {direction}  (ΔE = {gap['de_threshold']:.3f})")
        print(f"    Seeds between:  {gap['total_between']} total, "
              f"{gap['srgb_between']} sRGB, {gap['non_srgb_between']} non-sRGB")

        if gap["non_srgb_between"] > 0:
            print(f"    ⚠  GAMUT HOLE DETECTED — {gap['non_srgb_between']} colors filtered by sRGB")
        else:
            print(f"    ✓  No gamut holes — all intermediate seeds are in sRGB")

        if gap["seeds"]:
            print(f"    Details:")
            for s in gap["seeds"]:
                gamut = "sRGB" if s["in_srgb"] else "OUT"
                print(f"      L*={s['L']:.1f} a*={s['a']:.1f} b*={s['b']:.1f}  "
                      f"dE_ref={s['de_ref']:.3f}  dE_{direction}={s['de_neighbor']:.3f}  [{gamut}]")
        print()

    # Verdict
    any_holes = any(results["gaps"][l]["non_srgb_between"] > 0 for l in ["left", "right"])
    print("-" * 70)
    if any_holes:
        print("VERDICT: Gamut holes detected. The gap between these chain-walk")
        print("steps is partially an artifact of sRGB limitation — colors exist")
        print("in wider gamut spaces (P3, Rec.2020) that would fill this gap.")
    else:
        print("VERDICT: No gamut holes. The gap between these chain-walk steps")
        print("is a true packing boundary. No color in ANY gamut could be")
        print("inserted here and be meaningfully different from both neighbors.")
    print("-" * 70)


def main():
    parser = argparse.ArgumentParser(description="JND chain-walk gap analysis")
    parser.add_argument("--ref", nargs=3, type=float, default=[61.0, -9.5, -28.0],
                        metavar=("L", "a", "b"), help="Reference seed L*a*b*")
    parser.add_argument("--left", nargs=3, type=float, default=[60.0, -8.0, -32.5],
                        metavar=("L", "a", "b"), help="Left (prev) seed L*a*b*")
    parser.add_argument("--right", nargs=3, type=float, default=[59.5, -9.5, -32.0],
                        metavar=("L", "a", "b"), help="Right (next) seed L*a*b*")
    parser.add_argument("--db", default="/app/output/results.sqlite",
                        help="Path to results database")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    tid = conn.execute("SELECT id FROM thresholds WHERE name = 'JND'").fetchone()["id"]

    results = analyze_gap(conn, tid, args.ref, args.left, args.right)
    print_results(results)

    conn.close()


if __name__ == "__main__":
    main()
