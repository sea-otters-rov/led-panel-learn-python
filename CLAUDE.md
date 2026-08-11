# learn-py

A step-by-step Python tutorial for high school students, running CircuitPython
10.2.1 on an Adafruit MatrixPortal M4 (64x32 RGB matrix).

`Readme.md` covers setup and the daily workflow. This file is orientation for
working *on* the project.

## Hardware facts that change decisions

- **MatrixPortal M4 = SAMD51J19 + an ESP32 co-processor.** It has no native
  WiFi, so there is no web workflow and no BLE workflow. USB is the only way on
  or off the board: the CIRCUITPY mass-storage drive, and the USB CDC serial
  console. `CIRCUITPY_WIFI_*` and `CIRCUITPY_WEB_API_*` keys in `settings.toml`
  do nothing on this board — the stock Adafruit demo ships with them anyway.
- **~2 MB of flash**, ~1.83 MB free with the current library set. Check headroom
  before adding libraries.
- **The serial port is exclusive.** Only one program can hold it, so the Serial
  Monitor panel and `tools\console.ps1` cannot both be open.
- Entering the REPL disables auto-reload until Ctrl-D. This is the single most
  common "my saves stopped working" report.

## Invariants

- **`lessons\` is an exact image of the board's root.** Anything that is not
  board content lives outside it — which is why `settings.toml.example` sits at
  the repo root. This is what lets `sync.ps1 -Clean` trust robocopy `/PURGE`.
  It carries `lib\` and `settings.toml` as well as the lesson files, because the
  board's root has to.
- **`code.py` is a launcher, not lesson content.** It holds one import naming
  the current lesson; changing that line is how a student moves on. Verified on
  hardware: no `__init__.py` is needed, tracebacks name the lesson file and its
  real line number, and editing a lesson file is 13% *faster* per save than the
  flat layout it replaced.
- **One folder per lesson, always with a `main.py`.** `L00_does_it_work\main.py`,
  imported as `from L00_does_it_work import main`. A lesson that grows a bitmap,
  a font, or a helper module keeps them in its own folder instead of scattering
  them across the board root. Folder names must be valid Python identifiers,
  which is why they lead with a letter.
- **A lesson folder is not on `sys.path`, and the cwd is `/`.** So the two forms
  a student would guess both fail, measured on hardware 2026-08-10:

        from . import helper                 works, no __init__.py needed
        import helper                        ImportError: no module named 'helper'
        open("/L00_does_it_work/data.txt")   works
        open("data.txt")                     OSError: No such file/directory

  Use `from . import helper` for a sibling module and a leading-slash absolute
  path for data files. Deriving the path from `__file__` also works and survives
  a folder rename, but it is too much machinery to put in front of a beginner.
- **`ruff.toml` exists for one rule.** The launcher's import looks unused to
  F401, and `ruff --fix` would delete it and leave the board running nothing.
  Ruff is not in `setup.ps1`, so only maintainers ever see this; students have
  no linter.
- **Save = deploy.** Writing to CIRCUITPY is what triggers auto-reload, so
  copying a file *is* running it. Autosave is off deliberately; with it on,
  every pause in typing would push a half-written file and restart the board.
- **Stub version tracks firmware.** `circuitpython-stubs` is pinned to 10.2.1 to
  match `firmware\*.uf2`. Bump them together, or autocomplete quietly lies.
- **`lessons\lib` is committed.** circup installs into the repo (`--path
  .\lessons`), not onto the board, so a board can be rebuilt offline and
  identically. Students never run circup; adding a library is a maintainer job
  followed by a full sync.

## The save path is performance-sensitive

Student laptops are meaningfully slower than the machine this was built on, so
per-save cost matters more than it looks.

`tools\sync.py` runs on every Ctrl+S. **Read its module docstring before
changing how it copies** — it documents three traps that each cost real
debugging time: robocopy silently skipping same-length edits, an `fsync` that
buys nothing, and validating the drive letter on the happy path. Current
budget is ~430 ms host-side and ~850 ms board-side.

`tools\sync.ps1` handles full-tree and `-Clean` syncs and is not on the hot path.

**The board-side ~850 ms is not import cost, so do not chase it.** Measured
2026-08-10, 5 interleaved trials, medians in ms:

    variant                        wall   board work   fixed   matrix import
    adafruit_matrixportal.matrix  873.3         78.1   795.2            12.1
    rgbmatrix + framebufferio     860.3         64.0   796.3             0.2
    ...and no adafruit_display_text
                                  818.2         24.9   793.3             0.2

~795 ms of it is auto-reload debounce plus the soft reboot, flat to within 3 ms
however the display is brought up — 91% of the total, and not tunable. **We keep
`from adafruit_matrixportal.matrix import Matrix`.** Talking to rgbmatrix
directly saves 13 ms (1.5%), and costs ~10 lines of pin configuration on day one.

Two things that survey turned up, both worth more than the 13 ms:

- The chain everyone assumes is expensive is not being loaded. `matrix.mpy` is
  2 KB and `adafruit_matrixportal\__init__.py` is empty; portalbase and esp32spi
  hang off `.matrixportal` and `.network`, which nothing here imports. The
  network libraries are 55% of `lessons\lib` and cost 0 ms — trim them for
  clutter if you like, never for speed.
- `Matrix()` calls `displayio.release_displays()` for you. Go direct without it
  and the first run works, then every save after raises `RuntimeError: Too many
  display busses`. A student meets that on save #2 with nothing on screen to
  explain it.

`adafruit_display_text` is the largest real library cost at 34.8 ms — still 4%
of a save, and the lessons need it. There is no import trimming worth doing.

## Status

Dev environment: done, verified end to end on hardware (2026-08-10).

`lessons\` now holds the board image and one placeholder lesson
(`L00_does_it_work\main.py`, the old `device\code.py`) proving the launcher
works. The `device\` folder is gone; it was renamed, not copied, so
`git log --follow` still tracks the history.

Writing the actual lesson sequence is the next piece of work. Whether it should
assume zero prior programming experience is still an open question.
