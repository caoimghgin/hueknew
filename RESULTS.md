# How Many Colors Can You Actually See?

## The Number Everyone Quotes Is Wrong

Ask the internet how many colors the human eye can see and you'll get the same answer everywhere: about 10 million. It shows up in textbooks, Wikipedia, display marketing copy, and color science explainers. It's one of those satisfying, round-ish numbers that sounds authoritative enough to never question.

But where does it come from?

The figure traces to estimates from the mid-20th century — most notably work by Nickerson and Newhall (1943) and later Pointer and Attridge (1998). The method was reasonable for its time: estimate the number of just-noticeable steps along each perceptual axis (lightness, chroma, hue), then multiply. The logic is intuitive. If you can distinguish 100 levels of lightness, 100 levels of chroma, and 100 hues, that's 100 × 100 × 100 = one million. Scale up the axis counts and you get to 10 million.

The problem is that human color perception doesn't work like a Cartesian grid. The axes aren't independent. A step that's just noticeable at one lightness may be invisible at another. The blue-purple region of perceptual space is warped relative to the green-yellow region. Chroma and hue interact nonlinearly. Multiplying axis counts together assumes a rectangular box, but the actual shape of perceptual color space is an irregular, lumpy, asymmetric blob.

Nobody had actually counted. Until now.

---

## What We Did

We performed a brute-force enumeration — a chromatic census — of every distinguishable color in the human visual gamut. No estimation, no interpolation, no axis multiplication. Instead, we packed the space with actual colors and counted them.

### The Setup

Human color perception is modeled using CIELAB (L\*a\*b\*), a three-dimensional color space designed so that equal distances correspond to equal perceptual differences. The "distance" between two colors is measured using CIEDE2000 (also written ΔE2000 or ΔE₀₀), the most accurate color-difference formula currently standardized by the International Commission on Illumination (CIE). It accounts for:

- Lightness-dependent sensitivity (we're better at distinguishing light colors than dark ones)
- Chroma-dependent scaling (saturated colors are harder to tell apart)
- Hue-dependent weighting (some hue regions are more sensitive than others)
- A rotation correction for the problematic blue-purple region

A ΔE2000 of 1.0 is defined as a "just noticeable difference" (JND) — the smallest color change a trained observer can detect under controlled laboratory conditions.

### The Method

The algorithm is greedy sphere-packing in a non-Euclidean space:

1. **Generate candidates.** Lay a fine grid across the full CIELAB space: L\* from 0 to 100 in steps of 0.25, a\* and b\* from −128 to +127 in steps of 0.5. This produces approximately 104 million candidate points.

2. **Validate the gamut.** Not every L\*a\*b\* coordinate corresponds to a real color. Each candidate is converted to CIE XYZ tristimulus values and tested against the spectral locus — the boundary of physically realizable colors defined by the CIE 1931 standard observer. Points outside the boundary, or with negative tristimulus values, are discarded. About 75% of candidates survive.

3. **Pack.** Iterate through the valid points. For each one, check whether any previously selected "seed" color is within ΔE2000 < 1.0. If not, this point becomes a new seed — a new distinguishable color. Claim all neighbors within the threshold to prevent double-counting. Move on.

4. **Count.** When every valid point has been either selected as a seed or claimed by one, the number of seeds is the answer.

Spatial indexing (KD-trees) keeps the neighbor searches fast. The entire computation processes slice-by-slice along the lightness axis, with checkpointing for crash recovery. A live web dashboard tracks progress in real time.

### Three Thresholds, One Pass

Rather than run the census once, we ran it at three perceptual thresholds simultaneously:

| Threshold | ΔE2000 | What It Means |
|-----------|--------|---------------|
| **JND** | 1.0 | The smallest difference a trained observer can detect in a lab |
| **Acceptability** | 2.0 | The threshold used in industrial color matching — "would you reject this?" |
| **Obvious** | 5.0 | A difference anyone would notice under normal conditions |

Since these thresholds are nested (every JND neighborhood fits inside an acceptability neighborhood, which fits inside an obvious neighborhood), running all three simultaneously adds negligible computation. The expensive part — the ΔE2000 calculation for each neighbor pair — happens once regardless.

---

## The Results

| Tier | ΔE2000 | Distinguishable Colors |
|------|--------|------------------------|
| **JND** | 1.0 | **1,834,305** |
| **Acceptability** | 2.0 | **513,715** |
| **Obvious** | 5.0 | **337,085** |

### 1.8 Million, Not 10 Million

At the just-noticeable-difference threshold — the finest discrimination the human visual system can achieve — there are approximately 1.83 million distinguishable colors. Not 10 million. Not even close.

This isn't a rough estimate. Each of those 1,834,305 colors is an actual point in CIELAB space, verified to lie within the human visual gamut, with a ΔE2000 distance of at least 1.0 from every other seed. They are individually addressable. You could, in principle, display every one of them.

### Why the Old Estimate Was Wrong

The 10 million figure overcounts because it assumes perceptual independence along color axes. Multiplying "distinguishable steps" along lightness × chroma × hue treats color space as a rectangular grid where every combination is valid and every step is uniform. But:

- **The gamut isn't a box.** The human visual gamut in CIELAB is an irregular volume that varies dramatically with lightness. Near L\*=0 (black) and L\*=100 (white), the gamut shrinks to almost nothing. The widest cross-sections are in the mid-lightness range.

- **ΔE2000 isn't Euclidean.** The formula applies different weights depending on where you are in color space. The same numerical step in a\* or b\* can be a large perceptual difference in one region and imperceptible in another. Axis-multiplication assumes uniform step sizes.

- **The axes interact.** CIEDE2000 includes cross-terms — a rotation correction for blue, chroma-dependent scaling of hue sensitivity. These interactions mean you can't factor the space into independent dimensions and multiply.

The overcounting factor is roughly 5–6×. The old estimates weren't wildly wrong in order of magnitude, but they were wrong in a direction that matters.

### The Tier Ratios

The ratios between tiers reveal something about how human color perception actually operates:

**JND to Acceptability — 3.6:1.** Moving from "theoretically detectable" to "meaningfully different" reduces the count by nearly three-quarters. This means about 72% of the colors the eye can technically resolve are distinctions that don't matter in practice. For display engineering, color management, and print production, the relevant number is closer to 500,000 than 1.8 million.

**JND to Obvious — 5.4:1.** Casual perception — what people actually notice in everyday life — uses about 18% of the visual system's theoretical resolution. The average person walks around experiencing roughly 337,000 distinguishable colors, out of a possible 1.8 million.

**Acceptability to Obvious — 1.5:1.** This is perhaps the most surprising ratio. The gap between "meaningfully different" and "obviously different" is much smaller than the gap between "detectable" and "meaningful." Once a color difference crosses the acceptability threshold, there isn't much further to go before it becomes obvious. The jump from "a technician would notice" to "anyone would notice" is only a factor of 1.5.

### Where the Colors Live

The per-slice data shows that color density is not uniform across lightness:

- **Dark colors (L\* 0–20):** Sparse. The gamut is small and the eye is relatively insensitive.
- **Mid-lightness (L\* 40–70):** Peak density. This is where the gamut is widest and ΔE2000 packs most efficiently. The majority of distinguishable colors live here.
- **Light colors (L\* 80–100):** Moderately dense but declining. The gamut narrows as colors approach white.

This matches the everyday intuition that mid-tones are "where the color is" — there are literally more distinguishable colors in the middle of the lightness range than at either extreme.

---

## Caveats and Limitations

### Grid Resolution

Our fine grid uses steps of 0.25 in L\* and 0.5 in a\*/b\*. This is fine enough that most JND neighborhoods (radius ~1.0 in CIELAB) contain multiple grid points, but it's not infinitely fine. A finer grid would find *more* seeds, not fewer, because additional candidates between existing grid points might qualify as new seeds. Our result is therefore a **lower bound** — the true count is at least 1,834,305 and likely somewhat higher, though not dramatically so.

### Greedy Packing Is Order-Dependent

Greedy sphere-packing doesn't find the optimal packing — it finds *a* valid packing. Processing points in a different order would yield a different count. However, for well-behaved spaces, greedy packing typically achieves within 60–80% of the theoretical maximum. The true optimum is likely higher than our count but bounded above by the volume-integration estimate.

### The Gamut Is Theoretical

We validate against the full spectral locus — the boundary of all physically realizable colors under the CIE 1931 2° standard observer with D65 illumination. No real display, printer, or set of pigments can reproduce this entire gamut. The sRGB gamut (standard monitors), Adobe RGB (photography), and even Rec. 2020 (HDR video) are all strict subsets. The count of distinguishable colors *on your screen* is substantially smaller.

### Observer Variation

The CIE standard observer represents an average. Individual humans vary in cone sensitivity, lens transmission (especially with age — the lens yellows, reducing blue sensitivity), and even in the number of cone types (some women are tetrachromats with four cone types instead of three). Our count assumes the standard observer.

---

## What This Means

### For Color Science

The 10 million figure should be retired, or at minimum heavily qualified. A defensible number for the JND count is approximately 1.8 million (lower bound). The commonly cited figure overcounts by a factor of roughly 5–6× due to the assumption of perceptual axis independence.

### For Display Technology

If you're designing a display system and want to reproduce every "meaningfully different" color, you need about 500,000 distinct colors — not 10 million. A true 10-bit-per-channel display (1.07 billion colors) has roughly 2,000× more addressable colors than there are perceptually distinguishable ones at the acceptability threshold. The engineering headroom is enormous.

### For Color Naming

Linguists have long debated how many basic color terms a language needs. If there are only ~337,000 "obviously different" colors, and most languages have 4–12 basic color terms, each term covers roughly 30,000–80,000 distinguishable colors. The gap between what the eye resolves and what language names is even larger than previously thought.

### For Everyday Life

You will never see 10 million colors. Under normal conditions — not in a calibrated lab, not with side-by-side swatches — you experience roughly 337,000 distinguishable colors. That's still a staggeringly rich palette. But it's a small fraction of what the visual hardware could theoretically support, and a smaller fraction still of what gets claimed in marketing materials for wide-gamut displays.

---

## Methodology Details

**Color space:** CIELAB (CIE L\*a\*b\*) under CIE standard illuminant D65, 2° standard observer.

**Grid:** L\* ∈ [0, 100] step 0.25; a\* ∈ [−128, +127] step 0.5; b\* ∈ [−128, +127] step 0.5. Total candidates: ~104 million.

**Gamut validation:** L\*a\*b\* → XYZ → chromaticity (x, y) → point-in-polygon test against the CIE 1931 spectral locus. XYZ non-negativity enforced.

**Color difference:** CIEDE2000 (CIE 142-2001) with k_L = k_C = k_H = 1.0. Implementation validated against all 34 Sharma/Wu/Dalal published test pairs to 4 decimal places.

**Packing:** Greedy, single-pass, processing by L\* slice. KD-tree spatial indexing with Euclidean search radius of 6.0 (conservative overestimate). Three thresholds evaluated simultaneously per candidate.

**Software:** Python 3.12, NumPy, SciPy (cKDTree). Full source available at [github.com/caoimghgin/hueknew](https://github.com/caoimghgin/hueknew).

---

*How many colors can you see? Fewer than you've been told — but still more than you'll ever need a name for.*
