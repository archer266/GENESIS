# Ecosystem trials: tune-candidate13-hour

60 simulation minutes, or irreversible complete extinction. Counts are observations, not targets. The CSV files retain per-world ranges, extinction times, energy ledgers and checkpoint trait quantiles. Manifest records frozen settings and source hashes.

| Rules / conditions | Seed | Final prey / hunters | Extinction seconds (prey / hunters) | Births (prey / hunters) | Catches | Steps at cap |
|---|---:|---:|---|---:|---:|---:|
| normal-rules2 | 211 | 243 / 14 | none / none | 12427 / 405 | 5680 | 1.91% |
| normal-rules2 | 223 | 197 / 21 | none / none | 11828 / 401 | 5344 | 1.21% |
| normal-rules2 | 227 | 204 / 19 | none / none | 11740 / 382 | 5221 | 0.00% |
| stress-rules2 | 211 | 117 / 11 | none / none | 10581 / 311 | 3993 | 24.26% |
| stress-rules2 | 223 | 136 / 15 | none / none | 10546 / 309 | 3886 | 27.71% |
| stress-rules2 | 227 | 74 / 15 | none / none | 10651 / 351 | 4400 | 15.62% |

## Within-world prey diversity

Each entry is speed / sensing / body-size IQR, measured within that one world. Missing means the population was unavailable; nothing is pooled across seeds.

| Rules / conditions | Seed | 30 minutes | 45 minutes | 60 minutes |
|---|---:|---|---|---|
| normal-rules2 | 211 | 19.72 / 18.61 / 3.59 | 14.69 / 23.96 / 3.44 | 18.36 / 19.92 / 3.64 |
| normal-rules2 | 223 | 16.39 / 24.94 / 3.54 | 23.12 / 19.83 / 3.51 | 16.71 / 21.52 / 3.51 |
| normal-rules2 | 227 | 15.47 / 20.11 / 2.98 | 19.16 / 23.74 / 3.39 | 19.90 / 18.64 / 3.18 |
| stress-rules2 | 211 | 15.75 / 24.19 / 2.93 | 20.14 / 21.96 / 3.61 | 19.63 / 23.80 / 3.27 |
| stress-rules2 | 223 | 21.48 / 22.02 / 3.48 | 15.78 / 22.90 / 2.87 | 9.20 / 18.36 / 4.14 |
| stress-rules2 | 227 | 17.45 / 22.45 / 3.24 | 18.21 / 22.96 / 3.95 | 12.05 / 20.02 / 4.06 |
