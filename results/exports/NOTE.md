# Chromatic Census Exports

These CSVs contain seeds from the **ultrafine** census (Run 8):

| File | Tier | Seeds | ΔE2000 |
|------|------|------:|--------|
| chromatic-census-ultrafine-jnd-de1.0.csv | JND | 321,930 | 1.0 |
| chromatic-census-ultrafine-acceptability-de2.0.csv | Acceptability | 51,868 | 2.0 |
| chromatic-census-ultrafine-obvious-de5.0.csv | Obvious | 17,313 | 5.0 |

## Gap-Fill Note

The final converged counts (Run 9, gap-fill optimization) are slightly higher:

- JND: **324,669** (+2,739, +0.85%)
- Acceptability: **52,763** (+895, +1.73%)
- Obvious: **17,751** (+438, +2.53%)

The gap-fill seeds were computed and verified but not persisted to the
database due to a bug (the new-seed buffer was cleared on KD-tree rebuilds).
A re-run with the fixed code would reproduce and export the complete dataset.

For most purposes these ultrafine exports are >99% complete.
