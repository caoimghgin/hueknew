# Gap Analysis Finding: Brown/Orange Triple at L*=49.25

**Date:** 2026-02-25
**Census:** 276,941 JND seeds (fine grid, ΔE=1.0 threshold)
**sRGB filter:** 116,003 seeds survive gamut check (42% filtered out)
**Chain walk:** Pure ΔE ordering, no L* bias
**Chain walk stats:** min ΔE=0.88, median=1.74, mean=1.98, max=67.18

## The Triple

Observed at chain-walk offset ~58,274:

| Panel | L* | a* | b* | Hex | ΔE to ref |
|-------|------|-------|--------|---------|-----------|
| Left (prev) | 51.25 | 25.00 | 49.50 | #B36822 | 2.89 |
| **Reference** | **49.25** | **21.00** | **44.50** | **#A76627** | — |
| Right (next) | 48.50 | 22.50 | 47.50 | #A7631F | 1.26 |

The left gap (ΔE=2.89) is conspicuously large — nearly 3 JND steps.
Visually, one might expect a distinguishable brown to fit between them.

## The Question

Is this gap caused by the sRGB gamut boundary filtering out intermediate
seeds, or is there another explanation?

## Search Window

Queried all JND seeds in L* ∈ [45, 55]:

- **40,766** total JND seeds in window
- **21,255** in sRGB (52.1%)
- **19,511** outside sRGB (47.9%)

## Results

### Left Gap: ref ↔ prev (ΔE = 2.89)

Seeds within ΔE < 2.89 of BOTH ref and left: **18 total, 18 sRGB, 0 non-sRGB**

No gamut holes. All 18 intermediate seeds are representable in sRGB.

Notable intermediaries:

| L* | a* | b* | Hex | ΔE to ref | ΔE to left |
|----|-----|------|---------|-----------|------------|
| 49.50 | 23.00 | 46.50 | #AB6524 | 1.067 | 2.061 |
| 49.50 | 22.00 | 49.50 | #AA651C | 1.712 | 2.549 |
| 50.25 | 25.00 | 50.50 | #B0651C | 2.435 | 1.072 |
| 50.50 | 22.50 | 47.50 | #AD6824 | 1.614 | 1.455 |

Seed #AB6524 (L*=49.50, a=23.00, b=46.50) is only ΔE 1.067 from the
reference — well within 1 JND. It clearly "fits between" the pair.

### Right Gap: ref ↔ next (ΔE = 1.26)

Seeds between: **1 total, 1 sRGB, 0 non-sRGB**

Genuinely tight packing. Almost no room for anything.

## Verdict: Chain-Walk Artifact

**The ΔE 2.89 gap is NOT a gamut hole — it is a chain-walk ordering
artifact.**

The greedy chain walk places 9 seeds per step. By the time it reached
#A76627 at offset ~58,274, many of the intermediate browns between it
and #B36822 had already been consumed at earlier positions in the walk.
The walk had passed through this warm-brown neighborhood before and
claimed those seeds on a prior visit.

This is an inherent property of greedy nearest-neighbor traversals:
the walk can revisit neighborhoods it partially consumed earlier,
creating adjacencies with larger ΔE than the local packing density
would suggest.

## Key Insight for Article

The ΔE between adjacent chain-walk steps is not always the packing
density — it is the **remaining density** after earlier steps have
claimed nearby seeds. Large ΔE gaps in the walk indicate revisited
neighborhoods, not sparse packing or gamut holes.

To verify: the intermediate seeds exist, they are in sRGB, and they
appear earlier (or later) in the chain walk. A "jump to claimed
position" feature in the audit tool can demonstrate this directly.

## Reproduction

```bash
docker exec -w /app chromatic-census python analysis/gap_analysis.py \
    --ref 49.25 21.0 44.5 \
    --left 51.25 25.0 49.5 \
    --right 48.5 22.5 47.5
```
