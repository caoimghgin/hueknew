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

## What's Inside

- [chromatic-census/](chromatic-census/) — The census engine, dashboard, and deployment config

## Status

Currently running on a home server. Check back for results.
