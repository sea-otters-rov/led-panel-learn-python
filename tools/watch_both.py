r"""Watch both boards' serial consoles at once, interleaved and timestamped.

    .\.venv\Scripts\python.exe .\tools\watch_both.py

The "serial port is exclusive" rule in CLAUDE.md is about ONE port: two boards
have two ports, so one process can hold both. That matters more than it sounds
for Part 2. A networking bug is a disagreement between two boards, and reading
one board's console tells you what it believed, never whether the other agreed.
Both sides on one timeline is what turns "the ball vanished" into "A handed off
at t=4.812 and B never printed a receive".

Output is one line per board line, prefixed and coloured:

    12.031 A| here matt 192.168.1.41
    12.044 B| heard matt 192.168.1.41

Times are seconds since this program started, so the two columns share a clock
that neither board has. Board clocks are not comparable -- each resets its own
time.monotonic() on every reload, which during Part 2 is constantly.

Ctrl-C stops it. Add --reload to send Ctrl-C + Ctrl-D to both boards first, so
they start from the top together rather than mid-run.
"""

import argparse
import os
import re
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("pyserial is missing. Run .\\tools\\setup.ps1 first.")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boards  # noqa: E402

ANSI = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-9;?]*[A-Za-z]")

# One colour per board so a wall of interleaved lines stays readable.
COLOUR = {"A": "\x1b[36m", "B": "\x1b[33m"}
RESET = "\x1b[0m"


def open_all(labels):
    """Open every named board's console, or explain which one is unavailable."""
    opened = {}
    for label in labels:
        try:
            board = boards.resolve(label)
        except LookupError as exc:
            print(f"[watch] {exc}")
            return None
        if not board["port"]:
            print(
                f"[watch] Board {label} is mounted at {board['root']} but has "
                f"no serial port. Unplug and replug it."
            )
            return None
        try:
            opened[label] = serial.Serial(board["port"], 115200, timeout=0)
        except (serial.SerialException, OSError) as exc:
            print(f"[watch] Cannot open {board['port']} for board {label}: {exc}")
            print("        Close the VS Code Serial Monitor and any console task,")
            print("        then run this again.")
            for s in opened.values():
                s.close()
            return None
        print(f"[watch] board {label}  {board['port']}  {board['root']}")
    return opened


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--boards", default="A,B", help="labels to watch, comma separated (default A,B)"
    )
    ap.add_argument(
        "--reload",
        action="store_true",
        help="Ctrl-C + Ctrl-D both boards before listening",
    )
    ap.add_argument(
        "--seconds",
        type=float,
        default=0,
        help="stop after this long (default: until Ctrl-C)",
    )
    ap.add_argument("--plain", action="store_true", help="no colour")
    args = ap.parse_args()

    labels = [s.strip() for s in args.boards.split(",") if s.strip()]
    ports = open_all(labels)
    if ports is None:
        return 3

    if args.reload:
        # Ctrl-C breaks into the REPL, Ctrl-D leaves it and reloads -- which is
        # also what re-enables auto-reload. Both boards get it before either is
        # read, so they restart within a few ms of each other.
        for s in ports.values():
            s.reset_input_buffer()
            s.write(b"\x03")
        time.sleep(0.4)
        for s in ports.values():
            s.write(b"\x04")
        print("[watch] reloaded both boards")

    print("[watch] listening -- Ctrl-C to stop")
    started = time.perf_counter()
    deadline = started + args.seconds if args.seconds else None
    buffers = {label: "" for label in labels}

    try:
        while deadline is None or time.perf_counter() < deadline:
            quiet = True
            for label in labels:
                chunk = ports[label].read(4096)
                if not chunk:
                    continue
                quiet = False
                buffers[label] += chunk.decode("utf-8", "replace")

                # Print whole lines only. A partial line stays in the buffer
                # rather than being interleaved into the other board's output.
                while "\n" in buffers[label]:
                    line, _, buffers[label] = buffers[label].partition("\n")
                    line = ANSI.sub("", line).rstrip()
                    if not line:
                        continue
                    stamp = time.perf_counter() - started
                    tint = "" if args.plain else COLOUR.get(label, "")
                    end = "" if args.plain else RESET
                    print(f"{stamp:7.3f} {tint}{label}|{end} {line}", flush=True)
            if quiet:
                time.sleep(0.005)  # nothing waiting; do not spin a core
    except KeyboardInterrupt:
        print("\n[watch] stopped")
    finally:
        for s in ports.values():
            s.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
