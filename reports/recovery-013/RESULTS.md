# Phase 11 - World Recovery (0.13.0)

## Changes

Optional autosave defaults on. Changed worlds are captured every 120 seconds of
monotonic wall-clock time; unchanged paused worlds are skipped. Confirmed new
experiments/manual loads and clean exit establish recovery when enabled.
Settings > Worlds exposes the toggle and quiet status/errors. Preferences remain
separate from authoritative worlds. The simulation and save schema are unchanged.

Recovery uses `%LOCALAPPDATA%\GENESIS\Recovery\latest.json` and `previous.json`.
The existing validated format-7 atomic writer is shared with manual saves. A new
snapshot is validated before rotation. Corrupt latest data is never rotated over
a valid previous file. Startup offers Resume previous world (paused) or Start
fresh, with a fallback explanation when needed. No simulation steps or writes
occur while that choice is pending. Escape does not silently choose; closing the
app leaves pending recovery intact. A supplied `--load` explicitly takes precedence.

The UI thread copies mutable state after complete simulation updates. Detached
lists retain only recursively immutable history/lineage values. A single worker
serializes these archives, validates and writes. It never receives the world,
clock, history manager, or mutable live containers. New-world requests wait behind
an in-flight write. Disable prevents new writes; an existing write may finish.
Shutdown waits, then checkpoints the changed current world if enabled.

## Tests

Relevant 0.12 baseline: 21 persistence/desktop tests passed (12.600 s).
Focused Phase 11 integration: 50 tests passed (25.246 s). Coverage includes two-file
rotation, corrupt fallback, invalid incoming data, failed rename/commit, preserved
active recovery, interval scheduling, disabled mode, unchanged pause, pending
startup, explicit choices, manual load/new experiment, one writer, shutdown,
concurrent model advancement during writing, unchanged RNG and exact continuation.
Full release suite: **194 tests passed in 155.187 s**, run once before packaging.
The built executable passed native scripted checks at 1380x900 and 960x720:
Worlds autosave toggle, cross-process recovery offer/resume paused, preferences,
fullscreen/UI restoration, Unicode save/load, three CSV exports, errors, obsolete
save rejection, and exact corrected-world continuation. Ordinary startup/close
also passed. The ZIP was extracted outside the project in a directory containing
spaces and Omega, with Python/venv search paths removed. This is development-machine
validation, not an isolated-machine test. Render benchmarks were intentionally
skipped for this persistence-only release. Raw checks: [smoke](smoke.json),
[relaunch](relaunch.json), [launch environment](launch.json).

## Save costs

Intel Core i5-13600K development machine, Windows build 26200, Python 3.11.2;
local temporary-directory storage. Five captures/writes of one valid mature-world
fixture: **281 organisms, 4096 lineage records, 3601 history samples**. Its food
rate was raised to 80/s solely to construct a near-cap workload, after accumulating
real birth/death/history records. This is a stress fixture, not a balance trial.
No render loop or other simulation trial ran during measurement.

- Original synchronous document capture: **104.2-107.8 ms**.
- Deferred-archive snapshot capture: **5.4-7.0 ms** on the UI thread.
- Worker validation/serialization/atomic write: **398 ms** first save;
  **617.6-626.3 ms** with previous-file validation/rotation.
- A foreground 1 ms sleep scheduling probe while the worker ran observed
  **16.1 ms p95 / 20.6 ms maximum gaps**. This includes OS timer scheduling and
  Python thread contention; it is not a frame-time measurement.
- All measurements preserved the authoritative model and simulation RNG.

Raw observations: [before](recovery-capture-before.json), [after](recovery-costs.json).
Reproduce with `.\.venv\Scripts\python.exe tools\benchmark_recovery.py artifacts\recovery-benchmark-world.json`.

## Limits

Recovery is not permanent archival storage. A crash loses changes since the last
completed checkpoint, normally up to two minutes plus write time. Slow/failing
storage extends that window. Clean shutdown waits for an outstanding write;
unresponsive storage can delay exit. Background CPU serialization can contend
with rendering; no stall-free or sustained-FPS claim is made. Tests run on the
development machine, not an isolated computer. No Computer Use or screenshots
were needed for Phase 11. No ecosystem mechanics changed; no release was uploaded.

## Release artifacts

- Version: 0.13.0; authoritative save format remains 7.
- EXE: `C:\Users\Admin\Desktop\Coding Projects\Genesis\release\dist\GENESIS\GENESIS.exe`
- ZIP: `C:\Users\Admin\Desktop\Coding Projects\Genesis\release\GENESIS-0.13.0-windows-x64.zip`
- ZIP SHA256: `37CB43247A6571A1F925CC627E93FA12ACD084BDB6B268A251A591F30DF0C1E3`

Rebuild from the project directory:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-Release.ps1 -SkipInstall
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-Release.ps1 -SkipBenchmark
```
