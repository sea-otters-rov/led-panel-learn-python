r"""Report the ESP32 co-processor's nina-fw version.

Old firmware (factory-shipped 1.2.2) joins the wifi and resolves names fine,
then fails every socket_open with BrokenPipeError -- which looks like a
networking bug in a lesson and is not. 3.3.0 or newer is what this course
expects; see CLAUDE.md's networking notes. Check this BEFORE debugging a
lesson that cannot open a socket.

    .\.venv\Scripts\python.exe .\tools\check_firmware.py

Breaks into the REPL (same as tools\reset_board.py) and constructs the radio
directly, so it does not need wifi credentials or a joined network -- this is
meant to work even when networking is completely broken. Leaves the board
running normally afterwards (Ctrl-D, same as tools\verify_board.py).

With two boards attached, --board says which one, by the label in
tools\boards.json:

    .\.venv\Scripts\python.exe .\tools\check_firmware.py --board A

Exit codes:
    0  firmware is 3.3.0 or newer
    1  firmware is older than 3.3.0, or the version could not be read
    2  serial port is busy -- disconnect the other program and re-run
    3  no CircuitPython board found, or two were found and neither was named
"""

import argparse
import os
import re
import sys
import time

# Reuse the sibling tool rather than restating port discovery and the busy-port
# handling a second time.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verify_board import Ambiguous, find_port, open_port

EXPECTED = (3, 3, 0)

ANSI = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-9;?]*[A-Za-z]")
MARKER = "FIRMWARE:"

# One statement per line -- the REPL runs each on Enter, so nothing here can
# need paste mode (Ctrl-E), which would only complicate capturing the result.
SNIPPET = [
    "import board",
    "from digitalio import DigitalInOut",
    "import adafruit_esp32spi.adafruit_esp32spi as esp32spi",
    "_esp = esp32spi.ESP_SPIcontrol(board.SPI(), DigitalInOut(board.ESP_CS), "
    "DigitalInOut(board.ESP_BUSY), DigitalInOut(board.ESP_RESET))",
    # The serial console echoes back whatever it is sent, so the marker must
    # never appear as a literal substring of the line we transmit -- otherwise
    # the echo of the command itself is what gets matched, not its output.
    # Split it here and let the board's own print() reassemble it.
    f'print("{MARKER[:4]}" + "{MARKER[4:]}" + str(_esp.firmware_version, "utf-8").strip("\\x00"))',
]


def parse_version(text: str) -> tuple:
    """"3.3.0" -> (3, 3, 0). Raises ValueError if it does not look like one."""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", text.strip())
    if not m:
        raise ValueError(f"{text!r} does not look like a version number")
    return tuple(int(g) for g in m.groups())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--timeout", type=float, default=8.0, help="seconds to wait for a reply (default 8)"
    )
    ap.add_argument(
        "--attempts", type=int, default=3, help="tries at opening a busy port (default 3)"
    )
    ap.add_argument(
        "--wait", type=float, default=2.0, help="seconds between attempts (default 2)"
    )
    ap.add_argument("--port", help="override the auto-detected COM port")
    ap.add_argument("--board", help="which board, by label in tools\\boards.json")
    args = ap.parse_args()

    port = args.port
    if not port and args.board:
        import boards

        try:
            port = boards.resolve(args.board)["port"]
        except LookupError as exc:
            print(f"[firmware] {exc}")
            return 3
        if not port:
            print(
                f"[firmware] Board {args.board!r} is mounted but has no serial "
                f"port. Unplug and replug it."
            )
            return 3

    if not port:
        try:
            port = find_port()
        except Ambiguous as exc:
            print(f"[firmware] {exc}")
            print("           Say which one: --board A  (see tools\\boards.json)")
            return 3

    if not port:
        print("[firmware] No Adafruit USB serial port found.")
        print("           Check the cable is a DATA cable, not charge-only.")
        return 3

    who = f"board {args.board}, " if args.board else ""
    print(f"[firmware] {who}{port}   breaking into the REPL")

    ser = open_port(port, args.attempts, args.wait)
    if ser is None:
        return 2

    with ser:
        ser.reset_input_buffer()
        # Ctrl-C twice: the first stops code.py, the second is harmless and
        # covers the case where the first landed mid-import.
        ser.write(b"\x03")
        time.sleep(0.3)
        ser.write(b"\x03")
        time.sleep(0.7)

        banner = ser.read(4096).decode("utf-8", "replace")
        if ">>>" not in banner:
            print(
                "[firmware] No REPL prompt. The board may be running something "
                "that ignores Ctrl-C; unplug it, plug it back in, and retry."
            )
            return 1

        for line in SNIPPET:
            ser.write(line.encode("utf-8") + b"\r\n")
            time.sleep(0.3)

        buf = ""
        end = time.perf_counter() + args.timeout
        while time.perf_counter() < end:
            chunk = ser.read(4096)
            if not chunk:
                continue
            buf += chunk.decode("utf-8", "replace")
            if MARKER in buf or "Traceback (most recent call last)" in buf:
                break

        # Ctrl-D: soft reboot, back to the current lesson running normally and
        # auto-reload re-enabled -- same courtesy as tools\verify_board.py.
        ser.write(b"\x04")

    text = ANSI.sub("", buf)

    if "Traceback (most recent call last)" in text:
        print("[firmware] --- board said ---")
        for ln in text.splitlines():
            if ln.strip():
                print(f"           {ln.rstrip()}")
        print("[firmware] ------------------")
        print("[firmware] FAIL: could not talk to the radio (see traceback above).")
        return 1

    _, found, rest = text.partition(MARKER)
    if not found:
        print("[firmware] No reply from the board within the timeout.")
        return 1

    version = rest.splitlines()[0].strip()
    print(f"[firmware] nina-fw version: {version}")

    try:
        if parse_version(version) < EXPECTED:
            print(
                f"[firmware] FAIL: older than {'.'.join(map(str, EXPECTED))}. "
                "Sockets will fail with BrokenPipeError -- flash the current "
                "AirLift firmware before debugging anything else."
            )
            return 1
    except ValueError as exc:
        print(f"[firmware] Could not check the version against {EXPECTED}: {exc}")
        return 1

    print(f"[firmware] OK: {'.'.join(map(str, EXPECTED))} or newer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
