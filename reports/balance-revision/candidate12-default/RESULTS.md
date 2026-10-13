# Ecosystem trials: tune-candidate12-default

60 simulation minutes, or irreversible complete extinction. Counts are observations, not targets. The CSV files retain per-world ranges, extinction times, energy ledgers and checkpoint trait quantiles. Manifest records frozen settings and source hashes.

| Rules / conditions | Seed | Final prey / hunters | Extinction seconds (prey / hunters) | Births (prey / hunters) | Catches | Steps at cap |
|---|---:|---:|---|---:|---:|---:|
| normal-rules2 | 42 | 249 / 10 | none / none | 11407 / 333 | 4407 | 0.20% |
| stress-rules2 | 42 | 144 / 10 | none / none | 10739 / 349 | 4294 | 22.23% |

## Within-world prey diversity

Each entry is speed / sensing / body-size IQR, measured within that one world. Missing means the population was unavailable; nothing is pooled across seeds.

| Rules / conditions | Seed | 30 minutes | 45 minutes | 60 minutes |
|---|---:|---|---|---|
| normal-rules2 | 42 | 14.54 / 24.79 / 3.49 | 20.40 / 23.71 / 3.64 | 13.07 / 16.74 / 3.36 |
| stress-rules2 | 42 | 13.51 / 20.27 / 3.38 | 12.07 / 19.15 / 4.34 | 9.44 / 27.59 / 3.40 |
