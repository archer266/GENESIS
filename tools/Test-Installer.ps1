param([string]$Setup = '')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source = Join-Path $projectRoot 'release\dist\GENESIS'
$version = (Get-Content -Raw -LiteralPath (Join-Path $source 'build-info.json') | ConvertFrom-Json).version
if (-not $Setup) { $Setup = Join-Path $projectRoot "release\installer\GENESIS-$version-windows-x64-setup.exe" }
$Setup = (Resolve-Path -LiteralPath $Setup).Path
$key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{14EF869A-8464-40A5-AF05-D75D40826B46}_is1'
if (Test-Path $key) { throw 'A GENESIS installation is already registered. Test on a clean account; do not replace it.' }
$desktopLink = Join-Path ([Environment]::GetFolderPath('DesktopDirectory')) 'GENESIS.lnk'
if (Test-Path -LiteralPath $desktopLink) { throw 'A GENESIS desktop shortcut already exists; refusing to overwrite it.' }
$id = [guid]::NewGuid().ToString('N').Substring(0,8)
$root = Join-Path $projectRoot "artifacts\installer check $id"
$install = Join-Path $root ("Installed GENESIS " + [char]0x03a9)
$group = "GENESIS"
$menuLink = Join-Path ([Environment]::GetFolderPath('Programs')) "$group\GENESIS.lnk"
if (Test-Path -LiteralPath $menuLink) { throw 'A GENESIS Start menu shortcut already exists; refusing to overwrite it.' }
# Isolated but genuine per-user data location, never the user's existing files.
$data = Join-Path $env:LOCALAPPDATA "GENESIS\InstallerCheck-$id"
New-Item -ItemType Directory -Path $root | Out-Null
$priorData = $env:GENESIS_USER_DATA_DIR
$priorPath = $env:PATH
$priorPython = $env:PYTHONPATH
$priorHome = $env:PYTHONHOME
$priorVenv = $env:VIRTUAL_ENV

function Run-Checked([string]$file, [string[]]$arguments) {
    $p = Start-Process -FilePath $file -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden -PassThru
    if (-not $p.WaitForExit(60000)) { throw "Process timed out: $file. Inspect $root before retrying." }
    if ($p.ExitCode -ne 0) { throw "Process failed ($($p.ExitCode)): $file" }
}
function Data-Hashes {
    $hashes = @{}
    Get-ChildItem -LiteralPath $data -File -Recurse | ForEach-Object {
        $hashes[$_.FullName.Substring($data.Length)] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    }
    return $hashes
}
function Assert-Data($before) {
    $after = Data-Hashes
    if ($after.Count -ne $before.Count) { throw 'User data file count changed.' }
    foreach ($name in $before.Keys) { if ($before[$name] -ne $after[$name]) { throw "User data changed: $name" } }
}
function Read-UnicodeShortcut([string]$path) {
    # WScript.Shell returns lossy ANSI paths on this host. Read the standard
    # Unicode LinkInfo/StringData fields instead; never execute decoded content.
    $bytes = [IO.File]::ReadAllBytes($path)
    if ([BitConverter]::ToInt32($bytes,0) -ne 76) { throw 'Unexpected shortcut header.' }
    $flags = [BitConverter]::ToInt32($bytes,20)
    $offset = 76
    if ($flags -band 1) { $offset += 2 + [BitConverter]::ToUInt16($bytes,$offset) }
    if (-not ($flags -band 2)) { throw 'Shortcut lacks LinkInfo.' }
    $size = [BitConverter]::ToInt32($bytes,$offset)
    if ([BitConverter]::ToInt32($bytes,$offset+4) -lt 36) { throw 'Shortcut lacks Unicode LinkInfo.' }
    $localOffset = [BitConverter]::ToInt32($bytes,$offset+28)
    if ($localOffset -le 0) { throw 'Shortcut lacks Unicode local target.' }
    $target = [Text.Encoding]::Unicode.GetString($bytes,$offset+$localOffset,$size-$localOffset).Split([char]0)[0]
    $offset += $size
    if (-not ($flags -band 128)) { throw 'Expected Unicode shortcut strings.' }
    $values = @{TargetPath=$target}
    foreach ($pair in @(@(4,'Name'),@(8,'RelativePath'),@(16,'WorkingDirectory'),@(32,'Arguments'),@(64,'IconLocation'))) {
        if ($flags -band $pair[0]) {
            $length = 2 * [BitConverter]::ToUInt16($bytes,$offset)
            $offset += 2
            $values[$pair[1]] = [Text.Encoding]::Unicode.GetString($bytes,$offset,$length)
            $offset += $length
        }
    }
    return $values
}
try {
    Run-Checked $Setup @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/DIR=`"$install`"", "/GROUP=`"$group`"", '/TASKS=desktopicon', "/LOG=`"$root\install.log`"")
    $registration = Get-ItemProperty $key
    if ($registration.DisplayVersion -ne $version -or $registration.InstallLocation.TrimEnd('\') -ne $install) { throw 'Unexpected Installed Apps metadata.' }
    if ($registration.DisplayName -ne 'GENESIS') { throw 'Unexpected Installed Apps name.' }
    $exe = Join-Path $install 'GENESIS.exe'
    foreach ($path in @($menuLink, $desktopLink)) {
        if (-not (Test-Path -LiteralPath $path)) { throw "Shortcut missing: $path" }
        $link = Read-UnicodeShortcut $path
        if ($link.TargetPath -ne $exe -or $link.WorkingDirectory -ne $install -or
            -not $link.IconLocation.StartsWith((Join-Path $install '_internal\genesis\assets\genesis.ico'))) { throw "Shortcut mismatch: $path" }
    }
    $files = Get-ChildItem -LiteralPath $source -File -Recurse
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($source.Length+1)
        if ((Get-FileHash -LiteralPath $file.FullName).Hash -ne (Get-FileHash -LiteralPath (Join-Path $install $relative)).Hash) { throw "Payload mismatch: $relative" }
    }
    $env:GENESIS_USER_DATA_DIR = $data
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $env:PYTHONPATH = $null; $env:PYTHONHOME = $null; $env:VIRTUAL_ENV = $null
    # Launch the resolved shortcut target with a bounded smoke-check lifetime.
    Run-Checked $exe @('--frames','5')
    foreach ($required in @('preferences.json','Recovery\latest.json')) {
        if (-not (Test-Path -LiteralPath (Join-Path $data $required))) { throw "Launch did not create $required" }
    }
    New-Item -ItemType Directory -Path (Join-Path $data 'Worlds'),(Join-Path $data 'Exports') | Out-Null
    Copy-Item -LiteralPath (Join-Path $data 'Recovery\latest.json') -Destination (Join-Path $data 'Worlds\manual world.json')
    Set-Content -LiteralPath (Join-Path $data 'Exports\preservation.csv') -Value 'installer_preservation_probe'
    $before = Data-Hashes
    # Same AppId/version reinstall exercises the upgrade path and remembered dir.
    Run-Checked $Setup @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/LOG=`"$root\upgrade.log`"")
    if ((Get-ItemProperty $key).InstallLocation.TrimEnd('\') -ne $install) { throw 'Upgrade changed the install location.' }
    Assert-Data $before
    $uninstaller = Join-Path $install 'unins000.exe'
    if (-not (Test-Path -LiteralPath $uninstaller)) { throw 'Uninstaller missing.' }
    Run-Checked $uninstaller @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/LOG=`"$root\uninstall.log`"")
    Assert-Data $before
    if ((Test-Path $key) -or (Test-Path -LiteralPath $menuLink) -or (Test-Path -LiteralPath $desktopLink) -or (Test-Path -LiteralPath $exe)) { throw 'Uninstall left application registration, shortcut or executable.' }
    $result = [ordered]@{version=$version;passed=$true;source_files_verified=$files.Count;installed_path=$install;
        per_user_registration=$true;shortcuts_verified=$true;launch_without_python_search_path=$true;
        same_version_upgrade_preserved_data=$true;uninstall_preserved_data=$true;user_data_files=$before.Count;
        user_data_evidence=$data;isolated_machine=$false;interactive_wizard_checked=$false;
        standard_user_account_checked=$false}
    $result | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $root 'result.json')
    Write-Output "Installer checks passed: $root"
} finally {
    $env:GENESIS_USER_DATA_DIR=$priorData; $env:PATH=$priorPath; $env:PYTHONPATH=$priorPython
    $env:PYTHONHOME=$priorHome; $env:VIRTUAL_ENV=$priorVenv
}
