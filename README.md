# hueknew

**How many colors can the human eye actually see?**

The commonly cited answer — "about 10 million" — has never been rigorously computed. It traces back to rough estimates and interpolations from the 1940s. *hueknew* performs the actual count.

## The Approach

Greedy sphere-packing in CIELAB perceptual color space using the CIEDE2000 color-difference formula. Walk a fine grid of ~104 million candidate colors, validate each against the human visual gamut, and pack non-overlapping perceptual neighborhoods until no more fit. Every seed point in the packing is a color the eye can distinguish from all others.

Three perceptual thresholds run simultaneously:

- **JND** (ΔE=1.0) — How many colors can the eye *theoretically* distinguish?
- **Acceptability** (ΔE=2.0) — How many colors are *meaningfully* different?
- **Obvious** (ΔE=5.0) — How many colors are *obviously* different to anyone?

The ratios between tiers are arguably more interesting than the raw counts.

## Results

Counts increase with grid resolution as finer grids find seeds between previous grid points. Results across four runs:

| | Coarse | Fine | Superfine | Ultrafine |
|---|---|---|---|---|
| **Grid steps** (L\*/a\*/b\*) | 1.0 / 2.0 / 2.0 | 0.25 / 0.5 / 0.5 | 0.125 / 0.25 / 0.25 | 0.0625 / 0.125 / 0.125 |
| **Candidates** | ~1.6M | ~104M | ~835M | ~6.7B |
| **JND** (ΔE=1.0) | 313,115 | 1,834,305 | 3,997,938 | **8,414,939** |
| **Acceptability** (ΔE=2.0) | 109,032 | 513,715 | 1,063,584 | **2,162,115** |
| **Obvious** (ΔE=5.0) | 74,463 | 337,085 | 676,635 | **1,358,876** |
| **Runtime** | ~2 min | ~10 min | ~37 min | ~3.5 hrs |

Counts roughly double with each halving of step size, indicating the grid has not yet fully converged. These are lower bounds — the true counts are somewhat higher.

At 8.4 million JND, the old "10 million" folklore is looking closer than our early runs suggested — though the number was arrived at for the wrong reasons. About 2.2 million meaningfully different colors, and ~1.4 million obviously different to anyone.

## What's Inside

- [chromatic-census/](chromatic-census/) — The census engine, dashboard, and deployment config

## Dashboard

Live results at [http://10.0.0.108:8084/](http://10.0.0.108:8084/)
