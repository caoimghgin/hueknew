# Backgrounder: How Many Colors Can You Actually See?

## The Chromatic Census

We built a system to answer a deceptively simple question: **how many
visually distinguishable colors exist in the sRGB color space?**

The answer: **137,693**.

More precisely: 137,693 colors can be packed into sRGB such that no two
are closer than 1 ΔE2000 — the internationally accepted threshold for a
"just-noticeable difference" (JND) in human color perception.

This number comes from an ultrafine grid sweep — the densest resolution
we've run. A coarser grid found 116,003. The ultrafine grid found 19%
more, suggesting the true maximum is at least 137,693 and may be slightly
higher still. (See *Convergence* below.)

### Method

1. **Grid sweep.** We discretized the CIELAB perceptual color space into
   ~4.2 billion candidate points across 1,601 L* slices (lightness 0–100
   in 0.0625 steps, a* and b* in 0.125 steps).

2. **Greedy sphere packing.** For each candidate, we tested whether it
   was at least ΔE2000 ≥ 1.0 from every previously accepted seed. If so,
   it became a new seed. This is greedy sphere packing in a non-Euclidean
   space (CIEDE2000 is not a true metric — it varies with position).

3. **Gamut filtering.** The packing operates in full CIELAB (321,930
   JND seeds total). We then filtered to the sRGB gamut — the color
   space of standard monitors — yielding 137,693 seeds. The remaining
   184,237 seeds (57%) represent colors that exist perceptually but
   cannot be displayed on a standard screen.

### Census Results — Three Tiers

We ran three perceptual thresholds simultaneously:

| Tier | ΔE2000 | Total Seeds | sRGB Seeds | Non-sRGB | What It Means |
|------|--------|-------------|------------|----------|---------------|
| **JND** | 1.0 | 321,930 | **137,693** | 184,237 | Theoretical limit of human discrimination |
| **Acceptability** | 2.0 | 51,868 | **18,417** | 33,451 | Meaningfully different — would fail a color match |
| **Obvious** | 5.0 | 17,313 | **3,392** | 13,921 | Obviously different to anyone |

The ratios tell the real story: your eye can theoretically distinguish
**7.5×** more colors than would be "meaningfully different" in a color
matching test, and **40×** more than are "obviously" different to a
casual observer. Most humans walk around experiencing about 2.5% of
their visual system's color resolution.

### Convergence: Fine vs. Ultrafine

| Parameter | Fine Grid | Ultrafine Grid | Change |
|-----------|-----------|----------------|--------|
| L* step | 0.25 | 0.0625 | 4× finer |
| a*/b* step | 0.5 | 0.125 | 4× finer |
| Candidate points | ~105M | ~4.2B | 40× more |
| L* slices | 401 | 1,601 | 4× more |
| JND seeds (total) | 276,941 | 321,930 | +16.2% |
| JND seeds (sRGB) | 116,003 | 137,693 | +18.7% |
| Computation time | ~2.5 min | ~4 hours | |

The 19% increase from fine to ultrafine indicates the fine grid was not
fully converged. The ultrafine grid finds seeds in the gaps between the
fine grid's points. Whether an even finer grid would find significantly
more is an open question — diminishing returns are expected, but we
haven't proven convergence yet.

---

## The Chain Walk

The chain walk creates a single path through all 137,693 sRGB JND seeds,
optimized for perceptual smoothness. Adjacent steps in the walk should
look as similar as possible.

### Algorithm

```
1. Place seed (0, 0, 0) in ordered array       → black, the origin
2. Reference = last placed seed
3. Find 9 closest UNVISITED seeds by ΔE2000    → KD-tree + vectorized ΔE
4. Sort those 9 by ΔE ascending
5. Append sorted 9 to ordered array
6. Reference = seed in batch closest to target L*
   (target L* = proportion of seeds placed × 100)
7. Repeat until all seeds placed
```

The target L* pacing ensures the walk progresses smoothly from dark to
light. Without it, the greedy walk wanders erratically through lightness,
reaching L*≈97 within the first 1,000 seeds and zigzagging wildly.

### Chain Walk Statistics (Ultrafine)

| Statistic | Value |
|-----------|-------|
| Total adjacent pairs | 137,692 |
| Minimum ΔE | 0.943 |
| Median ΔE | 1.830 |
| Mean ΔE | — |
| Maximum ΔE | 40.004 |
| Computation time | ~2.7 seconds |

### The "Dregs" Problem

The largest gaps cluster in the final ~17,000 steps of the walk (offsets
>120,000). At that point, the remaining unvisited seeds are scattered
across the gamut — whatever colors the greedy walk didn't naturally
encounter. The top 5 gaps:

| Rank | Offset | ΔE | Left | Right |
|------|--------|----|------|-------|
| 1 | 137,691 | 49.69 | #EE5BFF (hot magenta) | #600318 (dark red) |
| 2 | 136,358 | 41.10 | #2A4A74 (steel blue) | #06B4F7 (sky blue) |
| 3 | 136,357 | 39.98 | #1AB0FD (bright blue) | #2A4A74 (steel blue) |
| 4 | 137,478 | 34.93 | #F37309 (orange) | #7C2C1A (rust) |
| 5 | 137,496 | 34.17 | #015E44 (forest) | #020819 (near-black) |

These are not meaningful perceptual transitions — they are the
algorithmic cost of linearizing a 3D packing into a 1D sequence.

---

## The JND Visual Audit

The audit tool (http://10.0.0.108:8084/jnd-audit) presents the chain walk
as a three-panel display:

```
┌──────────┬────────────┬──────────┐
│          │            │          │
│   prev   │    ref     │   next   │
│  seed    │   seed     │  seed    │
│          │  (taller)  │          │
│  ΔE 1.99 │            │ ΔE 1.96  │
│          │            │          │
└──────────┴────────────┴──────────┘
  L*a*b*       L*a*b*       L*a*b*
  #hex         #hex         #hex
```

- **Center panel:** The current seed in the chain walk
- **Left panel:** Previous seed (with ΔE to center overlaid)
- **Right panel:** Next seed (with ΔE to center overlaid)
- **Slider:** Jump to any of the 137,693 positions
- **Gap navigator:** Jump directly to the largest ΔE gaps

### The Falsifiable Claim (v1 — Linear)

At each step in the walk, the viewer can evaluate:

> **"In the sRGB color space, there is no color that can be inserted
> between the left and center — or between the center and right —
> that would be meaningfully visually different from both."**

This is testable at every single one of the 137,692 adjacent pairs.

---

## "He's intelligent, but not experienced." — Thinking in Three Dimensions

The linear chain walk presents an inherently two-dimensional view of a
three-dimensional problem. Like Khan in the Mutara Nebula, we were
thinking in two dimensions — linearizing a 3D sphere packing into a 1D
sequence and then asking whether a color "fits between" two adjacent
steps.

But the packing isn't a line. It's a graph.

### The neighborhood density analysis

We computed, for every one of the 137,693 sRGB JND seeds, how many
other seeds fall within ΔE 1.5:

| Statistic | Neighbors within ΔE < 1.5 |
|-----------|---------------------------|
| Maximum | **16** |
| Mean | **10.1** |
| Median | **10.0** |
| Seeds with 0 neighbors | 3 |

The average seed has **10 neighbors**. The linear chain walk shows only
2 of them (prev and next). The other 8 are invisible — consumed
elsewhere in the walk, or simply not adjacent in the linear ordering.

### Why this matters

The brown triple (ΔE 2.89 gap) looked like a packing failure in the
linear view. Investigation revealed 18 intermediate seeds — all in sRGB,
all already consumed earlier in the walk. The packing was dense; the
walk just couldn't show it.

A neighborhood view eliminates this problem entirely. Instead of asking
"does a color fit between these two?", it asks:

> **"Here is a color. Here are ALL the colors within 1.5 ΔE of it.
> There is no room for another distinguishable color."**

This is testable at every single one of the 137,693 seeds. No chain
walk needed. No dregs. No ordering artifacts. Just the raw packing
topology.

### The densest neighborhoods

The seeds with the most neighbors (16 within ΔE 1.5) cluster in
mid-tone, moderate-chroma regions — dusty blues, mauves, taupes:

| Hex | L* | a* | b* | Description | Neighbors |
|---------|-------|-------|-------|-------------|-----------|
| #316B86 | 42.4 | -10.1 | -20.6 | Steel blue | 16 |
| #F4B3BC | 79.1 | 25.1 | 4.9 | Dusty rose | 16 |
| #886C81 | 48.9 | 14.9 | -7.3 | Mauve | 16 |
| #4D757F | 46.6 | -11.0 | -9.9 | Teal gray | 16 |
| #E6A5C3 | 74.6 | 28.0 | -5.5 | Pink | 16 |

These are the regions where CIEDE2000's non-Euclidean geometry is most
"round" — the JND ellipsoids are closest to spheres, so more neighbors
fit within a given ΔE radius. At the gamut boundaries and in highly
chromatic regions, the ellipsoids elongate and fewer neighbors pack in.

### The sparsest neighborhoods

Only 3 seeds have zero neighbors within ΔE 1.5. These are likely at
extreme gamut corners — the most isolated colors in sRGB, with no other
distinguishable color anywhere nearby.

---

## Gap Analysis: Two Case Studies

### Case 1: Blue Triple at L*=61 (Tight Packing, No Gamut Holes)

**Offset ~54,183** — Three medium-saturation blues.

| Panel | Hex | ΔE to ref |
|-------|---------|-----------|\
| Left | #4E98C9 | 1.99 |
| **Ref** | **#579AC4** | — |
| Right | #4797C7 | 1.96 |

**Context:** In this blue region of CIELAB, 50.7% of JND seeds fall
outside sRGB. The gamut boundary is close.

**Finding:** Despite this, **zero non-sRGB seeds** sit between the
adjacent pairs. All 6 intermediate seeds in each gap are representable
in sRGB. The gap is a true packing boundary, not a gamut artifact.

The tightest intermediary: L*=60.2, a*=-9.0, b*=-30.0 sits at ΔE 1.035
from the reference and 1.022 from the left neighbor. It exists, it's in
sRGB, it's already a JND seed. There is no room for another
distinguishable color.

**Verdict:** Claim holds. The packing is tight.

*Full analysis: [findings-2026-02-25-blue-triple.md](findings-2026-02-25-blue-triple.md)*

### Case 2: Brown/Orange Triple at L*=49.25 (Chain-Walk Artifact)

**Offset ~58,274** — Three warm browns/oranges.

| Panel | Hex | ΔE to ref |
|-------|---------|-----------|\
| Left | #B36822 | 2.89 |
| **Ref** | **#A76627** | — |
| Right | #A7631F | 1.26 |

**Context:** The left gap of ΔE 2.89 is conspicuously large — nearly 3
JND steps. Visually, one expects a distinguishable brown between them.

**Finding:** 18 seeds fit between the pair. **All 18 are in sRGB.** Zero
non-sRGB seeds. The packing is actually dense here — seed #AB6524 is
only ΔE 1.067 from the reference.

The ΔE 2.89 gap exists because those 18 intermediate seeds were already
**consumed at earlier positions** in the greedy chain walk. The walk had
passed through this warm-brown neighborhood on a prior visit and claimed
those seeds.

**Verdict:** The packing holds — the gap is a chain-walk ordering
artifact, not a packing hole or gamut limitation. The brown triple's
reference seed actually has **10+ neighbors** within ΔE 1.5 — a
neighborhood the linear view completely hides.

*Full analysis: [findings-2026-02-25-brown-triple.md](findings-2026-02-25-brown-triple.md)*

---

## Key Insights

### 1. The packing is robust against gamut filtering

Even in regions where >50% of CIELAB JND seeds fall outside sRGB, the
remaining sRGB seeds maintain tight packing. We have not yet found a
case where a non-sRGB seed would "bridge" a gap between adjacent sRGB
seeds.

### 2. Large ΔE gaps are walk artifacts, not packing failures

The ΔE between adjacent chain-walk steps is not always the local packing
density — it is the **remaining density** after earlier steps have claimed
nearby seeds. A greedy nearest-neighbor traversal can revisit neighborhoods
it partially consumed, creating adjacencies with larger ΔE than the
packing would suggest.

### 3. The linear view hides the true topology

Each seed has a median of 10 neighbors within ΔE 1.5. The chain walk
shows only 2. Linearizing a 3D graph into a 1D sequence necessarily
discards most of the local structure. This is the "Wrath of Khan"
problem: thinking in two dimensions when the packing lives in three.

### 4. The "dregs" are a linearization artifact, not a packing feature

The final ~17,000 steps of the chain walk produce ΔE gaps up to 49.7.
These are not sparse packing regions — they are seeds that no smooth 1D
path naturally encounters. The dregs disappear entirely in a graph
view, where every seed simply shows its local neighborhood.

### 5. sRGB contains 43% of perceptually distinguishable colors

Of 321,930 JND seeds in all of CIELAB, only 137,693 (43%) survive the
sRGB gamut filter. Wider-gamut displays (P3, Rec.2020, Rec.2100) could
show significantly more distinguishable colors — up to 321,930 if the
display covered the entire human visual gamut.

### 6. The ultrafine grid found 19% more colors than fine

The fine grid (L*=0.25, a/b=0.5) found 116,003 sRGB JND seeds. The
ultrafine grid (L*=0.0625, a/b=0.125) found 137,693 — a 19% increase.
This means the fine grid was not fully converged. The true count is at
least 137,693 and likely somewhat higher. Convergence testing at even
finer resolutions would establish the asymptotic limit.

---

## The Stronger Claim

The chain walk's falsifiable claim was:

> *"No color fits between these two adjacent chain-walk steps."*

The neighborhood view enables a stronger, cleaner claim:

> **"Here is a color. Here are ALL the colors within 1.5 ΔE of it.
> There is no room for another distinguishable color."**

This claim:
- Is testable at every one of the 137,693 seeds
- Requires no chain walk ordering
- Has no dregs or artifacts
- Shows the actual 3D packing topology
- Is visually self-evident: the neighborhood is full

The graph view (planned) will render this as a force-directed network:
each seed surrounded by its neighbors, with edges showing all
connections within ΔE 1.5. The viewer can click any node to re-center,
walking the packing graph directly.

---

## Tools

| Tool | Description |
|------|-------------|
| JND Visual Audit | Interactive three-panel chain-walk viewer with gap navigation |
| JND Neighborhood | Orbital view showing all neighbors within ΔE radius |
| JND Graph (planned) | Force-directed network view with inter-neighbor edges |
| `analysis/gap_analysis.py` | Gap analysis for any chain-walk triple — checks for gamut holes |
| `analysis/neighbor_density.py` | Neighbor count analysis for all sRGB seeds |

## Reproduction

```bash
# Run the census (ultrafine grid, ~4 hours)
docker run -d --name chromatic-census \
    -p 8084:8084 -v /path/to/output:/app/output \
    chromatic-census python run.py --mode ultrafine

# Run the census (fine grid, ~2.5 minutes)
docker run -d --name chromatic-census \
    -p 8084:8084 -v /path/to/output:/app/output \
    chromatic-census python run.py --mode fine

# Dashboard-only mode (after census completes)
docker run -d --name chromatic-census \
    -p 8084:8084 -v /path/to/output:/app/output \
    chromatic-census python run.py --dashboard-only

# Gap analysis for a specific triple
docker exec -w /app chromatic-census python analysis/gap_analysis.py \
    --ref 61.0 -9.5 -28.0 \
    --left 60.0 -8.0 -32.5 \
    --right 59.5 -9.5 -32.0

# Neighbor density analysis
docker run --rm \
    -v /path/to/output:/data/output \
    chromatic-census python analysis/neighbor_density.py
```

---

## Timeline

| Date | Milestone |
|------|-----------|
| 2026-02-23 | Initial census (fine grid): 276,941 JND seeds, 116,003 sRGB |
| 2026-02-25 | JND Visual Audit: 3-panel chain walk viewer with gap navigation |
| 2026-02-25 | Pure ΔE chain walk (removed L* bias, then restored as paced target) |
| 2026-02-25 | Gap analysis: blue triple (tight packing) and brown triple (walk artifact) |
| 2026-02-25 | "Think in 3D" insight — neighborhood density analysis reveals median 10 neighbors |
| 2026-02-25 | Ultrafine census: 321,930 JND seeds, 137,693 sRGB (+19%) |
| 2026-02-25 | Chain walk pacing: target L* reference for smooth dark→light progression |
| Next | JND Graph View: force-directed neighborhood explorer |
