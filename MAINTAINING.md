# Maintaining learn-py

Everything a student does not need. [Readme.md](Readme.md) is written for them;
this is for whoever sets up the laptops and writes the lessons.

Code lives here, under version control. The board's flash is treated as a build
output — `lessons\` is an exact image of the board's root, and a sync rebuilds
the board from it.

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

## Layout

| Path | What it is |
| --- | --- |
| `lessons\` | An exact image of the board's root. Everything here, and only this, ships. |
| `lessons\code.py` | The launcher. One import line names the lesson that runs. |
| `lessons\L00_*\main.py` | One folder per lesson. The first docstring line is what the picker shows. |
| `lessons\colors.py` | Shared colour names, importable from any lesson as `import colors`. |
| `lessons\lib\` | Board libraries, managed by `circup`. Committed, so a board can be rebuilt offline. |
| `tools\` | `sync.py` (the on-save path), `sync.ps1`, `setup.ps1`, `console.ps1`, `verify_board.py`, `reset_board.py`, `lesson.py`. |
| `ruff.toml` | Lint config. One rule: the launcher's import only looks unused. |
| `firmware\` | The `.uf2` this project is pinned to. |
| `.venv\` | Host-side only: `circup`, stubs, library sources for IntelliSense. Never runs on the board. |

`lessons\settings.toml` is gitignored — it is where credentials go.
`settings.toml.example` at the repo root is the tracked template.

`CLAUDE.md` holds the decisions and the measurements behind them: why the
launcher exists, what the save path costs, which libraries were removed and why.
Read it before changing how anything copies.

---

## Adding a lesson

Create `lessons\L0N_short_name\main.py`. The folder name has to be a valid
Python identifier, which is why it starts with a letter, and the numbers are
zero-padded so they sort into teaching order.

**The first line of the docstring is the lesson's entry in the picker.** There
is no catalogue file. Keep it short and say what the student will *do*:

```python
"""Make the matrix show your own colours."""
```

Lesson content stays OS-neutral — no drive letters, no backslash paths, no shell
commands. A lesson may end up running on a Linux laptop, and rewriting twelve
lessons is the expensive kind of port. VS Code references such as Ctrl+S and the
Serial Monitor panel are fine; they are identical on Windows and Linux.

---

## Common tasks

**Push everything** (after adding a font, bitmap, or new module) — the
**Board: sync all files** task. On-save only copies the file you saved.

**Reset a board to a known-good state** (wipes anything not in `lessons\`):

```powershell
& .\tools\sync.ps1 -Clean
```

**Add a library** — add its name to `device-requirements.txt`, add the matching
PyPI name to `requirements-intellisense.txt`, then run circup by hand and sync:

```powershell
.\.venv\Scripts\circup.exe --path .\lessons --board-id matrixportal_m4 --cpy-version 10.2.1 install -r .\device-requirements.txt
```

There is deliberately no task or setup step for this. Students never change
which libraries exist, and a one-click install sat in their task list brought
the frozen libraries below straight back onto their boards.

Seven libraries are frozen into the firmware and must not be shipped in
`lessons\lib`; circup reinstalls them as dependencies every time it runs, so
delete them again afterwards. `CLAUDE.md` lists which ones and why.

**Reflash the firmware** — double-tap the reset button, wait for the bootloader
drive to appear, then:

```powershell
.\tools\setup.ps1 -Flash
```

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

`python.analysis.extraPaths` points at `lessons\`, which is the board's root, so
a lesson importing `colors` resolves in the editor the same way it does on the
board.

---

## Troubleshooting the toolchain

**"Failed to save 'code.py' ... UNKNOWN (FileSystemError)".**
A sync was still running and holding the file when VS Code tried to write it,
which means the save path got slow. Time one:

```powershell
Measure-Command { .\.venv\Scripts\python.exe .\tools\sync.py .\lessons\code.py }
```

Anything much over 400 ms means something new is slow — read the notes in
`tools\sync.py` before changing how it copies.

**The drive letter changed.** Fine. `sync.ps1` finds the board by volume label
and verifies `boot_out.txt` before writing, never by a hard-coded letter.

**A lesson fails with `SyntaxError` on line 1.** A UTF-8 BOM. CircuitPython does
not skip one. Both sync paths strip it and warn, but the editor that wrote it
will keep writing it — check the encoding indicator in the status bar.

**Tasks fail with `execvpe(...) failed`.** A task ran through WSL. Every task in
`tasks.json` is `"type": "process"` for exactly this reason; a `"shell"` task
would go through the default terminal profile.
