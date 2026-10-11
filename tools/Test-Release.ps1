param([switch]$SkipBenchmark)
$ErrorActionPreference = 'Stop'
Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class ReleaseWindow {
    public delegate bool Visit(IntPtr window, IntPtr data);
    [DllImport("user32.dll")] public static extern bool EnumWindows(Visit visit, IntPtr data);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr window, out uint pid);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr window, StringBuilder title, int length);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr window, uint message, IntPtr w, IntPtr l);
    public static bool Close(int process) {
        bool found=false;
        EnumWindows((window, data) => {
            uint pid; GetWindowThreadProcessId(window,out pid);
            var title=new StringBuilder(256); GetWindowText(window,title,256);
            if (pid==process && title.ToString().StartsWith("GENESIS")) {
                found=PostMessage(window,0x10,IntPtr.Zero,IntPtr.Zero);
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }
}
'@
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$version = (& $python -c "import sys;sys.path.insert(0,r'$projectRoot');from genesis import __version__;print(__version__)").Trim()
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ("GENESIS release $([char]0x03a9) " + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $testRoot | Out-Null
Expand-Archive -LiteralPath (Join-Path $projectRoot "release\GENESIS-$version-windows-x64.zip") -DestinationPath $testRoot
$fixtures = Join-Path $testRoot 'fixtures'
New-Item -ItemType Directory -Path $fixtures | Out-Null
Copy-Item -Path (Join-Path $projectRoot 'tests\fixtures\*_world_v*.json') -Destination $fixtures
Copy-Item -LiteralPath (Join-Path $projectRoot 'artifacts\environment-cap.json') -Destination $fixtures
$exe = Join-Path $testRoot 'GENESIS\GENESIS.exe'
$output = Join-Path $testRoot 'checks'
$prior = @{}
foreach ($name in @('PATH','PYTHONPATH','PYTHONHOME','VIRTUAL_ENV','GENESIS_USER_DATA_DIR','SDL_VIDEODRIVER','SDL_AUDIODRIVER')) {
    $prior[$name] = [Environment]::GetEnvironmentVariable($name,'Process')
}
function Run-Packaged([string]$mode,[string]$destination) {
    $process = Start-Process -FilePath $exe -WorkingDirectory $testRoot -WindowStyle Hidden -PassThru -ArgumentList @('--release-check','--output',('"'+$destination+'"'),'--fixtures',('"'+$fixtures+'"'),'--mode',$mode)
    if (-not $process.WaitForExit(120000)) { throw "Release check timed out; process $($process.Id), $testRoot" }
    if ($process.ExitCode -ne 0) { throw "Release check failed: $mode ($($process.ExitCode)); inspect $testRoot" }
    $result = Get-Content -Raw -LiteralPath (Join-Path $destination "$mode.json") | ConvertFrom-Json
    if (-not $result.passed -or -not $result.frozen) { throw 'Invalid release check result' }
}
try {
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $env:PYTHONPATH = $null; $env:PYTHONHOME = $null; $env:VIRTUAL_ENV = $null
    $env:SDL_VIDEODRIVER = $null; $env:SDL_AUDIODRIVER = $null
    $env:GENESIS_USER_DATA_DIR = Join-Path $testRoot 'user data'
    Run-Packaged 'smoke' $output
    Run-Packaged 'relaunch' $output
    # Exercise the ordinary, argument-free windowed entry point, then clean close.
    $process = Start-Process -FilePath $exe -WorkingDirectory $testRoot -WindowStyle Hidden -PassThru
    if (-not $process.WaitForInputIdle(10000)) { throw 'Desktop did not become ready' }
    Start-Sleep -Seconds 2
    $process.Refresh()
    if ($process.HasExited -or -not [ReleaseWindow]::Close($process.Id)) { throw 'Normal application window unavailable' }
    if (-not $process.WaitForExit(10000) -or $process.ExitCode -ne 0) { throw 'Normal application did not close cleanly' }
    if (-not $SkipBenchmark) {
        for ($trial=1; $trial -le 3; $trial++) {
            Run-Packaged 'benchmark' (Join-Path $output "packaged-$trial")
            $sourceOutput = Join-Path $output "source-$trial"
            Push-Location -LiteralPath $projectRoot
            try {
                & $python -m genesis --release-check --output $sourceOutput --fixtures $fixtures --mode benchmark
                if ($LASTEXITCODE -ne 0) { throw 'Source benchmark failed' }
            } finally { Pop-Location }
        }
    }
    $archive = Join-Path $projectRoot 'artifacts\desktop-release-check'
    New-Item -ItemType Directory -Force -Path $archive | Out-Null
    Copy-Item -LiteralPath $output -Destination $archive -Recurse -Force
    @{test_root=$testRoot;executable=$exe;normal_launch_and_close=$true;isolated_machine=$false;python_search_path_removed=$true} | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $archive 'launch.json')
    Write-Output "Desktop release checks passed. Artifacts: $archive. Extracted test copy: $testRoot"
} finally {
    foreach ($name in $prior.Keys) { [Environment]::SetEnvironmentVariable($name,$prior[$name],'Process') }
}
