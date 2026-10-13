# Ecosystem trials: tune-candidate11-default

60 simulation minutes, or irreversible complete extinction. Counts are observations, not targets. The CSV files retain per-world ranges, extinction times, energy ledgers and checkpoint trait quantiles. Manifest records frozen settings and source hashes.

| Rules / conditions | Seed | Final prey / hunters | Extinction seconds (prey / hunters) | Births (prey / hunters) | Catches | Steps at cap |
|---|---:|---:|---|---:|---:|---:|
| normal-rules2 | 42 | 194 / 21 | none / none | 12038 / 328 | 4535 | 1.89% |
| stress-rules2 | 42 | 102 / 14 | none / none | 10716 / 341 | 4184 | 22.68% |

## Within-world prey diversity

Each entry is speed / sensing / body-size IQR, measured within that one world. Missing means the population was unavailable; nothing is pooled across seeds.

| Rules / conditions | Seed | 30 minutes | 45 minutes | 60 minutes |
|---|---:|---|---|---|
| normal-rules2 | 42 | 13.71 / 13.06 / 3.45 | 12.12 / 17.41 / 3.73 | 17.34 / 17.29 / 3.57 |
| stress-rules2 | 42 | 9.50 / 15.46 / 4.17 | 13.60 / 13.87 / 3.83 | 20.57 / 22.53 / 3.94 |
