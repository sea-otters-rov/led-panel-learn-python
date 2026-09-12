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

   THIS ONE IS WINDOWS-ONLY. Linux page-caches writes to a FAT volume, so the
   save may sit in RAM and never trigger auto-reload. A Linux port will most
   likely need the fsync put back, or the volume mounted with flush/sync.
   Re-measure there; do not inherit this conclusion.

   That ~850ms is CircuitPython's auto-reload debounce plus the soft reboot and
   re-importing libraries. It is not tunable: supervisor.runtime exposes
   `autoreload` as an on/off bool, with no delay setting.

3. DO NOT validate the cached drive letter up front. Probing the FAT volume
   costs ~100ms per save. Just attempt the copy; a failure triggers rediscovery
   and one retry, so a replugged board or a changed drive letter self-heals.

   With TWO boards attached that self-healing is not enough, because the wrong
   board is a copy that succeeds. Set LEARNPY_BOARD to a label in
   tools\boards.json and the cached drive is checked against that board's CPU
   UID before use. Measured cost of the check, median of 200:

       cached(), student: no pin                202 us
       cached(), maintainer: UID validated      518 us

   So the pinned path adds ~0.3ms, not the ~100ms above -- reading one small
   boot_out.txt is not the same thing as probing the volume. The student path
   is untouched: LEARNPY_BOARD is unset, so it is one os.environ.get and no
   extra open(). Nobody without two boards pays anything.

   Unset, with two boards attached, sync.py REFUSES rather than picking the
   first. Two boards were seen swapping E: and G: across one session, so
   "the first one" is not stable even within a single afternoon.

   LEARNPY_BOARD=all copies to EVERY attached board instead, which is what a
   maintainer running both ends of a Part 2 lesson wants: one Ctrl+S, both
   panels. It is the one path that does not cache the drive list, because a
   stale list would silently skip a board plugged in since the last save --
   and a save that quietly reaches one board out of two is exactly the failure
   the refusal above exists to prevent. A full scan of the drive letters costs
   8.8 ms median / 20 ms worst, measured over 200 runs, against a ~430 ms save.

   The boards are written in parallel, so the second one is nearly free.
   Measured end to end, nine interleaved saves each:

       LEARNPY_BOARD=A      median 425 ms   best 380   worst 437
       LEARNPY_BOARD=all    median 577 ms   best 520   worst 603

   Sequential writes would have cost ~900 ms. It stays opt-in anyway, because
   two boards are usually two people, and because a maintainer deliberately
   running different lessons on each board wants a save to land on one.

A UTF-8 BOM on a .py file is stripped on the way to the board, with a warning.
CircuitPython does not skip one, and the SyntaxError it raises names line 1 and
points at a valid docstring. PowerShell's `Set-Content -Encoding utf8` writes a
BOM by default, which is how this got found.

Keep imports to os and sys. Even `shutil` costs measurable startup. That rule is
also why discovery walks directories with os.listdir instead of importing glob.

Board discovery is cross-platform. Every measurement above was taken on Windows
and none of it should be assumed to carry over -- see trap 2 especially.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LESSONS = os.path.normcase(os.path.join(os.path.dirname(HERE), "lessons"))
CACHE = os.path.join(HERE, ".circuitpy")


def candidate_roots(parents=None):
    """Places a mounted CIRCUITPY could be, likeliest first.

    Windows hands out drive letters. Everywhere else the desktop auto-mounter
    puts removable media under a per-user directory, and which one depends on
    the environment: GNOME/udisks2 uses /media/$USER, several distros use
    /run/media/$USER, macOS uses /Volumes. A volume actually named CIRCUITPY is
    tried before its neighbours so the usual case costs one open().

    `parents` overrides the directories to scan, which is how the POSIX branch
    gets tested without needing a real mount.
    """
    if os.name == "nt" and parents is None:
        return [c + ":\\" for c in "DEFGHIJKLMNOPQRSTUVWXYZ"]

    if parents is None:
        user = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
        parents = ("/media/" + user, "/run/media/" + user, "/media", "/Volumes")

    named, others = [], []
    for parent in parents:
        try:
            entries = sorted(os.listdir(parent))
        except OSError:
            continue  # that mount point does not exist on this machine
        for name in entries:
            path = os.path.join(parent, name)
            if os.path.isdir(path):
                (named if name == "CIRCUITPY" else others).append(path)
    return named + others


# Returned by discover() when it found boards but cannot tell which was meant.
# Distinct from None so the caller does not advise checking the USB cable when
# the cable is fine and the problem is that there are two of them.
AMBIGUOUS = "ambiguous"

# Returned by wanted_uid() for LEARNPY_BOARD=all. An object(), not a string, so
# it can never be mistaken for a UID and never reaches discover().
EVERY = object()


def board_uid(root):
    """The CPU UID of the board at `root`, or None if it is not a board.

    boot_out.txt is written by CircuitPython itself, so its presence is proof
    this is a real board and not a USB stick someone labelled CIRCUITPY. The
    UID line is what tells two attached boards apart; the drive letter does
    not, because it changes between replugs.
    """
    try:
        with open(os.path.join(root, "boot_out.txt")) as fh:
            text = fh.read()
    except OSError:
        return None
    if not text.startswith("Adafruit CircuitPython"):
        return None
    for line in text.splitlines():
        if line.startswith("UID:"):
            return line[4:].strip().upper()
    return ""  # a board, but an old firmware that does not print its UID


def wanted_uid():
    """The UID this machine is pinned to, from LEARNPY_BOARD. Usually None.

    A student has one board and never sets this. A maintainer running two at
    once sets LEARNPY_BOARD=A so that Ctrl+S keeps going to the same physical
    board no matter how the drive letters land. See tools\\boards.py.

    LEARNPY_BOARD=all returns EVERY, the copy-to-all-of-them sentinel.

    Raises LookupError for a label that is set but unknown. Falling back to
    "whichever board" there would be the worst of both worlds: the save looks
    fine and lands somewhere nobody chose.
    """
    label = os.environ.get("LEARNPY_BOARD")
    if not label:
        return None
    if label.strip().lower() == "all":
        return EVERY
    import boards  # slow path only -- json and re are not free at startup

    known = boards.labels()
    try:
        return known[label.strip()]
    except KeyError:
        raise LookupError(
            f"LEARNPY_BOARD={label!r} is not in tools\\boards.json. "
            f"It knows: {', '.join(sorted(known)) or '(nothing)'}"
        )


def discover(want=None):
    """Find the board. Only runs on the first save, or after a copy fails.

    With two boards attached, picking the first is not an answer: you get a
    successful-looking save onto the board you were not watching. Refuse
    instead, unless `want` names which UID is meant.
    """
    found = []
    for root in candidate_roots():
        uid = board_uid(root)
        if uid is None:
            continue
        if want and uid != want:
            continue
        found.append((root, uid))
        if want:
            break

    if not found:
        return None
    if len(found) > 1:
        print(f"[sync] {len(found)} boards attached: {', '.join(r for r, _ in found)}.")
        print(
            "       Set LEARNPY_BOARD=A (see tools\\boards.json) so saves go "
            "to a known one."
        )
        return AMBIGUOUS

    root, uid = found[0]
    try:
        with open(CACHE, "w") as fh:
            # The UID rides along so the happy path can tell a shuffled drive
            # letter from the board it was actually pinned to.
            fh.write(root + "\n" + (uid or ""))
    except OSError:
        pass
    return root


def cached(want=None):
    """The remembered drive, checked against `want` when one is given.

    Reading boot_out.txt costs ~100ms, so it happens ONLY in the two-board
    maintainer case. A student's save never pays for it -- see trap 3 in the
    module docstring, which is still the rule for the ordinary path.
    """
    try:
        with open(CACHE) as fh:
            parts = fh.read().split("\n")
    except OSError:
        return None

    root = parts[0].strip()
    if not root:
        return None

    if want and board_uid(root) != want:
        return None  # letters moved; discover() will find the right board

    return root


BOM = b"\xef\xbb\xbf"


def copy(src, dst):
    d = os.path.dirname(dst)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(src, "rb") as fh:
        data = fh.read()
    # CircuitPython does not skip a UTF-8 BOM. It reaches those three bytes
    # before the first line and reports "line 1: SyntaxError: invalid syntax",
    # pointing at a docstring that is perfectly valid -- a dead end for a
    # student. Strip it rather than ship a file the board cannot parse, but say
    # so, because the editor that wrote it will keep writing it.
    if src.endswith(".py") and data.startswith(BOM):
        data = data[len(BOM) :]
        print(
            f"[sync] stripped a UTF-8 BOM from {os.path.basename(src)} -- "
            f"the board cannot parse one. Save it as UTF-8 without BOM."
        )
    with open(dst, "wb") as fh:
        fh.write(data)


def copy_to_every_board(src, rel):
    """Put one file on every attached board. LEARNPY_BOARD=all.

    Deliberately looks for the boards every time instead of remembering them.
    The cached-drive trick the rest of this file uses works because a wrong or
    stale drive makes the copy FAIL, which triggers rediscovery -- but a board
    plugged in since the last save breaks nothing and fails nothing, so a
    remembered list would just quietly leave it behind. Scanning costs ~9 ms
    against a save that already costs hundreds.

    Reports every board it wrote to, and says so loudly if any of them failed:
    a partial save here means two boards running different code, which is the
    hardest kind of Part 2 bug to see.
    """
    roots = [root for root in candidate_roots() if board_uid(root) is not None]
    if not roots:
        print("[sync] No CIRCUITPY drive found.")
        print("       Check the USB cable is a DATA cable, not charge-only.")
        print("       If the board is in the bootloader, press reset once.")
        return 1

    trouble = {}
    if len(roots) == 1:
        # The ordinary case for anyone who set this and then unplugged a board.
        # No threads, so no reason for one attached board to cost more here.
        try:
            copy(src, os.path.join(roots[0], rel))
        except OSError as exc:
            trouble[roots[0]] = exc
    else:
        # Two boards are two USB volumes and the writes genuinely overlap:
        # measured 812 ms one after the other against 464 ms together, where
        # a single board is 309 ms. Nearly all of a save is the flash waiting,
        # not the CPU, so threads are the right tool even in Python. The import
        # is in here rather than at the top so the student path -- os and sys,
        # and see the module docstring on why that matters -- never pays it.
        import threading

        def put(root):
            try:
                copy(src, os.path.join(root, rel))
            except OSError as exc:
                trouble[root] = exc

        threads = [threading.Thread(target=put, args=(root,)) for root in roots]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    done = [root for root in roots if root not in trouble]
    failed = [f"{root} ({exc})" for root, exc in trouble.items()]

    if failed:
        if done:
            print(f"[sync] {rel} -> {', '.join(done)}")
        print(f"[sync] FAILED for {', '.join(failed)}")
        print("       Those boards are now running different code. Fix and save again.")
        return 1

    print(f"[sync] {rel} -> {', '.join(done)}")
    return 0


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
    rel = src[len(LESSONS) + 1 :]

    try:
        want = wanted_uid()
    except LookupError as exc:
        print(f"[sync] {exc}")
        return 1

    if want is EVERY:
        return copy_to_every_board(src, rel)

    root = cached(want)
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
            root = discover(want)
            if root is AMBIGUOUS:
                return 1  # discover() already said what to do about it

    if not root:
        print("[sync] No CIRCUITPY drive found.")
        print("       Check the USB cable is a DATA cable, not charge-only.")
        print("       If the board is in the bootloader, press reset once.")
        return 1

    print(f"[sync] copy of {rel} failed: {last}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
