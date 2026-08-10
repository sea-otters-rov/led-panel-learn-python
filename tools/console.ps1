#Requires -Version 5.1
<#
.SYNOPSIS
    Open the CircuitPython serial console (REPL + print() + tracebacks).

.DESCRIPTION
    An alternative to the Serial Monitor panel. Use this one when you need real
    key passthrough: Ctrl-C to break into the REPL, Ctrl-D to reload.

    Exit with Ctrl-] .

    Only one program can hold the COM port at a time. Close the Serial Monitor
    panel before running this, and vice versa.
#>
[CmdletBinding()]
param([string]$Port)

$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Host "[console] .venv not found. Run .\tools\setup.ps1 first." -ForegroundColor Red
    exit 1
}

if (-not $Port) {
    # 239A is Adafruit's USB vendor ID. MI_00 is the console CDC interface
    # (a second interface shows up only if CIRCUITPY_CDC data is enabled).
    $cand = Get-CimInstance Win32_SerialPort -ErrorAction SilentlyContinue |
        Where-Object { $_.PNPDeviceID -match 'VID_239A' }
    $pick = $cand | Where-Object { $_.PNPDeviceID -match 'MI_00' } | Select-Object -First 1
    if (-not $pick) { $pick = $cand | Select-Object -First 1 }
    if (-not $pick) {
        Write-Host "[console] No Adafruit USB serial port found. Is the board plugged in?" -ForegroundColor Yellow
        exit 1
    }
    $Port = $pick.DeviceID
}

Write-Host "[console] $Port  --  Ctrl-C = REPL, Ctrl-D = reload, Ctrl-] = quit" -ForegroundColor Cyan
# Baud is ignored by USB CDC; 115200 is just convention.
& $python -m serial.tools.miniterm $Port 115200 --raw
