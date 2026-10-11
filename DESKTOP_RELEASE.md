# GENESIS 0.11.0 — local desktop release validation

The onedir Windows x64 build and ZIP remain local. No simulation rules or
authoritative save fields changed. World format remains v6, accepting v1–v6.

## Deliverables and rebuild

- Executable: `C:\Users\Admin\Desktop\Coding Projects\Genesis\release\dist\GENESIS\GENESIS.exe`
- ZIP: `C:\Users\Admin\Desktop\Coding Projects\Genesis\release\GENESIS-0.11.0-windows-x64.zip`
- Build: `powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-Release.ps1`
- Check extracted ZIP: `powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-Release.ps1`

Run commands from the project directory. Build requires Windows Python 3.11 x64;
runtime does not require an installed Python. The ZIP contains the executable,
its `_internal` runtime/assets, quickstart instructions, version manifest and
dependency notices. Keep the entire folder together. Product/FileVersion is
0.11.0; the executable uses the Windows GUI subsystem and includes the neon icon.
Generated files remain under `release/`; build tools and assets remain in source.

## Functional evidence

Baseline: 136 tests, all passed in 94.663 seconds. Final suite: 148 tests passed in 94.305 seconds during the final build.
The 12 new tests cover preferences, atomic failed writes, malformed/oversized
input, monitor geometry, per-user paths, Unicode paths, bundled-directory write
protection, successful-directory retention, CSV picker handling, and separation
from world/RNG state. Existing persistence and speed tests were rerun.

`genesis.release_check` runs the same fixed automated native-SDL checks from
source or the frozen executable. The extracted executable ran outside the
repository in a temporary directory containing spaces and Ω. PATH was limited
to Windows directories; PYTHONHOME, PYTHONPATH and VIRTUAL_ENV were removed.
Reports confirm `sys.frozen=True` and Pygame imports from the extracted
`GENESIS/_internal`, not the development venv. Preferences/logs were redirected
to an isolated per-user test directory outside the application folder. The
ordinary no-argument entry point also launched and exited cleanly on WM_CLOSE.

Automated checks exercised:

- Pause, 1×/4× speed, every settings view, first-launch guide and reopen/dismiss
  at 1380×900 and 960×720; guide/control actions preserved world and RNG hashes.
- Fullscreen transition and window-size restoration, hidden controls restored
  with Escape. Fullscreen screenshot resolution: 3440×1440.
- Real Pygame modal pickers receiving SDL text/key events: save, load with
  replacement confirmation, statistics/lineage/diagnostics CSV exports.
- Filenames containing spaces, Ω and Japanese characters; last successful
  destinations; existing-CSV and malformed-load error messages; rejecting saves
  inside the executable folder without creating the file.
- Archived real v1–v5 fixtures loaded, advanced, saved as v6, reloaded, and
  advanced again with identical complete final state hashes. New v6 save/load
  was also checked through the native picker.
- Separate-process relaunch restored effects, Reduce Transparency, panel tab
  and width, window size, guide-seen flag and both destination directories.

Evidence lives under `artifacts/desktop-release-check`, with the source desktop
captures under `artifacts/release-source`. Normal/minimum first-launch, closed
and Appearance screenshots were inspected; no new clipping was found in those
views. These were scripted desktop checks and screenshot review, **not manual
pointer testing**. No clean-machine VM, machine without Python installed,
multiple-monitor hardware, scaling matrix or long-running endurance test was
performed. Removing Python from process search paths is not equivalent to a
clean-machine certification. This unsigned ZIP is not an installer and has no
update mechanism. Preferences are saved on clean exit; worlds still require an
explicit Save World action.

## Matched short performance comparison

Environment: 13th Gen Intel Core i5-13600K, Windows build 26200 x64, Python
3.11.2, Pygame 2.6.1, SDL 2.28.4, native Windows software surfaces. Source and
PyInstaller 6.22.0 bundle run alternately, three pairs, on the same development
machine. This does not measure hardware GPU acceleration.

Each case restores the same environment-enabled habitat/predator cap checkpoint,
advances ten fixed steps, then starts with 300 organisms. Population stayed at
300 throughout each measured case. FX and habitat lighting are on, History panel
is open, transparency is enabled, resolution is 1380×900. Thirty paused/frozen
warmup draws precede **360 active frames** with exactly 1/60 second input per
frame. Cases execute 180 ticks at 1× (6 simulated seconds), 720 at 4× (24 simulated
seconds). Wall durations per case: source 4.488–4.870 s at 1× and 6.246–6.568 s at
4×; packaged 4.226–4.356 s and 6.142–6.251 s. No simulation steps are discarded.
Event pumping is outside timings; draw includes display flip. Simulation time
counts only World.step; full update includes observational history and effects.

Values below are the **median of three run medians / median of three run p95s**,
in milliseconds. They are not pooled percentiles or sustained FPS measurements.

| Build / speed | Core simulation | Full update | Render | Total |
|---|---:|---:|---:|---:|
| Source 1× | 3.514 / 4.007 | 3.785 / 4.385 | 9.733 / 14.665 | 13.211 / 18.388 |
| Packaged 1× | 3.531 / 3.926 | 3.794 / 4.264 | 9.292 / 13.903 | 12.835 / 17.597 |
| Source 4× | 6.765 / 7.745 | 7.344 / 8.417 | 10.259 / 11.862 | 17.614 / 20.581 |
| Packaged 4× | 6.806 / 7.483 | 7.350 / 8.167 | 9.665 / 11.252 | 16.968 / 19.221 |

All final-state hashes matched between source and packaged runs at each speed,
including RNG, history, environment, lineage and diagnostics. This provides no
evidence of a packaging-induced outcome change. Small timing differences are
within a short desktop workload; **no performance improvement is claimed**.
At 4× and capacity the total median exceeds a 16.67 ms frame budget. Sustained
60 FPS, fullscreen performance and other hardware remain unverified.

Raw per-run reports: `artifacts/desktop-release-check/checks/source-{1,2,3}`
and `packaged-{1,2,3}/benchmark.json`. Benchmarks preceded a final picker-button
label/error-message adjustment; that adjustment does not execute in benchmark
frames. The final ZIP is checked again through the functional desktop workflow.

Final ZIP: 15355171 bytes. SHA-256: `e1b7afe22b32106774b3d73003a3b77751be4dcd2988bd6a265f1021bb4432ef`. ZIP CRC verification passed for all 104 entries. The final extracted-build smoke/relaunch/normal-entry checks passed again after rebuilding.
