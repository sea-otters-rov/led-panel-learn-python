# Learning Python: Interactive Lessons on a Matrix Portal M4 using CircuitPython 10.2.1

Code lives here, on the hard drive, under version control. The board's flash is
treated as a build output. **Ctrl+S deploys and runs.**

---

## Set up a new laptop

Install [VS Code](https://code.visualstudio.com/) and
[Python 3.10+](https://www.python.org/downloads/), clone this repo, then:

```powershell
.\tools\setup.ps1
```

That installs the VS Code extensions, builds `.venv`, fetches version-matched
stubs, and downloads the board libraries into `lessons\lib`. It is idempotent.

To also wipe an attached board and load this project onto it:

```powershell
.\tools\setup.ps1 -Provision
```

Then open the folder in VS Code and accept the recommended extensions.
Ctrl+Shift+P → *Python: Select Interpreter* → `.venv`.

---

## The daily loop

1. Open the serial console (once per session):
   Ctrl+Shift+P → **Serial Monitor: Focus on Monitor View** → pick the COM port →
   **Start Monitoring**.
   *Any baud rate works. USB CDC ignores it — 115200 is just convention.*
2. Edit anything under `lessons\`.
3. **Ctrl+S.**

On save, VS Code copies that one file to the board. Writing to CIRCUITPY is what
makes CircuitPython restart, so the save *is* the run. Roughly a second later the
console shows:

```
Code stopped by auto-reload. Reloading soon.
soft reboot

Auto-reload is on. Simply save files over USB to run them or enter REPL to disable.
code.py output:
showing: hello
```

Typos land in the same place, with a line number:

```
Traceback (most recent call last):
  File "code.py", line 33, in <module>
NameError: name 'MESSSAGE' isn't defined
```

Fix it, Ctrl+S, and it recovers on its own.

**Autosave is deliberately off.** With it on, every pause in typing would push a
half-written file to the board and restart it mid-edit.

---

## Layout

| Path | What it is |
| --- | --- |
| `lessons\` | An exact image of the board's root. Everything here, and only this, ships. |
| `lessons\code.py` | The launcher. One import line names the lesson that runs. |
| `lessons\L00_*\main.py` | One folder per lesson, each with a `main.py`. This is where you work. |
| `lessons\lib\` | Board libraries, managed by `circup`. Committed, so a board can be rebuilt offline. |
| `tools\` | `sync.py` (the on-save path), `setup.ps1`, `sync.ps1`, `console.ps1`, `verify_board.py`. |
| `ruff.toml` | Lint config. One rule: the launcher's import only looks unused. |
| `firmware\` | The `.uf2` this project is pinned to. |
| `.venv\` | Host-side only: `circup`, stubs, library sources for IntelliSense. Never runs on the board. |

`lessons\settings.toml` is gitignored — it is where credentials go.
`settings.toml.example` at the repo root is the tracked template.

---

## Why IntelliSense works

Two things are installed into `.venv`, and neither ever executes:

- **`circuitpython-stubs==10.2.1`** — the built-in modules (`board`, `displayio`,
  `rgbmatrix`, `digitalio`). Pinned to the firmware version, because the stubs
  are generated per release; a mismatch means autocomplete quietly lies to you.
  `circuitpython_setboard matrixportal_m4` points the `board` stubs at this
  board's real pinout.
- **`requirements-intellisense.txt`** — the plain-Python source of the Adafruit
  libraries that ship to the board as `.mpy`. Compiled `.mpy` is opaque to the
  editor, so without these, every `from adafruit_display_text import label` is a
  red squiggle with no completions. Installed with `--no-deps` to avoid pulling
  in Blinka.

---

## Common tasks

**Move to the next lesson** — open `lessons\code.py` and change the one import:

```python
from L01_colors import main
```

Ctrl+S. That is the whole thing; the lessons are already on the board. If a
lesson has a mistake in it, the traceback names the *lesson* file and line, not
`code.py`.

Each lesson is its own folder with a `main.py` inside, so a lesson that needs a
bitmap, a font, or a second module keeps them together in one place.

**Check the board is working** — Ctrl+Shift+P → *Run Task* → **Board: verify**.
It forces a reload and prints what the board said, which is the quickest way to
tell a broken lesson from a broken board. **Stop Monitoring in the Serial Monitor
panel first** — the port is exclusive, and the task will tell you so if you
forget.

**Push everything** (after adding a font, bitmap, or new module) —
Ctrl+Shift+P → *Run Task* → **Board: sync all files**. On-save only copies the
file you saved.

**Reset a board to a known-good state** (wipes anything not in `lessons\`):

```powershell
.\tools\sync.ps1 -Clean
```

**Add a library** — add its name to `device-requirements.txt`, add the matching
PyPI name to `requirements-intellisense.txt`, then run the
**Board: install libraries into lessons\lib** task and sync.

**Reflash the firmware** — double-tap the reset button, wait for the bootloader
drive to appear, then:

```powershell
.\tools\setup.ps1 -Flash
```

---

## Troubleshooting

**Saving stopped doing anything.**
Almost always the REPL. Pressing any key in the console drops you into the REPL,
which *disables auto-reload*. Press **Ctrl+D** to reload and re-enable it.

**"Failed to save 'code.py' ... UNKNOWN (FileSystemError)".**
A sync was still running and holding the file when VS Code tried to write it,
which means the save path got slow. Time one:
`Measure-Command { .\.venv\Scripts\python.exe .\tools\sync.py .\lessons\code.py }`.
Anything much over 400 ms means something new is slow — see the notes in
`tools\sync.py` before changing how it copies.

**No CIRCUITPY drive.**
Usually a charge-only USB cable. Otherwise press reset once — the board may be
sitting in the bootloader.

**The console won't connect.**
Only one program can hold a COM port. Close the Serial Monitor panel before
using the **Board: serial console** task, and vice versa.

**The console went silent and won't come back.**
A hard reset (the reset button, or unplugging) drops the USB port entirely, and
Serial Monitor does not reconnect by itself — hit **Start Monitoring** again.
A save-triggered reload is a *soft* reboot and keeps the connection.

**The drive letter changed.**
Fine. `sync.ps1` finds the board by volume label and verifies `boot_out.txt`
before writing, never by a hard-coded letter.

**Out of space.** The board has about 2 MB total. `sync.ps1` prints free space
after a full sync.

**The filesystem got corrupted.** In the REPL:

```python
import storage; storage.erase_filesystem()
```

Then run `.\tools\sync.ps1 -Clean`.

**Don't "safely eject" CIRCUITPY.** It stays mounted for the whole session by
design; ejecting it just makes saving stop working.
