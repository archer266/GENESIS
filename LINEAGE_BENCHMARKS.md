# UI refinement and Phase 7: active-world comparison

Measured on 2026-10-10 before either milestone and after both. These are short matched workloads, not a sustained FPS guarantee. The 93-test baseline and all prior benchmark processes had finished before the matched baseline run; no test suite was running during either matched measurement.

## Conditions

- Intel Core i5-13600K, Windows build 26200 (Python reports `Windows-10-10.0.26200-SP0`), Python 3.11.2, Pygame 2.6.1, SDL 2.28.4. Native Windows SDL, software surfaces, display flip included.
- Both runs load the identical genuine v3 checkpoint now retained as `tests/fixtures/phase6_world_v3.json`, then advance ten ticks to tick 4,247: **300 organisms, 36 predators, 420 food**. Seed/map seed 2026; original starting counts 260 prey/40 predators, food regeneration 80/s, mutation 6%, habitats on.
- Effects enabled, normal transparency, Fit World camera, **History panel open** at its initial scroll position. No selected organism. Resolutions 1380x900 and 960x720, speeds 1x and 4x.
- Thirty frozen rendering warmup frames, then **240 active frames per case**, with fixed 1/60-second input. Each case runs 120 ticks / 4 simulation seconds at 1x or 480 ticks / 16 simulation seconds at 4x. No simulation steps are discarded. Timing excludes event pumping, checkpoint load and warmup; rendering includes display flip.
- Core simulation is timed inside `World.step`; update includes history, effects and camera; total is update plus rendering. At 1x, alternate frames execute zero ticks. Reported median uses the **upper middle sample** of the sorted 240 values, and p95 uses index `floor((n-1)*0.95)`. This matters for the 1x core-simulation column; it is not a per-tick mean.
- Total measured wall duration: 13.724 seconds before, 14.048 seconds after (960 active frames each). This is deliberately a brief comparison, not long-duration profiling.

All timing pairs below are **upper median / p95, milliseconds per frame**.

| Resolution | Speed | Build | Core simulation | Full update | Rendering | Total | Wall seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1380x900 | 1x | Before | 3.230 / 3.870 | 3.495 / 4.224 | 10.710 / 14.557 | 12.952 / 18.352 | 3.170 |
| 1380x900 | 1x | After | 3.179 / 3.897 | 3.449 / 4.404 | 10.980 / 16.741 | 13.442 / 20.557 | 3.315 |
| 1380x900 | 4x | Before | 6.638 / 7.329 | 7.260 / 7.969 | 10.364 / 11.654 | 17.593 / 19.271 | 4.246 |
| 1380x900 | 4x | After | 6.619 / 7.165 | 7.224 / 7.907 | 10.400 / 11.801 | 17.563 / 19.683 | 4.240 |
| 960x720 | 1x | Before | 3.208 / 3.734 | 3.472 / 4.145 | 8.047 / 11.963 | 11.072 / 15.609 | 2.553 |
| 960x720 | 1x | After | 3.172 / 3.713 | 3.445 / 4.139 | 8.112 / 13.420 | 11.100 / 17.172 | 2.626 |
| 960x720 | 4x | Before | 6.581 / 7.132 | 7.194 / 7.818 | 8.375 / 9.651 | 15.629 / 17.283 | 3.755 |
| 960x720 | 4x | After | 6.748 / 7.708 | 7.409 / 8.412 | 8.636 / 10.150 | 16.082 / 18.018 | 3.867 |

## Observations and limitations

At 1x the population ranged **288-300**, ending at 290; at 4x it ranged **250-300**, ending at 300. The world evolves during timing; it is not artificially held at capacity. These ranges and every physical-state, simulation-RNG and retained-history hash match before/after and across resolutions. The compared document excludes the newly added observational archive and version metadata.

The 1380x900 4x total median was effectively unchanged, while its p95 rose from 19.271 to 19.683 ms. At 960x720 4x, median rose from 15.629 to 16.082 ms. Rendering tails at 1x were higher after the changes. Both runs include ordinary system/scheduling noise and only one short pass per case; no statistical significance, general performance improvement or sustained 60 FPS is claimed. In particular, 4x at 1380x900 remains above the 16.67 ms frame budget.

This measures an open History panel for a directly comparable workload. It does not measure full-archive ancestry browsing, maximum zoom, long-duration stability, all appearance combinations, full-screen resolution, or other hardware. The archive starts as a legacy snapshot and grows from actual births during playback; this is not a 4,096-record stress benchmark. Rendering caches, history and lineage storage remain bounded. The refinement uses a bounded local frost cache, not per-frame fullscreen blur.

Baseline physical hashes and after hashes:

- 1x: `57246105d410f172dac24822d420c92373221f70e5e41cc39c3c1d7a8526f7d5`
- 4x: `7b408d15e52e1c6c662611f7ef7b59598a847b06a2dcaac37eeaf1527152c8f2`

Raw results: `artifacts/lineage-performance-before.json` and `artifacts/lineage-performance-after.json`. Screenshots: `artifacts/refined-*.png` (milestone one, captured before lineage work) and `artifacts/lineage-*.png`; existing relocated-feature checks also regenerated `artifacts/glass-*.png`.

## Validation and reproduction

93 tests passed before implementation; **107 tests passed in 61.683 seconds** afterward. Native scripted checks exercised the refined switches and lineage controls at both sizes, plus existing panel, fullscreen, picker and confirmation behavior. Screenshots were visually reviewed; this was not manual mouse testing. UI actions were checked against unchanged seeded world documents, and lineage-enabled versus disabled observers were compared through actual births and catches. Existing v1/v2 migration, new v3 fixture migration, v4 continuation and speed-equivalence tests passed.

Run the current workload (the `local` label does not overwrite captured before/after results):

```powershell
Set-Location "C:\Users\Admin\Desktop\Coding Projects\Genesis"
.\.venv\Scripts\python.exe tools\benchmark_lineage.py --label local
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\check_lineage_ui.py
```
