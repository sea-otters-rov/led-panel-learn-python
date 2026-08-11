r"""Check that the attached board is alive and running the current lesson.

Forces a clean reload over the USB CDC console and reports what code.py did.
Use it after a sync, or any time the board's behaviour is in question.

    .\.venv\Scripts\python.exe .\tools\verify_board.py

Ctrl-C then Ctrl-D is sent before listening. Ctrl-C breaks whatever is running
into the REPL, Ctrl-D leaves it and reloads -- which is also what re-enables
auto-reload, so this doubles as the fix for "my saves stopped working".

The serial port is exclusive: only one program can hold it. If the VS Code
Serial Monitor panel or tools\console.ps1 is connected, this exits 2 and says
so rather than failing with a bare Windows error.

Exit codes:
    0  board reloaded and ran, no traceback
    1  the lesson raised a traceback (printed below)
    2  serial port is busy -- disconnect the other program and re-run
    3  no CircuitPython board found
"""

import argparse
import os
import re
import sys
import time

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    sys.exit("pyserial is missing. Run .\\tools\\setup.ps1 first.")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANSI = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-9;?]*[A-Za-z]")

# CircuitPython prints this immediately before handing control to code.py. Only
# what follows the LAST one is this run: the Ctrl-C used to break into the REPL
# raises KeyboardInterrupt first, and reading that as a failure would report a
# perfectly healthy board as broken.
MARKER = "code.py output:"


def find_port():
    cands = [p for p in serial.tools.list_ports.comports()
             if "VID:PID=239A" in (p.hwid or "").upper()]
    if not cands:
        return None
    # MI_00 is the console interface; a second one appears only when
    # CIRCUITPY_CDC data is enabled.
    for p in cands:
        if "MI_00" in (p.hwid or "").upper():
            return p.device
    return cands[0].device


def current_lesson():
    """Whatever code.py imports, for the report line. Best effort only."""
    try:
        with open(os.path.join(REPO, "lessons", "code.py")) as fh:
            m = re.search(r"^\s*(?:from\s+(\S+)\s+import\s+(\S+)|import\s+(\S+))",
                          fh.read(), re.MULTILINE)
    except OSError:
        return None
    if not m:
        return None
    return m.group(1) or m.group(3)


def open_port(port, attempts, wait):
    """Open the console, retrying briefly in case a monitor is mid-disconnect."""
    last = None
    for i in range(1, attempts + 1):
        try:
            return serial.Serial(port, 115200, timeout=0.2)
        except (serial.SerialException, OSError) as exc:
            last = exc
            if i < attempts:
                print(f"[verify] {port} busy, retrying ({i}/{attempts - 1})...")
                time.sleep(wait)
    print(f"[verify] Cannot open {port}: {last}")
    print("         Something else is holding the port. Close whichever applies:")
    print("           - the VS Code Serial Monitor panel (Stop Monitoring)")
    print("           - a 'Board: serial console' task / tools\\console.ps1")
    print("         Then run this again.")
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--timeout", type=float, default=10.0,
                    help="seconds to listen after the reload (default 10)")
    ap.add_argument("--attempts", type=int, default=3,
                    help="tries at opening a busy port (default 3)")
    ap.add_argument("--wait", type=float, default=2.0,
                    help="seconds between attempts (default 2)")
    ap.add_argument("--port", help="override the auto-detected COM port")
    args = ap.parse_args()

    port = args.port or find_port()
    if not port:
        print("[verify] No Adafruit USB serial port found.")
        print("         Check the cable is a DATA cable, not charge-only.")
        print("         If the board sits in the bootloader, press reset once.")
        return 3

    lesson = current_lesson()
    print(f"[verify] {port}   code.py imports: {lesson or 'unknown'}")

    ser = open_port(port, args.attempts, args.wait)
    if ser is None:
        return 2

    with ser:
        ser.reset_input_buffer()
        ser.write(b"\x03")
        time.sleep(0.4)
        ser.write(b"\x04")

        buf = ""
        end = time.perf_counter() + args.timeout
        while time.perf_counter() < end:
            chunk = ser.read(4096)
            if not chunk:
                continue
            buf += chunk.decode("utf-8", "replace")
            run = ANSI.sub("", buf).rpartition(MARKER)[2]
            if "Code done running." in run:
                break

    text = ANSI.sub("", buf)
    _, found, run = text.rpartition(MARKER)

    if not found:
        print("[verify] Board never reached code.py. It may be held in the REPL, "
              "or code.py is missing. Try tools\\sync.ps1 -Clean.")
        return 1

    lines = [ln.rstrip() for ln in run.splitlines() if ln.strip()]
    print("[verify] --- board said ---")
    for ln in lines or ["(no output -- the lesson prints nothing)"]:
        print(f"         {ln}")
    print("[verify] ------------------")

    if "Traceback (most recent call last)" in run:
        print("[verify] FAIL: the lesson raised an error (see above).")
        return 1
    if "Code done running." in run:
        print("[verify] OK: code.py ran to completion (no endless loop).")
        return 0
    print("[verify] OK: code.py is running.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
