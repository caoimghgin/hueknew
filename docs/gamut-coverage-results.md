# Gamut Coverage Analysis

How many distinguishable surface colors can standard RGB displays actually show?
And how do our results compare to published industry claims?

## Method 1: Perceptual Count (seed membership)

Every seed from the ultrafine MacAdam-fixed census was tested against the sRGB
and Adobe RGB (1998) gamut boundaries by converting CIE L*a*b* to XYZ, then to
linear RGB via the standard 3x3 matrices (D65 white point). A seed is "inside"
if all three linear RGB components fall within [0, 1].

Source data: `results/exports/ultrafine-macadam-*.csv`
Script: `results/analysis/gamut_coverage.py`

### Results by tier

| Tier | ΔE threshold | Total seeds | In sRGB | In Adobe RGB | Outside both |
|------|:------------:|------------:|--------:|-------------:|-------------:|
| JND | 1.0 | 269,812 | 159,248 (59.0%) | 194,868 (72.2%) | 74,944 (27.8%) |
| Acceptability | 2.3 | 33,509 | 17,632 (52.6%) | 22,053 (65.8%) | 11,456 (34.2%) |
| Obvious | 5.0 | 8,687 | 3,002 (34.6%) | 4,286 (49.3%) | 4,401 (50.7%) |

### JND-tier breakdown

| Breakdown | Count | % of total |
|-----------|------:|-----------:|
| Inside both (sRGB subset) | 159,248 | 59.0% |
| Adobe RGB only (not sRGB) | 35,620 | 13.2% |
| Outside both gamuts | 74,944 | 27.8% |
| sRGB only (not Adobe RGB) | 0 | 0.0% |

Adobe RGB is a strict superset of sRGB (same blue/red primaries, wider green).

### Interpretation

Coverage percentages **decrease** at coarser tiers. This is because JND-level
packing places disproportionately many seeds in the mid-gamut region where RGB
displays are strongest. At the obvious tier, seeds are spread toward the
hyper-saturated extremes that no RGB display can reach.

The obvious tier (ΔE=5.0) is arguably the most honest metric for "what fraction
of *noticeably different* colors can your display show?" At that level:

- **sRGB covers ~35%** of distinguishable surface colors
- **Adobe RGB covers ~49%** of distinguishable surface colors
- **Over half** of all obviously-different colors are outside both gamuts

---

## Method 2: CIELAB Volume (Monte Carlo)

To compare directly against published industry claims (which use CIELAB volume,
not perceptual seed counts), we ran a Monte Carlo volume analysis.

5,000,000 points were sampled uniformly in the Lab bounding box
(L: 0-100, a: -128 to 128, b: -128 to 128). Each point was classified as:

- **Inside sRGB:** Lab → XYZ → linear sRGB, all channels in [0, 1]
- **Inside Adobe RGB:** Lab → XYZ → linear Adobe RGB, all channels in [0, 1]
- **Inside MacAdam solid:** within ΔE76 threshold of any JND seed (269,812
  seeds used as a KD-tree proxy for the Rosch-MacAdam optimal color solid)

The MacAdam threshold matters because our JND seeds are packed at CIEDE2000
ΔE=1.0, but CIEDE2000 and Euclidean ΔE76 diverge in saturated regions. A
CIEDE2000 step of 1.0 can be 2-3 units in ΔE76 at the gamut periphery, so
ΔE76 <= 2.0 best approximates the true solid boundary.

Script: `results/analysis/gamut_volume.py`

### Results by threshold

| MacAdam threshold (ΔE76) | MacAdam vol (Lab³) | sRGB % of MacAdam | Adobe RGB % of MacAdam | Adobe/sRGB ratio |
|:------------------------:|-------------------:|------------------:|-----------------------:|-----------------:|
| 1.0 | 919,397 | 52.7% | 67.6% | 1.28x |
| 1.25 | 1,398,929 | 47.1% | 62.9% | 1.34x |
| 1.5 | 1,786,914 | 42.3% | 58.4% | 1.38x |
| **2.0** | **2,219,952** | **36.5%** | **52.5%** | **1.44x** |

### Raw gamut volumes (unconstrained by MacAdam)

| Gamut | CIELAB Volume (Lab³) |
|-------|---------------------:|
| sRGB | 819,203 |
| Adobe RGB (1998) | 1,195,021 |
| **Adobe / sRGB ratio** | **1.46x** |

---

## Convergence with Published Data

| Metric | sRGB | Adobe RGB | Source |
|--------|-----:|----------:|--------|
| CIELAB volume (Monte Carlo, ΔE76 <= 2.0) | 36.5% | **52.5%** | This study |
| Published industry claims | 33-55% | **~50%** | Various (Adobe, ICC literature) |
| Perceptual count — obvious tier (ΔE=5.0) | 34.6% | **49.3%** | This study |
| Perceptual count — JND tier (ΔE=1.0) | 59.0% | 72.2% | This study |
| Adobe/sRGB volume ratio | — | **1.46x** | This study |
| Adobe/sRGB published ratio | — | **~1.4-1.5x** | Industry standard |

### Key findings

1. **Our CIELAB volume measurement reproduces Adobe's published claim** that
   Adobe RGB covers ~50% of the visible (surface color) gamut. We measure
   52.5%, squarely within the range cited in ICC and color science literature.

2. **Our sRGB volume measurement (36.5%) falls within the published range**
   of 33-55%. The wide range in published estimates reflects different
   measurement methodologies; our Monte Carlo approach is rigorous and
   reproducible.

3. **The Adobe/sRGB volume ratio of 1.46x** matches the commonly cited
   figure that Adobe RGB is "about 40-50% larger" than sRGB in CIELAB.

4. **Perceptual count vs volume count diverge** — and both are correct.
   Lab volume treats every cubic unit of CIELAB equally. Perceptual count
   weights regions by how many distinguishable colors they contain. The
   mid-gamut (where sRGB lives) is perceptually dense, so sRGB "punches
   above its weight" in perceptual terms (59%) vs raw volume (36.5%).

5. **The obvious-tier perceptual count closely matches Lab volume estimates.**
   At ΔE=5.0 spacing, the seeds are spread uniformly enough that counting
   them approximates volume measurement. This makes the obvious tier a
   natural bridge between the two metrics.

---

## Date

2026-03-06
