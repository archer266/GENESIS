# GENESIS - Desktop Release 0.11.0

A Python/Pygame artificial-life ecosystem with a quiet floating glass interface, Neon Microcosm visuals, a live Evolution Observatory, editable presets, CSV export and resumable worlds. Explore with cursor-centered zoom, drag panning, organism following and an immersive fullscreen view. Optional predators pursue prey; prey flee while foraging. Population changes arise from feeding, energy costs, inherited mutations and reproduction. Optional seeded habitats add food-rich gardens and slower dense regions while preserving the uniform world as the default. No outcomes or population cycles are scripted.

## Launch the Windows desktop build (no Python needed)

Double-click **`release\dist\GENESIS\GENESIS.exe`**, or extract **`release\GENESIS-0.11.0-windows-x64.zip`** and double-click `GENESIS.exe` inside the extracted GENESIS folder. Keep the executable beside its `_internal` folder. Do not run it from inside the ZIP. This local Windows x64 build is unsigned; it has not been published or uploaded.

```powershell
Set-Location "C:\Users\Admin\Desktop\Coding Projects\Genesis"
Start-Process -FilePath ".\release\dist\GENESIS\GENESIS.exe"
```

## Phase 10: Desktop Release

The folder distribution bundles Python 3.11.2, Pygame 2.6.1, runtime libraries, a multi-resolution neon cell icon, Windows product/version resources, dependency notices, and a short `GETTING_STARTED.txt`. Generated files stay under `release/build` and `release/dist`; the versioned ZIP is under `release/`. Simulation rules, presets, RNG consumption, diagnostics and save format **6** are unchanged. **Valid v1?v6 worlds remain supported.**

**Personal files:** preferences and rotating logs live in `%LOCALAPPDATA%\GENESIS`. Initial picker destinations are its `Worlds` and `Exports` subfolders. World saves/loads and all three CSV exports let you browse or type another destination. The last successful world and export directories are remembered independently; cancellations and failed operations do not replace them. A missing destination falls back to the per-user folder. Packaged application-folder writes are rejected. CSV requires a new filename; replacing an existing world save requires confirmation. Starting/restarting/loading still asks before replacing an active experiment; loads open paused.

`preferences.json` is a separate, validated version-1 presentation document, written atomically. Effects, habitat illumination, environment chip, Reduce Transparency, panel position/size/tab/open/minimized state, window size/position and fullscreen preference are restored. Unavailable/off-screen geometry is clamped to the primary display and panel bounds. Invalid, oversized or unsupported preferences recover to defaults and log a warning. Appearance/layout are saved on normal exit; successful file operations also persist the directories immediately. Preferences do **not** save the ecosystem, selection, camera follow target or unsaved experiment drafts. Scroll offsets remain session-only. Deleting preferences restores the first-launch experience. `GENESIS_USER_DATA_DIR` optionally redirects this non-authoritative storage for isolated testing; it cannot point inside the packaged application folder.

The first launch opens the ecosystem with its compact bar and a **12-second dismissible guide** for pause, zoom, pan, Settings and selection. **Settings > Appearance > Show quick guide** reopens it; the controls reference remains in the same tab. Closing/hiding Settings never pauses or resizes the world. File pickers remain modal and their time is excluded from playback. Logs (`genesis.log`, three rotated backups, 1 MB each) record I/O errors and unexpected failures. Unexpected desktop exceptions show a readable Windows error with the log location when writable.

### Rebuild (Windows PowerShell)

Use **Windows Python 3.11 x64**. The script checks architecture/version, installs pinned build requirements, runs the full suite, builds a windowed PyInstaller onedir application, collects notices/metadata, and creates the ZIP atomically. The spec follows [PyInstaller's documented spec-file workflow](https://pyinstaller.org/en/stable/spec-files.html). Product metadata comes from `genesis.__version__`; save versions are independent. Builds are repeatable from these inputs, not claimed to be byte-for-byte reproducible or signed.

```powershell
Set-Location "C:\Users\Admin\Desktop\Coding Projects\Genesis"
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-Release.ps1
```

For an already prepared environment: `powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-Release.ps1 -SkipInstall`. `-SkipTests` is available for iterative packaging, but the delivered build ran the full suite. No activation, admin installation, network access at runtime, installer or upload step is required. The optional icon generator is `tools/create_icon.py`; normal builds use the included assets. Dependency notices are included in source, so normal builds do not fetch them.

### Checks and limitations

The reported baseline was verified: **136 tests passed in 94.663 seconds**. The final suite has **148 passing tests**, including malformed/oversized preferences, atomic-write failure, unavailable monitor geometry, Unicode paths, bundle-folder protection, destination retention, guide/model isolation and CSV picker behavior. Existing simulation, speed-equivalence, RNG and persistence tests still pass.

Native Windows scripted desktop checks exercised both **1380?900 and 960?720**, fullscreen restoration, playback controls, all Settings tabs, guide dismissal/reopening, Hide UI restoration, actual modal save/load and three CSV pickers, replacement confirmation, failed I/O, v1?v5 migration and exact continuation after v6 re-save. Separate process launches verified preference restoration. The extracted ZIP was tested from a **temporary folder containing spaces and ?**, outside this repository, with Python/venv variables removed and PATH limited to Windows. The frozen interpreter imported Pygame from its own `_internal` directory. The ordinary argument-free executable also started and closed through a Windows close event. Screenshots were inspected. These are **automated native desktop checks plus screenshot review, not manual pointer testing or an isolated-machine/VM certification**. The development machine still has Python installed; no clean-machine, varied-DPI, multi-monitor hardware or sustained endurance certification is claimed.

Matched short benchmarks at 300 organisms, predators/habitats/environment enabled, FX on, and History panel open showed packaged/source final-state hashes identical. Three alternating runs per build, 360 active frames per case at 1380?900: packaged total frame median **12.835 ms (1?)** / **16.968 ms (4?)**, versus source **13.211 / 17.614 ms**. Median-of-run p95 values were **17.597 / 19.221 ms** packaged and **18.388 / 20.581 ms** source. These small differences do not establish a performance improvement; 60 FPS at capacity is not guaranteed. See [DESKTOP_RELEASE.md](DESKTOP_RELEASE.md) for separate simulation/render timings and complete conditions.

To reproduce the extracted-build checks and matched short benchmarks (uses the retained `artifacts/environment-cap.json` fixture):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-Release.ps1
# Desktop functional checks only:
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-Release.ps1 -SkipBenchmark
```

The fixture can be regenerated with `.\.venv\Scripts\python.exe tools/benchmark_lineage.py --label release-fixture --environment` if artifacts were removed. Tests use isolated preference folders and retain their evidence under `artifacts/desktop-release-check`. World files are never automatically saved on exit. No ecosystem mechanics were added in this phase. Earlier phase sections below record historical validation results; the desktop paths and preference behavior described above supersede earlier session-only behavior.

## Install, test and launch (Windows PowerShell)

Requires Python 3.11 or newer, pip and a desktop display. Tested here with Python 3.11.2 and Pygame 2.6.1. Pygame is the only external dependency, pinned in `requirements.txt`. No activation or Tk installation is needed.

```powershell
Set-Location "C:\Users\Admin\Desktop\Coding Projects\Genesis"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m genesis
```

The existing workspace already has an installed `.venv`; use the last command to launch it. The default remains the original uniform, predator-disabled experiment. To start Patchwork with predators directly:

```powershell
.\.venv\Scripts\python.exe -m genesis --seed 7 --predators 8 --habitats --map-seed 7
.\.venv\Scripts\python.exe -m genesis --seed 2026 --population 100 --food-rate 20 --mutation-percent 6 --predators 8
.\.venv\Scripts\python.exe -m genesis --load ".\saves\my-world.json"
```

`--predators 0` enables the new mode without founding hunters; it does not spawn hunters later. Omitting `--habitats` preserves Phase 4 behavior and simulation random-number consumption, with or without predators. Omitting both options starts the original prey-only uniform world. `--map-seed` is independent of the organism seed and has no simulation effect when habitats are disabled. Loaded settings override startup settings and loaded worlds always open paused.

## Phase 9: Ecosystem Balance and Diagnostics

The Phase 8 investigation reproduced all six recorded outcomes exactly. All predator deaths were energy depletion; no hunting, catch-ordering, reproduction-accounting or environmental-food bug was demonstrated. Predators' high costs, capped feeding gains, pursuit pressures and population limits remain part of the model. **No survival rules, original defaults or trait bounds changed.**

The new opt-in **Coexistence** preset uses existing settings: **160 prey, 4 predators, 24 food/second, +/-0.5% mutation**, habitats, a **300-second seasonal cycle**, and **5-second droughts with 300–600-second gaps**. Choose **Settings > Experiment > Coexistence**, review its draft and confirm **Start new experiment**. No new advanced tuning parameters were needed.

**Coexistence is still unreliable across seeds.** The recipe retained both species for 30 simulated minutes on all three tuning seeds (101, 103, 107), then on **4/10 held-out seeds (1001–1010)**. The unchanged Changing Seasons recipe retained predators on **0/10** of those evaluation seeds. The literal Balanced default was also run on the same ten seeds for 30 minutes; it remains prey-only. The preset's visible reference world/map seed is **101**, an explicitly curated tuning example. It was not chosen from evaluation successes. A separate seed-42 check lost predators at 220.1 seconds; that failure is retained in the report. Finite-horizon coexistence is not a guarantee of long-term survival or stable cycles.

**Observatory > Diagnostics** provides:

- Species-level offspring births, deaths by energy/age/predation, catches and current average energy.
- Accepted feeding energy, energy lost to the cap, metabolic expense, reproduction cost and energy transferred to offspring.
- Eligible reproduction attempts blocked by the world/predator cap. These count repeated attempts per tick, not distinct lost births.
- Lifetime totals for new experiments and recent per-second rates over up to 60 simulation seconds, with the actual interval labeled. Catches per observed predator divides catches by founders plus offspring, including living individuals; it is not a hunting rate.

The default world view is unchanged. Observatory navigation uses two readable rows in the floating panel. Diagnostics never consume either RNG or influence decisions. Storage is bounded to **61 one-second snapshots**, fixed species totals and catch counts for at most 40 living predators; dead-predator catches are aggregated. **Worlds > Export diagnostics as CSV** writes the retained cumulative snapshots, an additional current row if needed, origin/legacy metadata and experiment settings. Existing statistics and lineage CSV exports remain available.

**Save format 6** preserves these ledgers and recent samples. Valid **v1–v5** saves still load and resume their existing trajectories; diagnostics begin at the load tick and explicitly mark earlier measurements unknown. Version 5 environmental state is retained. Validation checks diagnostic schemas, counters, energy balances, predator IDs and sample timing before replacing a world. Save/load remains atomic/paused, respectively.

Baseline: **122 tests passed**. The expanded suite contains **136 passing tests**, including accounting, bounded samples, cap deferrals, exact Phase 8 physical/RNG equivalence, speed equivalence, v1–v5 migration, new-save continuation, invalid state, CSV, preset defaults and UI isolation. Native scripted glass, environment, lineage and diagnostics checks passed at **1380×900 and 960×720**; screenshots were reviewed. These were automated desktop checks and screenshot inspection, not manual pointer testing.

[BALANCE_REPORT.md](BALANCE_REPORT.md) contains the investigation, all tuning/evaluation outcomes, extinction times, population ranges, cap frequency, energy measurements, matched performance measurements and limitations. Headless 30-minute trials are not sustained rendering benchmarks.

The matched 300-organism, 1380×900, 4× workload with effects and the History panel enabled measured **17.89 ms median / 20.18 ms p95** total frame time after diagnostics, versus **17.51 / 19.41 ms** before. Physical-state/RNG/history fingerprints matched. These were short 240-frame runs; sustained 60 FPS is not guaranteed.

Launch the reference preset directly, with all settings explicit:

```powershell
Set-Location "C:\Users\Admin\Desktop\Coding Projects\Genesis"
.\.venv\Scripts\python.exe -m genesis --seed 101 --map-seed 101 --population 160 --predators 4 --food-rate 24 --mutation-percent 0.5 --habitats --seasons --season-length 300 --droughts --drought-duration 5 --drought-interval 300
```

Repeat the checks with `tools\check_balance.py --stage baseline`, `--stage evaluate`, or `--stage preset --workers 1`; `tools\check_diagnostics_ui.py` checks the new desktop controls. Run headless trials separately from rendering benchmarks. The `tune`, `moderate`, and `reproduce` stages retain the investigation recipes and original Phase 8 comparisons.

## Phase 8: Environmental Events

Seasons and droughts are **off by default**. In **Settings > Experiment > Environment**, enable either switch to reveal its settings. Drafts apply only when starting a new experiment, after confirmation. Turning a switch off preserves its hidden draft; starting with it off applies the inactive defaults. The **Changing Seasons** preset combines 100 prey, 8 predators, habitats, 20 base food/second and 6% mutation with both environmental features enabled. These pressures do not promise coexistence or adaptation.

| Setting | Default | Allowed whole seconds |
| --- | --- | --- |
| Full seasonal cycle | 120 | 40–600 |
| Drought duration | 15 | 5–60 |
| Minimum drought gap | 90 | 30–300 |

At fixed simulation ticks, the seasonal multiplier is `1 + 0.5*sin(2*pi*cycle_position/cycle_length)`, smoothly ranging from **0.5 to 1.5**. Spring, Summer, Autumn and Winter label the four cycle quarters. Drought multiplies regeneration by **0.25** for its configured duration. Each gap is an inclusive uniform integer-tick draw between the minimum gap and twice that gap, measured from initialization or the previous drought's end. Droughts never overlap. A private RNG seeded with `experiment_seed XOR 0xE17A5EED` schedules them; it never draws from organism randomness.

Food regeneration uses **base rate × seasonal factor × drought factor × habitat food multiplier**. Environmental factors combine to **0.125–1.5**; open water/dense food multipliers remain 1 and gardens remain 2, so local factors range from 0.125 to 3. Existing area-weighted spawning, fractional food credit and the 650-food cap remain. The environment advances to the tick's end before that tick's food regeneration. Events never directly kill, mutate, reproduce or respawn organisms, or change movement/energy rules. Pause and complete extinction stop the simulation and environmental clock. Disabled mode preserves the previous simulation trajectory and RNG consumption.

**Observatory > Events** shows factors, cycle position, next transition, drought timing and a paginated log. It retains the latest **256 events**, evicting the oldest and reporting dropped entries; pages show up to 12. Population graphs mark retained seasonal transitions in cyan, drought starts in gold and ends in pale gold. Markers use simulation time and appear once the sampled graph includes that time. Population changes alone do not establish adaptation or environmental causation.

An optional glass status chip shows current conditions and opens Events. **Appearance > Environment status chip** hides it; Hide UI also hides it. Subtle background illumination responds to conditions only when effects and the habitat overlay are on. It is cached separately from simulation, preserves organism visibility, and respects Reduce Transparency for glass surfaces. One additional tinted background surface is retained; no full-screen tint pass is required when its color/background is unchanged.

Statistics CSV now includes environmental settings, derived environment seed, fixed multiplier bounds and each sample's seasonal, drought and combined factors. **Save format 5** stores configuration, tick/cycle position, schedules, bounded event history and environment RNG state. Valid **v1–v4** saves load with events disabled; v4 lineage records remain intact. Invalid environmental records are rejected before replacing the active world. Exact continuation through future transitions is tested.

### Phase 8 checks and observations

Baseline: **107 tests passed in 59.981 seconds**. Final: **122 tests passed in 79.068 seconds**. Added coverage includes smooth cycle boundaries, duration/gap bounds, combined food factors, event pruning, settings, independent RNG, disabled equivalence against frozen Phase 7 code, speed equivalence, genuine old saves, malformed state, exact continuation, CSV and UI isolation.

Native scripted desktop checks passed at **1380×900 and 960×720**, covering conditional settings, chip, Events/history/graphs, effects/transparency, save/load and CSV. Existing glass and lineage checks also passed, including fullscreen/hidden-control restoration, file pickers, confirmations and relative browsing. Screenshots were inspected at both sizes. These were automated desktop interactions and visual screenshot review, not manual pointer testing. A 120-frame CLI launch with predators, habitats, seasons and droughts also completed.

Six seeded trials ran to 600 simulation seconds or complete extinction. At base food 20, seed 42 became completely extinct at 243.77 seconds; seeds 7 and 2026 ended with 179 and 206 prey and no predators. At base food 2, the three seeds ended with 22, 19 and 26 prey and no predators. No outcome was scripted. [ENVIRONMENT_REPORT.md](ENVIRONMENT_REPORT.md) contains settings, occupancy, extinction times and matched benchmark results. Short benchmarks do not establish sustained 60 FPS; the final 1380×900, 4× environment-enabled case measured **17.98 ms median / 20.09 ms p95 total frame time** at 300 organisms.

```powershell
.\.venv\Scripts\python.exe -m genesis --predators 8 --habitats --seasons --droughts
.\.venv\Scripts\python.exe tools\check_environment_ui.py
.\.venv\Scripts\python.exe tools\check_environment_trials.py
.\.venv\Scripts\python.exe tools\benchmark_lineage.py --label local-environment --environment
```

Optional CLI settings are `--season-length 120`, `--drought-duration 15` and `--drought-interval 90`. Omitting `--seasons` and `--droughts` keeps both disabled. Loading a world uses its stored environmental settings.

## UI refinement and Phase 7

The refined glass UI uses slightly larger, higher-contrast text, softer corners, curved highlights and stronger local frost. Playback speeds share one segmented selector. Predators and Habitats use keyboard-accessible **Off / On switches**. Starting predator count appears only when enabled; map seed appears only when habitats are enabled. Switching off preserves the hidden draft, and switching back on restores it. Starting with predators off applies zero predators; habitats off applies uniform water and inactive map seed 42. Hidden drafts are validated only when enabled. Defaults, presets, starting and loading replace the draft form.

**Select a cell > Details > Lineage** opens the recorded family inside the optional floating panel. The default world view stays uncluttered. The lineage record shows stable ID, species, parent ID, generation, birth simulation time, inherited traits, and death time/cause when recorded. Founders are recorded at time zero; births and deaths during a tick are timestamped at the tick's end. Death causes are energy depletion, maximum age or caught; energy takes precedence if both survival limits occur on one tick. Birth snapshots and traits are immutable; lifecycle updates replace only death fields. Recording and browsing never use simulation randomness or influence behavior.

The ancestry chain starts with the viewed organism and follows actual parent IDs. The direct offspring list includes its retained children. Each list shows at most five rows, with its own wheel scrolling and **Earlier / Later** controls inside the panel's outer scroll area. Clicking a relative changes only the viewed record. **Select living relative** changes world selection; **Follow relative** selects and follows it using the existing camera. Dead and unavailable records disable these actions. **View selected cell** returns to the current world selection. Known child/parent birth traits show signed changes in speed, sensing radius and body size; missing birth information is explicitly unavailable.

The viewed record survives death and deselection; reset or successful load clears it. The archive retains at most **4,096 records**, keeping all living organisms and pruning the oldest dead organism IDs first. IDs increase monotonically. Ancestry can end at an unavailable parent; offspring lists may be incomplete. The UI reports pruned and legacy-unavailable counts and never reconstructs missing relatives. List rendering and the Details content surface stay bounded independently of archive size.

**Save format 4** includes this archive and still accepts valid v1/v2/v3 saves. Older saves create records only for available living organisms using their actual IDs, parent IDs, generation, species and current traits. These are labeled **legacy snapshots** at the load simulation time. Birth times, birth-trait comparisons and absent earlier ancestry remain unknown, even for surviving founders. New births/deaths are recorded normally; a new child of a legacy parent still has no parent birth-trait comparison. Version 4 validates archive capacity/accounting, ordered unique IDs, parent ordering, retained parent species/generation/time relationships, lifecycle ordering, living-state agreement and explicit legacy unknowns before replacing a world.

**Worlds > Export lineage archive as CSV** creates a separate, uniquely named file in `exports`. Rows include experiment seed/settings, IDs/relationships, generation, birth time, record origin and observation time, recorded traits, death details, living/dead status, parent-record availability, whether birth traits are known, signed changes when available, and archive limits/pruning counts. Unknown values are blank. The panel shows the absolute saved path or an error. This contains retained records, not a complete historical family tree.

### Earlier Phase 7 validation and measurements

Baseline verified: **93 tests passed**. Final suite: **107 tests passed in 61.683 seconds**. Coverage includes switches, retained drafts, keyboard navigation, scrolling/input isolation, immutable records, parent/child relationships, trait changes, death, pruning, archived browsing, CSV, genuine v1/v2/v3 fixtures, v4 continuation, seeded RNG isolation and speed equivalence. All existing ecosystem, camera, habitat, observatory and persistence checks remain.

The refinement milestone was rendered and inspected at 1380x900 and 960x720 before lineage implementation. Native scripted checks and screenshot review then covered lineage records/lists, living/dead/unavailable/legacy states, selection/follow, death/reset/load lifecycle and exports at both sizes. The existing native glass checks were rerun, including all tabs, dragging/resizing/minimizing, fullscreen restoration, hidden controls, actual Pygame file picker and replacement confirmations. These are programmatic desktop checks plus screenshot inspection, not manual pointer testing.

[LINEAGE_BENCHMARKS.md](LINEAGE_BENCHMARKS.md) reports matched active-world before/after timings: same 300-organism fixture, predators/habitats and effects enabled, History panel open, two resolutions and 1x/4x. All physical-state/history/RNG hashes match before and after. No performance improvement or sustained 60 FPS is claimed. The 4x workload exceeds 16.67 ms in several cases. Historical measurements below describe earlier implementations.

```powershell
.\.venv\Scripts\python.exe tools\check_refined_ui.py
.\.venv\Scripts\python.exe tools\check_lineage_ui.py
.\.venv\Scripts\python.exe tools\check_glass_ui.py
.\.venv\Scripts\python.exe tools\benchmark_lineage.py --label local
```

## Interface and controls

The ecosystem occupies the full viewport, with aspect-ratio letterboxing when needed. The only persistent default UI is a compact bottom glass bar: **Pause / Play, 1x / 2x / 4x, Settings**. Opening Settings never resizes the world or pauses playback. The first-launch guide appears for 12 seconds, can be dismissed, and can be reopened from Appearance. It does not repeat after restarting an experiment.

Settings is a floating panel with four tabs:

- **Experiment:** conditional numeric drafts, Predators/Habitats and Seasons/Droughts switches, Defaults, New seed draft, Start new, Restart same seed, and all eight presets with settings/descriptions. Scroll for presets and messages.
- **Observatory:** Overview (live statistics and full organism inspector), History (species population/trait graphs), Traits (founder comparisons and distributions), Habitats (map/occupancy), Events (environment timing/history), and Diagnostics (species ledgers/recent rates). Overview is labeled Details when an organism is selected.
- **Worlds:** Save World, Load World, history CSV, lineage CSV and diagnostics CSV, with scrollable success/error messages.
- **Appearance:** effects, habitat illumination and legend, Reduce Transparency, fullscreen, Hide UI, Fit World, Follow, and the interaction shortcuts.

Drag the panel header to move it; drag the bottom-right corner to resize it. The panel stays inside the window, with a minimum size of 400x360. Scroll the content with the wheel, drag its scrollbar, or use Page Up / Page Down. The top tabs and window controls remain fixed. The minus button minimizes to a small right-edge Settings tab; the x closes the panel. Reopening preserves the active view, scroll position and panel geometry for the session, subject to window bounds. Phase 10 also persists the active tab, geometry and presentation preferences across launches; scroll positions remain session-only.

Selecting a cell shows a **small glass card** with type, energy, age and generation without opening Settings. Details opens its full inspector; Deselect closes the card. Death, restart and load update selection safely. A white ring and faint sensing overlay identify the selected cell; its label remains available with the UI hidden.

| Action | Control |
| --- | --- |
| Pause / play | Space or bottom playback button |
| Playback speed | 1, 2, 4 or bottom segmented control |
| Open / close Settings | Settings button or O |
| Restart applied settings and seed | Experiment > Restart same seed, or R; confirmation required |
| Prepare a different seed | Experiment > New seed draft; Start new asks before applying |
| Select organism | Left click its displayed position |
| Deselect | Card > Deselect, or Esc when no panel/modal/fullscreen needs closing |
| Zoom at cursor | Mouse wheel outside UI surfaces |
| Pan / stop following | Right-button or middle-button drag outside UI |
| Fit world / stop following | Home, or Appearance > Fit World |
| Follow / unfollow selected | F, inspector Follow, or Appearance > Follow |
| Fullscreen / window | F11, or Appearance > Fullscreen / Windowed |
| Hide / restore UI | I; Appearance > Hide interface; Restore UI button or Esc |
| Habitat illumination | H, or Appearance > Habitat overlay; visual only |
| Visual effects | E, or Appearance > Effects; preference survives reset/load |
| Save / load | Ctrl+S / Ctrl+L, or Worlds; load confirmation required |
| CSV export | Worlds > Export retained history as CSV |
| Lineage export | Worlds > Export lineage archive as CSV |
| Recorded relatives | Card > Details > Lineage; click a relative to inspect |
| Navigate UI controls | Tab / Shift+Tab, then Enter or Space; focused controls have a light outline |
| Exit | Close the application window |

UI clicks, scrolling and dragging never select cells or pan/zoom behind the panel, card, playback bar or minimized tab. World interaction remains available outside these surfaces. Escape cancels confirmation, ends field editing, closes Settings, restores hidden UI, exits fullscreen, or clears selection, in that order as applicable. Confirmation initially focuses **Cancel**. The world continues while confirmation is shown; input is modal until a choice is made.

**Restart, Start new and desktop Load ask before replacing the current world/history.** Loading validates the candidate first; malformed files never replace the experiment. Cancel leaves the world running as it was. Accepted loads open paused. The explicit `--load` startup command opens the chosen checkpoint directly, paused. The existing file picker separately confirms overwriting an existing save and explicitly suspends simulation playback while choosing a path.

Experiment fields are drafts. Click a field to replace its value; Tab/Shift+Tab visits visible controls and skips hidden fields, Ctrl+A selects text, Backspace edits, and Enter/Escape ends editing. Space/Enter activates a focused switch without pausing. Playback shortcuts are suppressed while typing. Defaults and presets only fill drafts. New seed uses independent system randomness; Restart replays the applied seed. Habitat drafts never modify an active map. Invalid effective settings leave the world intact.

### Glass and camera

Local surface crops are downsampled by 18 and smoothly enlarged to approximate a frosted backdrop, then navy-tinted with soft corners, restrained shadows, interior sheen and curved highlights. Only visible glass regions are sampled; there is no per-frame fullscreen blur. Up to eight role-based surface cache entries are retained, refreshed at most ten times per second unless their geometry changes. **Reduce Transparency** uses more opaque, reusable surfaces without backdrop sampling. Text remains high contrast. Panel scrolling hints appear briefly on first opening; hovering the header/corner briefly shows move/resize hints. Transitions are immediate; the desktop guide is brief and dismissible without decorative animation.

On first launch the app starts at 1380x900 (clamped to the display) and supports a 960x720 minimum; later launches restore the saved window settings. Zoom ranges from Fit World to 6x fit, additionally capped at eight pixels per world unit. World bounds take precedence over exact cursor anchoring at edges. Follow uses rendering time and may finish settling while paused. Manual pan and Fit stop following. A followed death/catch shows a brief notice. Restart and successful load clear follow and fit the world; valid loaded selection is retained.

Fullscreen uses a borderless primary-desktop-sized window without changing monitor resolution. F11 restores window size and position. Hide UI is separate; the Restore UI button remains visible. Camera, panel layout, transparency, resizing and effects never change simulation coordinates or RNG state. Every elapsed playback tick is processed; none are silently discarded for frame rate. Camera and UI state are excluded from saved simulation state.

| Setting | Default | Limits |
| --- | --- | --- |
| Seed | 42 | Integer 0-4,294,967,295 |
| Starting prey | 100 | Integer 1-300 |
| Food regenerated per simulation second | 20 | Finite number 0-80 |
| Mutation strength | +/-6% | Finite percent 0-20 |
| Predator mode | Off | Off / On switch |
| Starting predators | 0 | Integer 0-40 when enabled; applied count is zero when off |
| Habitat mode | Off (uniform) | Off / On (patchwork) switch |
| Map seed | 42 | Integer 0-4,294,967,295; independent map generator |

Combined starting and living populations cannot exceed 300. The living predator cap is 40. No organism type respawns automatically. If one species disappears, surviving organisms continue normally and graphs show zero population and undefined trait means for the extinct species. Full extinction stops simulation time and presents a reset option. Export and save/load remain available.

## Presets

Choose an Experiment preset to fill its drafts, edit if desired, then Start new. Recipes use seed 42 and 100 starting prey except Coexistence, which uses the documented reference seed/map seed 101 and 160 prey. All start with 420 food particles. Both experiment seed and map seed are independent of recipe classification; other edits may produce Custom.

| Preset | Food / second | Mutation | Predator mode / starting count |
| --- | --- | --- | --- |
| Balanced | 20 | +/-6% | Off / 0 |
| Abundance | 40 | +/-6% | Off / 0 |
| Scarcity | 6 | +/-6% | Off / 0 |
| Rapid Mutation | 20 | +/-18% | Off / 0 |
| Predator-Prey | 20 | +/-6% | On / 8 |
| Patchwork Ecosystem | 20 base rate | +/-6% | On / 8; habitats enabled, map seed 42 |
| Changing Seasons | 20 base rate | +/-6% | On / 8; habitats, 120s cycle, 15s droughts, 90–180s gaps |
| Coexistence | 24 base rate | +/-0.5% | On / 4; habitats, 300s cycle, 5s droughts, 300–600s gaps; reference seed 101 |

Patchwork, Changing Seasons and Coexistence use habitats; the others use uniform worlds. Only Changing Seasons and Coexistence enable environmental events. Presets configure starting conditions, never survival outcomes. Descriptions and settings appear on each preset card.

## Living habitats

Patchwork maps contain three broad, connected, traversable regions. Two seeded, gently meandering boundaries divide a **55x38 grid** into bands; seeded ordering changes which habitat occupies each band. Each tile spans 20x20 world units in the 1100x760 world. Each region spans the map height and adjacent rows overlap, avoiding isolated islands. There are no obstacles, blocked tiles or pathfinding. Uniform mode uses one open-water tile.

| Region | Local food regeneration multiplier | Movement multiplier, both species |
| --- | --- | --- |
| Open water | 1.0 | 1.0 |
| Gardens | 2.0 | 1.0 |
| Dense regions | 1.0 | 0.6 |

These fixed, validated multipliers are bounded to food **1-2** and movement **0.6-1**; they are not editable in this phase. Effects use organism/food world coordinates, never window pixels. The start-of-tick habitat determines movement for that whole tick; crossing a boundary changes the multiplier on the next tick. Every boundary is traversable and world walls retain their original reflection behavior.

The food-rate setting is a **uniform-equivalent base rate**. Patchwork regeneration is `base_rate * area_weighted_mean(food_multiplier)`. New food is sampled from tiles in proportion to tile area times food multiplier, then uniformly within the chosen tile. Gardens therefore receive twice the expected food per unit area per second as water or dense regions, not a guaranteed number every tick. The global 650-food cap still applies. Initial food remains 420 particles, using the same regional density weighting in habitat mode. Uniform mode retains exactly its old two-coordinate RNG draws and regeneration arithmetic.

Dense movement uses `actual_speed = inherited_speed * 0.6`. Its locomotion cost is calculated from actual speed with inverse-square resistance: `0.52 * (actual_speed/40)^2 * (size/5) / movement_multiplier^2`. This models **constant propulsion effort**: slowing through resistance costs the same energy per second (and more per unit distance), without a free energy discount. Basal, body and sensing costs remain time-based; predators retain their 2.5 cost factor. Tiny floating-point discounts are explicitly prevented. There is no new survival, reproduction or targeting rule.

The map generator uses its own `random.Random(map_seed)`, without drawing from the simulation RNG. Maps are immutable within an experiment. Choose Experiment > Patchwork Ecosystem to preview editable settings before Start new; edit Map seed to try another reproducible layout. Restart repeats both applied seeds. New seed changes only the organism/world seed. Observatory > Habitats shows the active map, its seed, and **current occupancy**: prey, predators and food in each region. These are location counts, not evidence that organisms have adapted to a location; resource supply, region area and movement all influence occupancy.

Gardens have subtle emerald/cyan illumination; dense water has violet clouds. Smoothly blended boundaries are decorative around the authoritative tile boundaries. Backgrounds and the map thumbnail are cached by map identity and viewport size. Cloud geometry is static and deterministic, with no RNG calls. Golden food and luminous organisms remain in the foreground. **H / Appearance > Habitat overlay hides illumination only**, retaining all rules and occupancy counts; a small legend identifies the colors. Effects and habitat overlay have separate toggles.

## Ecosystem rules

The bounded 1100x760 world uses a fixed 1/30-second tick and a private seeded `random.Random`. Organisms reflect off walls. Food renews up to 650 particles. Prey sense the nearest food within their inherited sensing radius and consume it within body radius plus 3 units; a food particle is eaten once. Without a target, organisms use seeded wandering turns.

Prey founder traits are uniformly sampled from speed 28-52, sense 60-120 and size 4-6.5. Predator founders use speed 50-65, sense 100-150 and size 5.5-8. Both species and all descendants obey the same trait bounds: speed 18-75, sensing radius 35-160, body radius 3-9.

In predator mode, perception uses positions captured at the start of the tick, with distance and then ID breaking target ties. Predators pursue sensed prey. Prey flee sensed predators with an escape vector plus a 15% food-direction contribution when food is visible. Steering is limited to 4 radians/second. Animals continue moving at their inherited speed, with no hidden pursuit or escape speed bonus.

After movement and prey eating, catches are resolved in ascending predator ID order. Each predator can catch at most one prey per tick, choosing the nearest overlapping body, then the lowest prey ID. A caught prey is removed immediately and cannot be caught again or reproduce. Contact uses the sum of physical body radii, independently of visual halos. Predators gain **65% of the victim's remaining energy**, capped at 180; excess energy and digestion loss are discarded. Catches count as deaths and emit one presentation event.

All founders start with 85 energy; food gives prey 27 energy, capped at 180. Base energy consumed per simulation second is:

```text
0.48 + 0.52*(speed/40)^2*(size/5) + 0.34*(size/5)^2 + 0.30*(sense/90)^2
```

Predators pay **2.5 times** this cost and cannot eat food. Both species die at depleted energy or age 180 seconds, checked before movement/feeding. Reproduction requires 145 energy, age at least 8 seconds and no cooldown. The parent transfers 65 energy to its child, spends 6 more, and both get a 12-second cooldown. Species is inherited unchanged. Each trait is independently multiplied by `1 + uniform(-strength, strength)` and clamped to its bounds. No birth creates energy. At a population cap, reproduction is deferred without energy expenditure or mutation RNG calls.

In predator mode, surviving parents reproduce after catches; newborns first act next tick. In disabled mode, the Phase 3 operation order and RNG calls are preserved exactly, including its within-organism reproduction order. Total births exclude founders; deaths include catches. Food is the only external energy source after initialization.

## Observatory and CSV

- **History:** separate cyan prey and pink predator population curves and separate species averages for speed, sensing and size. The live header reports both populations and total catches. Curve values are from the latest sampled tick; the header is current. X axes use simulation seconds; trait Y axes adapt to both species' retained data. Population uses a fixed 0-300 scale.
- **Traits (evolution comparison):** switch between prey and predator founder/current trait comparisons and ten-bin trait distributions. Highest living generation is the maximum across the whole ecosystem. Empty groups have undefined averages shown as dashes and empty histograms.
- **Habitats:** live regional occupancy, active map thumbnail, map seed and bounded multipliers. Counts are explicitly labeled as occupancy, not adaptation.
- **Experiment:** conditional draft settings, switches and presets (a separate top-level tab).
- **Worlds:** persistence and CSV export (a separate top-level tab).
- **Overview / Details:** ecosystem summary, selected organism and Lineage Explorer. Its summary trait averages cover all living organisms; use History/Traits for separate species averages.

History samples tick 0 and every 30 ticks (one simulation second), independently of rendering and playback speed. A final full-extinction sample captures the exact terminal tick between intervals. Species-specific extinction appears in the next regular sample and immediately in live counts. Storage is capped at 3,601 rows; evicted rows are counted. Founder comparisons remain independently retained. Graphs are cached between samples, with bounded storage.

Worlds > Export writes retained rows to `exports`, using a unique filename without overwriting existing files. The panel displays the saved absolute path or a readable error; scroll long Worlds messages at small window sizes. CSV includes simulation tick/time, population, births, deaths, food, catches, each species' population and average traits, aggregate averages and highest living generation. CSV also includes nine regional occupancy columns (`open_water`, `garden`, `dense` times `prey`, `predator`, `food`). Metadata includes the seed, map seed, habitat mode, food/movement multipliers, every configuration value (including predator settings and costs), application version, sampling interval, capacity, dropped rows and founder averages. Undefined means export as blanks. CSV is an analysis export, not a resumable world.

## Persistent worlds

Saves use UTF-8 JSON `format: "genesis-world"`, **version 6** with bounded lineage, environmental and diagnostic archives. Valid **versions 1–5** remain accepted; their diagnostics begin at load with earlier measurements marked unknown. Versions 1–4 load with events disabled, while version 5 retains its environmental state. Versions 1–3 receive explicit legacy lineage snapshots; versions 4 and 5 preserve their archives. Versions 1 and 2 load as uniform worlds, preserving previous trajectories and predator settings. Unknown versions are rejected. The authoritative habitat grid, dimensions, region values and multiplier arrays remain stored. Loading uses the stored map rather than regenerating it from the seed. Validation rejects mismatched dimensions, incorrect grid lengths, unknown/non-integer region values, unsupported/non-finite multipliers, mode/map mismatches and inconsistent regional counts before replacing the world.

- Organisms, traits, energy, age, lineage, positions, headings, reproduction cooldowns and wander state.
- Food and ordered entity IDs, tick count, births/deaths/catches, next IDs and fractional food credit.
- Applied settings, preset label, full rules and complete simulation RNG state as JSON arrays (never pickle).
- Playback speed and partial-tick accumulator, retained statistics, sampling phase and founder comparisons.
- Selected organism ID, restored if present.
- Retained birth/lifecycle records, archive capacity, pruned count and legacy-unavailable count. The viewed relative in the UI is not saved.
- Environmental configuration, cycle position, scheduled transitions, retained event records/accounting and separate RNG state. Validation checks schemas, bounds, event order, timing, factors and agreement with the world clock and sampled statistics.

Loads validate into a separate candidate before replacing the active world and always open paused. Cancel, malformed input and failed validation preserve the current experiment. Rendering effects, trails, sprite caches and interpolation snapshots are not simulation state and start clean. FX preference remains unchanged.

Validation checks exact schemas, finite ranges, population accounting, IDs, species/lineage, RNG shape and history consistency; duplicate keys and files above **16 MiB** are rejected. Saves use a temporary file in the destination directory, flush and `fsync`, then atomic `os.replace`; failed writes preserve an existing save and attempt temporary-file cleanup. Saving does not consume simulation randomness.

The built-in Pygame file picker supports folder navigation, scrolling, folder/filename fields and full paths. Enter accepts, Escape cancels, and replacing an existing file requires a second confirmation. Ctrl+A selects field text. Picker time is discarded rather than accumulated as simulation catch-up. Long Worlds and Experiment messages can be scrolled. Listings are bounded to 2,000 entries, but exact paths may be typed.

Exact continuation is tested on the same Python runtime and simulation code. Cross-platform or future runtime floating-point identity is not guaranteed. Atomic replacement is not an autosave or backup system.

## Neon Microcosm

Rounded prey retain saturated cores, translucent bodies and soft halos against midnight blue. Predator bodies are luminous triangles, using warm pink-to-violet hues. Both palettes use the same stable inherited speed bands: below 33, 33-39, 39-45, 45-51 and at least 51 units/s. Prey bands are cyan, lime, orange, pink and violet; predator bands progress coral through pink to violet. Golden four-point food sparkles remain distinct.

Real movement creates short fading trails. Eating produces gold ripples, births flashes, deaths gentle particles and catches short angular ripples. FX toggling, rendering and deterministic effect geometry never consume simulation RNG or alter organisms. Cells pulse subtly with presentation time. Caches are bounded to 96 sprites per organism shape, 16 food sprites, ten trail points per living organism and 256 effects. Overloaded effects evict older entries. Zoom draws cells at their display radius (larger radii quantized to two pixels), rather than magnifying small cell bitmaps. Backgrounds crop before scaling and retain one viewport-sized camera image; trails, particles, halos, food and bodies share the camera transform. Selection rings and UI text retain readable screen-space sizes.

Movement and heading interpolate between fixed ticks, with at most one tick of visual latency. Pause freezes presentation; new births appear at their spawn position; deaths/catches remove obsolete poses; reset/load clear old effects. FX off keeps smooth movement, shape, trait colors and selection.

## Earlier floating glass UI validation

Baseline: **87 tests passed** before UI changes. **93 final tests passed.** The suite covers the relocated controls, scroll clipping, panel movement/resizing/minimization, card lifecycle, input isolation, draft validation, confirmations, CSV/save/load, keyboard focus, transparency caches, seeded presentation isolation, and existing simulation/persistence regressions. Native Windows checks exercise 1380x900 and 960x720 layouts, all relocated features, fullscreen restoration and the actual Pygame file picker. Closed/open, selected-cell, scrolled and confirmation screenshots were reviewed. These are programmatic desktop checks and screenshot review, not manual pointer testing.

[GLASS_BENCHMARKS.md](GLASS_BENCHMARKS.md) records separate glass and complete rendering costs with the panel open/closed and transparency reduced/on. These short frozen-world measurements do not establish sustained gameplay FPS or population-cap performance for this redesign. Simulation rules and save format 3 remained unchanged in that milestone; Phase 7 introduced version 4; Phase 8 introduced version 5; Phase 9 now uses version 6.

```powershell
.\.venv\Scripts\python.exe tools\check_glass_ui.py
.\.venv\Scripts\python.exe tools\check_glass_ui.py --benchmark
```

The frost is a software approximation rather than an operating-system glass effect. Phase 10 persists geometry/transparency preferences across launches. The file picker remains modal. Fullscreen glass performance and long-duration stability were not measured.

## Earlier Phase 6 validation and measured performance

Baseline inspection and tests completed before changes: **75 passed**. Phase 6 finished with **87 tests**, covering camera coordinate round trips and zoom anchoring, bounds/resizing, selection, follow/death/pause/reset/load, hidden controls/fullscreen, clipping, cache bounds, presentation/RNG isolation and processing a long frame without dropping ticks. Existing save migrations, exact continuation and 1x/2x/4x equivalence remain covered. Query optimizations are compared against the previous methods across six seeded uniform/habitat trajectories and contact-boundary/tie cases.

Native Windows desktop checks exercise all tabs, camera controls and follow at **1380x900 and 960x720**, plus **3440x1440 borderless fullscreen**, restoring the original window size/position, hidden UI restoration, retained shortcuts and save/load/death lifecycle. Screenshot review checks readability, selected-cell HUD and zoomed neon cells. These are automated desktop checks and screenshot inspection, not manual pointer testing.

On this i5-13600K development machine, the naturally evolved 300-organism habitat/predator checkpoint costs about **3.5 ms per simulation tick** and **8.1 ms to render** at 1380x900 with FX. Continuous 4x workload with FX measured **16.92 ms median / 21.74 ms p95 per frame**; steady 60 FPS near capacity is not guaranteed. No simulation ticks are dropped. FX off lowers that workload to **12.95 / 16.40 ms**. All eight continuous-case saved-state hashes match their pre-optimization results. See [BENCHMARKS.md](BENCHMARKS.md) for hardware, methods, sample counts, duration, separate simulation/render timings at both sizes, FX comparisons and limitations. Performance at fullscreen resolution and long-duration stability were not measured.

```powershell
.\.venv\Scripts\python.exe tools\check_explore_ui.py
.\.venv\Scripts\python.exe tools\benchmark_explore.py --label final
```

That milestone retained save format **version 3**, accepting valid v1/v2 worlds through its migrations. No habitat, feeding, mutation or survival rule changed. New spatial indexing only removes impossible contact candidates; exact interaction order and tie-breaking are preserved.

## Earlier Phase 5 validation and observed habitats

Baseline before Phase 5: **63 tests passed**. Phase 5 finished with **75 tests**. Its coverage includes reproducible and connected maps, independent map randomness, unchanged Phase 4 uniform trajectories/RNG (predators both off and on), regional food density and rate/cap, both species' movement and energy costs, traversable boundaries, occupancy/CSV totals, settings validation, genuine v1/v2 migrations, invalid maps, authoritative-map restoration, exact future continuation and 1x/2x/4x equivalence. UI tests check immutable drafts, overlay/cache/resize isolation, rejected loads and long-message scrolling. Existing survival, predation, inheritance, history, effects and atomic-write-failure tests remain.

Additional reproducible checks:

```powershell
.\.venv\Scripts\python.exe tools\check_habitats.py
.\.venv\Scripts\python.exe -m genesis --seed 7 --predators 8 --habitats --map-seed 7 --frames 180 --screenshot artifacts\phase5-launch.png
```

The habitat trials ran **300 simulation seconds** with 100 starting prey, 8 predators, 20 base food/second, +/-6% mutation, and map seed equal to the experiment seed. Population, energy, boundary, food-cap and occupancy invariants were checked. All three retained both species through the endpoint:

| World / map seed | Prey | Predators | Catches | Open-water occupancy P/H/F | Garden occupancy P/H/F | Dense occupancy P/H/F |
| --- | --- | --- | --- | --- | --- | --- |
| 42 / 42 | 219 | 2 | 796 | 59 / 1 / 8 | 90 / 1 / 12 | 70 / 0 / 13 |
| 7 / 7 | 68 | 24 | 1113 | 10 / 6 / 62 | 35 / 15 / 40 | 23 / 3 / 56 |
| 2026 / 2026 | 296 | 4 | 717 | 86 / 0 / 5 | 126 / 1 / 6 | 84 / 3 / 7 |

P/H/F means prey / hunters (predators) / food, counted at the endpoint. Seed 2026 reached the combined cap of 300. More organisms in gardens does not establish adaptation; the habitats differ in area, food availability and movement. Three finite trials do not demonstrate stable cycles or guarantee long-term coexistence. Full minute samples, map area counts and settings are recorded in `artifacts/habitat-trials.json`.

The real **Windows SDL display** check exercised presets/drafts, map overlay via button and H, all six tabs, invalid map seed, CSV, the actual Pygame save/load picker, exact paused restoration and rejection of a corrupt map. It checked 1380x900 and 960x720 layouts. Screenshots of both sizes were visually reviewed, including habitat lighting, graphs, occupancy, settings, presets, inspector and messages. This is programmatic desktop interaction and screenshot review, not manual pointer testing.

Measured locally with FX and habitat illumination enabled, 30 warmup frames then 240 **uncapped update/draw frames** per case, using a fixed 1/60-second input per frame and fresh Patchwork founders:

| Window | Playback | Measured uncapped FPS | Median frame ms | 95th percentile ms | Ending population |
| --- | --- | --- | --- | --- | --- |
| 1380x900 | 1x | 172.3 | 5.79 | 8.12 | 97 |
| 1380x900 | 4x | 117.9 | 8.40 | 11.23 | 129 |
| 960x720 | 1x | 255.5 | 4.02 | 5.29 | 97 |
| 960x720 | 4x | 145.3 | 6.94 | 8.78 | 129 |

These short development-machine measurements include drawing, display flip and simulation steps. They are not a benchmark at the population cap, a long-duration stability test or a hardware-independent guarantee. The normal app still caps rendering at 60 FPS. Background creation/resizing is excluded by warmup; map changes and synchronous save/load may briefly interrupt rendering. Raw results are in `artifacts/habitat-performance.json`.

## Scope and files

This is a simple asexual evolutionary model, not a validated biological simulation. Bodies can overlap; contact triggers predation but there is no physical collision solver. Caps affect selection near capacity. Habitat effects change discretely at tile boundaries while illumination is softly blended. Maps use broad connected bands rather than arbitrary terrain. No obstacles, pathfinding, terrain editing, neural networks, new species, autosave or multi-run overlays are included. The lineage viewer and folder-based Windows executable are available. There is no guarantee that both populations survive any seed. History/CSV contains only the retained rolling window.

`genesis/camera.py` owns presentation-only coordinate transforms and bounds; `genesis/simulation.py` owns the model; `habitats.py` owns immutable maps, coordinate lookup, weighted spawning and occupancy; `observatory.py` owns settings/statistics/CSV; `lineage.py` owns immutable birth records, lifecycle observations and bounded archive/CSV; `lineage_ui.py` owns virtualized relative lists; `persistence.py` validates and restores checkpoints; `presets.py` contains starting recipes. `app.py` owns world rendering and main input routing; `floating_ui.py` owns the panel and confirmations; `glass.py` owns cached frosted surfaces. `observatory_ui.py` provides reusable read-only charts and editing/export helpers; `visuals.py` and `file_dialogs.py` handle ecosystem effects and the modal picker. Tests live in `tests`; frozen v1/v2/v3/v4/v5 fixtures support compatibility regressions. `tools/check_refined_ui.py` captures the refined controls; `tools/check_lineage_ui.py` exercises lineage browsing; `tools/benchmark_lineage.py` measures the matched active-world workload; `tools/check_glass_ui.py` exercises the relocated desktop controls and optionally measures glass cost; `tools/check_explore_ui.py` forwards to it for compatibility; `tools/benchmark_explore.py` measures native simulation/render costs separately. `tools/check_habitats.py` provides repeatable simulation trials. Earlier desktop-check scripts and earlier benchmark results describe their historical layouts; use `check_glass_ui.py` for the current UI. Screenshots, exported files and local saves are ignored by Git.

`genesis/environment.py` owns fixed-tick seasons, independent drought scheduling and the bounded event log; `environment_ui.py` provides its read-only panel. `tools/check_environment_ui.py` checks native environment controls, and `tools/check_environment_trials.py` records repeatable ecosystem outcomes.

`genesis/diagnostics.py` owns the observational ledger, bounded snapshots, validation and diagnostics CSV; `diagnostics_ui.py` draws its read-only panel. `tools/check_balance.py` runs seeded investigation/tuning/evaluation trials, and `tools/summarize_balance.py` builds the findings report from recorded results.
