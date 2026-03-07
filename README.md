# hueknew

**How many colors can the human eye actually see?**

The commonly cited answer — "about 10 million" — has never been rigorously computed. It traces back to rough estimates and interpolations from the 1940s. This project performs the actual count.

**The answer is roughly 324,000.** The old folklore is off by about 30x.

This repo contains the computation engine, pre-computed results, and interactive tools to explore them yourself.

## Quick Start

**Explore the colors** — no install needed, just a browser:

```bash
git clone https://github.com/caoimghgin/hueknew.git
cd hueknew
python3 launch/gamut-model.py
```

Your browser opens to the 3D viewer — every distinguishable color rendered as a point cloud in perceptual color space. Drag to orbit, scroll to zoom, switch between tiers.

**Browse the dashboard** with swatch-by-swatch comparison:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install .
python3 launch/census-dashboard.py
```

Opens at [http://localhost:8084](http://localhost:8084) — JND visual audit (side-by-side swatches), neighborhood explorer, and progress charts.

**Run your own census:**

```bash
python3 launch/census-runner.py              # coarse (~2 minutes)
python3 launch/census-runner.py fine          # full count (~10 minutes)
python3 launch/census-runner.py ultrafine     # deep run (~5-10 hours)
```

Watch the dashboard at `:8084` as it discovers colors in real time. When it finishes, your results are written to `data/jnd.csv`, `data/acceptability.csv`, and `data/obvious.csv` — the viewer picks them up automatically.

## Results

| Tier | ΔE2000 | Count | What it means |
|------|--------|-------|---------------|
| **JND** | 1.0 | **324,669** | Colors the eye can *theoretically* distinguish (lab conditions) |
| **Acceptability** | 2.0 | **52,763** | Colors that are *meaningfully* different |
| **Obvious** | 5.0 | **17,751** | Colors *anyone* would call different |

## How It Works

Greedy sphere-packing in CIELAB perceptual color space using the CIEDE2000 color-difference formula. Walk ~6.7 billion candidate colors, validate each against the Rosch-MacAdam human visual gamut, and pack non-overlapping perceptual neighborhoods until no more fit. Then gap-fill to prove the packing is saturated (+0.85% more seeds from 50 million random probes).

The census runs in two phases:

1. **Grid pack** (`--mode coarse|fine|superfine|ultrafine`) — systematic sweep through CIELAB space at increasing resolution
2. **Gap fill** (`--mode gapfill --seed-db output/results.sqlite`) — shifted grid + random probes to find any remaining holes

Full methodology in [docs/article.md](docs/article.md).

## What's Inside

```
hueknew/
├── launch/     Start here — simple scripts to launch everything
├── census/     The sphere-packing engine (Python)
├── viewer/     Interactive 3D gamut viewer (Three.js, runs in browser)
├── data/       Pre-computed results — 3 CSV files, ready to explore
├── tools/      Analysis & visualization scripts
├── docs/       Research article, findings, and methodology
└── deploy/     Docker config (optional, for long runs)
```

## Requirements

Python 3.10+ for the census engine and dashboard. The 3D viewer is pure HTML/JavaScript and needs only a browser.

Core dependencies: NumPy, SciPy, colorspacious, matplotlib, PyArrow, Starlette, uvicorn. All declared in `pyproject.toml` and installed automatically with `pip install .`.

## Tests

```bash
pip install ".[dev]"
cd census
pytest tests/
```

The CIEDE2000 test suite validates against all 34 Sharma/Wu/Dalal published CIE test pairs, matching to 4 decimal places.

## Docker (optional)

For long-running census jobs on a server:

```bash
docker build -f deploy/Dockerfile -t hueknew .
docker run -d --name census \
  --cpus='4' --memory=8g \
  -p 8084:8084 \
  -v $(pwd)/census/output:/app/output \
  hueknew
```

## License

MIT
