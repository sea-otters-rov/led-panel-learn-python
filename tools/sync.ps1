#Requires -Version 5.1
<#
.SYNOPSIS
    Push files from .\device to the attached CIRCUITPY drive.

.DESCRIPTION
    The repo on your hard drive is the source of truth. The board's flash is a
    build output. This script copies one file (fast path, used on every Ctrl+S)
    or the whole tree.

    Writing to CIRCUITPY is what makes CircuitPython auto-reload, so a copy here
    is the same thing as "run my code".

    The single-file path is kept well under a second on purpose. If it is slow,
    saves queue up behind each other in VS Code and you get
    "Unable to write file ... UNKNOWN" when the next save collides with a sync
    that is still running.

.EXAMPLE
    .\tools\sync.ps1 -File C:\...\learn-py\device\code.py
    Copy a single file. This is what VS Code runs on save.

.EXAMPLE
    .\tools\sync.ps1
    Copy the whole device\ tree (added files, libraries, fonts, bitmaps).

.EXAMPLE
    .\tools\sync.ps1 -Clean
    Copy the whole tree AND delete anything on the board that is not in device\.
    Use this to wipe the factory demo off a fresh board.
#>
[CmdletBinding()]
param(
    [string]$File,
    [switch]$Clean,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$src = (Resolve-Path (Join-Path $PSScriptRoot '..\device')).Path.TrimEnd('\')

function Find-CircuitPy {
    # Resolve by volume label, never a hard-coded letter -- the drive letter
    # changes between machines and between reboots.
    #
    # [System.IO.DriveInfo] is a direct Win32 call, ~40ms. Do NOT use Get-Volume
    # here: it goes through CIM/WMI and takes over three seconds, which is far
    # too slow to sit on the save path.
    foreach ($d in [System.IO.DriveInfo]::GetDrives()) {
        if (-not $d.IsReady) { continue }
        if ($d.DriveType -ne [System.IO.DriveType]::Removable) { continue }
        if ($d.VolumeLabel -ne 'CIRCUITPY') { continue }
        # boot_out.txt only exists on a real CircuitPython device. This guard is
        # what keeps -Clean from ever purging a USB stick someone relabeled.
        if (Test-Path (Join-Path $d.RootDirectory.FullName 'boot_out.txt')) { return $d }
    }
    return $null
}

function Copy-Streaming {
    <#
        Copy-Item opens the source with a restrictive share mode, so a save that
        lands while a sync is in flight fails inside VS Code. Open the source
        shared for read, write, AND delete so the editor is never blocked by us,
        and retry briefly if the editor happens to be mid-write.
    #>
    param([string]$From, [string]$To, [int]$Tries = 4)

    $share = [System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete
    for ($i = 1; $i -le $Tries; $i++) {
        try {
            $in = [System.IO.File]::Open($From, [System.IO.FileMode]::Open,
                                         [System.IO.FileAccess]::Read, $share)
            try {
                $out = [System.IO.File]::Open($To, [System.IO.FileMode]::Create,
                                              [System.IO.FileAccess]::Write,
                                              [System.IO.FileShare]::None)
                try {
                    $in.CopyTo($out)
                    # Flush through the OS cache so the board sees a complete
                    # file rather than reloading on a half-written one.
                    $out.Flush($true)
                } finally { $out.Dispose() }
            } finally { $in.Dispose() }
            return
        } catch [System.IO.IOException] {
            if ($i -eq $Tries) { throw }
            Start-Sleep -Milliseconds (60 * $i)
        }
    }
}

$drive = Find-CircuitPy
if (-not $drive) {
    Write-Host "[sync] No CIRCUITPY drive found." -ForegroundColor Yellow
    Write-Host "       Check the USB cable is a DATA cable, not charge-only." -ForegroundColor Yellow
    Write-Host "       If the board is in the bootloader, press reset once." -ForegroundColor Yellow
    exit 1
}
$dst = $drive.RootDirectory.FullName

# ---- fast path: one file -----------------------------------------------------
if ($File) {
    if (-not (Test-Path -LiteralPath $File)) { exit 0 }
    $full = (Resolve-Path -LiteralPath $File).Path

    # Saves outside device\ (lessons, tools, README) are not device code.
    if (-not $full.StartsWith($src, [StringComparison]::OrdinalIgnoreCase)) { exit 0 }

    $rel = $full.Substring($src.Length).TrimStart('\')
    $target = Join-Path $dst $rel
    $dir = Split-Path $target -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

    Copy-Streaming -From $full -To $target
    if (-not $Quiet) { Write-Host "[sync] $rel -> $dst" -ForegroundColor Green }
    exit 0
}

# ---- full tree ---------------------------------------------------------------
if ($Clean) {
    # /XD dirs are invisible to robocopy, so /PURGE will never remove them.
    # Sweep host-side junk off the board explicitly before mirroring.
    Get-ChildItem -Path $dst -Directory -Recurse -Force -Filter '__pycache__' -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

# device\ is an exact image of the board's root -- anything that is not board
# content lives outside it, so /PURGE can be trusted to clean up strays.
#
# /FFT : compare timestamps at FAT's 2-second granularity (NTFS -> FAT)
# /XF  : boot_out.txt is written by the board itself; never touch it
$rb = @(
    $src, $dst.TrimEnd('\'), '/E', '/FFT', '/R:2', '/W:1',
    '/NFL', '/NDL', '/NJH', '/NJS', '/NP',
    '/XD', '__pycache__', '.git', 'System Volume Information',
    '/XF', 'boot_out.txt', '.gitkeep'
)
if ($Clean) { $rb += '/PURGE' }

& robocopy @rb | Out-Null
$rc = $LASTEXITCODE
if ($rc -ge 8) {
    Write-Host "[sync] robocopy failed with exit code $rc" -ForegroundColor Red
    exit 1
}

if (-not $Quiet) {
    # Re-stat: the copy just changed how much is free.
    $freeKB = [math]::Round((Find-CircuitPy).AvailableFreeSpace / 1KB)
    $verb = if ($Clean) { 'synced (clean)' } else { 'synced' }
    Write-Host "[sync] device\ $verb -> $dst  ($freeKB KB free)" -ForegroundColor Green
}
