# Perceptible Tier Findings (March 2026)

## The Question

We set out to disprove the claim that humans can see 10 million colors. Our census at ΔE 1.0 (the classical JND) found ~238K distinguishable colors — far fewer than 10 million. But then we built a tool to measure people's actual JND, and the results were surprising.

## What We Measured

### Side-by-Side JND Test (jnd-test.html)
Two colors share an edge on a full screen. The user clicks where they meet.

| Tester | Result |
|--------|--------|
| Kevin  | 0.316 ΔE₀₀ |
| Kevin (second attempt) | 0.464 ΔE₀₀ |
| Others reporting | ~0.215 ΔE₀₀ |

These are all well below the "theoretical" JND of 1.0 ΔE₀₀.

### Odd-One-Out Test (odd-one-out.html)
Nine 1" swatches on L*=50 gray background, 16px gaps between them. No shared edges. User picks the different one. Forced-choice paradigm.

| Tester | Result |
|--------|--------|
| Kevin  | 2.05 ΔE₀₀ |

### Keith Cirkel's Test (keithcirkel.co.uk/whats-my-jnd-hard/)
Nine massive swatches (1/3 screen width each) on black background. ΔEOK color space (not CIEDE2000).

| Tester | Result |
|--------|--------|
| Kevin  | 0.0145 ΔEOK (~0.7-1.5 ΔE₀₀ equivalent) |

## The Key Insight

The same person, with the same eyes, scores dramatically differently depending on the test design:

| Condition | JND (ΔE₀₀) | Factor |
|-----------|-------------|--------|
| Side-by-side, shared edge, full screen | ~0.3-0.5 | 1x (best case) |
| Large swatches, black background (Cirkel) | ~0.7-1.5 | ~2-3x |
| Classical literature | 1.0 | ~2-3x |
| Small isolated swatches, neutral gray background | ~2.0 | ~5-6x |

This isn't surprising when you understand visual neuroscience: the human visual cortex is optimized for **edge detection**. When two colors share a border, your neurons fire at the contrast boundary, making even tiny differences detectable. Remove that edge, shrink the color field, and add a neutral surround, and the task becomes much harder.

## What This Means for Color Counts

Using our sphere-packing census data:

| Threshold | ΔE₀₀ | Count (ultrafine) | Viewing Condition |
|-----------|-------|-------|-------------------|
| Perceptible | 0.5 | **1,971,934** | Ideal: side-by-side, shared edge |
| JND | 1.0 | **238,241** | Classical: controlled laboratory |
| Acceptability | 2.0 | **34,496** | Practical: isolated swatches |
| Obvious | 5.0 | **9,052** | Casual: obviously different |

Projected (from 8x-per-halving scaling):

| Threshold | ΔE₀₀ | Projected Count | Viewing Condition |
|-----------|-------|-----------------|-------------------|
| 0.25 | 0.25 | ~16 million | Best observed human threshold |
| 0.125 | 0.125 | ~120 million | Theoretical lower bound |

## The Irony

The "10 million colors" claim we set out to challenge falls right in the ΔE 0.25-0.5 range — which corresponds to what people actually perceive under ideal side-by-side viewing conditions. The number wasn't wrong. It just assumed a viewing condition that nobody had properly defined or measured.

## The Real Story

The answer to "how many colors can humans see?" is not a single number. It's a spectrum:

- **~2 million** under ideal edge-detection conditions (ΔE 0.5)
- **~238K** under classical laboratory conditions (ΔE 1.0)
- **~35K** under practical isolated-swatch conditions (ΔE 2.0)
- **~9K** that are obvious to anyone (ΔE 5.0)

The contribution of the Chromatic Census is not just one number — it's a rigorous enumeration at each threshold, backed by actual perceptual measurements showing why different thresholds matter.

## Test Design Factors That Affect Measured JND

| Factor | Lower JND (easier) | Higher JND (harder) |
|--------|--------------------|--------------------|
| Swatch size | Large (1/3 screen) | Small (1 inch) |
| Border | Shared edge | Separated with gaps |
| Background | Black | Neutral gray (L*=50) |
| Task | "Are these different?" | "Find the odd one out" |
| Viewing | Controlled, dark room | Normal ambient lighting |

## Census Run Details (March 15, 2026)

- **Phase 1 complete**: Ultrafine packing with perceptible tier, 10h 41m on darkstar
- **Phase 2 pending**: Gapfill (expected +1-3%)
- **Phase 3 validated**: CSV export bug fixed, all four tiers export cleanly

### Bugs Fixed Before This Run
1. `ResultsDatabase.get_all_seeds()` — missing method that crashed CSV export
2. Gapfill ignoring `--no-dashboard` flag
3. JND tier name casing mismatch (`"JND"` vs `"jnd"`) in both export locations
