#Requires -Version 5.1
<#
.SYNOPSIS
    One-shot setup of the CircuitPython dev environment on a Windows machine.

.DESCRIPTION
    Run this once per laptop. It is idempotent -- running it again is harmless.

      1. checks for VS Code and Python
      2. installs the four VS Code extensions the workflow needs
      3. creates .venv and installs circup, version-pinned stubs, and the
         plain-Python Adafruit library sources that give Pylance something to read
      4. points the `board` stubs at the MatrixPortal M4 pinout
      5. seeds lessons\settings.toml from the example
      6. downloads the board libraries into lessons\lib via circup

.PARAMETER Provision
    Also push lessons\ to an attached board with -Clean, wiping the factory demo.

.PARAMETER Flash
    Also copy the bundled .uf2 firmware if a UF2 bootloader drive is attached.
    Double-tap the board's reset button first.

.EXAMPLE
    .\tools\setup.ps1

.EXAMPLE
    .\tools\setup.ps1 -Provision
#>
[CmdletBinding()]
param(
    [switch]$Provision,
    [switch]$Flash
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

# Keep these in lockstep with the .uf2 in firmware\ and the version pin in
# requirements-dev.txt. Stubs are per-firmware-release.
$CpyVersion = '10.2.1'
$BoardId    = 'matrixportal_m4'

function Step($n, $msg) { Write-Host "`n[$n] $msg" -ForegroundColor Cyan }
function Ok($msg)       { Write-Host "    $msg" -ForegroundColor Green }
function Warn($msg)     { Write-Host "    $msg" -ForegroundColor Yellow }

# --- 1. preflight -------------------------------------------------------------
Step 1 'Checking prerequisites'

$code = Get-Command code -ErrorAction SilentlyContinue
if (-not $code) {
    Write-Host "    VS Code's 'code' command is not on PATH." -ForegroundColor Red
    Write-Host "    In VS Code: Ctrl+Shift+P -> 'Shell Command: Install code command in PATH'" -ForegroundColor Red
    exit 1
}
Ok "VS Code $(& code --version | Select-Object -First 1)"

$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if (-not $py) {
    Write-Host "    No Python found. Install 3.10+ from python.org and re-run." -ForegroundColor Red
    exit 1
}
Ok "Python $(& $py.Source -V)"

# --- 2. VS Code extensions ----------------------------------------------------
Step 2 'Installing VS Code extensions'

$installed = & code --list-extensions
foreach ($ext in @(
    'ms-python.python',
    'ms-python.vscode-pylance',
    'ms-vscode.vscode-serial-monitor',
    'emeraldwalk.runonsave'
)) {
    if ($installed -contains $ext) {
        Ok "$ext (already installed)"
    } else {
        & code --install-extension $ext --force | Out-Null
        Ok "$ext (installed)"
    }
}

# --- 3. virtualenv ------------------------------------------------------------
Step 3 'Creating .venv and installing tooling'

$venv = Join-Path $repo '.venv'
$vpy  = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $vpy)) {
    & $py.Source -m venv $venv
    Ok 'created .venv'
} else {
    Ok '.venv already exists'
}

& $vpy -m pip install --quiet --upgrade pip
& $vpy -m pip install --quiet -r (Join-Path $repo 'requirements-dev.txt')
# --no-deps: these are only ever read by Pylance. Their real dependency is
# Blinka, which is a large stack we do not want and never import.
& $vpy -m pip install --quiet --no-deps -r (Join-Path $repo 'requirements-intellisense.txt')
Ok 'circup, stubs, and library sources installed'

# --- 4. board-specific stubs --------------------------------------------------
Step 4 "Pointing 'board' stubs at $BoardId"
& (Join-Path $venv 'Scripts\circuitpython_setboard.exe') $BoardId | Out-Null
Ok "board.MTX_R1, board.ACCELEROMETER, etc. will now autocomplete"

# --- 5. settings.toml ---------------------------------------------------------
Step 5 'Seeding lessons\settings.toml'
$toml    = Join-Path $repo 'lessons\settings.toml'
$tomlEx  = Join-Path $repo 'settings.toml.example'
if (Test-Path $toml) {
    Ok 'lessons\settings.toml already exists (left alone)'
} else {
    Copy-Item $tomlEx $toml
    Ok 'copied from settings.toml.example -- it is gitignored, put secrets there'
}

# --- 6. board libraries -------------------------------------------------------
Step 6 'Fetching board libraries into lessons\lib'
$circup = Join-Path $venv 'Scripts\circup.exe'
& $circup --path (Join-Path $repo 'lessons') --board-id $BoardId --cpy-version $CpyVersion `
          install -r (Join-Path $repo 'device-requirements.txt')
if ($LASTEXITCODE -ne 0) { Warn 'circup reported a problem -- check the output above' }
Ok 'lessons\lib populated'

# --- 7. optional: firmware ----------------------------------------------------
if ($Flash) {
    Step 7 'Flashing CircuitPython firmware'
    # The UF2 bootloader mounts as its own drive. Identify it by INFO_UF2.TXT
    # rather than by label, so this works across board revisions.
    $boot = Get-Volume -ErrorAction SilentlyContinue |
        Where-Object { $_.DriveLetter } |
        Where-Object { Test-Path "$($_.DriveLetter):\INFO_UF2.TXT" } |
        Select-Object -First 1
    if (-not $boot) {
        Warn 'No UF2 bootloader drive found. Double-tap the reset button, then re-run with -Flash.'
    } else {
        $uf2 = Get-ChildItem (Join-Path $repo 'firmware') -Filter '*.uf2' | Select-Object -First 1
        Copy-Item $uf2.FullName "$($boot.DriveLetter):\"
        Ok "$($uf2.Name) -> $($boot.DriveLetter):  (the board will reboot on its own)"
        Start-Sleep -Seconds 8
    }
}

# --- 8. optional: provision the attached board --------------------------------
if ($Provision) {
    Step 8 'Provisioning the attached board'
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'tools\sync.ps1') -Clean
}

Write-Host "`nDone." -ForegroundColor Green
Write-Host "  Open this folder in VS Code, then:" -ForegroundColor Green
Write-Host "    - Ctrl+Shift+P -> 'Python: Select Interpreter' -> .venv" -ForegroundColor Green
Write-Host "    - Ctrl+Shift+P -> 'Serial Monitor: Focus on Monitor View' -> pick the COM port -> Start Monitoring" -ForegroundColor Green
Write-Host "    - edit lessons\L00_does_it_work\main.py and hit Ctrl+S" -ForegroundColor Green
