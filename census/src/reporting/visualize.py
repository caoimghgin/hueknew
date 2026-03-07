"""Visualization utilities for snapshot reports.

Generates charts as PNG files for inclusion in snapshots.
These are also served by the dashboard API as static images.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def plot_slice_histogram(slice_data, output_path):
    """Plot seeds per L* slice for all three tiers.

    Args:
        slice_data: List of dicts from ResultsDatabase.get_slice_summary().
        output_path: Path to save the PNG.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not available, skipping plot")
        return

    # Group by tier
    tiers = {}
    for row in slice_data:
        name = row["tier_name"]
        if name not in tiers:
            tiers[name] = {"L": [], "seeds": []}
        tiers[name]["L"].append(row["L_value"])
        tiers[name]["seeds"].append(row["seeds_found"])

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = {"JND": "#2196F3", "acceptability": "#FF9800", "obvious": "#4CAF50"}

    for name, data in tiers.items():
        ax.plot(data["L"], data["seeds"], label=f"{name} (ΔE={_get_delta(name)})",
                color=colors.get(name, "#999"), linewidth=1.5)

    ax.set_xlabel("L* (Lightness)")
    ax.set_ylabel("Seeds Found")
    ax.set_title("Distinguishable Colors per Lightness Slice")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def plot_tier_ratios(slice_data, output_path):
    """Plot JND/Acceptability and JND/Obvious ratios per slice.

    Args:
        slice_data: List of dicts from ResultsDatabase.get_slice_summary().
        output_path: Path to save the PNG.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    # Group by slice_id
    slices = {}
    for row in slice_data:
        sid = row["slice_id"]
        if sid not in slices:
            slices[sid] = {"L": row["L_value"]}
        slices[sid][row["tier_name"]] = row["seeds_found"]

    L_values = []
    ratio_accept = []
    ratio_obvious = []

    for sid in sorted(slices.keys()):
        s = slices[sid]
        jnd = s.get("JND", 0)
        accept = s.get("acceptability", 0)
        obvious = s.get("obvious", 0)
        if accept > 0 and obvious > 0:
            L_values.append(s["L"])
            ratio_accept.append(jnd / accept)
            ratio_obvious.append(jnd / obvious)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(L_values, ratio_accept, label="JND / Acceptability", color="#FF9800")
    ax.plot(L_values, ratio_obvious, label="JND / Obvious", color="#4CAF50")
    ax.set_xlabel("L* (Lightness)")
    ax.set_ylabel("Ratio")
    ax.set_title("Tier Ratios Across Lightness")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _get_delta(tier_name):
    """Get the ΔE2000 value for a tier name."""
    return {"JND": "1.0", "acceptability": "2.0", "obvious": "5.0"}.get(tier_name, "?")
