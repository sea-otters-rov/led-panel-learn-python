r"""Erase a corrupted CIRCUITPY filesystem and wait for the board to come back.

Use this when the board's filesystem is damaged rather than its code. The signs:

  - Explorer lists a file, but opening it says the file cannot be found
  - a save fails with "[Errno 22] Invalid argument"
  - Get-Volume reports HealthStatus Warning on the CIRCUITPY drive
  - reading a file raises "The file or directory is corrupted and unreadable"

FAT on a 2 MB device does get corrupted, usually after a write is interrupted.
Re-syncing never fixes it, because the damage is in the filesystem rather than
in any file -- the directory entry survives while the data it points at does not.

This wipes the board completely, which costs nothing here: lessons\ is an exact
image of the board root, so a sync afterwards puts every byte back.

    .\.venv\Scripts\python.exe .\tools\reset_board.py --yes
    & .\tools\sync.ps1 -Clean

Refuses to run without --yes, so it cannot erase a board by accident.

Exit codes:
    0  erased, and CIRCUITPY came back ready to sync
    1  erase did not complete
    2  serial port busy -- close the Serial Monitor and retry
    3  no board found
"""

import argparse
import os
import sys
import time

# Reuse the sibling tools rather than restating drive discovery and the
# busy-port handling a third time.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sync import discover
from verify_board import find_port, open_port


def wait_for_drive(seconds):
    """Poll until CIRCUITPY is mountable again, refreshing the cached letter.

    The board re-enumerates over USB after erasing, so it may come back on a
    different drive letter. discover() checks boot_out.txt and rewrites the
    cache, which is exactly what the next sync needs.
    """
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        root = discover()
        if root:
            return root
        time.sleep(1.0)
    return None


def main():
    ap = argparse.ArgumentParser(description="Erase a corrupted CIRCUITPY filesystem.")
    ap.add_argument("--yes", action="store_true",
                    help="required; confirms you want the board wiped")
    ap.add_argument("--wait", type=float, default=45.0,
                    help="seconds to wait for the drive to return (default 45)")
    args = ap.parse_args()

    if not args.yes:
        print("[reset] This ERASES everything on the board. Re-run with --yes.")
        print("        Everything is restored by a sync afterwards, since")
        print("        lessons\\ is an exact image of the board root.")
        return 1

    port = find_port()
    if not port:
        print("[reset] No Adafruit USB serial port found. Is the board plugged in?")
        return 3

    print(f"[reset] {port}: breaking into the REPL")
    ser = open_port(port, attempts=3, wait=2.0)
    if ser is None:
        return 2

    with ser:
        # Ctrl-C twice: the first stops code.py, the second is harmless and
        # covers the case where the first landed mid-import.
        ser.reset_input_buffer()
        ser.write(b"\x03")
        time.sleep(0.3)
        ser.write(b"\x03")
        time.sleep(0.7)

        banner = ser.read(4096).decode("utf-8", "replace")
        if ">>>" not in banner:
            print("[reset] No REPL prompt. The board may be running something that "
                  "ignores Ctrl-C; unplug it, plug it back in, and retry.")
            return 1

        print("[reset] erasing...")
        ser.write(b"import storage\r\n")
        time.sleep(0.4)
        ser.write(b"storage.erase_filesystem()\r\n")
        # The board formats and reboots on its own; the port drops with it.
        time.sleep(3.0)

    root = wait_for_drive(args.wait)
    if not root:
        print(f"[reset] Erased, but CIRCUITPY did not reappear within {args.wait:.0f}s.")
        print("        Unplug and replug the board, then run the sync.")
        return 1

    print(f"[reset] done. CIRCUITPY is back at {root} and empty.")
    print("        Now run:  & .\\tools\\sync.ps1 -Clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
