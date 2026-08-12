r"""List the lessons and switch which one the board runs.

    .\.venv\Scripts\python.exe .\tools\lesson.py            pick from a list
    .\.venv\Scripts\python.exe .\tools\lesson.py list       just show them
    .\.venv\Scripts\python.exe .\tools\lesson.py L01_colors switch directly

Switching rewrites the single import line in lessons\code.py and pushes it to
the board, so the change takes effect the same way a save does.

The list is built by scanning lessons\ for folders holding a main.py, and the
synopsis is the first line of that file's docstring. There is no catalogue file
to keep in step -- add a lesson folder and it appears here.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sync import LESSONS, cached, copy, discover

IMPORT_RE = re.compile(r"^from\s+(\w+)\s+import\s+main\s*$", re.MULTILINE)
CODE_PY = os.path.join(LESSONS, "code.py")


def synopsis(folder):
    """First line of main.py's docstring, or a placeholder."""
    path = os.path.join(LESSONS, folder, "main.py")
    try:
        # utf-8-sig, not utf-8: a stray BOM is not whitespace, so it would stop
        # the docstring regex matching and every lesson would look undescribed.
        with open(path, encoding="utf-8-sig") as fh:
            src = fh.read()
    except OSError:
        return "(unreadable)"
    m = re.search(r'^\s*(?:r|u|b)?("""|\'\'\')(.*?)\1', src, re.DOTALL)
    if not m:
        return "(no description -- add a docstring to main.py)"
    for line in m.group(2).splitlines():
        line = line.strip()
        if line:
            return line
    return "(no description -- add a docstring to main.py)"


def lessons():
    """Every folder under lessons\\ that holds a main.py, in name order."""
    try:
        names = sorted(os.listdir(LESSONS))
    except OSError:
        return []
    return [n for n in names
            if os.path.isfile(os.path.join(LESSONS, n, "main.py"))]


def current():
    try:
        with open(CODE_PY, encoding="utf-8-sig") as fh:
            m = IMPORT_RE.search(fh.read())
    except OSError:
        return None
    return m.group(1) if m else None


def show(names, now):
    width = max(len(n) for n in names)
    for i, name in enumerate(names, 1):
        mark = "*" if name == now else " "
        print(f" {mark} {i:2}. {name.ljust(width)}  {synopsis(name)}")
    print("\n   * = running now")


def switch(name):
    """Rewrite the import in code.py, then push code.py to the board."""
    with open(CODE_PY, encoding="utf-8-sig") as fh:
        src = fh.read()
    if not IMPORT_RE.search(src):
        print(f"[lesson] No 'from X import main' line in {CODE_PY}.")
        return 1
    src = IMPORT_RE.sub(f"from {name} import main", src)
    with open(CODE_PY, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(src)
    print(f"[lesson] code.py now runs {name}")

    root = cached() or discover()
    if not root:
        print("[lesson] No board found -- the change is saved, sync when it is plugged in.")
        return 0
    try:
        copy(CODE_PY, os.path.join(root, "code.py"))
    except OSError as exc:
        print(f"[lesson] Could not push code.py to {root}: {exc}")
        return 1
    print(f"[lesson] pushed to {root} -- the board is restarting into it now.")
    return 0


def main():
    names = lessons()
    if not names:
        print(r"[lesson] No lessons found. A lesson is a folder under lessons\ "
              r"containing a main.py.")
        return 1

    arg = sys.argv[1] if len(sys.argv) > 1 else None
    now = current()

    if arg == "list":
        show(names, now)
        return 0

    if arg:
        if arg in names:
            return switch(arg)
        # Allow the number from the list as well as the folder name.
        if arg.isdigit() and 1 <= int(arg) <= len(names):
            return switch(names[int(arg) - 1])
        print(f"[lesson] No lesson called {arg!r}. Available:")
        show(names, now)
        return 1

    print("Lessons:\n")
    show(names, now)
    try:
        choice = input("\nNumber to switch to (Enter to cancel): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n[lesson] cancelled")
        return 0
    if not choice:
        print("[lesson] cancelled")
        return 0
    if not choice.isdigit() or not 1 <= int(choice) <= len(names):
        print(f"[lesson] {choice!r} is not one of the numbers above.")
        return 1
    return switch(names[int(choice) - 1])


if __name__ == "__main__":
    sys.exit(main())
