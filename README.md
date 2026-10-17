# GENESIS — Living Ecosystem 0.13.0

A Python/Pygame artificial-life simulator with luminous cells, a quiet floating
glass interface, predators and prey, seeded habitats, environmental events and
an Evolution Observatory. Feeding, energy costs, reproduction and inherited
mutations determine outcomes. There are no respawns, species quotas, scripted
population cycles or hidden difficulty adjustments.

## UI Preview

![Source-generated UI preview of GENESIS with ecosystem, quick guide, and floating controls](docs/screenshots/main-interface.png)

**Source-generated UI preview — not an actual application screenshot.**
Reconstructed from the UI drawing code at 2760 × 1800, with the quick guide
visible and Settings closed. Organism, food, and habitat placement is illustrative;
no application or simulation was launched to create this preview.

## Launch the Windows application

**Installer:** double-click
`release\installer\GENESIS-0.13.0-windows-x64-setup.exe`, follow the wizard,
and optionally select a desktop shortcut. Leave **Launch GENESIS** selected to
open it immediately, or use **Start > GENESIS** afterward. Installation is
per-user without administrator privileges, under
`%LOCALAPPDATA%\Programs\GENESIS`. Python is not required. Windows 10/11 x64 is
the installer target; this local build is unsigned.

Run a newer installer to update the same application, preferably after closing
GENESIS so recovery finishes. Windows **Settings > Apps > Installed apps >
GENESIS > Uninstall** removes the program and shortcuts, but preserves preferences,
worlds, exports, and recovery in `%LOCALAPPDATA%\GENESIS` and chosen user folders.
Reinstalling can reuse those files. The installer does not migrate or delete them.

**Portable alternative:**
Double-click `release\dist\GENESIS\GENESIS.exe`, or extract
`release\GENESIS-0.13.0-windows-x64.zip` and double-click the executable inside
its `GENESIS` folder. Keep `_internal` beside the executable. Python and a
terminal are not required. Extract the ZIP before launching.

```powershell
Set-Location "C:\Users\Admin\Desktop\Coding Projects\Genesis"
Start-Process -FilePath ".\release\dist\GENESIS\GENESIS.exe"
```

The portable ZIP is unchanged. Portable and installed copies share the same
default user-data folder; avoid running both against it simultaneously.
No binary release has been published or uploaded.

### Rebuild the installer

Install [Inno Setup 6.3 or later](https://jrsoftware.org/isinfo.php) (validated
with 6.7.3), then run from the project directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-Installer.ps1
# If ISCC.exe is not in a standard location:
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-Installer.ps1 -Compiler "C:\Tools\Inno Setup 6\ISCC.exe"
```

This packages the existing `release\dist\GENESIS` build without rebuilding the
app or changing its version. It fails clearly if Inno Setup is unavailable.
`tools\Test-Installer.ps1` performs an isolated install/upgrade/uninstall test;
it refuses to overwrite an already registered GENESIS installation or shortcuts.
It leaves preserved test data as evidence. See [installer checks and pending
validation](reports/installer-013/RESULTS.md). Another Windows computer without
Python and hands-on wizard/post-install Launch checks remain pending.

## The corrected ecosystem

**Living Ecosystem** is the recommended startup recipe: seed 42, 160 prey,
8 predators, base food regeneration 28/s, 20% mutation strength, and habitats
with independent map seed 42. Seasons and droughts are off. **Living Seasons**
uses 18% mutation and adds a 180-second seasonal cycle, 10-second droughts and
drought-free intervals of 120–240 seconds. Presets fill editable drafts; Start
new applies them. Enabling events manually never silently changes mutation.

Ecology rules provide three renewable food resources suited to different body
sizes. Small bodies are cheaper and harder to detect; large bodies can use
larger food particles and predators can handle larger prey. Speed improves
travel and escape but has propulsion and maintenance costs. Sensing increases
food choice, warning distance and hunting range but consumes energy. Arrival
braking prevents orbiting food; hunters predict movement, digest catches and
pay local interference costs. Reproduction transfers parental energy and
charges overhead. Mutations reflect at the unchanged trait bounds.

Cell color now follows inherited **body size 3–9**, interpolating 33 shades:
small cyan/lime, medium orange, large pink/violet. Predators are angular and
use a warmer palette. Food remains a golden sparkle, with three particle
sizes. Appearance explains the mapping. Color is not fitness or adaptation.

The previous renderer colored every speed from 51 through 75 purple. This
hid variation, but real convergence and predator loss also occurred. See
[the diagnosis, exact equations and measured comparison](BALANCE_REVISION.md)
and [the predeclared acceptance criteria](BALANCE_REVISION_PLAN.md).

Only the corrected ecosystem is available in the desktop app. There is no
Classic switch or command-line option. Extinction remains possible; hour-long
evidence does not guarantee indefinite survival.

## Controls and information

The ecosystem fills the window. The bottom glass bar contains playback, speed
and Settings. The dismissible first-launch guide can be reopened in Appearance.
Settings overlays the world without resizing or pausing it. Drag its header,
resize its lower corner, scroll inside it, or minimize it to an edge tab.
UI surfaces isolate their clicks, wheel events and drags from the world.

| Action | Control |
|---|---|
| Pause / play | Space or playback bar |
| Speed | 1, 2, 4 or segmented control |
| Settings | O or Settings button |
| Select / inspect | Left-click a cell; small card > Details |
| Zoom | Mouse wheel centered on cursor |
| Pan / stop following | Right or middle drag outside UI |
| Follow selected | F or inspector Follow |
| Fit World | Home or Appearance |
| Fullscreen | F11 or Appearance |
| Hide / restore UI | I; Esc or visible Restore UI button |
| Effects / habitat illumination | E / H; also in Appearance |
| Save / load | Ctrl+S / Ctrl+L; also in Worlds |
| Restart same seed | R; confirmation required |
| Navigate controls | Tab / Shift+Tab, then Enter or Space |

Escape cancels dialogs/editing, closes Settings, restores hidden controls or
exits fullscreen as applicable. Focused text fields suppress playback shortcuts.
The window supports 960×720 minimum; default first-launch size is 1380×900.
Zoom, follow, resizing, effects and transparency never affect simulation RNG.

- **Experiment:** presets, rules, seed, populations, food, mutation, habitats
  and environmental drafts. Conditional switches retain hidden draft values.
  New seed prepares an independent seed; Restart repeats the applied seed.
  Restart, Start new and Load confirm before replacing the active world.
- **Observatory:** population/trait histories, founder comparisons, distributions,
  generation, habitat occupancy, environmental timing and diagnostic ledgers.
  Diagnostics distinguish lifetime counts from recent rates, including death
  causes, births, catches, average energy, energy flows and cap deferrals.
- **Details / Lineage:** immutable recorded birth traits, ancestry, direct
  offspring and signed parent/child trait changes. Archived relatives remain
  inspectable; living relatives offer Select and Follow. Missing history is
  marked unavailable. At most 4,096 records are retained, preserving living
  organisms and pruning the oldest dead IDs first.
- **Worlds:** Save World, Load World, statistics CSV, lineage CSV and diagnostics
  CSV. Destination pickers show readable failures and retain successful paths.
- **Appearance:** effects, habitat illumination, environment chip, Reduce
  Transparency, fullscreen, Fit, Follow, Hide UI, guide and color legend.

History samples every simulation second and retains at most 3,601 rows;
founder comparisons remain separate. Diagnostics retain 61 recent samples;
environment history retains 256 events. CSV includes simulation time, seeds,
rules/settings, species statistics and regional occupancy. Location counts
and population changes alone do not demonstrate adaptation. CSV requires a
new filename and is not a resumable save.

## Determinism, habitats and limits

The bounded 1100×760 world advances at a fixed 1/30-second timestep. No steps
are silently dropped for frame rate. Population is limited to 300 organisms,
including at most 40 predators. Food is bounded to 650 particles. Ecology
allocates resource capacities of 217/217/216; an unused resource cannot block
renewal of another. These are resource limits, not organism quotas.

All regions are traversable. Gardens multiply food regeneration by 2; open
water and dense regions use 1. Dense regions multiply movement by 0.6 for both
species without giving a free propulsion-energy discount. Habitats use world
coordinates and a separate seeded map generator. They cannot be edited during
an active experiment.

Seasons smoothly multiply regeneration by 0.5–1.5; active droughts multiply it
by 0.25. These multiply the base rate and habitat factors. Their independent
environment RNG, scheduled ticks and bounded event history are saved. They
never directly kill, reproduce or alter traits. Enabled settings apply only
when starting a new world.

Glow sprites are cached with both a 512-entry and 16 MiB pixel-buffer limit
per species. Trails and particles are bounded. Glass samples only visible
surface crops at reduced resolution; Reduce Transparency avoids backdrop
sampling. Effects and camera state stay separate from authoritative state.

## User files and persistence

Preferences and rotating logs live in `%LOCALAPPDATA%\GENESIS`. Initial picker
destinations are its `Worlds` and `Exports` folders; other writable locations
can be chosen. No user data is written inside the packaged application folder.
The last successful save/export directories are remembered separately.

Appearance, panel layout and window settings persist across launches.
Malformed preferences recover to defaults and log a warning; unavailable
display geometry is clamped. Preferences remain separate from world state. Optional recovery snapshots
protect ongoing worlds; use Save World for permanent named checkpoints. `GENESIS_USER_DATA_DIR` redirects test
preferences/logs; it cannot point into the packaged application directory.

World JSON uses **format version 7**, including the rules version, organisms,
food, digestion timers, authoritative habitat map, IDs, clock, RNG states,
environment schedule/history, diagnostics, lineage, retained statistics and
founder comparisons. Saves are atomic; loads validate before replacement and
open paused. Worlds using obsolete rules are rejected without replacing the
active world. Rendering effects are not saved.

## World recovery (Phase 11)

Autosave defaults to **On** in Settings > Worlds. It checkpoints changed worlds
every **two minutes of wall-clock time**, independent of simulation speed.
An unchanged paused world is not repeatedly saved. New experiments and successful
manual loads establish recovery snapshots when autosave is enabled. Clean exit
finishes any write and saves the changed current world. Disabling autosave stops
new writes; an in-flight atomic write is allowed to finish.

Recovery is separate from named manual saves:
`%LOCALAPPDATA%\GENESIS\Recovery\latest.json` and `previous.json`.
Startup validates both as needed and offers **Resume previous world** (paused)
or **Start fresh**. A corrupt latest snapshot falls back to the previous valid
one with an explanation. While the choice is pending, simulation and recovery
writes are held; closing the app leaves those snapshots intact. Existing files
are retained when autosave is disabled. `--load` explicitly selects a manual
world instead of showing the startup recovery choice.

Worlds shows quiet save status and readable failures; failures are logged without
repeated popups. Recovery uses authoritative format 7 and the same atomic writer
as manual saves. Mutable state is copied between complete simulation steps;
immutable history/lineage records are serialized by a single background writer.
The worker never reads the active world. At most one write is in flight. A newly
selected world waits behind an earlier write and is then checkpointed.

Recovery is not a substitute for permanent saves: a crash can lose changes since
the last completed checkpoint (normally up to two minutes plus write time).
Slow or failing storage can extend this; clean shutdown waits for the writer.
See [Phase 11 validation and save costs](reports/recovery-013/RESULTS.md).

## Source launch, tests and rebuild

Pygame 2.6.1 is pinned in `requirements.txt`. The Windows build uses Python
3.11 x64 and pinned PyInstaller dependencies in `requirements-build.txt`.

```powershell
Set-Location "C:\Users\Admin\Desktop\Coding Projects\Genesis"
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m genesis

# Optional source recipes:
.\.venv\Scripts\python.exe -m genesis --seasons --droughts --mutation-percent 18
.\.venv\Scripts\python.exe -m genesis --no-predators --no-habitats
.\.venv\Scripts\python.exe -m genesis --load "C:\My Worlds\experiment.json"

# Build an onedir executable and ZIP; runs the complete test suite:
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-Release.ps1 -SkipInstall

# Native packaged checks and matched short source/package benchmarks:
.\.venv\Scripts\python.exe tools/make_ecology_fixture.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-Release.ps1
```

Build products stay under `release/build`, `release/dist` and `release/`.
Build metadata follows `genesis.__version__`; save format versions are separate.
No upload, installer, telemetry or automatic update is included.

## Validation and limitations

The [final 0.13.0 release check and manual checklist](reports/recovery-013/FINAL_CHECK.md)
found no demonstrated blocker and verified ZIP integrity/completeness. Hands-on
checklist testing and another Windows computer without Python remain pending.

Phase 11 passed **194 tests** and native scripted packaged checks, including
cross-process recovery resumed paused, autosave controls, preferences, fullscreen,
Unicode file operations and exact continuation. At 281 organisms with full
lineage/history archives, snapshot capture took **5.4-7.0 ms**; background
validation/rotation/writing took **398-626 ms** on this development machine.
See [Phase 11 results and limitations](reports/recovery-013/RESULTS.md).

The current ecosystem's held-out hour-long trials retained both species in
10/10 normal worlds and 9/10 stressed worlds; these mechanics were unchanged
in Phase 11. See [balance results](reports/balance-revision/candidate14-heldout/RESULTS.md).

Packaged checks ran outside the repository with Python removed from the search
path, but not on an isolated machine. No Computer Use, screenshots, or new render
benchmarks were needed for Phase 11. Slow storage can delay shutdown and extend
the interval since the last successful recovery checkpoint.

Historical reports describe earlier releases, not current balance:
[desktop 0.11](DESKTOP_RELEASE.md), [Phase 9 balance](BALANCE_REPORT.md),
[environment](ENVIRONMENT_REPORT.md), [camera](BENCHMARKS.md),
[glass](GLASS_BENCHMARKS.md), [lineage](LINEAGE_BENCHMARKS.md).
