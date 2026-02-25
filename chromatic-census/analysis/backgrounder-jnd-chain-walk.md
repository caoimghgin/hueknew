# Backgrounder: How Many Colors Can You Actually See?

## The Chromatic Census

We built a system to answer a deceptively simple question: **how many
visually distinguishable colors exist in the sRGB color space?**

The answer: **116,003**.

More precisely: 116,003 colors can be packed into sRGB such that no two
are closer than 1 ΔE2000 — the internationally accepted threshold for a
"just-noticeable difference" (JND) in human color perception.

### Method

1. **Grid sweep.** We discretized the CIELAB perceptual color space into
   ~105 million candidate points across 401 L* slices (lightness 0–100
   in 0.25 steps, a* and b* in 0.5 steps).

2. **Greedy sphere packing.** For each candidate, we tested whether it
   was at least ΔE2000 ≥ 1.0 from every previously accepted seed. If so,
   it became a new seed. This is greedy sphere packing in a non-Euclidean
   space (CIEDE2000 is not a true metric — it varies with position).

3. **Gamut filtering.** The packing operates in full CIELAB (276,941
   JND seeds total). We then filtered to the sRGB gamut — the color
   space of standard monitors — yielding 116,003 seeds. The remaining
   160,938 seeds (58%) represent colors that exist perceptually but
   cannot be displayed on a standard screen.

4. **Chain walk ordering.** To create a meaningful viewing sequence, we
   ordered the 116,003 sRGB seeds via a greedy nearest-neighbor walk
   through ΔE2000 space, starting at black (0,0,0). Each step finds the
   9 closest unvisited seeds, appends them sorted by ΔE, then advances
   the reference to the farthest of the batch.

### Census Parameters

| Parameter | Value |
|-----------|-------|
| Grid resolution | L*=0.25, a*=0.5, b*=0.5 |
| Candidate points | ~104,709,521 |
| L* slices | 401 (0.00 to 100.00) |
| JND threshold | ΔE2000 = 1.0 |
| Total JND seeds (all gamuts) | 276,941 |
| sRGB JND seeds | 116,003 |
| Computation time | ~2.5 minutes (Ryzen 5 5600) |

---

## The Chain Walk

The chain walk creates a single path through all 116,003 sRGB JND seeds,
optimized for perceptual smoothness. Adjacent steps in the walk should
look as similar as possible.

### Algorithm

```
1. Place seed (0, 0, 0) in ordered array       → black, the origin
2. Reference = last placed seed
3. Find 9 closest UNVISITED seeds by ΔE2000    → KD-tree + vectorized ΔE
4. Sort those 9 by ΔE ascending
5. Append sorted 9 to ordered array
6. Reference = last appended seed (farthest of the 9)
7. Repeat until all seeds placed
```

### Chain Walk Statistics

| Statistic | Value |
|-----------|-------|
| Total adjacent pairs | 116,002 |
| Minimum ΔE | 0.878 |
| Median ΔE | 1.742 |
| Mean ΔE | 1.983 |
| Maximum ΔE | 67.176 |
| Computation time | ~2.7 seconds |

The median step of 1.74 ΔE means most adjacent pairs are under 2 JND —
at the very edge of distinguishability. The walk stays perceptually smooth
across the vast majority of its 116,003 steps.

### The "Dregs" Problem

The largest gaps cluster in the final ~1,000 steps of the walk (offsets
>115,000). At that point, the remaining unvisited seeds are scattered
across the gamut — whatever colors the greedy walk didn't naturally
encounter. The top 5 gaps:

| Rank | Offset | ΔE | Left | Right |
|------|--------|----|------|-------|
| 1 | 115,999 | 67.18 | #FC16DC (hot pink) | #1F3927 (dark green) |
| 2 | 115,964 | 51.20 | #FFE2FE (pale pink) | #4B43C5 (blue-violet) |
| 3 | 115,963 | 40.60 | #74FEE7 (mint) | #FFE2FE (pale pink) |
| 4 | 115,468 | 35.36 | #D5FDB1 (pale green) | #FEA910 (orange) |
| 5 | 114,469 | 31.66 | #6FA994 (sage) | #125849 (dark teal) |

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
- **Slider:** Jump to any of the 116,003 positions
- **Gap navigator:** Jump directly to the largest ΔE gaps

### The Falsifiable Claim

At each step in the walk, the viewer can evaluate:

> **"In the sRGB color space, there is no color that can be inserted
> between the left and center — or between the center and right —
> that would be meaningfully visually different from both."**

This is testable at every single one of the 116,002 adjacent pairs.

---

## Gap Analysis: Two Case Studies

### Case 1: Blue Triple at L*=61 (Tight Packing, No Gamut Holes)

**Offset ~54,183** — Three medium-saturation blues.

| Panel | Hex | ΔE to ref |
|-------|---------|-----------|
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
|-------|---------|-----------|
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
artifact, not a packing hole or gamut limitation.

*Full analysis: [findings-2026-02-25-brown-triple.md](findings-2026-02-25-brown-triple.md)*

---

## Key Insights

### 1. The packing is robust against gamut filtering

Even in regions where >50% of CIELAB JND seeds fall outside sRGB, the
remaining sRGB seeds maintain tight packing. We have not yet found a
case where a non-sRGB seed would "bridge" a gap between adjacent sRGB
chain-walk steps.

### 2. Large ΔE gaps are walk artifacts, not packing failures

The ΔE between adjacent chain-walk steps is not always the local packing
density — it is the **remaining density** after earlier steps have claimed
nearby seeds. A greedy nearest-neighbor traversal can revisit neighborhoods
it partially consumed, creating adjacencies with larger ΔE than the
packing would suggest.

### 3. The "dregs" reveal the topology of sRGB

The final ~1,000 steps of the walk produce enormous ΔE gaps (up to 67)
as the algorithm connects the last scattered unvisited seeds. These
residual colors — hot pinks, mints, pale purples — are the seeds that
no smooth perceptual path naturally encounters. They reveal that sRGB
has isolated pockets in perceptual space that cannot be reached by small
steps from any direction.

### 4. sRGB contains 42% of perceptually distinguishable colors

Of 276,941 JND seeds in all of CIELAB, only 116,003 (42%) survive the
sRGB gamut filter. Wider-gamut displays (P3, Rec.2020, Rec.2100) could
show significantly more distinguishable colors — up to 276,941 if the
display covered the entire human visual gamut.

---

## Tools

| Tool | Description |
|------|-------------|
| JND Visual Audit | Interactive three-panel chain-walk viewer with gap navigation |
| `analysis/gap_analysis.py` | Gap analysis for any chain-walk triple — checks for gamut holes |

## Reproduction

```bash
# Run the census (fine grid, ~2.5 minutes)
docker run -d --name chromatic-census \
    -p 8084:8084 -v /path/to/output:/app/output \
    chromatic-census

# Dashboard-only mode (after census completes)
docker run -d --name chromatic-census \
    -p 8084:8084 -v /path/to/output:/app/output \
    chromatic-census python run.py --dashboard-only

# Gap analysis for a specific triple
docker exec -w /app chromatic-census python analysis/gap_analysis.py \
    --ref 61.0 -9.5 -28.0 \
    --left 60.0 -8.0 -32.5 \
    --right 59.5 -9.5 -32.0
```
