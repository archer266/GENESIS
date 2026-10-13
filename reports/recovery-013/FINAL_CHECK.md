# Final release check - GENESIS 0.13.0

Reviewed 2026-10-13. **No demonstrated release blocker found.** Ready for local
Windows x64 use and external-machine validation; not certified across Windows
hardware. No application changes, version bump, rebuild, or publication.

## Completed this review

- ZIP CRC passed for all 105 files. Every file matched `release/dist/GENESIS`
  byte-for-byte; no build files were omitted.
- Verified embedded Python 3.11 runtime, Python standard-library archive,
  Pygame/SDL dependencies, application icons, licenses, third-party notices,
  build metadata, and getting-started instructions are included.
- Executable metadata reports GENESIS 0.13.0 for product and file versions.
- Bundled `GETTING_STARTED.txt` exactly matches its source. Extraction,
  `_internal` folder, controls, Worlds operations, per-user paths, autosave,
  paused resume, and obsolete-world restrictions match the packaged release's
  recorded native checks and the relevant current implementation.
- ZIP SHA256 remains
  `37CB43247A6571A1F925CC627E93FA12ACD084BDB6B268A251A591F30DF0C1E3`.

The existing [release report](RESULTS.md) records 194 passing regression tests
and successful packaged native checks outside the project, including paths with
spaces/non-ASCII characters and Python removed from the search path. Those
checks were reviewed, **not rerun** here. Documentation-only changes do not
require another test suite or rebuild. No screenshots, Computer Use, or balance
trials were performed for this review.

## Limitations and remaining validation

- **PENDING: another Windows x64 computer without Python installed.** Removing
  Python from PATH on the development machine is not that test.
- **PENDING: the manual checklist below.** Prior scripted UI checks are not a
  substitute for hands-on confirmation of the release on the target computer.
- The build is unsigned and folder-based, not an installer. Windows may show
  a reputation/security prompt; signing was not part of this release.
- Recovery can lose changes since the last successful snapshot. Slow/failing
  storage extends that interval and can delay clean shutdown. This is documented
  behavior, not evidence of a current defect.
- Background serialization can contend with rendering. Save measurements are
  short development-machine measurements, not universal latency guarantees.
  Prior near-cap 4x benchmarks did not establish sustained 60 FPS.
- Ecological extinction remains possible. No new regression evidence justifies
  repeating balance trials for this persistence-only release.

## Short manual checklist (all pending)

- [ ] **Launch:** extract the whole ZIP outside the project, keep `_internal`
  beside `GENESIS.exe`, double-click, and verify the ecosystem/guide appears.
  With existing recovery, explicitly choose Resume or Start fresh.
- [ ] **Settings:** open with O or the bar, visit all tabs, drag/resize/minimize
  the panel, close it, and verify controls remain readable at a smaller window.
- [ ] **Organisms:** click a living cell, inspect Details, press F to follow,
  zoom, and pan to stop following. Deselect and verify the card closes.
- [ ] **Save/load:** save a named world in a writable folder, advance it, load
  it, confirm replacement, and verify it returns paused to the saved time.
- [ ] **Autosave recovery:** enable Autosave in Worlds, run for over two real
  minutes, and verify saved status. Pause for another interval and verify the
  unchanged recovery file is not repeatedly rewritten. Close/relaunch, verify
  the explicit recovery choice, and resume paused. Check the toggle persists.
- [ ] **Fullscreen:** use F11 twice, then I and Escape; verify windowed controls
  and organism selection remain usable.
- [ ] **Exports:** export statistics, lineage, and diagnostics CSVs to new
  filenames; open each and verify headers/data and readable destination feedback.

## Launch paths

Executable:
`C:\Users\Admin\Desktop\Coding Projects\Genesis\release\dist\GENESIS\GENESIS.exe`

ZIP:
`C:\Users\Admin\Desktop\Coding Projects\Genesis\release\GENESIS-0.13.0-windows-x64.zip`
