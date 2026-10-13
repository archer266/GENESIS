param([string]$Compiler = '')
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source = Join-Path $projectRoot 'release\dist\GENESIS'
$metadata = Get-Content -Raw -LiteralPath (Join-Path $source 'build-info.json') | ConvertFrom-Json
$version = [string]$metadata.version
if ($version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid existing build version.' }
$exe = Join-Path $source 'GENESIS.exe'
if ((Get-Item -LiteralPath $exe).VersionInfo.ProductVersion -ne $version) {
    throw 'Executable metadata does not match build-info.json. Rebuild the portable release first.'
}
foreach ($required in @('_internal\python311.dll','_internal\base_library.zip',
                        '_internal\pygame\SDL2.dll','_internal\genesis\assets\genesis.ico',
                        'GETTING_STARTED.txt','THIRD_PARTY.txt','licenses')) {
    if (-not (Test-Path -LiteralPath (Join-Path $source $required))) { throw "Incomplete distribution: $required" }
}
if (-not $Compiler) {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command) { $Compiler = $command.Source }
    else {
        foreach ($candidate in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
                                "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
                                "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")) {
            if (Test-Path -LiteralPath $candidate) { $Compiler = $candidate; break }
        }
    }
}
if (-not $Compiler -or -not (Test-Path -LiteralPath $Compiler)) {
    throw 'Inno Setup 6.3+ is unavailable. Install it from https://jrsoftware.org/isinfo.php or pass -Compiler with the ISCC.exe path. No installer was built.'
}
$output = Join-Path $projectRoot 'release\installer'
New-Item -ItemType Directory -Force -Path $output | Out-Null
& $Compiler '/Q' "/DSourceDir=$source" "/DReleaseVersion=$version" "/O$output" (Join-Path $projectRoot 'packaging\GENESIS.iss')
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compile failed ($LASTEXITCODE)." }
$setup = Join-Path $output "GENESIS-$version-windows-x64-setup.exe"
if (-not (Test-Path -LiteralPath $setup)) { throw 'Compiler did not produce the expected installer.' }
Write-Output "Setup: $setup"
Get-FileHash -Algorithm SHA256 -LiteralPath $setup | Select-Object Hash, Path
