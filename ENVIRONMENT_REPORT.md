# Phase 8 validation and measurements

Measured on October 10, 2026. Baseline: 107 tests passed in 59.981 seconds. Final: 122 passed in 79.068 seconds. Native scripted environment, glass and lineage checks passed at 1380x900 and 960x720; glass checks also exercised fullscreen transitions and hidden controls. Screenshots were reviewed, including closed/open panels, conditional settings and graph markers. This was automated desktop interaction plus screenshot inspection, not manual pointer testing.

## Seeded trials

All runs started with 100 prey and 8 predators, habitats enabled, map seed equal to organism seed, mutation strength 0.06, a 120-second seasonal cycle, 15-second droughts, and uniformly sampled gaps of 90-180 seconds after initialization/each drought end. Runs used normal fixed ticks and stopped at 600 simulation seconds or full extinction. No populations were held constant or respawned. Default survival, feeding and reproduction rules were unchanged.

| Seed | Base food/s | End time (s) | Prey | Predators | Births | Deaths | Catches | Predator extinction (s) | Droughts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 20 | 243.77 | 0 | 0 | 737 | 845 | 694 | 243.767 | 1 |
| 7 | 20 | 600.00 | 179 | 0 | 1844 | 1773 | 915 | 347.700 | 3 |
| 2026 | 20 | 600.00 | 206 | 0 | 1932 | 1834 | 1071 | 390.300 | 3 |
| 42 | 2 | 600.00 | 22 | 0 | 225 | 311 | 140 | 115.800 | 3 |
| 7 | 2 | 600.00 | 19 | 0 | 217 | 306 | 111 | 114.333 | 3 |
| 2026 | 2 | 600.00 | 26 | 0 | 230 | 312 | 117 | 97.133 | 3 |

Seed 42 at base food 20 lost its last prey at 220.767 seconds and its last predator at 243.767 seconds. All other runs retained prey through 600 seconds but lost predators. Six finite trials neither establish stable coexistence nor isolate a causal environmental effect; there is no matched no-events trial control here. Occupancy is location, not evidence of adaptation.

| Seed | Base food/s | Open water P/H/F | Garden P/H/F | Dense P/H/F |
| --- | --- | --- | --- | --- |
| 42 | 20 | 0 / 0 / 194 | 0 / 0 / 280 | 0 / 0 / 176 |
| 7 | 20 | 66 / 0 / 3 | 69 / 0 / 14 | 44 / 0 / 14 |
| 2026 | 20 | 59 / 0 / 5 | 92 / 0 / 12 | 55 / 0 / 12 |
| 42 | 2 | 9 / 0 / 4 | 8 / 0 / 3 | 5 / 0 / 3 |
| 7 | 2 | 11 / 0 / 3 | 6 / 0 / 4 | 2 / 0 / 9 |
| 2026 | 2 | 11 / 0 / 1 | 9 / 0 / 5 | 6 / 0 / 0 |

P/H/F means prey / hunters / food. Raw settings, minute samples and counts are in `artifacts/environment-trials.json`. Trial wall times are not rendering benchmarks.

## Active-world performance

Hardware: Intel Core i5-13600K; native Windows build 26200; Python 3.11.2; Pygame 2.6.1; SDL 2.28.4 Windows display driver. Software Pygame surfaces, display flip included. Each case used 30 frozen warmup draws, then **240 active frames** at a fixed input delta of 1/60 second. Effects and habitat overlay were on, normal glass transparency, History panel open, fitted camera. Simulation/update/render/total were timed separately. Event pumping, initialization, saving and warmup were excluded. Benchmarks ran without simultaneous test/trial workloads.

Exactly 120 ticks at 1x or 480 ticks at 4x were processed: 4 or 16 simulation seconds. No simulation steps were dropped. "Median" is the upper middle sorted sample; p95 uses index floor((N-1)*0.95). Simulation frame times at 1x include alternating zero-step frames; the upper middle lands on a stepping frame. Update additionally includes presentation/history work; total is update plus render, so it is not the sum of core simulation and render alone.

### Disabled-mode matched baseline and final integration

The same genuine Phase 6 checkpoint was loaded and advanced ten ticks before each case (start tick 4247, 300 organisms, 36 predators and 420 food). Environments were disabled. Populations ranged 288-300 at 1x (ending 290), and 250-300 at 4x (ending 300). Physical world, simulation RNG, settings, habitats and retained-history fingerprints matched before/after at each speed and across resolutions, excluding new observational schema fields. These measurements preceded the final enabled-only tint cache change.

Values below are median / p95 milliseconds.

| Build | Resolution | Speed | Core simulation | Full update | Render | Total | Wall seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Before | 1380x900 | 1x | 3.146 / 3.527 | 3.414 / 3.838 | 9.871 / 14.252 | 12.049 / 17.899 | 2.978 |
| Before | 1380x900 | 4x | 6.479 / 6.992 | 7.057 / 7.699 | 9.868 / 11.063 | 16.946 / 18.464 | 4.082 |
| Before | 960x720 | 1x | 3.173 / 3.507 | 3.441 / 3.920 | 7.773 / 11.858 | 10.712 / 15.490 | 2.484 |
| Before | 960x720 | 4x | 6.603 / 7.122 | 7.218 / 7.913 | 8.410 / 9.953 | 15.682 / 17.724 | 3.811 |
| After | 1380x900 | 1x | 3.173 / 3.686 | 3.416 / 4.136 | 10.015 / 14.689 | 12.705 / 18.231 | 3.036 |
| After | 1380x900 | 4x | 6.585 / 7.256 | 7.165 / 8.135 | 9.964 / 11.419 | 17.117 / 19.130 | 4.148 |
| After | 960x720 | 1x | 3.155 / 3.685 | 3.424 / 4.019 | 7.912 / 12.481 | 10.871 / 16.321 | 2.557 |
| After | 960x720 | 4x | 6.581 / 7.239 | 7.201 / 7.957 | 8.353 / 9.559 | 15.658 / 16.984 | 3.729 |

These small differences do not demonstrate a general disabled-mode performance improvement.

### Environment-enabled matched optimization

A separate naturally evolved checkpoint used seed/map seed 2026, 260 founding prey, 40 founding predators, base food 80, habitats, a 40-second cycle, 5-second droughts and gaps of 30-60 seconds. Both versions loaded the identical `artifacts/environment-cap.json` checkpoint, then advanced ten ticks to tick 2651. The population naturally remained **300 throughout all measured cases**; the benchmark did not force counts. One environmental transition occurred at 1x and two at 4x. This workload differs from the disabled fixture and should not be used to attribute their entire timing difference to environments.

The first implementation added a tint over the full viewport every frame. The final implementation retains one tinted background, regenerating only when the underlying camera image or quantized illumination color changes. Organisms and glass still render normally. The matched physical-world/history fingerprints remained identical after this rendering change; separate unit tests verify both RNGs and exact environmental continuation.

| Build | Resolution | Speed | Core simulation | Full update | Render | Total | Wall seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Per-frame tint | 1380x900 | 1x | 3.454 / 3.877 | 3.741 / 4.268 | 14.929 / 19.240 | 18.037 / 23.301 | 4.232 |
| Per-frame tint | 1380x900 | 4x | 7.031 / 7.664 | 7.626 / 8.358 | 15.576 / 16.539 | 23.231 / 24.546 | 5.591 |
| Per-frame tint | 960x720 | 1x | 3.449 / 3.860 | 3.694 / 4.214 | 10.758 / 15.035 | 14.167 / 18.954 | 3.22 |
| Per-frame tint | 960x720 | 4x | 7.088 / 7.707 | 7.691 / 8.515 | 11.527 / 12.680 | 19.273 / 20.872 | 4.673 |
| Cached tint | 1380x900 | 1x | 3.466 / 3.927 | 3.732 / 4.351 | 9.981 / 14.649 | 13.297 / 18.659 | 3.067 |
| Cached tint | 1380x900 | 4x | 6.939 / 7.779 | 7.552 / 8.397 | 10.423 / 12.351 | 17.975 / 20.091 | 4.388 |
| Cached tint | 960x720 | 1x | 3.454 / 3.966 | 3.716 / 4.324 | 7.709 / 12.286 | 11.189 / 16.238 | 2.531 |
| Cached tint | 960x720 | 4x | 7.007 / 7.458 | 7.580 / 8.169 | 8.450 / 9.493 | 16.041 / 17.593 | 3.883 |

At 1380x900/4x, caching reduced median rendering from 15.576 to 10.423 ms and median total from 23.231 to 17.975 ms in this matched short run. This is not a sustained 60 FPS claim: final p95 total was 20.091 ms, above a 16.67 ms frame budget. Results include normal scheduling noise and only one measured run per case. Continuous camera movement invalidates the background cache and was not benchmarked here. Fullscreen performance, effects-off Phase 8 performance, long-duration rendering stability and other hardware were not measured.

Raw results are `artifacts/lineage-performance-phase8-before.json`, `...phase8-after.json`, `...phase8-enabled.json` and `...phase8-enabled-cached.json`. Reproduce a current run with:

```powershell
Set-Location "C:\Users\Admin\Desktop\Coding Projects\Genesis"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\check_environment_ui.py
.\.venv\Scripts\python.exe tools\check_environment_trials.py
.\.venv\Scripts\python.exe tools\benchmark_lineage.py --label local-disabled
.\.venv\Scripts\python.exe tools\benchmark_lineage.py --label local-enabled --environment
```

## Limits

Environmental history retains 256 events, while sampled statistics retain 3,601 rows. Old graph data may outlive its event markers. Settings apply only to a new experiment. Events affect renewable food only; existing food remains available through droughts. Complete extinction stops the clock. Save continuation is verified on the same Python/runtime, not guaranteed bit-identical across future platforms. No neural networks, terrain editing, new species, autosave or packaged executable were added.
