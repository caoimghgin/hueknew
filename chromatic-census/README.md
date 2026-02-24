# Chromatic Census

**A rigorous computational enumeration of human-distinguishable colors using CIELAB space and CIEDE2000.**

---

The commonly cited figure of "~10 million distinguishable colors" for human vision has never been rigorously computed. It traces back to rough estimates and interpolations from the 1940s. This project performs an actual enumeration by systematically walking the CIELAB color space, validating points against the human visual gamut, and counting distinct colors using the CIEDE2000 perceptual difference formula.

The result is either a vindication or a correction of that number — backed by computation rather than estimation.

## How It Works

The core algorithm is **greedy sphere-packing in a non-Euclidean perceptual color space**. It asks: how many non-overlapping ΔE2000 neighborhoods fit inside the human visual gamut?

1. Generate a fine grid of ~104 million candidate points in CIELAB (L\*a\*b\*) space
2. Filter out points that fall outside the human visual gamut (spectral locus boundary check via CIE 1931 chromaticity diagram)
3. Greedy packing: iterate through valid points, claim each as a "seed" color, then exclude all neighbors within the ΔE2000 threshold
4. Spatial indexing via KD-trees keeps neighbor queries fast (O(k) instead of O(n))
5. Process slice-by-slice along L\* (lightness) for memory efficiency and natural checkpointing

Three thresholds run simultaneously in a single pass:

| Tier | ΔE2000 | Name | What It Measures |
|------|--------|------|------------------|
| 1 | 1.0 | **JND** | Colors the eye can *theoretically* distinguish (lab conditions) |
| 2 | 2.0 | **Acceptability** | Colors that are *meaningfully* different (industrial standard) |
| 3 | 5.0 | **Obvious** | Colors *anyone* would call different (everyday perception) |

Since the thresholds are nested (1.0 ⊂ 2.0 ⊂ 5.0), the multi-threshold approach adds negligible runtime — the expensive ΔE2000 computation happens once per neighbor pair regardless.

## Live Dashboard

A built-in web dashboard provides real-time monitoring at `http://<host>:8084`:

- Progress bar with ETA and elapsed time
- Three tier count cards with per-slice rates
- Color strip visualization of completed L\* slices
- a\*b\* heatmap of seed positions (colored by actual sRGB value)
- Tier comparison line chart
- Running projection of final counts
- "Color of the moment" — the most recently discovered seed, displayed as a swatch

## Installation

Requires Python 3.10+.

```bash
git clone https://github.com/caoimghgin/chromatic-census.git
cd chromatic-census
pip install -r requirements.txt
```

### Dependencies

- **numpy** / **scipy** — Vectorized math, KD-tree spatial indexing
- **colorspacious** — Reference ΔE2000 for validation (we use our own NumPy implementation for performance)
- **matplotlib** — Snapshot visualizations
- **pyarrow** — Parquet output for seed logs
- **pyyaml** — Configuration
- **psutil** — Memory monitoring
- **starlette** / **uvicorn** — Dashboard web server

## Usage

```bash
# Quick validation run (~2 hours at coarse resolution)
python run.py --mode coarse

# Full census (~2-4 weeks at fine resolution)
python run.py --mode fine

# Resume from last checkpoint after interruption
python run.py --resume

# Check current progress
python run.py --status

# Run dashboard without the engine (view existing results)
python run.py --dashboard-only

# Quick volume-integration estimate (sanity check)
python run.py --estimate
```

All runtime parameters are in `config.yaml`.

## Docker

```bash
# Build
docker build -f deploy/Dockerfile -t chromatic-census .

# Run (fine mode with auto-resume, dashboard on port 8084)
docker run -d --name census \
  --cpus='4' --memory=8g \
  -p 8084:8084 \
  -v /path/to/output:/app/output \
  chromatic-census
```

A `deploy/docker-compose.yml` is included for production deployment.

## Project Structure

```
chromatic-census/
├── run.py                    # CLI entry point
├── config.yaml               # Runtime configuration
├── src/
│   ├── core/
│   │   ├── cielab.py         # L*a*b* ↔ XYZ conversions (vectorized)
│   │   ├── delta_e.py        # CIEDE2000 implementation
│   │   ├── gamut.py          # Spectral locus boundary validation
│   │   └── spectral_data.py  # CIE 1931 2° observer data
│   ├── engine/
│   │   ├── grid.py           # CIELAB grid generation (per-slice)
│   │   ├── packer.py         # Greedy sphere-packing algorithm
│   │   ├── spatial.py        # KD-tree wrapper with lazy deletion
│   │   └── estimator.py      # Fast volume-integration estimate
│   ├── persistence/
│   │   ├── checkpoint.py     # Atomic checkpoints for multi-week runs
│   │   └── results.py        # SQLite results database (WAL mode)
│   ├── reporting/
│   │   ├── progress.py       # Console output + status.json
│   │   ├── snapshots.py      # Hourly progress snapshots
│   │   └── visualize.py      # Matplotlib charts
│   └── dashboard/
│       ├── server.py         # Starlette + uvicorn web server
│       ├── api.py            # JSON API endpoints
│       └── page.py           # Self-contained HTML/CSS/JS dashboard
├── tests/
│   ├── test_delta_e.py       # 34 published CIE test pairs (4 decimal places)
│   ├── test_gamut.py         # Gamut boundary validation
│   └── test_packer.py        # Small-scale packing verification
└── deploy/
    ├── Dockerfile
    └── docker-compose.yml
```

## Technical Details

### CIELAB Grid

| Parameter | Range | Fine Step | Coarse Step |
|-----------|-------|-----------|-------------|
| L\* (lightness) | 0–100 | 0.25 | 1.0 |
| a\* (green–red) | -128 to +127 | 0.5 | 2.0 |
| b\* (blue–yellow) | -128 to +127 | 0.5 | 2.0 |

Fine grid: 401 × 510 × 510 = ~104 million candidate points.

### Gamut Validation

Not all L\*a\*b\* coordinates map to physically realizable colors. Each point is validated through:

1. L\*a\*b\* → XYZ (CIE standard illuminant D65)
2. XYZ non-negativity check
3. XYZ → chromaticity (x, y)
4. Point-in-polygon test against the CIE 1931 spectral locus boundary

### Persistence

Designed for multi-week runs. Checkpoints save every 5 minutes with atomic writes (temp file + rename). SIGINT/SIGTERM trigger a graceful checkpoint before exit. The `--resume` flag picks up from the last checkpoint.

Results are stored in SQLite (WAL mode for concurrent dashboard reads) with tables for thresholds, seeds, per-slice statistics, and a run log.

## Tests

```bash
pip install pytest
pytest tests/
```

The ΔE2000 test suite validates against all 34 Sharma/Wu/Dalal published CIE test pairs, matching to 4 decimal places.

## License

MIT
