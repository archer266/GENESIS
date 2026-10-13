# Ecosystem trials: tune-candidate12-hour

60 simulation minutes, or irreversible complete extinction. Counts are observations, not targets. The CSV files retain per-world ranges, extinction times, energy ledgers and checkpoint trait quantiles. Manifest records frozen settings and source hashes.

| Rules / conditions | Seed | Final prey / hunters | Extinction seconds (prey / hunters) | Births (prey / hunters) | Catches | Steps at cap |
|---|---:|---:|---|---:|---:|---:|
| normal-rules2 | 211 | 204 / 9 | none / none | 12666 / 412 | 5826 | 2.21% |
| normal-rules2 | 223 | 216 / 14 | none / none | 11665 / 320 | 4604 | 0.72% |
| normal-rules2 | 227 | 217 / 17 | none / none | 11832 / 339 | 4691 | 0.69% |
| stress-rules2 | 211 | 134 / 7 | none / none | 11006 / 314 | 4065 | 19.68% |
| stress-rules2 | 223 | 141 / 11 | none / none | 10791 / 316 | 4087 | 22.01% |
| stress-rules2 | 227 | 90 / 8 | none / none | 10263 / 288 | 3640 | 26.72% |

## Within-world prey diversity

Each entry is speed / sensing / body-size IQR, measured within that one world. Missing means the population was unavailable; nothing is pooled across seeds.

| Rules / conditions | Seed | 30 minutes | 45 minutes | 60 minutes |
|---|---:|---|---|---|
| normal-rules2 | 211 | 20.10 / 21.18 / 3.67 | 13.56 / 17.82 / 3.72 | 16.43 / 24.41 / 3.11 |
| normal-rules2 | 223 | 19.91 / 20.28 / 3.55 | 10.72 / 22.94 / 3.29 | 22.50 / 20.11 / 3.97 |
| normal-rules2 | 227 | 19.11 / 16.85 / 3.57 | 18.41 / 13.67 / 3.59 | 16.64 / 23.58 / 3.20 |
| stress-rules2 | 211 | 11.90 / 16.11 / 3.20 | 9.09 / 22.62 / 3.67 | 12.96 / 20.45 / 3.55 |
| stress-rules2 | 223 | 12.37 / 18.35 / 2.58 | 17.96 / 23.45 / 3.62 | 13.56 / 16.52 / 3.72 |
| stress-rules2 | 227 | 17.39 / 17.53 / 2.73 | 17.19 / 23.54 / 3.59 | 13.41 / 18.88 / 3.32 |
