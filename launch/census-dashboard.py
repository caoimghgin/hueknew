#!/usr/bin/env python3
"""Launch the census dashboard to browse results and swatch comparisons.

Requires: pip install .  (from the project root)
"""

import os
import subprocess
import sys

try:
    import uvicorn  # noqa: F401
except ImportError:
    print("Dependencies not installed. Run this first:\n")
    print("  pip install .\n")
    sys.exit(1)

os.chdir(os.path.join(os.path.dirname(__file__), "..", "census"))

print("Starting census dashboard at http://localhost:8084")
print("Press Ctrl+C to stop.\n")
subprocess.run([sys.executable, "run.py", "--dashboard-only"])
