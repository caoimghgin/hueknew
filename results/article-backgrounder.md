# Chromatic Census — Article Backgrounder

A reference sheet of citable facts, findings, and context for the Medium article.

---

## The Headline Numbers

- **272,672** — distinguishable surface colors at JND threshold (CIEDE2000 ΔE = 1.0)
- **35,348** — at acceptability threshold (ΔE = 2.0)
- **9,256** — at obvious threshold (ΔE = 5.0)
- These are the final, gap-filled, MacAdam-bounded, exhaustively verified counts
- 50 million random probes found only 3 additional JND seeds and 0 at other tiers — the packing is saturated

## What These Thresholds Mean

- **JND (ΔE = 1.0):** The smallest color difference a trained observer can detect under ideal lab conditions. "Is this swatch *slightly* different from that one?"
- **Acceptability (ΔE = 2.0):** The threshold below which most people would accept two colors as "the same" in commercial/industrial contexts. The print industry standard for color matching.
- **Obvious (ΔE = 5.0):** A difference anyone would immediately notice. "Those are clearly two different colors." No training, no side-by-side comparison needed.

## How It Was Done

- **Method:** Greedy sphere packing (sequential inhibition / Poisson disk sampling) in CIELAB color space using CIEDE2000 as the distance metric
- **Domain:** Rösch–MacAdam optimal color solid — all physically realizable surface colors under CIE D65 daylight illumination
- **Grid:** Ultrafine resolution (L* step = 0.0625, a*/b* step = 0.125), iterated slice-by-slice along the L* (lightness) axis
- **Gap-fill:** Two-pass optimization after the main sweep — an offset grid at half-step resolution, followed by 50M uniformly random probes to verify saturation
- **Ghost-seed deduplication:** Each slice checks for seeds that might duplicate across slice boundaries, preventing double-counting at fine resolutions
- **Compute:** ~18 hours total on a 4-core AMD Ryzen 5 (ultrafine sweep + gap-fill)

## Gamut Coverage — What Your Display Can Show

### By perceptual count (number of distinguishable colors)

| Display | JND (272,672) | Obvious (9,256) |
|---------|:------------:|:---------------:|
| sRGB (most monitors) | 58.7% | 33.2% |
| Display P3 (iPhone, Mac, iPad) | 72.1% | 49.5% |
| Adobe RGB (photography monitors) | 71.8% | 48.1% |
| Outside all three | 27.8% | 50.5% |

### By CIELAB volume (Monte Carlo, 5M samples)

| Display | % of MacAdam solid |
|---------|-----------------:|
| sRGB | 36.5% |
| Adobe RGB | 52.5% |
| Adobe / sRGB ratio | 1.46x |

### Key insights

- **sRGB covers only ~1/3 of obviously-different surface colors.** Most monitors can't show you more than a third of what your eyes can distinguish.
- **Display P3 and Adobe RGB cover nearly identical territory (~50%)** but in different directions — P3 pushes further into reds and greens, Adobe RGB into cyans.
- **Over half of all obviously-different colors are outside every standard RGB gamut.** No consumer display can show them.
- **sRGB "punches above its weight" perceptually** — 33% of volume but 59% of JND colors, because the mid-gamut where sRGB lives is perceptually dense (more distinguishable colors per unit of CIELAB volume).
- Our Adobe RGB volume measurement (52.5%) reproduces the published industry claim of "~50% of the visible gamut."
- Our Adobe/sRGB volume ratio (1.46x) matches the commonly cited "Adobe RGB is ~40-50% larger than sRGB."

## Context and Comparisons

- **Published estimates for total distinguishable colors range from ~300K to 2.3M+**, depending on methodology, viewing conditions, and whether surface-color or self-luminous boundaries are used
- Our 272,672 JND count is for **surface colors only** (the Rösch–MacAdam solid under D65). Self-luminous colors (LEDs, monitors) can exceed these boundaries, particularly in saturated greens at high luminance
- The ±128 a*/b* grid commonly used in CIELAB is a bounding box for surface colors, not an exact boundary. Spectral green at L*=100 reaches a* ≈ −273 in the self-luminous domain
- The **shape of the color solid** is a lemon/spindle — wide at mid-lightness (~L*=50-60), pinching to single points at black (L*=0) and white (L*=100). Peak color diversity is at medium brightness.

## The Shape of Color

- At **L* = 0** (black): exactly 1 color. There is only one black.
- At **L* = 50** (mid-gray brightness): thousands of distinguishable colors per slice — the widest part of the solid
- At **L* = 100** (white): exactly 1 color. There is only one white.
- The solid is **asymmetric** — more distinguishable colors exist in the yellow-green region than in the blue-violet region at the same lightness
- The "tendril" at the dark end: near L*=2-5, the solid narrows to a thin chain of barely-chromatic dark colors threading down to the single black point

## Gap-Fill Impact

| Tier | Before gap-fill | After gap-fill | Added | % increase |
|------|----------------:|---------------:|------:|-----------:|
| JND | 269,812 | 272,672 | +2,860 | +1.1% |
| Acceptability | 33,509 | 35,348 | +1,839 | +5.5% |
| Obvious | 8,687 | 9,256 | +569 | +6.6% |

- The obvious tier gains the most (%) because the larger ΔE=5.0 ellipsoids have more room to nestle between the original slices
- The gap-fill also eliminates visible "layering" artifacts from the regular grid, producing a smooth, stochastic-looking distribution
- After gap-fill + 50M random verification, the packing can be considered exhaustive

## Grid Convergence

| Resolution | L* step | JND | Acceptability | Obvious |
|-----------|--------:|----:|-------------:|--------:|
| Coarse | 1.0 | 172,588 | 35,873 | 12,467 |
| Fine | 0.5 | 276,941 | 45,038 | 15,446 |
| Superfine | 0.25 | 299,370 | 48,675 | 16,456 |
| Ultrafine | 0.125 | 321,930 | 51,868 | 17,313 |

Note: These are pre-MacAdam numbers. After applying the MacAdam boundary (restricting to surface colors), the counts decrease because phantom self-luminous colors are excluded.

## Technical Vocabulary

- **CIELAB (CIE L\*a\*b\*)** — A perceptually (approximately) uniform color space. L* = lightness (0–100), a* = green-to-red, b* = blue-to-yellow
- **CIEDE2000 (ΔE00)** — The current gold-standard formula for perceptual color difference. Corrects for non-uniformities in CIELAB, especially in blues and low chroma
- **Rösch–MacAdam boundary** — The theoretical limit of all surface colors achievable under a given illuminant. Named for Siegfried Rösch (1928) and David MacAdam (1935)
- **Optimal color solid** — The 3D volume enclosed by the Rösch–MacAdam boundary. Every surface color you can see under daylight lives inside this shape.
- **JND (Just Noticeable Difference)** — The smallest perceptual difference detectable by a human observer. Corresponds to ΔE ≈ 1.0
- **Greedy sphere packing** — Place a seed, exclude everything within ΔE of it, repeat. Also called sequential inhibition or Poisson disk sampling in other fields.
- **Ghost seeds** — Seeds that appear valid in one L* slice but are actually too close to seeds in adjacent slices. Deduplication is critical at fine grid resolutions.
- **D65** — CIE Standard Illuminant D65, representing average daylight (~6500K). The standard reference illuminant for color science.

## Quotable Framings

- "We counted every color the human eye can distinguish — one by one."
- "Your iPhone can show you about half the colors you can see. The other half? No screen on Earth can display them."
- "There are 9,256 obviously different colors in the world. Your sRGB monitor can show you 3,072 of them."
- "The color solid is shaped like a lemon — wide in the middle, pinching to single points at black and white."
- "50 million random searches found zero new colors. The census is complete."
- "Adobe RGB and Display P3 cover almost exactly the same amount of color — about half — but they reach for different parts of the rainbow."

---

*Last updated: 2026-03-07*
*Data source: Chromatic Census, MacAdam-fixed ultrafine with gap-fill*
