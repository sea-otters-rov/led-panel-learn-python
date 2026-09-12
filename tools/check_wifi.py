r"""Say why a board cannot join the wifi: can it SEE the network, and is it let in?

Run this when one board will not join and another one will. It answers the two
questions that separate a broken board from a network that is refusing it:

    can the radio see the network?   a scan, with signal strength and channel
    is it allowed to associate?      connect_AP, twice, with the status code

    .\.venv\Scripts\python.exe .\tools\check_wifi.py --board B

Breaks into the REPL (same as tools\check_firmware.py) and drives the radio
directly, so nothing depends on the lesson that happens to be on the board. It
uses the SSID and password from the board's own settings.toml, which is the
copy that matters. Leaves the board running normally afterwards.

Reading the result:

    NOT SEEN in the scan      wrong SSID, out of range, or a 5 GHz-only
                              network -- this radio is 2.4 GHz only
    seen, and joins           the board is fine
    seen, but will not join   the network is refusing THIS board. Check the
                              access point's client list for a stale entry:
                              2026-09-12, a NETGEAR listed a board as connected
                              at an address it no longer held, and dropped every
                              fresh association from that MAC until the router
                              was rebooted. The board joined a phone hotspot
                              throughout, which is what proved the board was
                              innocent -- try that before reflashing anything.

Exit codes:
    0  joined
    1  did not join, or the radio could not be driven
    2  serial port is busy -- disconnect the other program and re-run
    3  no CircuitPython board found, or two were found and neither was named
"""

import argparse
import os
import re
import sys
import time

# Reuse the sibling tools rather than restating port discovery a third time.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verify_board import Ambiguous, find_port, open_port

ANSI = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-9;?]*[A-Za-z]")
MARKER = "WIFICHK:"

# What nina-fw's status byte means. 3 is the only good one.
STATUS = {
    0: "idle",
    1: "no such network (the radio's own scan did not find it)",
    2: "scan finished",
    3: "connected",
    4: "connection failed",
    5: "connection lost (it associated, then was dropped)",
    6: "disconnected",
    7: "listening as an access point",
}

# One statement per line: the REPL runs each on Enter, so nothing here can need
# paste mode. That rules out `for` and `try`, hence the list comprehension and
# the conditional expression below. A failed connect_AP raises and prints a
# traceback, which is fine -- the REPL carries on, and the next line reports the
# status code that explains it.
#
# The marker is split so the console's echo of the command cannot match it; only
# the board's own print() reassembles it.
M = f'"{MARKER[:4]}" + "{MARKER[4:]}" + '

SNIPPET = [
    "import os",
    "import board",
    "from digitalio import DigitalInOut",
    "import adafruit_esp32spi.adafruit_esp32spi as esp32spi",
    "_esp = esp32spi.ESP_SPIcontrol(board.SPI(), DigitalInOut(board.ESP_CS), "
    "DigitalInOut(board.ESP_BUSY), DigitalInOut(board.ESP_RESET))",
    '_want = os.getenv("WIFI_SSID")',
    f'print({M}"ssid " + str(_want))',
    "_seen = [a for a in _esp.scan_networks() "
    'if str(a.ssid, "utf-8", "replace") == _want]',
    f'print({M}"signal " + (str(_seen[0].rssi) + " dBm, channel " '
    '+ str(_seen[0].channel) if _seen else "NOT SEEN"))',
    '_esp.connect_AP(_want, os.getenv("WIFI_PASSWORD"))',
    f'print({M}"attempt1 status " + str(_esp.status))',
    'None if _esp.is_connected else _esp.connect_AP(_want, os.getenv("WIFI_PASSWORD"))',
    f'print({M}"attempt2 status " + str(_esp.status))',
    f'print({M}"address " + (_esp.pretty_ip(_esp.ip_address) '
    'if _esp.is_connected else "none"))',
    f'print({M}"done")',
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--timeout",
        type=float,
        default=45.0,
        help="seconds to wait for the whole check (default 45)",
    )
    ap.add_argument(
        "--attempts",
        type=int,
        default=3,
        help="tries at opening a busy port (default 3)",
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
            print(f"[wifi] {exc}")
            return 3
        if not port:
            print(
                f"[wifi] Board {args.board!r} is mounted but has no serial "
                f"port. Unplug and replug it."
            )
            return 3

    if not port:
        try:
            port = find_port()
        except Ambiguous as exc:
            print(f"[wifi] {exc}")
            print("       Say which one: --board A  (see tools\\boards.json)")
            return 3

    if not port:
        print("[wifi] No Adafruit USB serial port found.")
        print("       Check the cable is a DATA cable, not charge-only.")
        return 3

    who = f"board {args.board}, " if args.board else ""
    print(f"[wifi] {who}{port}   breaking into the REPL")

    ser = open_port(port, args.attempts, args.wait)
    if ser is None:
        return 2

    with ser:
        ser.reset_input_buffer()
        ser.write(b"\x03")
        time.sleep(0.3)
        ser.write(b"\x03")
        time.sleep(0.7)

        banner = ser.read(4096).decode("utf-8", "replace")
        if ">>>" not in banner:
            print(
                "[wifi] No REPL prompt. The board may be running something that "
                "ignores Ctrl-C; unplug it, plug it back in, and retry."
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
            if MARKER + "done" in buf:
                break

        # Ctrl-D: soft reboot, back to the lesson, auto-reload re-enabled.
        ser.write(b"\x04")

    text = ANSI.sub("", buf)
    said = {}
    for line in text.splitlines():
        _, found, rest = line.partition(MARKER)
        if found:
            key, _, value = rest.strip().partition(" ")
            said[key] = value

    if not said:
        print("[wifi] No reply from the board within the timeout.")
        if "Traceback (most recent call last)" in text:
            print("[wifi] --- board said ---")
            for ln in text.splitlines():
                if ln.strip():
                    print(f"       {ln.rstrip()}")
            print("[wifi] ------------------")
        return 1

    print(f"[wifi] settings.toml wants: {said.get('ssid', '?')}")
    print(f"[wifi] in the scan:         {said.get('signal', '?')}")

    for n in ("1", "2"):
        raw = said.get("attempt" + n)
        if not raw:
            continue
        code = raw.rsplit(" ", 1)[-1]
        meaning = STATUS.get(int(code), "unknown") if code.isdigit() else "?"
        print(f"[wifi] attempt {n}:           status {code}, {meaning}")

    address = said.get("address", "none")
    if address != "none":
        print(f"[wifi] OK: joined, address {address}")
        return 0

    if said.get("signal") == "NOT SEEN":
        print(
            "[wifi] FAIL: the radio cannot see that network at all. Check the "
            "SSID spelling, the distance, and that it is 2.4 GHz -- this radio "
            "cannot use 5 GHz."
        )
    else:
        print(
            "[wifi] FAIL: the network can be seen but will not let this board "
            "in. Try the same board on a phone hotspot: if THAT works, the "
            "board is fine and the access point is refusing it -- look for a "
            "stale entry for its MAC in the router's client list, and reboot "
            "the router. See this file's notes."
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
