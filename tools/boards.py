r"""Which physical board is which, when more than one is attached.

A student has one board and never needs this: every tool finds the only
CIRCUITPY drive and the only Adafruit serial port. A maintainer working on
Part 2 has two, and then "the first one" is not an answer -- Windows hands out
drive letters in whatever order the boards enumerated, and that order changes
between replugs. This was observed: two boards swapped E: and G: across a
single session, so a cached drive letter silently addressed the wrong board.

The stable handle is the SAMD51's CPU UID. It appears in two places, which is
what makes this work with no board-side code at all:

    <drive>\boot_out.txt        UID:9722D10F364D47532020204D341602FF
    USB serial number           SER=9722D10F364D47532020204D341602FF

So one UID resolves to both the drive to copy onto and the port to listen on.
tools\boards.json maps a short label to a UID; see boards.json.example.

Run this module directly to list what is attached:

    .\.venv\Scripts\python.exe .\tools\boards.py
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = os.path.join(HERE, "boards.json")

UID = re.compile(r"^UID:([0-9A-Fa-f]+)\s*$", re.MULTILINE)


def labels() -> dict:
    """The label -> UID map, or {} if this machine has not set one up."""
    try:
        with open(MAP) as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        return {}
    return {k: v.upper() for k, v in raw.items()
            if not k.startswith("_") and isinstance(v, str)}


def uid_of(root: str) -> str:
    """The CPU UID of the board mounted at `root`, or "" if it is not a board.

    boot_out.txt is written by CircuitPython itself, so reading it is also the
    proof that this is a real board and not a USB stick someone relabelled.
    """
    try:
        with open(os.path.join(root, "boot_out.txt")) as fh:
            text = fh.read()
    except OSError:
        return ""
    if not text.startswith("Adafruit CircuitPython"):
        return ""
    m = UID.search(text)
    return m.group(1).upper() if m else ""


def attached() -> list:
    """Every attached board, as {"uid", "root", "port"}, drive order.

    port is "" when pyserial is missing or the board's port cannot be matched.
    """
    from sync import candidate_roots  # same directory; see its docstring

    ports = {}
    try:
        import serial.tools.list_ports

        for p in serial.tools.list_ports.comports():
            hw = (p.hwid or "").upper()
            if "VID:PID=239A" not in hw:
                continue
            m = re.search(r"SER=([0-9A-F]+)", hw)
            if not m:
                continue
            # MI_00 is the console interface. A second interface appears only
            # when CIRCUITPY_CDC data is enabled, and it is not the console.
            if m.group(1) in ports and "MI_00" not in hw:
                continue
            ports[m.group(1)] = p.device
    except ImportError:
        pass

    found = []
    for root in candidate_roots():
        uid = uid_of(root)
        if uid:
            found.append({"uid": uid, "root": root, "port": ports.get(uid, "")})
    return found


def resolve(label: str) -> dict:
    """The attached board that `label` names.

    Raises LookupError with something actionable, because every failure here is
    a setup problem the caller cannot fix on its own.
    """
    known = labels()
    if not known:
        raise LookupError(
            f"No {os.path.basename(MAP)}. Copy tools\boards.json.example to "
            f"tools\boards.json and put your boards' UIDs in it.")
    if label not in known:
        raise LookupError(
            f"boards.json has no board called {label!r}. "
            f"It knows: {', '.join(sorted(known)) or '(nothing)'}")

    want = known[label]
    for board in attached():
        if board["uid"] == want:
            return board
    raise LookupError(
        f"Board {label!r} (UID {want}) is not attached. "
        f"Attached now: {', '.join(b['uid'] for b in attached()) or '(none)'}")


def main() -> int:
    boards = attached()
    if not boards:
        print("No CircuitPython board found.")
        print("  Check the cable is a DATA cable, not charge-only.")
        print("  If a board sits in the bootloader, press reset once.")
        return 3

    known = labels()
    by_uid = {uid: label for label, uid in known.items()}

    print(f"{'label':<7}{'drive':<8}{'port':<8}uid")
    for b in boards:
        label = by_uid.get(b["uid"], "-")
        print(f"{label:<7}{b['root']:<8}{b['port'] or '?':<8}{b['uid']}")

    unknown = [b for b in boards if b["uid"] not in by_uid]
    if unknown and len(boards) > 1:
        print()
        print("Boards showing '-' are not in boards.json, so -Board cannot "
              "address them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
