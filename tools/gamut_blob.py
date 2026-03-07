#!/usr/bin/env python3
"""Generate 3D gamut blob visualizations from chromatic census data.

Produces high-resolution scatter plots of seed colors in CIELAB space,
rendered in their actual sRGB colors. Used as hero images for the article.

Usage:
    python tools/gamut_blob.py
"""

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import numpy as np

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent

BG_COLOR = "#0d0d0d"


def load_seeds(csv_path):
    """Load seed data from a CSV file.

    Returns:
        Tuple of (L, a, b, colors) where colors is a list of hex strings.
    """
    L_vals, a_vals, b_vals, colors = [], [], [], []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            L_vals.append(float(row["L"]))
            a_vals.append(float(row["a"]))
            b_vals.append(float(row["b"]))
            colors.append(row["hex_srgb"])
    return np.array(L_vals), np.array(a_vals), np.array(b_vals), colors


def render_blob(L, a, b, colors, elev, azim, output_path,
                point_size=2.0, figsize=(16, 14), title=None, alpha=1.0,
                tight_axes=False, size_by_lightness=False):
    """Render a single 3D scatter view and save to disk."""
    fig = plt.figure(figsize=figsize, facecolor=BG_COLOR)
    ax = fig.add_subplot(111, projection="3d", facecolor=BG_COLOR)

    # Sort by L* ascending so white seeds render last (on top, not occluded)
    order = np.argsort(L)
    L_sorted = L[order]
    a_sorted = a[order]
    b_sorted = b[order]
    colors_sorted = [colors[i] for i in order]

    # Optionally scale point size by lightness — larger at top for white crown
    if size_by_lightness:
        # Map L* [0, 100] to size range [point_size * 0.4, point_size * 1.8]
        L_norm = L_sorted / 100.0
        sizes = point_size * (0.4 + 1.4 * L_norm)
    else:
        sizes = point_size

    ax.scatter(
        a_sorted, b_sorted, L_sorted,
        c=colors_sorted,
        s=sizes,
        alpha=alpha,
        edgecolors="none",
        depthshade=False,
    )

    ax.view_init(elev=elev, azim=azim)

    if tight_axes:
        pad_ab = 5
        pad_L = 2
        ax.set_xlim(a.min() - pad_ab, a.max() + pad_ab)
        ax.set_ylim(b.min() - pad_ab, b.max() + pad_ab)
        ax.set_zlim(max(0, L.min() - pad_L), min(100, L.max() + pad_L))
    else:
        ax.set_xlim(-128, 127)
        ax.set_ylim(-128, 127)
        ax.set_zlim(0, 100)

    # Clean: no axis labels, ticks, or grid
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_zticklabels([])
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
        axis.pane.fill = False
        axis.pane.set_edgecolor("none")
        axis.line.set_color("none")
    ax.grid(False)

    if title:
        ax.set_title(title, color="white", fontsize=16, pad=20, fontweight="bold")

    plt.tight_layout()
    fig.savefig(output_path, dpi=300, facecolor=BG_COLOR,
                bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    print(f"  Saved: {output_path} ({output_path.stat().st_size / 1024:.0f} KB)")


def main():
    print("Loading obvious-tier seeds...")
    obvious_path = DATA_DIR / "obvious.csv"
    L_ob, a_ob, b_ob, colors_ob = load_seeds(obvious_path)
    print(f"  {len(L_ob):,} seeds loaded")

    print("\nRendering hero gamut blob variations...")

    # D: Low dramatic angle + lightness-scaled point sizes + dark gray BG
    # The mountain silhouette: wide mid-section narrowing to white peak and dark nadir
    render_blob(
        L_ob, a_ob, b_ob, colors_ob,
        elev=12, azim=150,
        output_path=OUTPUT_DIR / "gamut-blob-obvious-hero-D.png",
        point_size=14.0,
        tight_axes=True,
        size_by_lightness=True,
        title=f"Every Obviously Distinguishable Color — {len(L_ob):,} Seeds",
    )

    # E: Same concept but slightly higher, rotated to show more of the green/blue face
    render_blob(
        L_ob, a_ob, b_ob, colors_ob,
        elev=18, azim=210,
        output_path=OUTPUT_DIR / "gamut-blob-obvious-hero-E.png",
        point_size=14.0,
        tight_axes=True,
        size_by_lightness=True,
        title=f"Every Obviously Distinguishable Color — {len(L_ob):,} Seeds",
    )

    # F: Very low, almost eye-level — maximum mountain drama
    render_blob(
        L_ob, a_ob, b_ob, colors_ob,
        elev=6, azim=135,
        output_path=OUTPUT_DIR / "gamut-blob-obvious-hero-F.png",
        point_size=14.0,
        tight_axes=True,
        size_by_lightness=True,
        title=f"Every Obviously Distinguishable Color — {len(L_ob):,} Seeds",
    )

    print("\nDone!")


if __name__ == "__main__":
    main()
