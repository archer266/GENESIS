# GENESIS 0.13.0 Windows installer

Built 2026-10-13 using Inno Setup 6.7.3 from the existing validated folder build.
Application version, simulation, UI and portable ZIP are unchanged. No release
was published or uploaded. No application test suite or balance trials were
repeated for this packaging-only change.

## Artifact and installation

Setup executable:
`C:\Users\Admin\Desktop\Coding Projects\Genesis\release\installer\GENESIS-0.13.0-windows-x64-setup.exe`

SHA256: `59DD0F62F0F6B633B326352C5D581020F3133A88B5F1A4FB7CB4DE24555446A7`

Double-click setup, follow the wizard, optionally choose a desktop shortcut,
then use the Launch GENESIS checkbox or Start > GENESIS. Windows 10/11 x64;
unsigned local build. Default install directory:
`%LOCALAPPDATA%\Programs\GENESIS`. The installer uses
[`PrivilegesRequired=lowest`](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm)
and does not request administrator privileges.

A stable AppId and remembered directory support upgrades. Inno registers an
uninstaller, version, name, publisher, location and application icon in the
current user's Installed Apps registration. Uninstall through Windows Settings
> Apps > Installed apps > GENESIS. User preferences, saves, exports and recovery
remain outside the installed payload, and no uninstall deletion rules target
them. Close the application before updating or uninstalling so recovery finishes.

## Actual checks

- Compiled setup successfully. Installed silently into an isolated directory
  containing spaces and a Greek Omega on the development machine.
- Installer log confirms `User privileges: None`, `Administrative install mode:
  No`, and `HKEY_CURRENT_USER` registration.
- All **105 existing distribution files** were present after installation and
  matched source SHA256 hashes. The install also includes `INSTALLING.txt` and
  the generated uninstaller.
- Start menu and optional desktop shortcut target, working directory and icon
  fields matched the installed Unicode paths. The test reads Unicode shortcut
  fields because the host's legacy WScript accessor returned lossy ANSI strings;
  the actual shortcuts contained the correct Unicode paths.
- Launched the installed shortcut's resolved target with a bounded five-frame
  smoke check, outside the project working directory, with Python/venv search
  paths removed. The app exited successfully and produced preferences/recovery.
- Reinstalled the **same version** over the test installation without supplying
  its directory again; the remembered location was retained. All five test data
  files (preferences, log, recovery, manual-world copy and export probe) remained
  byte-identical through upgrade and uninstall.
- Uninstaller exited successfully and removed app executable, registry entry,
  Start menu shortcut and desktop shortcut. Test user data was retained in an
  isolated `%LOCALAPPDATA%\GENESIS\InstallerCheck-*` evidence directory; existing
  user data was not modified. No test installation remains.
- Portable ZIP SHA256 is unchanged:
  `37CB43247A6571A1F925CC627E93FA12ACD084BDB6B268A251A591F30DF0C1E3`.

Structured check results: [result.json](result.json). Install, upgrade and
uninstall logs are retained locally under `artifacts/installer check e7b67602`.
Initial test-harness assumptions about a custom menu folder and the legacy
shortcut reader were corrected; both preliminary test installs were removed.
No application or installer payload defect was found.

## Pending / limits

- Interactive wizard layout, unchecked-by-default desktop task, and clicking
  the final Launch GENESIS checkbox: configured in the compiled script, not
  manually exercised. Silent tests intentionally skip post-install launch.
- Real shortcut activation via Start/desktop: targets verified and executed,
  but not clicked manually.
- A later **different-version** upgrade: stable-ID path configured; the actual
  check was a same-version reinstall.
- Another Windows machine without Python, including an independent standard
  user account: pending. Non-administrative mode on this development account is
  verified but is not separate-machine certification.
- Signing and reputation prompts remain outside this task. No screenshots or
  Computer Use were necessary. Do not run portable and installed copies against
  the same recovery directory concurrently; cross-process recovery is untested.

## Repeatable build/check

```powershell
Set-Location "C:\Users\Admin\Desktop\Coding Projects\Genesis"
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-Installer.ps1
# Test only where GENESIS is not already installed or shortcut-registered:
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-Installer.ps1
```

Build requires Inno Setup 6.3+ and the existing complete distribution. It reports
a missing compiler explicitly; it does not download dependencies or claim a build
succeeded without the expected setup executable.
