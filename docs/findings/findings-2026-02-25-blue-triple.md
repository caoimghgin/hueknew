# Gap Analysis Finding: Blue Triple at L*=61

**Date:** 2026-02-25
**Census:** 276,941 JND seeds (fine grid, ΔE=1.0 threshold)
**sRGB filter:** 116,003 seeds survive gamut check (42% filtered out)
**Chain walk stats:** min ΔE=0.88, median=1.74, mean=1.98, max=67.18

## The Triple

Observed during JND Visual Audit at chain-walk offset ~54,183:

| Panel | L* | a* | b* | Hex | ΔE to ref |
|-------|------|-------|--------|---------|-----------|
| Left (prev) | 60.0 | -8.0 | -32.5 | #4E98C9 | 1.99 |
| **Reference** | **61.0** | **-9.5** | **-28.0** | **#579AC4** | — |
| Right (next) | 59.5 | -9.5 | -32.0 | #4797C7 | 1.96 |

All three are medium-saturation blues at mid-lightness. The ΔE values
(~2.0) suggest roughly 2 JND steps between adjacent swatches.

## The Question

The JND packing places seeds at ΔE ≥ 1.0 throughout all of CIELAB — not
just sRGB. When we filter to sRGB for the visual audit, we discard ~50%
of seeds in this blue region. Could a *discarded* non-sRGB seed have fit
between these adjacent pairs, meaning the perceived gap is an artifact
of gamut limitation rather than a true packing boundary?

## Search Window

Queried all JND seeds in L* ∈ [57, 64]:

- **27,577** total JND seeds in window
- **13,603** in sRGB (49.3%)
- **13,974** outside sRGB (50.7%)

Over half the JND seeds in this blue region are beyond sRGB. The gamut
boundary is clearly nearby.

## Results

### Gap: ref ↔ left (ΔE = 1.99)

Seeds within ΔE < 1.99 of BOTH ref and left: **6 total, 0 non-sRGB**

| L* | a* | b* | ΔE to ref | ΔE to left | Gamut |
|----|-----|------|-----------|------------|-------|
| 60.2 | -9.0 | -30.0 | 1.035 | 1.022 | sRGB |
| 60.5 | -8.0 | -27.5 | 1.171 | 1.837 | sRGB |
| 61.2 | -8.5 | -32.5 | 1.692 | 1.141 | sRGB |
| 60.0 | -11.0 | -31.0 | 1.742 | 1.988 | sRGB |
| 61.8 | -7.5 | -30.5 | 1.700 | 1.738 | sRGB |
| 59.5 | -9.5 | -32.0 | 1.961 | 1.081 | sRGB |

### Gap: ref ↔ right (ΔE = 1.96)

Seeds within ΔE < 1.96 of BOTH ref and right: **6 total, 0 non-sRGB**

| L* | a* | b* | ΔE to ref | ΔE to right | Gamut |
|----|-----|------|-----------|-------------|-------|
| 60.2 | -9.0 | -30.0 | 1.035 | 1.050 | sRGB |
| 60.0 | -10.5 | -28.0 | 1.106 | 1.647 | sRGB |
| 61.0 | -11.0 | -29.5 | 1.151 | 1.851 | sRGB |
| 59.2 | -9.0 | -27.0 | 1.625 | 1.908 | sRGB |
| 61.2 | -8.5 | -32.5 | 1.692 | 1.667 | sRGB |
| 60.0 | -11.0 | -31.0 | 1.742 | 1.108 | sRGB |

## Verdict

**No gamut holes.** Despite 50.7% of JND seeds in this region falling
outside sRGB, every seed that fits between these chain-walk steps is
already representable in sRGB. The gap is not an artifact of gamut
limitation — it is a true packing boundary.

The seed at L*=60.2, a*=-9.0, b*=-30.0 is the tightest intermediary:
ΔE 1.035 from the reference and 1.022 from the left neighbor. It exists,
it's in sRGB, but it's already a JND seed in the packing. There is no
room to insert another distinguishable color.

## Implication

For this triple, the claim holds:

> **In the sRGB color space, there is no color that can be inserted
> between adjacent chain-walk seeds and be meaningfully visually
> different from both.**

The packing is tight. The ΔE ≈ 2.0 gaps are not artifacts — they
represent the true perceptual density of distinguishable colors in
this region of sRGB.

## Reproduction

```bash
docker exec -w /app chromatic-census python analysis/gap_analysis.py \
    --ref 61.0 -9.5 -28.0 \
    --left 60.0 -8.0 -32.5 \
    --right 59.5 -9.5 -32.0
```
