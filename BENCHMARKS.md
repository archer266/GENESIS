# Phase 6 performance and validation

Historical measurements from the pre-glass layout. See [GLASS_BENCHMARKS.md](GLASS_BENCHMARKS.md) for the current interface; these old timings are not claims about its performance.

Measured 2026-10-10 using the native Windows SDL display. These are development-machine measurements, not hardware-independent performance guarantees.

## Environment and workload

- Intel Core i5-13600K, 20 logical processors, 31.8 GiB reported physical RAM; Windows build 26200.
- Python 3.11.2, Pygame 2.6.1, SDL 2.28.4; software surfaces and display flip included. No GPU acceleration is claimed.
- Window resolutions: 1380x900 and 960x720. Fullscreen control checks used the 3440x1440 primary desktop, but fullscreen performance was not benchmarked.
- Predator and habitat modes enabled, habitat overlay on, History panel open, camera at Fit World. FX tested both on and off.
- Seed/map seed 2026; 260 founding prey, 40 founding predators, food rate 80, mutation strength 0.06. A naturally evolved checkpoint at tick 4247 (141.57 simulation seconds) contains exactly 300 organisms: 264 prey and 36 predators, plus 420 food. Real movement trails and event effects are retained for rendering; population outcomes are not forced.
- Each case has 30 untimed draw warmups and 240 measured samples. The 16 measured cases took 62.95 seconds of wall time in total, excluding fixture generation, warmup and profiling. Separate cProfile runs informed optimization; profiler overhead is excluded from the timing tables.

## Population-cap replay

Before each simulation timing, clone the same 300-organism world outside the timed block. A 1/30-second clock input executes exactly one tick at 1x or four ticks at 4x. Measure core simulation independently from rendering the original 300-organism snapshot. Snapshot rendering includes UI and flip. This isolates capacity cost; it is not continuous gameplay or an FPS estimate. Organisms can die in the simulated clone. Copying and observer callbacks are excluded from core simulation timing.

All timing pairs are **median / 95th percentile milliseconds**.

| Resolution | Speed | FX | Core simulation, 1 or 4 ticks | Render at 300 | Case wall seconds |
| --- | --- | --- | --- | --- | --- |
| 1380x900 | 1x | On | 3.49 / 4.04 | 8.08 / 11.05 | 4.32 |
| 1380x900 | 1x | Off | 3.52 / 4.05 | 5.44 / 7.81 | 3.68 |
| 1380x900 | 4x | On | 13.85 / 15.43 | 8.34 / 10.98 | 6.93 |
| 1380x900 | 4x | Off | 14.07 / 15.39 | 5.93 / 7.93 | 6.38 |
| 960x720 | 1x | On | 3.47 / 3.83 | 6.81 / 8.75 | 3.98 |
| 960x720 | 1x | Off | 3.44 / 3.87 | 4.09 / 5.74 | 3.31 |
| 960x720 | 4x | On | 13.90 / 15.49 | 6.99 / 9.25 | 6.57 |
| 960x720 | 4x | Off | 13.70 / 15.13 | 4.19 / 5.47 | 5.79 |

## Continuous playback workload

Start at the same checkpoint, then execute 240 consecutive update/draw frames with a fixed 1/60-second clock input per frame, uncapped. The 1x cases execute 120 ticks (4 simulation seconds); 4x executes 480 ticks (16 simulation seconds). Every requested tick is executed. Core simulation is timed inside the update; total frame time also includes history/effects/camera updates and rendering. The 1x core median includes alternate frames with zero fixed steps. This is a target-60-FPS workload, not a long-running real-time FPS measurement.

| Resolution | Speed | FX | Core simulation/frame | Render/frame | Total frame | Case wall seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 1380x900 | 1x | On | 1.72 / 4.05 | 8.08 / 10.85 | 11.36 / 14.84 | 2.54 |
| 1380x900 | 1x | Off | 1.69 / 4.02 | 5.25 / 8.00 | 8.35 / 11.62 | 1.84 |
| 1380x900 | 4x | On | 7.34 / 8.56 | 8.85 / 12.51 | 16.92 / 21.74 | 4.19 |
| 1380x900 | 4x | Off | 7.19 / 8.06 | 5.34 / 8.17 | 12.95 / 16.40 | 3.21 |
| 960x720 | 1x | On | 1.71 / 3.93 | 6.61 / 8.75 | 10.13 / 12.76 | 2.15 |
| 960x720 | 1x | Off | 1.68 / 3.94 | 3.90 / 5.70 | 7.19 / 9.51 | 1.49 |
| 960x720 | 4x | On | 7.30 / 8.39 | 7.31 / 9.51 | 15.24 / 18.18 | 3.74 |
| 960x720 | 4x | Off | 7.25 / 8.31 | 3.94 / 5.28 | 11.57 / 13.68 | 2.83 |

At 1x, population ranged from 288 to 300 and ended at 290. At 4x it ranged from 250 to 300 and ended at 300. Final saved-state hashes match across FX toggles and resolutions, and all eight match the corresponding pre-optimization runs. Hashes, settings, exact durations, population ranges and observer-inclusive update costs are in `artifacts/phase6-performance-final.json`.

**Limit:** 1380x900 at 4x with FX on measured 16.92 ms median and 21.74 ms p95, so steady 60 FPS is not guaranteed near capacity. FX off reduced this workload to 12.95 / 16.40 ms. There is no claim about sustained fullscreen performance, other hardware, maximum-zoom performance or long-duration stability.

## Evidence-led optimization

The renderer profile identified repeated camera properties and trail transforms as a major cost. Caching the frame transform and transforming each trail point once reduced the fixed-scene unprofiled render median from 12.10 ms to 8.16 ms in the first after-change run. Later runs vary slightly with system load.

The simulation profile identified distance checks against same-species targets, all-prey contact scans and predator counts for ineligible parents. Sensing now rejects impossible species before calculating distances; a fresh post-movement spatial grid prunes impossible catches; reproduction checks cheap eligibility before counting predators. Predator ID order, nearest-distance/prey-ID ties, floating-point distance expressions and RNG consumption remain unchanged. In the same 1380x900/FX-on capacity workload, the one-tick median fell from 6.22 to 3.49 ms. Six seeded uniform/habitat trajectories and dedicated contact-boundary/tie cases compare exactly against the previous methods; existing frozen-model and persistence tests also pass.

## Reproduce the checks

From the project folder in Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\check_explore_ui.py
.\.venv\Scripts\python.exe tools\benchmark_explore.py --label final
```

The benchmark creates a validated JSON fixture on its first run and reuses it thereafter. It takes control of a native Pygame window while running. The desktop check posts Pygame events, asserts state and geometry, and captures screenshots. Screenshots were visually reviewed at normal/minimum sizes, including follow, graphs, settings, fullscreen, hidden controls and maximum zoom. This is automated desktop checking and screenshot review, not manual pointer testing. Native display checks require a desktop and cannot run with `SDL_VIDEODRIVER=dummy`.
