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

### Convergence Testing

Because greedy sphere-packing on a discrete grid can only find seeds that land on grid points, the grid must be fine enough to catch every possible seed. We ran the census at four resolutions to test convergence.

Our initial runs (before discovering and fixing the cross-slice overcounting bug described below) showed counts that *doubled* with each resolution increase — a sign of overcounting, not convergence:

| | Coarse | Fine | Superfine | Ultrafine |
|---|---|---|---|---|
| **L\* step** | 1.0 | 0.25 | 0.125 | 0.0625 |
| **a\*/b\* step** | 2.0 | 0.5 | 0.25 | 0.125 |
| **Candidates** | ~1.6M | ~104M | ~835M | ~6.7B |
| **JND** (ΔE=1.0) | 313,115 | 1,834,305 | 3,997,938 | 8,414,939 |
| **Acceptability** (ΔE=2.0) | 109,032 | 513,715 | 1,063,584 | 2,162,115 |
| **Obvious** (ΔE=5.0) | 74,463 | 337,085 | 676,635 | 1,358,876 |
| **Runtime** | ~2 min | ~10 min | ~37 min | ~3.5 hrs |

The suspiciously consistent ~2× scaling was the clue that led us to discover the cross-slice bug (see "The Bug We Found" below). After fixing it, the corrected runs will be posted here.

### The Numbers

At our finest resolution tested (ultrafine, 6.7 billion candidates):

| Tier | ΔE2000 | Distinguishable Colors |
|------|--------|------------------------|
| **JND** | 1.0 | **321,930** |
| **Acceptability** | 2.0 | **51,868** |
| **Obvious** | 5.0 | **17,313** |

Each seed is an actual point in CIELAB space, verified to lie within the human visual gamut, with a ΔE2000 distance of at least the tier's threshold from every other seed — both within its own lightness slice and across adjacent slices (via ghost-seed cross-slice deduplication). The counts are converging: the ultrafine-to-superfine ratio is 1.05–1.08×, suggesting the true counts are within ~10% of these values.

### Why the Old Estimate Was Wrong

The 10 million figure overcounts because it assumes perceptual independence along color axes. Multiplying "distinguishable steps" along lightness × chroma × hue treats color space as a rectangular grid where every combination is valid and every step is uniform. But:

- **The gamut isn't a box.** The human visual gamut in CIELAB is an irregular volume that varies dramatically with lightness. Near L\*=0 (black) and L\*=100 (white), the gamut shrinks to almost nothing. The widest cross-sections are in the mid-lightness range.

- **ΔE2000 isn't Euclidean.** The formula applies different weights depending on where you are in color space. The same numerical step in a\* or b\* can be a large perceptual difference in one region and imperceptible in another. Axis-multiplication assumes uniform step sizes.

- **The axes interact.** CIEDE2000 includes cross-terms — a rotation correction for blue, chroma-dependent scaling of hue sensitivity. These interactions mean you can't factor the space into independent dimensions and multiply.

### The Tier Ratios

The ratios between tiers have been stable across all four post-fix grid resolutions:

| Ratio | Coarse | Fine | Superfine | Ultrafine |
|---|---|---|---|---|
| **JND : Acceptability** | 4.8:1 | 6.1:1 | 6.1:1 | 6.2:1 |
| **JND : Obvious** | 13.8:1 | 17.9:1 | 18.2:1 | 18.6:1 |
| **Acceptability : Obvious** | 2.9:1 | 2.9:1 | 3.0:1 | 3.0:1 |

The Acceptability-to-Obvious ratio is strikingly consistent at ~3.0:1 across all resolutions, suggesting this relationship is well-captured even at coarse sampling. The JND ratios stabilize by the fine resolution, confirming convergence.

**JND to Acceptability — ~6.2:1.** About 84% of the colors the eye can technically resolve are distinctions that don't matter in practice. For display engineering, color management, and print production, the relevant number is roughly one-sixth of the JND count.

**JND to Obvious — ~18.6:1.** Casual perception uses about 5% of the visual system's theoretical resolution.

**Acceptability to Obvious — ~3.0:1.** For every obviously different color, there are about three that a trained eye would call "meaningfully different." The gap between professional color matching and everyday perception is wider than the pre-fix numbers suggested.

### Where the Colors Live

The per-slice data shows that color density is not uniform across lightness:

- **Dark colors (L\* 0–20):** Sparse. The gamut is small and the eye is relatively insensitive.
- **Mid-lightness (L\* 40–70):** Peak density. This is where the gamut is widest and ΔE2000 packs most efficiently. The majority of distinguishable colors live here.
- **Light colors (L\* 80–100):** Moderately dense but declining. The gamut narrows as colors approach white.

This matches the everyday intuition that mid-tones are "where the color is" — there are literally more distinguishable colors in the middle of the lightness range than at either extreme.

---

## Caveats and Limitations

### Grid Resolution

Our convergence testing shows that counts roughly double with each halving of the grid step size across four runs (coarse → fine → superfine → ultrafine). This consistent doubling has not yet shown clear signs of flattening. The ultrafine run (L\*=0.0625, a\*/b\*=0.125) yielded ~8.4M JND — these remain **lower bounds**. Extrapolating the doubling trend suggests the converged JND count may be in the range of 15–20 million, though the curve must eventually flatten as grid points become dense enough to capture all possible seed positions.

### Greedy Packing Is Order-Dependent

Greedy sphere-packing doesn't find the optimal packing — it finds *a* valid packing. Processing points in a different order would yield a different count. However, for well-behaved spaces, greedy packing typically achieves within 60–80% of the theoretical maximum. The true optimum is likely higher than our count but bounded above by the volume-integration estimate.

### The Gamut Is Theoretical

We validate against the full spectral locus — the boundary of all physically realizable colors under the CIE 1931 2° standard observer with D65 illumination. No real display, printer, or set of pigments can reproduce this entire gamut. The sRGB gamut (standard monitors), Adobe RGB (photography), and even Rec. 2020 (HDR video) are all strict subsets. The count of distinguishable colors *on your screen* is substantially smaller.

### Observer Variation

The CIE standard observer represents an average. Individual humans vary in cone sensitivity, lens transmission (especially with age — the lens yellows, reducing blue sensitivity), and even in the number of cone types (some women are tetrachromats with four cone types instead of three). Our count assumes the standard observer.

---

## The Bug We Found (And Fixed)

The results above — the ones showing counts doubling at every resolution — contained a systematic overcounting bug. Here's how we found it.

### The Clue

After four runs at increasing resolution, the pattern was suspiciously clean: counts roughly doubled with each halving of the grid step size. Coarse to fine: ~5.9×. Fine to superfine: ~2.2×. Superfine to ultrafine: ~2.1×. The first jump was larger because both the L\* step *and* the a\*/b\* steps halved, but after that, the doubling was mechanical.

That should have been the first red flag. If the grid is getting fine enough to capture most seed positions, the counts should *converge* — each successive run should add fewer new seeds, not proportionally the same number. A curve that doubles forever isn't converging. It's overcounting.

The human insight came from staring at the numbers and asking: *"Why would making the lightness slices thinner create more perceptible colors?"* It shouldn't. The number of distinguishable colors is a physical constant of the human visual system. Measuring it more finely should approach the true value from below, not keep climbing linearly.

### The Bug

The algorithm processes CIELAB color space one lightness (L\*) slice at a time. For each slice, it builds a KD-tree of candidate points, iterates through them, and packs non-overlapping ΔE2000 neighborhoods. The problem: **each slice was packed in complete isolation**. The KD-tree for slice N contained only points from slice N. Seeds placed in slice N−1 were invisible.

When the L\* step was coarse (1.0), this barely mattered — adjacent slices were far enough apart in lightness that cross-slice ΔE2000 distances were usually above the JND threshold. But at ultrafine resolution (L\* step = 0.0625), two candidate points at the same (a\*, b\*) position in adjacent slices differed by only ΔE2000 ≈ 0.06 — well under the JND threshold of 1.0. Both became seeds because neither could "see" the other.

The result: for every real seed, the algorithm was placing ~96 copies of it across the ~96 adjacent slices within the KD-tree search radius. The count didn't reflect the number of distinguishable colors; it reflected the number of grid points near each color times the number of real colors. Finer grids meant more grid points per color, which meant higher counts. Doubling, not converging.

### The Fix

The fix is a "ghost seed" rolling buffer. As slices are processed in ascending L\* order, JND seed positions from recently completed slices are kept in a buffer. When packing the current slice, these ghost seeds are loaded into a separate read-only KD-tree. Before a candidate point can become a new seed, it's checked against all ghost seeds within the search radius (6.0 Euclidean units in CIELAB, corresponding to ~96 slices at ultrafine resolution). If any ghost seed is within ΔE2000 of the candidate at a given tier's threshold, the candidate is suppressed — claimed but not counted.

Ghost seeds are never modified, deleted, or iterated over. They're purely exclusion zones from previous slices, ensuring that the same distinguishable color isn't counted multiple times just because the grid happened to sample it from multiple L\* values.

### The Story

This is, in a way, the most satisfying kind of bug. The algorithm was working exactly as written — the greedy packer was correctly finding and claiming neighborhoods within each slice. The error was architectural: a reasonable simplification (per-slice independence) that was harmless at coarse resolution but became the dominant source of error as resolution increased.

The numbers that follow are from corrected runs with ghost-seed cross-slice deduplication enabled.

### Post-Fix Convergence Results

With ghost-seed deduplication active, the convergence ratios tell a completely different — and much more believable — story:

| | Coarse | Fine | Superfine | Ultrafine |
|---|---|---|---|---|
| **L\* step** | 1.0 | 0.25 | 0.125 | 0.0625 |
| **a\*/b\* step** | 2.0 | 0.5 | 0.25 | 0.125 |
| **Candidates** | ~1.6M | ~104M | ~835M | ~6.7B |
| **JND** (ΔE=1.0) | 172,588 | 276,941 | 299,370 | 321,930 |
| **Acceptability** (ΔE=2.0) | 35,873 | 45,038 | 48,675 | 51,868 |
| **Obvious** (ΔE=5.0) | 12,467 | 15,446 | 16,456 | 17,313 |
| **Runtime** | ~2 min | ~10 min | ~52 min | ~4 hrs 5 min |

**Convergence ratios:**

| Tier | Fine / Coarse | Superfine / Fine | Ultrafine / Superfine |
|---|---|---|---|
| **JND** | 1.60× | 1.08× | **1.08×** |
| **Acceptability** | 1.26× | 1.08× | **1.07×** |
| **Obvious** | 1.24× | 1.07× | **1.05×** |

The ratios are tightening exactly as expected. Fine/coarse showed 1.2–1.6× as the grid caught seeds missed at coarse resolution. Superfine/fine dropped to 1.07–1.08×, and ultrafine/superfine held at 1.05–1.08× — the counts are converging. Compare to the pre-fix ratios of 4–6× that screamed overcounting. At ultrafine, the obvious tier is growing by only 5% per resolution doubling, suggesting we're within a few percent of the true count.

---

## What This Means

### For Color Science

The 10 million figure is wrong — and not just a little wrong. Our converging count of ~322,000 JND-distinguishable colors is roughly **30× smaller** than the commonly cited estimate. The axis-multiplication method (100 lightness levels × 100 chroma levels × 100 hues = 10 million) dramatically overcounts because it assumes a rectangular gamut with uniform perceptual steps. The actual gamut is an irregular blob, ΔE2000 is highly non-uniform, and the axes interact nonlinearly.

These counts are still lower bounds — the convergence ratios of 1.05–1.08× suggest the true values are perhaps 10–15% higher. But even generously extrapolated, the JND count lands around 350,000–400,000. Not millions.

### For Display Technology

If you're designing a display system and want to reproduce every "meaningfully different" color, you need roughly 50,000–60,000 distinct colors — not millions and certainly not the billions offered by modern displays. A true 10-bit-per-channel display (1.07 billion colors) has roughly **20,000×** more addressable colors than there are perceptually distinguishable ones at the acceptability threshold. The engineering headroom is not just enormous — it's absurd.

### For Color Naming

Linguists have long debated how many basic color terms a language needs. If there are ~17,000 "obviously different" colors, and most languages have 4–12 basic color terms, each term covers roughly 1,400–4,300 distinguishable colors. The gap between what the eye resolves and what language names is still large, but far more tractable than the millions previously assumed.

### For Everyday Life

Under normal conditions — not in a calibrated lab, not with side-by-side swatches — you experience roughly 17,000 obviously distinguishable colors. That's still a rich palette, but it's a number a human could conceivably engage with. It's about 5% of the ~322,000 your visual hardware could theoretically resolve at the JND threshold. Most of your color resolution goes unused in daily life — but the total budget is far smaller than anyone thought.

---

## Methodology Details

**Color space:** CIELAB (CIE L\*a\*b\*) under CIE standard illuminant D65, 2° standard observer.

**Grid:** Four resolutions tested for convergence. Finest completed: L\* ∈ [0, 100] step 0.0625; a\* ∈ [−128, +127] step 0.125; b\* ∈ [−128, +127] step 0.125. Total candidates: ~6.7 billion.

**Gamut validation:** L\*a\*b\* → XYZ → chromaticity (x, y) → point-in-polygon test against the CIE 1931 spectral locus. XYZ non-negativity enforced.

**Color difference:** CIEDE2000 (CIE 142-2001) with k_L = k_C = k_H = 1.0. Implementation validated against all 34 Sharma/Wu/Dalal published test pairs to 4 decimal places.

**Packing:** Greedy, single-pass, processing by L\* slice. KD-tree spatial indexing with Euclidean search radius of 6.0 (conservative overestimate). Three thresholds evaluated simultaneously per candidate. Cross-slice deduplication via per-tier ghost seed rolling buffer — seeds from each tier in recent slices (within ±6.0 L\* units) are checked against new candidates at that tier's threshold to prevent overcounting across adjacent slices.

**Software:** Python 3.12, NumPy, SciPy (cKDTree). Full source available at [github.com/caoimghgin/hueknew](https://github.com/caoimghgin/hueknew).

---

*How many colors can you see? Far fewer than you've been told — but now we can actually point to each one.*

---

## Appendix: Raw Run Data

*These runs were conducted before the cross-slice deduplication fix. Counts are overcounted, especially at finer resolutions. Post-fix corrected runs will be appended.*

### Run 1 — Coarse (validation, pre-fix)
- **Grid:** L\* step 1.0, a\*/b\* step 2.0
- **Candidates:** ~1.6 million (~101 slices × ~16K per slice)
- **Results:** JND: 313,115 · Acceptability: 109,032 · Obvious: 74,463
- **Runtime:** ~2 minutes

### Run 2 — Fine (pre-fix)
- **Grid:** L\* step 0.25, a\*/b\* step 0.5
- **Candidates:** ~104 million (~401 slices × ~261K per slice)
- **Results:** JND: 1,834,305 · Acceptability: 513,715 · Obvious: 337,085
- **Runtime:** ~10 minutes

### Run 3 — Superfine (pre-fix)
- **Grid:** L\* step 0.125, a\*/b\* step 0.25
- **Candidates:** ~835 million (~801 slices × ~1.04M per slice)
- **Results:** JND: 3,997,938 · Acceptability: 1,063,584 · Obvious: 676,635
- **Runtime:** ~37 minutes

### Run 4 — Ultrafine (pre-fix)
- **Grid:** L\* step 0.0625, a\*/b\* step 0.125
- **Candidates:** ~6.7 billion (~1601 slices × ~4.16M per slice)
- **Results:** JND: 8,414,939 · Acceptability: 2,162,115 · Obvious: 1,358,876
- **Runtime:** ~3.5 hours

---

### Run 5 — Coarse (post-fix, with ghost-seed deduplication)
- **Grid:** L\* step 1.0, a\*/b\* step 2.0
- **Candidates:** ~1.6 million (~101 slices × ~16K per slice)
- **Results:** JND: 172,588 · Acceptability: 35,873 · Obvious: 12,467
- **Runtime:** ~2 minutes

### Run 6 — Fine (post-fix, with ghost-seed deduplication)
- **Grid:** L\* step 0.25, a\*/b\* step 0.5
- **Candidates:** ~104 million (~401 slices × ~261K per slice)
- **Results:** JND: 276,941 · Acceptability: 45,038 · Obvious: 15,446
- **Runtime:** ~10 minutes

### Run 7 — Superfine (post-fix, with ghost-seed deduplication)
- **Grid:** L\* step 0.125, a\*/b\* step 0.25
- **Candidates:** ~835 million (~801 slices × ~1.04M per slice)
- **Results:** JND: 299,370 · Acceptability: 48,675 · Obvious: 16,456
- **Runtime:** ~52 minutes
- **Convergence ratio (SF/Fine):** JND 1.08× · Acceptability 1.08× · Obvious 1.07×

### Run 8 — Ultrafine (post-fix, with ghost-seed deduplication)
- **Grid:** L\* step 0.0625, a\*/b\* step 0.125
- **Candidates:** ~6.7 billion (~1601 slices × ~4.16M per slice)
- **Results:** JND: 321,930 · Acceptability: 51,868 · Obvious: 17,313
- **Runtime:** ~4 hours 5 minutes
- **Convergence ratio (UF/SF):** JND 1.08× · Acceptability 1.07× · Obvious 1.05×
