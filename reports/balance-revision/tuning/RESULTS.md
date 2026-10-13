# Ecosystem trials: tune-candidate11-hour

60 simulation minutes, or irreversible complete extinction. Counts are observations, not targets. The CSV files retain per-world ranges, extinction times, energy ledgers and checkpoint trait quantiles. Manifest records frozen settings and source hashes.

| Rules / conditions | Seed | Final prey / hunters | Extinction seconds (prey / hunters) | Births (prey / hunters) | Catches | Steps at cap |
|---|---:|---:|---|---:|---:|---:|
| normal-rules2 | 211 | 237 / 21 | none / none | 12884 / 379 | 5167 | 2.81% |
| normal-rules2 | 223 | 259 / 15 | none / none | 12189 / 334 | 4584 | 1.28% |
| normal-rules2 | 227 | 225 / 16 | none / none | 12158 / 386 | 5237 | 1.51% |
| stress-rules2 | 211 | 150 / 11 | none / none | 10834 / 244 | 3384 | 32.04% |
| stress-rules2 | 223 | 136 / 16 | none / none | 10744 / 300 | 4067 | 30.54% |
| stress-rules2 | 227 | 145 / 8 | none / none | 10476 / 254 | 3504 | 31.56% |

## Within-world prey diversity

Each entry is speed / sensing / body-size IQR, measured within that one world. Missing means the population was unavailable; nothing is pooled across seeds.

| Rules / conditions | Seed | 30 minutes | 45 minutes | 60 minutes |
|---|---:|---|---|---|
| normal-rules2 | 211 | 9.13 / 15.09 / 3.57 | 12.34 / 15.13 / 3.75 | 13.47 / 18.92 / 3.61 |
| normal-rules2 | 223 | 21.61 / 25.28 / 3.44 | 13.11 / 17.26 / 2.79 | 19.25 / 18.22 / 3.50 |
| normal-rules2 | 227 | 13.89 / 18.68 / 2.99 | 14.98 / 23.53 / 3.55 | 16.40 / 24.08 / 3.49 |
| stress-rules2 | 211 | 17.13 / 19.21 / 3.53 | 19.52 / 15.69 / 2.65 | 12.23 / 19.10 / 3.06 |
| stress-rules2 | 223 | 16.55 / 17.65 / 3.06 | 17.43 / 19.60 / 3.58 | 19.57 / 21.20 / 4.40 |
| stress-rules2 | 227 | 15.02 / 14.64 / 4.09 | 12.69 / 15.40 / 3.16 | 10.78 / 19.05 / 3.19 |
