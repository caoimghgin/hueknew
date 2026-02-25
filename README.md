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

Counts converge as grid resolution increases. Results across four runs (with cross-slice ghost-seed deduplication):

| | Coarse | Fine | Superfine | Ultrafine |
|---|---|---|---|---|
| **Grid steps** (L\*/a\*/b\*) | 1.0 / 2.0 / 2.0 | 0.25 / 0.5 / 0.5 | 0.125 / 0.25 / 0.25 | 0.0625 / 0.125 / 0.125 |
| **Candidates** | ~1.6M | ~104M | ~835M | ~6.7B |
| **JND** (ΔE=1.0) | 172,588 | 276,941 | 299,370 | **321,930** |
| **Acceptability** (ΔE=2.0) | 35,873 | 45,038 | 48,675 | **51,868** |
| **Obvious** (ΔE=5.0) | 12,467 | 15,446 | 16,456 | **17,313** |
| **Runtime** | ~2 min | ~10 min | ~52 min | ~4 hrs |

Convergence ratios tighten from 1.2–1.6× (fine/coarse) to 1.05–1.08× (ultrafine/superfine), indicating the counts are within ~10% of the true values.

At ~322,000 JND, the old "10 million" folklore is off by roughly 30×. About 52,000 meaningfully different colors, and ~17,000 obviously different to anyone. See [results/RESULTS.md](results/RESULTS.md) for the full story — including the cross-slice overcounting bug we found and fixed.

## What's Inside

- [chromatic-census/](chromatic-census/) — The census engine, dashboard, and deployment config

## Dashboard

Live results at [http://10.0.0.108:8084/](http://10.0.0.108:8084/)
