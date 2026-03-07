#!/usr/bin/env python3
"""Run the census engine to generate your own color count.

Usage:
    python launch/census-runner.py              # coarse mode (~2 minutes)
    python launch/census-runner.py fine          # full count (~10 minutes)
    python launch/census-runner.py ultrafine     # deep run (~5-10 hours)

Requires: pip install .  (from the project root)
"""

import os
import subprocess
import sys

try:
    import numpy  # noqa: F401
except ImportError:
    print("Dependencies not installed. Run this first:\n")
    print("  pip install .\n")
    sys.exit(1)

os.chdir(os.path.join(os.path.dirname(__file__), "..", "census"))

mode = sys.argv[1] if len(sys.argv) > 1 else "coarse"
valid_modes = ["coarse", "fine", "superfine", "ultrafine", "hyperfine"]

if mode not in valid_modes:
    print(f"Unknown mode: {mode}")
    print(f"Valid modes: {', '.join(valid_modes)}")
    sys.exit(1)

print(f"Running census in {mode} mode...")
print("Dashboard at http://localhost:8084\n")
subprocess.run([sys.executable, "run.py", "--mode", mode])
