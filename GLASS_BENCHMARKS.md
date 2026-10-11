# Floating glass UI: measured rendering cost

Historical initial glass redesign measurements. The current refinement and Phase 7 active-world comparison is in [LINEAGE_BENCHMARKS.md](LINEAGE_BENCHMARKS.md).

Measured 2026-10-10 on the native Windows SDL display. These measurements isolate presentation cost; they do not claim a gameplay FPS improvement over the previous layout.

## Environment and method

- CPU: 13th Gen Intel(R) Core(TM) i5-13600K; Windows build 26200; Python 3.11.2, Pygame 2.6.1, SDL 2.28.4. Software surfaces; display flip included.
- Frozen, seeded Patchwork snapshot: 106 organisms, 358 food particles; predators, habitats and effects enabled. Camera at Fit World. No simulation steps are timed.
- Two resolutions: 1380x900 and 960x720. Four cases per resolution: panel closed/open crossed with normal/reduced transparency. Open panel displays History at its initial scroll position.
- 30 warmup frames followed by 240 uncapped frames per case (1,920 measured frames total). UI time advances 1/60 second per frame to exercise local frost refresh. The simulation and its seeded RNG remain frozen and unchanged.
- Glass time measures only the sum of Glass.draw calls, including cached blits, local downsample/upsample work, tint, edge/shadow creation and refreshes. Total rendering includes the ecosystem, content, controls and display flip. Event pumping is outside those per-frame timings.
- Measured cases took 9.768 wall seconds in total, excluding warmup and desktop checks. Each represents four seconds of UI-time input; uncapped runtime differs from that nominal duration.

All timing pairs below are **median / p95 milliseconds**.

| Resolution | Panel | Reduce Transparency | Glass only | Complete rendering | Wall seconds |
| --- | --- | --- | --- | --- | --- |
| 1380x900 | Closed | Off | 0.044 / 0.325 | 4.929 / 6.999 | 1.245 |
| 1380x900 | Closed | On | 0.044 / 0.076 | 5.013 / 7.399 | 1.295 |
| 1380x900 | Open | Off | 0.439 / 3.623 | 6.382 / 11.327 | 1.764 |
| 1380x900 | Open | On | 0.448 / 0.756 | 5.997 / 9.056 | 1.511 |
| 960x720 | Closed | Off | 0.039 / 0.312 | 3.133 / 4.250 | 0.782 |
| 960x720 | Closed | On | 0.039 / 0.060 | 3.114 / 4.401 | 0.790 |
| 960x720 | Open | Off | 0.406 / 3.274 | 4.580 / 7.482 | 1.228 |
| 960x720 | Open | On | 0.390 / 0.560 | 4.564 / 6.324 | 1.153 |

Normal glass samples only local UI rectangles, downscales by 12 and smoothly enlarges them, then applies a navy tint. Frost refreshes at most 10 Hz unless geometry changes; measured cases refreshed each surface 34 times in 240 frames. Reduced-transparency surfaces do not sample the backdrop and required zero refreshes after warmup. The cache retains at most eight role-based entries. No fullscreen blur runs every frame.

The earlier implementation of reduced transparency unnecessarily regenerated the same opaque surfaces on each refresh interval. Before removing that work, open-panel glass at 1380x900 measured 0.440 / 2.526 ms. Final measurements above show the isolated glass cost after caching those surfaces. Differences in complete rendering time include ordinary measurement noise; no broad application-speed improvement is claimed.

## Checks and limitations

- Native scripted checks covered every relocated feature, scrolling, drag/resize bounds, minimize/restore, selection/details/follow, settings validation, CSV, the actual Pygame save/load picker, replacement confirmation, fullscreen and hidden-control restoration.
- Screenshots at normal and minimum sizes were visually reviewed with the panel open and closed, including cards, settings, graphs, presets, confirmations and reduced transparency. This is programmatic desktop testing and screenshot review, not manual mouse testing.
- All 93 tests passed (87 at baseline). Unit tests verify that UI interactions and effects leave seeded simulation results unchanged; existing exact persistence and speed-equivalence tests remain.
- This is a short, frozen-world rendering measurement. It does not benchmark continuous simulation, the 300-organism cap, dragging/resizing under load, maximum zoom, fullscreen glass cost, other hardware or long-duration stability.
- Panel geometry, active view and transparency preferences persist only within the running session. The existing file picker still explicitly suspends playback; the floating panel and confirmation do not.

Raw data: `artifacts/glass-performance.json`. Screenshots and desktop assertions: `artifacts/glass-*.png` and `artifacts/glass-desktop-checks.json`.

Reproduce from the project folder:

```powershell
.\.venv\Scripts\python.exe tools\check_glass_ui.py --benchmark
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
