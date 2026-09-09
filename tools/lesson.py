r"""List the lessons and switch which one the board runs.

    .\.venv\Scripts\python.exe .\tools\lesson.py            pick from a list
    .\.venv\Scripts\python.exe .\tools\lesson.py list       just show them
    .\.venv\Scripts\python.exe .\tools\lesson.py L101_say_something switch directly

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

# [ \t]* rather than \s*: \s is greedy across newlines, so it ate the file's
# trailing newline and every switch left code.py without one.
IMPORT_RE = re.compile(r"^from\s+(\w+)\s+import\s+main[ \t]*$", re.MULTILINE)
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
    return [n for n in names if os.path.isfile(os.path.join(LESSONS, n, "main.py"))]


def number(folder):
    """The lesson number in a folder name: L101_say_something -> 101.

    The number a student types has to be the number in the folder name, not
    the row's position in the list. The two coincided while lessons were
    L01-L14, and stopped coinciding the moment Part 2 became L201 -- at which
    point typing "13" would have selected lesson 201 without saying so.
    """
    m = re.match(r"L(\d+)_", folder)
    return int(m.group(1)) if m else None


def by_number(names):
    """{lesson number: folder}, skipping anything not numbered."""
    return {number(n): n for n in names if number(n) is not None}


def current():
    try:
        with open(CODE_PY, encoding="utf-8-sig") as fh:
            m = IMPORT_RE.search(fh.read())
    except OSError:
        return None
    return m.group(1) if m else None


def show(names, now):
    width = max(len(n) for n in names)
    last_part = None
    for name in names:
        n = number(name)
        # A blank line between the parts, taken straight off the number.
        part = n // 100 if n else None
        if last_part is not None and part != last_part:
            print()
        last_part = part
        mark = "*" if name == now else " "
        label = "%d." % n if n else ""
        print(f" {mark} {label:>5} {name.ljust(width)}  {synopsis(name)}")
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
        print(
            "[lesson] No board found -- the change is saved, sync when it is plugged in."
        )
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
        print(
            r"[lesson] No lessons found. A lesson is a folder under lessons\ "
            r"containing a main.py."
        )
        return 1

    arg = sys.argv[1] if len(sys.argv) > 1 else None
    now = current()

    if arg == "list":
        show(names, now)
        return 0

    if arg:
        if arg in names:
            return switch(arg)
        # Allow the lesson number as well as the folder name.
        numbered = by_number(names)
        if arg.isdigit() and int(arg) in numbered:
            return switch(numbered[int(arg)])
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
    numbered = by_number(names)
    if not choice.isdigit() or int(choice) not in numbered:
        print(f"[lesson] {choice!r} is not one of the numbers above.")
        return 1
    return switch(numbered[int(choice)])


if __name__ == "__main__":
    sys.exit(main())
