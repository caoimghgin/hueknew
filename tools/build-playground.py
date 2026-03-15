#!/usr/bin/env python3
"""
Build a standalone playground bundle for deployment on muldoon.design.

Outputs to dist/playground/ with:
  - index.html  (viewer with adjusted data paths)
  - data/       (trimmed CSVs: only L, a, b, hex_srgb columns)

Usage:
    python3 tools/build-playground.py
"""

import csv
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIEWER_DIR = ROOT / "viewer"
DATA_DIR = ROOT / "data"
DIST_DIR = ROOT / "dist" / "playground"

TIERS = ["obvious", "acceptability", "jnd"]
KEEP_COLUMNS = ["L", "a", "b", "hex_srgb"]


def trim_csv(src: Path, dst: Path) -> tuple[int, int]:
    """Copy CSV keeping only the columns the viewer needs. Returns (src_size, dst_size)."""
    src_size = src.stat().st_size
    with open(src) as fin, open(dst, "w", newline="") as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=KEEP_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in reader:
            writer.writerow({k: row[k] for k in KEEP_COLUMNS})
    dst_size = dst.stat().st_size
    return src_size, dst_size


def patch_html(html: str) -> str:
    """Adjust the viewer HTML for standalone deployment."""
    # Fix data paths: ../data/ → ./data/
    html = html.replace("'../data/", "'./data/")

    # Update title for the playground context
    html = html.replace(
        "<title>Chromatic Census — Interactive Gamut Viewer</title>",
        "<title>Chromatic Census — Playground</title>",
    )

    return html


def main():
    print("Building playground bundle...")

    # Clean and create output directory
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    data_out = DIST_DIR / "data"
    data_out.mkdir(parents=True)

    # Trim and copy CSVs
    total_src = 0
    total_dst = 0
    for tier in TIERS:
        src = DATA_DIR / f"{tier}.csv"
        dst = data_out / f"{tier}.csv"
        src_size, dst_size = trim_csv(src, dst)
        total_src += src_size
        total_dst += dst_size
        saved = (1 - dst_size / src_size) * 100
        print(f"  {tier}.csv: {src_size:,} → {dst_size:,} bytes ({saved:.0f}% smaller)")

    print(f"  Total data: {total_src:,} → {total_dst:,} bytes")

    # Patch and write gamut viewer
    html = (VIEWER_DIR / "index.html").read_text()
    html = patch_html(html)
    (DIST_DIR / "index.html").write_text(html)
    print(f"  index.html: {len(html):,} bytes")

    # Copy JND tests (no patching needed — they're fully self-contained)
    for test_file in ["jnd-test.html", "odd-one-out.html"]:
        src = VIEWER_DIR / test_file
        html = src.read_text()
        (DIST_DIR / test_file).write_text(html)
        print(f"  {test_file}: {len(html):,} bytes")

    print(f"\nPlayground bundle ready at: {DIST_DIR.relative_to(ROOT)}/")
    print("Deploy this folder to muldoon.design/playground/ (or any path).")


if __name__ == "__main__":
    main()
