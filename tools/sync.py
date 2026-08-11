"""Push one saved file to the CIRCUITPY drive. Run by VS Code on every Ctrl+S.

Full-tree and -Clean syncs live in sync.ps1; those are not on the hot path.

Design notes, because "a Python script to copy one file" looks like the wrong
tool until you measure it. Median wall time for a *real* write of code.py:

    tools/sync.py                426 ms
    cmd  + copy                  809 ms
    powershell + Copy-Item      1442 ms
    cmd  + robocopy /IS         1621 ms

Two things drive that. Process startup: powershell.exe costs ~500ms before it
runs a line, cmd.exe ~30ms, python.exe ~110ms. And the copy mechanism, which
matters more: a plain read/write takes ~420ms where cmd's `copy` takes ~760ms,
because `copy` forces a synchronous write-through on a FAT removable volume.
Roughly 400ms of any of these is the flash itself and no tool avoids it.

Three traps, all of which cost real debugging time:

1. DO NOT switch to robocopy. It benchmarks at 35ms, which is a lie -- by
   default it skips files it judges unchanged from size + timestamp, and FAT
   timestamps are only accurate to 2 seconds. A student changing one character
   and saving immediately gets a silent no-op. Forcing the write with /IS /IT
   makes it correct and also the slowest option in the table.

2. DO NOT add os.fsync. It is tempting -- surely a fast write only reached the
   cache and the board pays later? Measured end to end, from copy-start to the
   board printing the new value on serial:

       sync.py            copy 434ms   board 883ms   total 1317ms
       sync.py + fsync    copy 585ms   board 834ms   total 1419ms
       cmd copy           copy 689ms   board 844ms   total 1533ms

   The board-side share is flat at ~850ms however the file got there, and
   fsync buys none of it back. Windows defaults removable volumes to "Quick
   removal", which disables write caching, so there is no write-back cache to
   hide behind. (On a fixed disk the worry would have been justified.)

   That ~850ms is CircuitPython's auto-reload debounce plus the soft reboot and
   re-importing libraries. It is not tunable: supervisor.runtime exposes
   `autoreload` as an on/off bool, with no delay setting.

3. DO NOT validate the cached drive letter up front. Probing the FAT volume
   costs ~100ms per save. Just attempt the copy; a failure triggers rediscovery
   and one retry, so a replugged board or a changed drive letter self-heals.

Keep imports to os and sys. Even `shutil` costs measurable startup.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LESSONS = os.path.normcase(os.path.join(os.path.dirname(HERE), "lessons"))
CACHE = os.path.join(HERE, ".circuitpy")


def discover():
    """Find the board. Only runs on the first save, or after a copy fails.

    boot_out.txt is written by CircuitPython itself, so its presence is proof
    this is a real board and not a USB stick someone labelled CIRCUITPY.
    """
    magic = b"Adafruit CircuitPython"
    for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
        root = letter + ":\\"
        try:
            with open(root + "boot_out.txt", "rb") as fh:
                if fh.read(len(magic)) != magic:
                    continue
        except OSError:
            continue
        try:
            with open(CACHE, "w") as fh:
                fh.write(root)
        except OSError:
            pass
        return root
    return None


def cached():
    try:
        with open(CACHE) as fh:
            return fh.read().strip() or None
    except OSError:
        return None


def copy(src, dst):
    d = os.path.dirname(dst)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(src, "rb") as fh:
        data = fh.read()
    with open(dst, "wb") as fh:
        fh.write(data)


def main():
    if len(sys.argv) < 2:
        print("[sync] usage: sync.py <file>")
        return 2

    src = os.path.abspath(sys.argv[1])
    if not os.path.isfile(src):
        return 0

    # Saves outside lessons\ (tools, README, firmware) are not board content.
    if not os.path.normcase(src).startswith(LESSONS + os.sep):
        return 0
    rel = src[len(LESSONS) + 1:]

    root = cached()
    for attempt in (1, 2):
        if root:
            try:
                copy(src, os.path.join(root, rel))
                print(f"[sync] {rel} -> {root}")
                return 0
            except OSError as exc:
                last = exc
        if attempt == 1:
            # Board moved to a different letter, or was unplugged and replugged.
            root = discover()

    if not root:
        print("[sync] No CIRCUITPY drive found.")
        print("       Check the USB cable is a DATA cable, not charge-only.")
        print("       If the board is in the bootloader, press reset once.")
        return 1

    print(f"[sync] copy of {rel} failed: {last}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
