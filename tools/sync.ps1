#Requires -Version 5.1
<#
.SYNOPSIS
    Push files from .\lessons to the attached CIRCUITPY drive.

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
    .\tools\sync.ps1 -File C:\...\learn-py\lessons\code.py
    Copy a single file. This is what VS Code runs on save.

.EXAMPLE
    .\tools\sync.ps1
    Copy the whole lessons\ tree (added files, libraries, fonts, bitmaps).

.EXAMPLE
    .\tools\sync.ps1 -Clean
    Copy the whole tree AND delete anything on the board that is not in lessons\.
    Use this to wipe the factory demo off a fresh board.
#>
[CmdletBinding()]
param(
    [string]$File,
    [string]$Board,
    [switch]$Clean,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$src = (Resolve-Path (Join-Path $PSScriptRoot '..\lessons')).Path.TrimEnd('\')

function Get-BoardUid {
    <#
        The SAMD51's CPU UID, read from boot_out.txt, which CircuitPython writes
        itself. Empty for anything that is not a board.
    #>
    param([string]$Root)

    $f = Join-Path $Root 'boot_out.txt'
    if (-not (Test-Path $f)) { return '' }
    $text = Get-Content $f -Raw
    if ($text -notlike 'Adafruit CircuitPython*') { return '' }
    if ($text -match '(?m)^UID:([0-9A-Fa-f]+)\s*$') { return $Matches[1].ToUpper() }
    return ''
}

function Resolve-BoardUid {
    <#
        Turn a -Board label into a UID using tools\boards.json. Only maintainers
        with two boards attached ever pass -Board; see tools\boards.py.
    #>
    param([string]$Label)

    $map = Join-Path $PSScriptRoot 'boards.json'
    if (-not (Test-Path $map)) {
        throw "No tools\boards.json. Copy tools\boards.json.example to it and put your boards' UIDs in."
    }
    $json = Get-Content $map -Raw | ConvertFrom-Json
    $prop = $json.PSObject.Properties | Where-Object { $_.Name -eq $Label }
    if (-not $prop) {
        $names = ($json.PSObject.Properties | Where-Object { $_.Name -notlike '_*' } | ForEach-Object { $_.Name }) -join ', '
        throw "boards.json has no board called '$Label'. It knows: $names"
    }
    return ([string]$prop.Value).ToUpper()
}

function Find-CircuitPy {
    <#
        Resolve by volume label, never a hard-coded letter -- the drive letter
        changes between machines and between reboots. With two boards attached
        it changes between REPLUGS: two were seen swapping E: and G: inside one
        session, so pass -Board and match on the UID instead of trusting order.

        [System.IO.DriveInfo] is a direct Win32 call, ~40ms. Do NOT use
        Get-Volume here: it goes through CIM/WMI and takes over three seconds,
        which is far too slow to sit on the save path.
    #>
    param([string]$Uid)

    $seen = @()
    foreach ($d in [System.IO.DriveInfo]::GetDrives()) {
        if (-not $d.IsReady) { continue }
        if ($d.DriveType -ne [System.IO.DriveType]::Removable) { continue }
        if ($d.VolumeLabel -ne 'CIRCUITPY') { continue }
        # boot_out.txt only exists on a real CircuitPython device. This guard is
        # what keeps -Clean from ever purging a USB stick someone relabeled.
        $found = Get-BoardUid $d.RootDirectory.FullName
        if (-not $found) { continue }
        if (-not $Uid) { $seen += $d; continue }
        if ($found -eq $Uid) { return $d }
    }

    if ($Uid) { return $null }

    # No -Board given. One board is the normal case and needs no label; two is
    # ambiguous, and picking the first silently is how you spend an afternoon
    # debugging code that was never on the board you were watching.
    if ($seen.Count -gt 1) {
        $letters = ($seen | ForEach-Object { $_.Name.TrimEnd('\') }) -join ', '
        throw "$($seen.Count) boards attached ($letters). Say which one: -Board A or -Board B (see tools\boards.json)."
    }
    if ($seen.Count -eq 1) { return $seen[0] }
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

function Repair-Bom {
    <#
        CircuitPython does not skip a UTF-8 BOM. It reaches those three bytes
        before the first line and reports "line 1: SyntaxError: invalid syntax",
        pointing at a docstring that is perfectly valid -- a dead end for a
        student, and it survives every save until someone inspects the bytes.

        robocopy and Copy-Streaming both copy verbatim, so this is the only
        place to catch it. Fixed in the source rather than in transit: a BOM on
        a .py file in this repo is always wrong, and repairing it once stops it
        coming back on every sync. PowerShell's Set-Content -Encoding utf8
        writes one by default, which is how this was found.
    #>
    param([string[]]$Paths)

    foreach ($p in $Paths) {
        try { $b = [System.IO.File]::ReadAllBytes($p) } catch { continue }
        if ($b.Length -lt 3 -or $b[0] -ne 0xEF -or $b[1] -ne 0xBB -or $b[2] -ne 0xBF) { continue }
        $rest = New-Object byte[] ($b.Length - 3)
        [Array]::Copy($b, 3, $rest, 0, $rest.Length)
        [System.IO.File]::WriteAllBytes($p, $rest)
        Write-Host "[sync] stripped a UTF-8 BOM from $(Split-Path $p -Leaf) -- the board cannot parse one." -ForegroundColor Yellow
    }
}

$uid = if ($Board) { Resolve-BoardUid $Board } else { '' }

$drive = Find-CircuitPy -Uid $uid
if (-not $drive) {
    if ($Board) {
        Write-Host "[sync] Board '$Board' (UID $uid) is not attached." -ForegroundColor Yellow
        Write-Host "       Run: .\.venv\Scripts\python.exe .\tools\boards.py" -ForegroundColor Yellow
        exit 1
    }
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

    # Saves outside lessons\ (tools, README, firmware) are not board content.
    if (-not $full.StartsWith($src, [StringComparison]::OrdinalIgnoreCase)) { exit 0 }

    if ($full -like '*.py') { Repair-Bom -Paths $full }

    $rel = $full.Substring($src.Length).TrimStart('\')
    $target = Join-Path $dst $rel
    $dir = Split-Path $target -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

    Copy-Streaming -From $full -To $target
    if (-not $Quiet) { Write-Host "[sync] $rel -> $(if ($Board) { "board $Board, " })$dst" -ForegroundColor Green }
    exit 0
}

# ---- full tree ---------------------------------------------------------------
if ($Clean) {
    # /XD dirs are invisible to robocopy, so /PURGE will never remove them.
    # Sweep host-side junk off the board explicitly before mirroring.
    Get-ChildItem -Path $dst -Directory -Recurse -Force -Filter '__pycache__' -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

Repair-Bom -Paths (Get-ChildItem $src -Recurse -Filter *.py -File).FullName

# lessons\ is an exact image of the board's root -- anything that is not board
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
    $freeKB = [math]::Round((Find-CircuitPy -Uid $uid).AvailableFreeSpace / 1KB)
    $verb = if ($Clean) { 'synced (clean)' } else { 'synced' }
    $who = if ($Board) { "board $Board, " } else { '' }
    Write-Host "[sync] lessons\ $verb -> $who$dst  ($freeKB KB free)" -ForegroundColor Green
}

# Without this the script leaks robocopy's exit code, and robocopy uses 1 for
# "files copied" and 2 for "extra files detected" -- both success. Harmless when
# launched via `powershell -File`, but a false failure when dot-invoked.
exit 0
