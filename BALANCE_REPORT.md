# Phase 9: Ecosystem balance and diagnostics

Coexistence retained both species at 30 simulated minutes in **4/10 held-out runs**, compared with **0/10** for the unchanged Changing Seasons recipe. **Coexistence remains unreliable across seeds.** This is finite-horizon coexistence, not proof of a stable equilibrium or permanent survival. The original Balanced default remains prey-only and unchanged.

## Investigation before balance selection

The six recorded Phase 8 trials were rerun at their original seeds (42, 7, 2026), settings and 600-second horizon, or full extinction. End times, populations, total births, deaths and catches matched exactly. Every predator death was energy depletion; none reached maximum age. Seed 42 at food 20 exhausted its prey at 220.767 seconds and predators at 243.767 seconds. At food 2, sparse feeding and low prey energy were consistent with the early predator losses. At food 20, surviving prey became faster while predators approached the speed ceiling; this raises pursuit difficulty and metabolic expense. These observations do not isolate the effect of each trait or setting.

Code review and focused regression checks found no demonstrated defect in hunting/fleeing, start-of-tick perception, physical contact ordering, one-time catches, offspring transfers, or environmental food calculations. Contact remains the established discrete endpoint rule. Food regeneration remains base rate times the seasonal/drought product times habitat weighting, with fractional credit and a food cap. No survival rule was changed.

Predators continue paying 2.5 times the trait-based metabolic rate and receiving 65% of caught prey's remaining energy, limited by capacity. Catches occur even near capacity, so surplus energy is lost. A child receives 65 energy from its parent, plus the parent pays 6 extra; transfers are not new species-level energy. New diagnostics confirmed substantial overflow, births and eventual starvation. The shared population cap also blocks eligible reproduction attempts; this is existing behavior, not a hidden balance adjustment.

| Seed | Base food/s | Predator births | Predator energy/age deaths | Catches / observed predator | Accepted feeding energy | Metabolic energy spent | Reproduction cost | Feeding overflow |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 7 | 20 | 145 | 153 / 0 | 5.98 | 37130.5 | 36962.2 | 870.0 | 13788.2 |
| 42 | 20 | 121 | 129 / 0 | 5.38 | 28432.8 | 28403.1 | 726.0 | 12491.9 |
| 2026 | 20 | 155 | 163 / 0 | 6.57 | 41119.6 | 40892.1 | 930.0 | 19813.3 |
| 7 | 2 | 15 | 23 / 0 | 4.83 | 4284.6 | 4878.1 | 90.0 | 706.4 |
| 42 | 2 | 19 | 27 / 0 | 5.19 | 5554.9 | 6123.7 | 114.0 | 869.5 |
| 2026 | 2 | 16 | 24 / 0 | 4.88 | 4908.3 | 5496.1 | 96.0 | 1006.8 |

The denominator for catches/observed predator is initial predators plus subsequent predator births, including living individuals; it is not a per-second hunting rate. Full species ledgers, minute samples, traits and individual living-predator catch counts are in `artifacts/balance-reproduce.json`. Dead-predator catch counts are aggregated, not retained as an unlimited individual archive.

| Seed | Base food/s | Prey births | Prey energy / age / caught deaths | Accepted food energy | Metabolic energy spent |
| --- | --- | --- | --- | --- | --- |
| 7 | 20 | 1699 | 562 / 143 / 915 | 362849.3 | 261336.6 |
| 42 | 20 | 616 | 22 / 0 / 694 | 104215.9 | 46059.6 |
| 2026 | 20 | 1777 | 459 / 141 / 1071 | 372210.8 | 255186.4 |
| 7 | 2 | 202 | 126 / 46 / 111 | 47785.9 | 43640.2 |
| 42 | 2 | 206 | 96 / 48 / 140 | 47269.6 | 39923.3 |
| 2026 | 2 | 214 | 119 / 52 / 117 | 49311.9 | 42285.3 |

## Tuning and frozen candidate

Only tuning seeds **101, 103, 107** were used to choose settings. Five recipes were run for 1,800 seconds each. All had habitats, predators, seasons and droughts enabled; map seed equaled world seed; cycle length was 300 seconds, drought duration 5 seconds and gaps 300-600 seconds. No new parameters were needed.

| Recipe | Initial prey/predators | Food/s | Mutation | Both species at 30 min | Mean time at combined cap |
| --- | --- | --- | --- | --- | --- |
| gentle | 160 / 8 | 40 | 2% | 0/3 | 88.81% |
| stable_traits | 160 / 8 | 40 | 0% | 0/3 | 98.20% |
| rich | 200 / 8 | 60 | 1% | 0/3 | 98.30% |
| moderate_zero | 160 / 4 | 20 | 0% | 1/3 | 35.95% |
| moderate_low | 160 / 4 | 24 | 0.5% | 3/3 | 45.97% |

More food alone was ineffective: the richer recipes lost all predators and spent much of each run at the cap. The moderate-food, low-mutation recipe was the only one retaining both species on all three tuning seeds. It became **Coexistence**, frozen before candidate evaluation: **160 prey, 4 predators, 24 food/s, +/-0.5% mutation**, habitats, 300-second seasons and 5-second droughts with 300-600-second gaps. After evaluation, the shipped preset uses visible world/map seed **101**, an existing tuning example, rather than claiming that arbitrary seeds reliably coexist. The frozen parameter recipe was not retuned; evaluation always overrides world/map seeds with 1001-1010. The frozen recipe is recorded in `artifacts/coexistence-frozen-recipe.json`; the later, explicit reference-seed choice is in `artifacts/coexistence-reference.json`. No rules, costs, trait bounds or original defaults changed; no advanced tuning controls were added.

## Held-out evaluation

All three configurations used the same previously untuned seeds **1001-1010**, with map seed equal to world seed. Each run was scheduled for **1,800 simulation seconds (54,000 fixed ticks)**, stopping only on complete ecosystem extinction as the app does. Balanced is the literal default (predators, habitats and events off). Changing Seasons is the Phase 8 environmental baseline (100/8 organisms, food 20, mutation 6%, cycle 120s, drought 15s, gaps 90-180s). Coexistence is the frozen recipe above. All 30 evaluation runs reached the full 1,800-second endpoint. Changing Seasons completed 15 seasonal cycles and Coexistence completed six, with several droughts in each enabled run. Seeded randomness remained the sole behavioral randomness; nothing respawned, held populations constant or adjusted difficulty.

Ranges include initial populations and every post-step population. Cap percentage is the proportion of actual simulated ticks with total population exactly 300, not the proportion of minute samples. Predator cap is still 40. “Absent” means predators were not introduced, not that they became extinct. Extinction times are simulation seconds. A dash means no extinction before the endpoint.

### Balanced (unchanged literal default)

| Seed | End seconds | Final prey/predators | Prey range | Predator range | Prey extinction | Predator extinction | At combined cap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1001 | 1800.00 | 246 / 0 | 100-300 | 0-0 | - | Absent | 6.44% |
| 1002 | 1800.00 | 211 / 0 | 100-300 | 0-0 | - | Absent | 1.38% |
| 1003 | 1800.00 | 230 / 0 | 100-300 | 0-0 | - | Absent | 6.16% |
| 1004 | 1800.00 | 240 / 0 | 100-300 | 0-0 | - | Absent | 2.76% |
| 1005 | 1800.00 | 222 / 0 | 100-300 | 0-0 | - | Absent | 4.22% |
| 1006 | 1800.00 | 236 / 0 | 100-300 | 0-0 | - | Absent | 6.17% |
| 1007 | 1800.00 | 222 / 0 | 100-300 | 0-0 | - | Absent | 5.90% |
| 1008 | 1800.00 | 236 / 0 | 100-300 | 0-0 | - | Absent | 6.78% |
| 1009 | 1800.00 | 204 / 0 | 100-300 | 0-0 | - | Absent | 3.97% |
| 1010 | 1800.00 | 248 / 0 | 100-300 | 0-0 | - | Absent | 4.45% |

10/10 runs reached the combined cap; mean fraction of time there: 4.82%. 

### Changing Seasons (unchanged environmental baseline)

| Seed | End seconds | Final prey/predators | Prey range | Predator range | Prey extinction | Predator extinction | At combined cap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1001 | 1800.00 | 141 / 0 | 61-300 | 0-26 | - | 463.93 | 10.52% |
| 1002 | 1800.00 | 215 / 0 | 67-300 | 0-29 | - | 585.20 | 23.61% |
| 1003 | 1800.00 | 223 / 0 | 78-300 | 0-21 | - | 535.73 | 22.50% |
| 1004 | 1800.00 | 185 / 0 | 49-300 | 0-28 | - | 366.63 | 16.94% |
| 1005 | 1800.00 | 217 / 0 | 39-300 | 0-31 | - | 627.90 | 29.24% |
| 1006 | 1800.00 | 216 / 0 | 27-300 | 0-29 | - | 579.23 | 19.03% |
| 1007 | 1800.00 | 190 / 0 | 79-300 | 0-18 | - | 383.17 | 21.19% |
| 1008 | 1800.00 | 207 / 0 | 63-300 | 0-22 | - | 453.13 | 24.70% |
| 1009 | 1800.00 | 168 / 0 | 44-300 | 0-22 | - | 235.70 | 16.21% |
| 1010 | 1800.00 | 217 / 0 | 18-300 | 0-31 | - | 139.47 | 28.86% |

10/10 runs reached the combined cap; mean fraction of time there: 21.28%. Observed droughts per run: 11-13. 

### Coexistence (held-out evaluation)

| Seed | End seconds | Final prey/predators | Prey range | Predator range | Prey extinction | Predator extinction | At combined cap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1001 | 1800.00 | 218 / 2 | 88-298 | 1-26 | - | - | 45.63% |
| 1002 | 1800.00 | 201 / 4 | 131-297 | 1-29 | - | - | 55.56% |
| 1003 | 1800.00 | 116 / 10 | 76-297 | 2-35 | - | - | 38.24% |
| 1004 | 1800.00 | 201 / 8 | 58-297 | 2-40 | - | - | 43.19% |
| 1005 | 1800.00 | 269 / 0 | 148-300 | 0-9 | - | 238.87 | 64.52% |
| 1006 | 1800.00 | 279 / 0 | 149-300 | 0-13 | - | 790.23 | 64.10% |
| 1007 | 1800.00 | 274 / 0 | 149-300 | 0-11 | - | 494.07 | 65.82% |
| 1008 | 1800.00 | 263 / 0 | 67-300 | 0-25 | - | 753.23 | 63.38% |
| 1009 | 1800.00 | 259 / 0 | 125-300 | 0-14 | - | 544.90 | 54.92% |
| 1010 | 1800.00 | 269 / 0 | 86-300 | 0-24 | - | 1222.33 | 45.33% |

10/10 runs reached the combined cap; mean fraction of time there: 54.07%. Observed droughts per run: 3-4. 

A separate rerun of the shipped reference seed **101** ended at 1800.00s with **69 prey / 17 predators**; extinction times: none before the endpoint. The earlier post-freeze seed-42 check lost predators at 220.1 seconds and ended with 246 prey; it remains recorded in `artifacts/balance-reference42.json`. Reference 101 was chosen from the tuning set, never from held-out evaluation successes. This curated example does not improve the 4/10 held-out result.

Full results and minute diagnostics are in `artifacts/balance-baseline.json`, `balance-evaluate.json`, `balance-preset.json`, `balance-tune.json` and `balance-moderate.json`. These are small finite seed sets, not statistical guarantees. Reduced mutation deliberately slows inherited change; the observations cannot establish long-term stability, adaptation or the isolated causal contribution of each changed setting. Population caps materially affect reproduction.

## Diagnostics, persistence and checks

**Observatory > Diagnostics** shows species-level births, death causes, catches, current average energy, energy flows, eligible cap-blocked attempts, lifetime totals and recent per-second rates. It does not add default-world chrome. Recent rates span up to 60 simulation seconds and report the actual interval. The ledger keeps 61 tick-sampled rows plus fixed-size species totals; individual catch counters exist only for living predators (at most 40), with dead counts aggregated. **Worlds > Export diagnostics as CSV** writes these cumulative snapshots plus the current row and experiment settings, including the seed. Existing statistics and lineage exports remain available.

Version **6** is necessary to retain these otherwise unreconstructable ledgers and recent history. Valid **v1-v5** files still load. Legacy diagnostics begin at the load tick with explicit partial-history labeling; no earlier deaths, energy or individual catches are invented. Version 5 environment state and earlier lineage/habitat migrations remain intact. Validation checks schemas, finite bounds, species/world counters, energy balance, offspring transfers, predator IDs/catches, sample phase/capacity and current state before replacement. Saves remain atomic and loads paused. The signed energy removed at death includes the existing final-tick depletion overshoot, allowing conservation checks without changing costs.

Baseline: **122 tests passed in 77.933 seconds**. Final: **136 tests passed in 93.919 seconds** (the final suite shared CPU with headless trials; this duration is not a performance benchmark). Added checks cover accounting, caps, RNG/physical equivalence against frozen Phase 8 code, fixed-speed equivalence, exact save continuation, all old versions, old Custom saves matching the newly named preset, malformed diagnostics, CSV and UI isolation. Existing atomic-write failures, environmental calculations, catch ordering, energy conservation, habitats, camera, lineage and visual tests pass.

Native scripted glass, environment, lineage and diagnostic UI checks passed at **1380x900 and 960x720**, including file pickers, replacement confirmations, fullscreen/hidden-control restoration, scroll/keyboard access, exports, and Coexistence draft/cancel/confirm. Screenshots of normal/minimum layouts were reviewed. These were automated desktop interactions and screenshot inspection, not manual pointer testing.

## Matched short performance measurements

Hardware/environment: 13th Gen Intel(R) Core(TM) i5-13600K; Windows-10-10.0.26200-SP0; Python 3.11.2; Pygame 2.6.1; SDL 2.28.4. Native Windows software rendering, display flip included.

Before/after used the identical naturally evolved environment-enabled checkpoint, loaded and advanced ten ticks to 2651. The start contained 273 prey, 27 predators and 404 food. Population remained 300 throughout, predators/habitats/events/effects enabled, normal glass, History panel open and fitted camera. Each case used 30 frozen warmup draws, then 240 active frames at 1/60-second input, processing exactly 120 ticks at 1x or 480 at 4x. These are 4 or 16 simulation seconds, not sustained gameplay measurements. No ticks were dropped. Final measurements ran after headless trial workers stopped. Event pumping/setup are excluded. Simulation, full update, rendering and total are measured separately; total is update plus render. Median is the upper middle sample; p95 uses floor((N-1)*0.95). Core simulation times are per rendered frame, including zero-step frames at 1x, not per-tick averages.

| Build | Resolution | Speed | Core simulation median/p95 ms | Render median/p95 ms | Total median/p95 ms | Wall seconds |
| --- | --- | --- | --- | --- | --- | --- |
| Before | 1380x900 | 1x | 3.454 / 3.899 | 9.713 / 14.213 | 12.712 / 18.136 | 2.987 |
| Before | 1380x900 | 4x | 6.866 / 7.376 | 10.108 / 11.358 | 17.507 / 19.407 | 4.275 |
| Before | 960x720 | 1x | 3.406 / 3.953 | 7.833 / 12.380 | 10.989 / 16.481 | 2.563 |
| Before | 960x720 | 4x | 7.114 / 7.664 | 8.769 / 11.996 | 16.557 / 19.286 | 4.024 |
| After | 1380x900 | 1x | 3.502 / 4.026 | 9.670 / 14.163 | 12.451 / 18.304 | 2.975 |
| After | 1380x900 | 4x | 7.168 / 8.096 | 10.119 / 11.713 | 17.888 / 20.181 | 4.375 |
| After | 960x720 | 1x | 3.507 / 4.092 | 7.650 / 11.855 | 11.043 / 15.904 | 2.484 |
| After | 960x720 | 4x | 7.234 / 7.831 | 8.364 / 9.398 | 16.210 / 17.831 | 3.925 |

Physical world/RNG, habitat, settings and retained-statistics hashes match in every before/after case. New diagnostic records are intentionally outside that historical fingerprint; their exact continuation is tested separately. Raw files are `artifacts/lineage-performance-phase9-before.json` and `...phase9-after.json`. Small timing differences include scheduling noise. This is not a claim of sustained 60 FPS, fullscreen performance, effects-off performance or long-duration rendering stability. No simulation optimization was introduced; diagnostics add observational work.

## Reproduce and launch (PowerShell)

```powershell
Set-Location "C:\Users\Admin\Desktop\Coding Projects\Genesis"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\check_balance.py --stage reproduce
.\.venv\Scripts\python.exe tools\check_balance.py --stage tune
.\.venv\Scripts\python.exe tools\check_balance.py --stage moderate
.\.venv\Scripts\python.exe tools\check_balance.py --stage baseline
.\.venv\Scripts\python.exe tools\check_balance.py --stage evaluate
.\.venv\Scripts\python.exe tools\check_balance.py --stage preset --workers 1
.\.venv\Scripts\python.exe tools\check_diagnostics_ui.py
.\.venv\Scripts\python.exe tools\benchmark_lineage.py --label local-balance --environment
.\.venv\Scripts\python.exe -m genesis
```

Choose **Settings > Experiment > Coexistence**, inspect the draft, then **Start new experiment** and confirm. Defaults remain unchanged. Headless trials can use `--workers 1` to reduce CPU load; do not run them alongside a rendering benchmark. Dependencies and fresh-install commands are in README.md. No neural networks, new species, terrain editing, forced cycles, respawning or adaptive difficulty were added.
