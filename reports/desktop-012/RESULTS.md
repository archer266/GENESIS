# GENESIS 0.12.0 release validation

184 tests passed in 144.596 seconds during the release build. Focused UI/CLI checks: 25 passed. Native scripted packaged checks passed; no manual visual inspection was performed in this final validation pass. Earlier candidate screenshots were reviewed separately.

The ZIP was extracted outside the project to a temporary directory containing spaces and ?. Python/venv search paths were removed for the packaged process. Ordinary argument-free startup/close, 1380?900 and 960?720 controls, fullscreen restoration, hidden-UI restoration, preferences across relaunches, Unicode save/load, three CSV exports, error handling, old-world rejection and corrected save continuation through future births/catches all passed. This was the development machine, not an isolated machine.

## Matched short benchmarks

Intel Core i5-13600K; Windows build 26200; Python 3.11.2; Pygame 2.6.1 / SDL 2.28.4. Three alternating packaged/source repetitions. Seed/map 1931; predator/habitat/environment enabled; effects on; History panel open; 1380?900. Each case: 30 warmup draws then 360 active frames with fixed 1/60 s input. Population 280?292 at 1? and 280?300 at 4?. Exactly 180/720 simulation ticks; none discarded. Each case lasted approximately 4.1?6.6 wall seconds. Rendering includes display flip, excludes event pumping. These are short workloads, not sustained FPS measurements.

| Build / speed | Simulation median range ms | Render median range ms | Total median range ms | Total p95 range ms |
|---|---:|---:|---:|---:|
| source / 1? | 3.221?3.236 | 9.350?9.371 | 12.414?12.627 | 16.760?17.098 |
| source / 4? | 7.381?7.496 | 10.041?10.057 | 18.086?18.121 | 19.618?19.801 |
| packaged / 1? | 3.212?3.263 | 8.850?8.928 | 12.097?12.190 | 16.346?16.639 |
| packaged / 4? | 7.375?7.461 | 9.576?9.817 | 17.471?17.863 | 18.945?19.930 |

Every source/packaged repetition produced the same authoritative state hash for its speed. 4? total frame time exceeds the 16.67 ms budget near the cap; sustained 60 FPS is not claimed. Effects-off performance was not measured in this final comparison. Sprite caches stayed below their explicit 16 MiB per-species budgets.

## Balance evidence

Fresh held-out seeds 4001?4010, 60 simulated minutes each, passed the predefined gates: normal 10/10 persistent/active/diverse with cap occupancy 0.05?2.84%; stress 9/10 persistent/active, cap occupancy 14.22?23.84%. Stress seed 4004 lost predators at 3100.43 s; all stress prey populations survived. Matched old rules retained both species in 0/10 runs for either recipe. See [per-world outcomes and trait checkpoints](../balance-revision/candidate14-heldout/RESULTS.md). Finite trials cannot establish indefinite survival.

## Artifacts

- Executable: `release/dist/GENESIS/GENESIS.exe`
- ZIP: `release/GENESIS-0.12.0-windows-x64.zip`
- ZIP SHA256: `6189A6A283F14D8B3DD4A1D3E7BE1905DE10F9E1C1800E4B15F3C31946D22443`

Only corrected rules are exposed in the desktop. No Classic switch or preset; obsolete-rule saves are rejected without replacing the current world. Research/regression support for old rules is internal. No upload or publication performed.
