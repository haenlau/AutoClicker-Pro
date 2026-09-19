$ErrorActionPreference = 'Stop'
$pythonExe = (Get-Command python -ErrorAction Stop).Source
$savedPath = $env:PATH
$savedTemp = $env:TEMP
$savedTmp = $env:TMP
$savedCache = $env:PYINSTALLER_CONFIG_DIR
Push-Location $PSScriptRoot
try {
    New-Item -ItemType Directory -Path 'scratch' -Force | Out-Null
    # Avoid collecting incompatible DLLs from other applications on PATH (e.g. ICU).
    $env:PATH = "$(Split-Path $pythonExe);$env:SystemRoot\System32;$env:SystemRoot"
    $env:TEMP = Join-Path $PSScriptRoot 'scratch'
    $env:TMP = $env:TEMP
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $env:TEMP 'pyinstaller'
    & $pythonExe -m PyInstaller --noconfirm --clean --workpath build --distpath dist AutoClicker.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
    Copy-Item -LiteralPath 'dist\AutoClicker.exe' -Destination 'dist\鼠标连点器.exe' -Force
} finally {
    $env:PATH = $savedPath
    $env:TEMP = $savedTemp
    $env:TMP = $savedTmp
    $env:PYINSTALLER_CONFIG_DIR = $savedCache
    Pop-Location
}
