# Ecosystem trials: tune-candidate13-default

60 simulation minutes, or irreversible complete extinction. Counts are observations, not targets. The CSV files retain per-world ranges, extinction times, energy ledgers and checkpoint trait quantiles. Manifest records frozen settings and source hashes.

| Rules / conditions | Seed | Final prey / hunters | Extinction seconds (prey / hunters) | Births (prey / hunters) | Catches | Steps at cap |
|---|---:|---:|---|---:|---:|---:|
| normal-rules2 | 42 | 185 / 16 | none / none | 11985 / 455 | 5865 | 0.06% |
| stress-rules2 | 42 | 245 / 0 | none / 1144.97 | 8681 / 92 | 1200 | 37.52% |

## Within-world prey diversity

Each entry is speed / sensing / body-size IQR, measured within that one world. Missing means the population was unavailable; nothing is pooled across seeds.

| Rules / conditions | Seed | 30 minutes | 45 minutes | 60 minutes |
|---|---:|---|---|---|
| normal-rules2 | 42 | 13.54 / 22.41 / 3.74 | 16.25 / 19.08 / 3.23 | 21.24 / 22.12 / 3.30 |
| stress-rules2 | 42 | 11.47 / 22.22 / 3.50 | 13.38 / 28.57 / 3.09 | 10.43 / 24.65 / 3.34 |
