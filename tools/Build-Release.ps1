param(
    [string]$Python = "",
    [switch]$SkipTests,
    [switch]$SkipInstall
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $Python) { $Python = Join-Path $projectRoot '.venv\Scripts\python.exe' }
$Python = (Resolve-Path -LiteralPath $Python).Path
function Invoke-Python {
    & $Python @args
    if ($LASTEXITCODE -ne 0) { throw "Python command failed ($LASTEXITCODE): $args" }
}
Push-Location -LiteralPath $projectRoot
$oldUserData = $env:GENESIS_USER_DATA_DIR
try {
    Invoke-Python -c "import sys,struct; assert sys.platform=='win32' and sys.version_info[:2]==(3,11) and struct.calcsize('P')==8, 'Build with Windows Python 3.11 x64'"
    if (-not $SkipInstall) { Invoke-Python -m pip install -r requirements-build.txt }
    if (-not $SkipTests) {
        $env:GENESIS_USER_DATA_DIR = Join-Path $projectRoot 'artifacts\build-test-user'
        Invoke-Python -m unittest discover -s tests -q
    }
    Invoke-Python tools/release_metadata.py
    Invoke-Python -m PyInstaller --noconfirm --clean --distpath release/dist --workpath release/build packaging/GENESIS.spec
    Invoke-Python tools/release_metadata.py --collect
    $version = (& $Python -c 'from genesis import __version__; print(__version__)').Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read version' }
    $zipPath = Join-Path $projectRoot "release\GENESIS-$version-windows-x64.zip"
    Invoke-Python tools/release_metadata.py --zip
    Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath | Format-List
    Write-Output "Executable: $(Join-Path $projectRoot 'release\dist\GENESIS\GENESIS.exe')"
    Write-Output "ZIP: $zipPath"
} finally {
    $env:GENESIS_USER_DATA_DIR = $oldUserData
    Pop-Location
}
