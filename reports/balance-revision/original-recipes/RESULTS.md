# Ecosystem trials: diagnose-initial

60 simulation minutes, or irreversible complete extinction. Counts are observations, not targets. The CSV files retain per-world ranges, extinction times, energy ledgers and checkpoint trait quantiles. These initial diagnostic runs preceded manifest capture; no source-hash record is claimed.

| Rules / conditions | Seed | Final prey / hunters | Extinction seconds (prey / hunters) | Births (prey / hunters) | Catches | Steps at cap |
|---|---:|---:|---|---:|---:|---:|
| original-coexistence | 101 | 300 / 0 | none / 3273.23 | 10638 / 913 | 7699 | 45.06% |
| original-default | 42 | 234 / 0 | none / 0.00 | 5742 / 0 | 0 | 1.12% |
| original-environment | 42 | 0 / 0 | 220.77 / 243.77 | 616 / 121 | 694 | 0.00% |

## Within-world prey diversity

Each entry is speed / sensing / body-size IQR, measured within that one world. Missing means the population was unavailable; nothing is pooled across seeds.

| Rules / conditions | Seed | 30 minutes | 45 minutes | 60 minutes |
|---|---:|---|---|---|
| original-coexistence | 101 | 1.23 / 0.76 / 0.05 | 0.39 / 3.45 / 0.05 | 0.59 / 3.37 / 0.05 |
| original-default | 42 | 6.90 / 10.91 / 0.81 | 5.94 / 15.52 / 0.49 | 5.31 / 12.74 / 0.38 |
| original-environment | 42 | missing / missing / missing | missing / missing / missing | missing / missing / missing |
