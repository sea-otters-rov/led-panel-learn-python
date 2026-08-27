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
- **WiFi and sockets work, but only after upgrading the ESP32 firmware.** The
  factory nina-fw **1.2.2** could associate and resolve DNS, yet *every*
  `socket_open` failed with `BrokenPipeError: Expected 01 but got 00` — TCP and
  UDP, unicast and broadcast alike. Modern `adafruit_esp32spi` speaks a
  `startClient` that old firmware rejects. Flashing the all-in-one AirLift
  firmware to **3.3.0** fixed it completely. If a board cannot open a socket,
  check `esp.firmware_version` first.

  Measured on 3.3.0, 2026-08-27:

        connect_AP                        3.9 s, no retries (was 6.8 s and flaky)
        TCP round trip           best 12.1  avg 16.0  worst 22.9 ms
        UDP round trip           best 14.7  avg 19.3  worst 56.9 ms, 0/25 lost
        UDP send, socket_open before each write       7.8 ms   <- do this
        UDP send, brand new socket each time          8.5 ms
        socket_available() poll                       1.2 ms

  A frame costs ~9.2 ms of network work (one send plus one receive), which is
  28% of a 33 ms frame. Affordable, but send every other frame if it gets tight.

- **`socket_write` in UDP mode never clears the radio's send buffer.** Known
  library bug, `Adafruit_CircuitPython_ESP32SPI` issue #135: in nina-fw only
  `beginPacket()` resets the buffer, and `sendUdpData` calls `endPacket()`
  without a `beginPacket()` after it. Write twice on one open socket and the
  second datagram arrives with the first stuck to the front of it.

  **Call `socket_open` before EVERY write** — `socket_open` is `beginPacket`, so
  it flushes. Do not "optimise" it away; the board reports success either way
  and only a second machine listening reveals the corruption. Measured 100/100
  clean with the fix, and 0 concatenated datagrams over 100 sends.

  This also corrects an earlier note here claiming ~1 send in 10 fails. That was
  socket-allocation churn, not the network. There is no meaningful UDP loss.

- **UDP receive needs the raw API; the socketpool cannot do it.**
  `pool.socket(...)` + `bind()` + `recv_into()` hears nothing at all. This works:

        rx = esp.get_socket()
        esp.start_server(port, rx, conn_mode=esp.UDP_MODE)
        avail = esp.socket_available(rx)
        data = esp.socket_read(rx, avail)

  UDP *send* works either way, but keep one socket open and reuse it.

- **Do not mix the raw `esp.get_socket()` API and the socketpool in one program.**
  A raw `socket_open` followed by a pool socket makes the pool socket fail with
  the same `BrokenPipeError`; pool first then raw was fine. Since UDP receive
  has to be raw, use raw throughout for anything with UDP in it.

- **There is no `recvfrom`** — only `recv` and `recv_into` — so a receiver never
  learns who sent a datagram. Any discovery message must carry the sender's
  address in its own payload.

- **Broadcast to the subnet (`192.168.1.255`), not `255.255.255.255`.** The
  global address sends without error but did not arrive; the subnet address is
  reliable in both directions.

- **The ESP32 cannot keep its association across a reload, and the reset is not
  optional.** Tested 2026-08-27 both ways. `reset_dio=None` raises
  (`can't set attribute 'direction'`), and a subclass whose `reset()` skips the
  pulse then fails on the very first command with
  `TimeoutError: ESP32 timed out on SPI select` — a soft reboot leaves the two
  chips out of step on SPI, and the reset pulse is what resynchronises them.

  So every save pays: **0.76 s to reset, plus 2.9–6.8 s for `connect_AP`**
  (highly variable). A networking lesson must therefore bring the matrix up
  first and connect *lazily in the background*, showing a status pixel, rather
  than blocking on the network before anything appears.

- **~2 MB of flash**, ~1.83 MB free with the current library set. Check headroom
  before adding libraries.
- **The serial port is exclusive.** Only one program can hold it, so the Serial
  Monitor panel and `tools\console.ps1` cannot both be open.
  `tools\verify_board.py` forces a reload and reports what the board printed:
  exit 0 running, 1 traceback, 2 port busy, 3 no board. **On a 2, ask the user
  to disconnect whatever holds the port, then retry** — do not skip the check or
  route around it, and do not report a board as unverified when the only problem
  was a busy port. It sends Ctrl-C then Ctrl-D, so the `KeyboardInterrupt` that
  produces is expected; only output after the last `code.py output:` counts.
- Entering the REPL disables auto-reload until Ctrl-D. This is the single most
  common "my saves stopped working" report.

## Canonical commands

Permission rules match the exact command string, so vary these and you buy the
user another approval prompt. Run them from the repo root, one per call:

    .\.venv\Scripts\python.exe .\tools\verify_board.py
    & .\tools\sync.ps1
    & .\tools\sync.ps1 -Clean
    git add -A
    git commit --quiet -F .commitmsg

**Never `git add <paths>`.** Every distinct file list is a different string, so
it can never be allowlisted — it prompts every single time. Stage everything and
say in the message what the commit covers. If the working tree holds someone
else's unfinished work, ask before committing rather than reaching for a path
list.

**Switch lessons by editing `lessons\code.py`, then full-syncing.** Never
`tools\lesson.py <name>` — the lesson name is an argument, so every switch is a
different command string and prompts every single time, exactly like
`git add <paths>`. Editing the one import line and running `& .\tools\sync.ps1`
uses only operations that are already allowlisted. `lesson.py` stays for
students, who click the task and never go through these rules.
(`.\.venv\Scripts\python.exe .\tools\lesson.py list` is invariant, so that one
can be allowlisted if you want the catalogue.)

Full-sync instead of `sync.py <path>`; the path varies, the full sync does not.
Write commit messages to `.commitmsg` (gitignored) rather than a temp file whose
name changes. Never prefix git with `cd` or `git -C` — the rule matches on the
leading token.

**Do not launch the sync through `powershell -File`.** That form spawns a nested
shell and prompts every single time no matter what the allow rules say — proven
after a restart, with a correctly escaped rule present in both settings files.
`& .\tools\sync.ps1` is the same script without the child process, and it
allowlists normally. The VS Code task in `tasks.json` still uses `-File`, which
is fine: students click the task, they do not go through these rules.

A rule added to `.claude\settings.json` mid-session is not read until the app
restarts. Say so when adding one, instead of letting the next prompt reveal it.

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
  which is why they lead with a letter, and they sort into teaching order, which
  is why they are zero-padded.
- **The first docstring line of `main.py` is the lesson's catalogue entry.**
  `tools\lesson.py` scans for folders holding a `main.py` and lists that line, so
  a new lesson appears in the picker with no catalogue file to update. Keep that
  line short and say what the student will *do*, not what the lesson covers.
- **A lesson folder is not on `sys.path`, and the cwd is `/`.** So the two forms
  a student would guess both fail, measured on hardware 2026-08-10:

        from . import helper                 works, no __init__.py needed
        import helper                        ImportError: no module named 'helper'
        open("/L00_does_it_work/data.txt")   works
        open("data.txt")                     OSError: No such file/directory

  Use `from . import helper` for a sibling module and a leading-slash absolute
  path for data files. Deriving the path from `__file__` also works and survives
  a folder rename, but it is too much machinery to put in front of a beginner.
- **Lesson content stays OS-neutral.** A lesson may end up running on a Linux
  laptop, and rewriting twelve lessons is the expensive kind of port. Inside
  `lessons\`, never write:

        E:\ or any drive letter          the mount point differs per OS
        backslash paths                  CircuitPython itself uses /
        PowerShell or bash commands      point at a VS Code task instead
        "the CIRCUITPY drive"            say "the board"

  Board paths are absolute with forward slashes — `/L03_bitmaps/logo.bmp` —
  which is what CircuitPython wants anyway. VS Code UI *is* fine: Ctrl+S, the
  Serial Monitor panel, and the task list are identical on Windows and Linux.
  (Only macOS differs, with Cmd+S, and no Mac is in scope.) Anything genuinely
  per-OS goes in `Readme.md`, which can grow a Linux section without touching a
  single lesson.
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
- **Seven libraries are frozen into the firmware; do not ship them in `lib`.**
  `help("modules")` on the board lists `adafruit_bus_device`,
  `adafruit_connection_manager`, `adafruit_esp32spi`, `adafruit_pixelbuf`,
  `adafruit_portalbase`, `adafruit_requests`, and `neopixel` as built in. A copy
  in `lib\` shadows the frozen one and costs 57.6 KB for nothing. They were
  removed and the frozen versions verified on hardware: `adafruit_lis3dh` still
  reads the accelerometer through frozen `bus_device`, and `neopixel` still
  drives the onboard pixel through frozen `pixelbuf`.

  **circup puts them all back.** They are dependencies of `adafruit_matrixportal`
  and `adafruit_lis3dh`, so `install -r device-requirements.txt` reinstalls every
  one. After any circup run, delete them again and re-sync — or the 57.6 KB
  quietly returns.

## The save path is performance-sensitive

Student laptops are meaningfully slower than the machine this was built on, so
per-save cost matters more than it looks.

`tools\sync.py` runs on every Ctrl+S. **Read its module docstring before
changing how it copies** — it documents three traps that each cost real
debugging time: robocopy silently skipping same-length edits, an `fsync` that
buys nothing, and validating the drive letter on the happy path. Current
budget is ~430 ms host-side and ~850 ms board-side.

`tools\sync.ps1` handles full-tree and `-Clean` syncs and is not on the hot path.

**Those three traps, and the ~430 ms host budget, are Windows findings.** The
board-side numbers below are host-independent and do carry over; the host-side
ones do not. The `fsync` conclusion actively inverts — Windows disables write
caching on removable volumes, Linux page-caches FAT writes, so a Linux port
probably needs the `fsync` back. `discover()` already handles Linux and macOS
mount points; nothing else has been tried off Windows.

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
  hang off `.matrixportal` and `.network`, which nothing here imports.
- `Matrix()` calls `displayio.release_displays()` for you. Go direct without it
  and the first run works, then every save after raises `RuntimeError: Too many
  display busses`. A student meets that on save #2 with nothing on screen to
  explain it.

`adafruit_display_text` is the largest real library cost at 34.8 ms — still 4%
of a save, and the lessons need it. There is no import trimming worth doing.

## Drawing

**`screen.py` at the board root owns all display and sensor setup**, and hands
back real display objects — a lesson only ever touches `.x`, `.y`, `.text`,
`.color`, `.hidden`. Students never see `Matrix`, `Group`, `Palette`, or
`TileGrid`. The rule that keeps this coherent: **lessons get visible things from
`screen`, and only from `screen`.** The backing implementation is then free to
change without touching a lesson.

**`screen.block()` is backed by `vectorio.Rectangle`, not `Bitmap` + `TileGrid`.**
Measured on hardware 2026-08-13, 40 moving 2×2 objects, 60 frames, each owning
its palette so colours can differ:

    variant                              bytes each   ms/frame
    Bitmap + Palette + TileGrid               214.8     17.395
    vectorio.Rectangle + Palette              134.8     13.184

37% less RAM and 24% less compositing time, for a *simpler* five-line
constructor and no library cost — `vectorio` is frozen into the firmware
(`Circle`, `Polygon`, `Rectangle`).

**Practical ceiling is a few hundred `screen.block()` objects.** Measured on the
board 2026-08-13 with the falling-stars lesson: 100 is smooth, 500 is visibly
slow, 1000 runs out of memory. Nothing in the course goes past ~30, so this is
headroom rather than a constraint — but it is the number to quote when a student
asks how many they can have.

**`displayio` auto-refresh tears once a loop moves many objects.** The background
refresh fires between bytecodes, so with ~100 moving blocks it composites a
half-updated frame. `screen.draw()` sets `auto_refresh = False` on first call and
refreshes explicitly. It is **opt-in** — lessons that never call it keep
auto-refresh and cannot freeze, so nothing needed retrofitting.

**Off-screen positions clip silently; they do not raise.** Verified for both
backings at `(70, 40)`, `(-10, -5)`, `(63, 31)`, `(-3, 16)`. This is
load-bearing: it is what lets the accelerometer lesson land *before* `if`, with
no bounds test in front of a beginner. **Re-verify it if the backing ever
changes again.**

**`vectorio.Polygon` is unusable.** Same measurement run:

    vectorio.Circle r=1                       134.8     21.832
    vectorio.Polygon 3-point triangle         118.8    104.834
    vectorio.Polygon 10-point star            150.8    152.783

Polygon is 6–9× slower than a rectangle — 40 of them is 7 fps.

**`vectorio.Circle` is the wrong shape at these sizes, not the wrong speed.**
Mapped with `contains(x, y)` on hardware 2026-08-13: radius 2 rasterises to a
5×5 diamond, and radii 3–4 grow single-pixel spikes off each side. Its 0.55 ms
per object only matters past ~50 objects, so speed was never the real objection.

**`screen.circle(size, color)` is a `Bitmap` + `TileGrid` instead**, lighting a
pixel where `across² + down² <= edge² + 0.5`. That 0.5 is load-bearing: without
it a 4×4 collapses to a 2×2 square. Sizes 4, 6, 8 come out convincingly round;
3 becomes a plus. `make_transparent(0)` keeps the corners see-through.

**A `TileGrid` can hold an animation, and the frame index is free state.** One
wide `Bitmap` holds N frames side by side; `tile_width`/`tile_height` slice it,
and `shape[0] = n` picks the frame (readable too). `screen.burst()` uses this for
an expanding ring, and caches the sheet by `(size, frames)` so fifty fireworks
share one bitmap and pay only for their own `Palette`. Because the index reads
back, **it doubles as per-object state** — the same trick as reading the palette
for brightness, and it is what keeps the course clear of parallel lists and
index iteration.

**`ValueError: tile must be 0--1` means zero tiles, not "0 to 1".** It is
`0` to `count - 1` with `count == 0`, printed without a space. Cause is a sheet
built with `frames = 0` — usually an argument-order slip into `burst()`, which
every-argument-is-an-int makes invisible to Pylance. `burst()` now raises a named
error for `frames < 1` instead.

**Text costs are not where people assume.** Measured 2026-08-27, five
characters, three interleaved passes each, `screen.draw()` per frame:

    operation                                 ms/frame   bytes
    move a block 20x2                             4.49      96
    move a Label, 6x12 glyphs                     4.61    1936
    move a Label, 3x5 glyphs                      4.69    2048
    Label .text = a NEW string, 6x12              9.11
    Label .text = a NEW string, 3x5               8.98
    Label .text = the SAME string                 0.39
    new Label appended every frame               30.27   ~1 KB each, leaked

**Moving a Label is as cheap as moving a block** — the folk belief that text is
slow to move is wrong. *Changing* it costs ~9 ms, but setting the **same** string
is nearly free because the library short-circuits, so `sign.text = str(score)`
every frame is fine. What destroys a frame rate is **creating a Label inside the
loop**: 30 ms a frame and ~1 KB leaked every frame, because it stays in the
group. That is the bug to look for when a student says text made things slow.

**One `screen.text(message, color, x, y, font=...)`, two sizes.** `screen.NORMAL`
is terminalio's 6x12; `screen.SMALL` is a 3x5 font defined in `font.py`. Both
return an ordinary `Label`, so `.text`, `.color`, `.x`, `.y` and variable-length
strings behave identically, and `y` is the middle of the line either way. 3x5
fits 16 characters across and five stacked lines, against 10 and two — which is
the only way six names fit on a 64x32 panel.

`font.SMALL` is a small class implementing the font protocol: `get_bounding_box()`
plus `get_glyph(codepoint)` handing back a cached `fontio.Glyph` pointing into a
tile sheet built once from the `#`/`.` pictures. `fontio.Glyph` is constructible
from Python, which is the whole reason this works.

**A bare `TileGrid` was built for the small font and then rejected.** It is 2x
faster on frames where the text changes (4.5 ms vs 9.0), but `Label`
short-circuits an *unchanged* string at 0.39 ms where a TileGrid rewrite costs
1.17 ms. For a score that changes once a second at 30 fps that is ~12 ms/sec for
`Label` against ~39 ms/sec for the TileGrid — **`Label` wins the normal case**,
and memory is a wash (2048 vs 1936 bytes for five characters) because per-glyph
overhead dominates, not glyph size. **The small font buys screen space, not
speed.** Do not reintroduce a second API for it.

**Glyph size barely moves the frame cost.** A 6x12 tile font built from
`terminalio.FONT`'s own bitmap changed in 8.74 ms against `Label`'s 8.98 — no
real difference. So converting `screen.text()` to tiles for speed is not worth
doing. Related and occasionally useful: **`terminalio.FONT` is itself a sprite
sheet** — `FONT.bitmap` is 570x12, every glyph a fixed 6x12 tile, and
`FONT.get_glyph(ord(c)).tile_index` gives the slot.

**Measure interleaved, never in sequence.** Measuring these one after another
gave 8.79 ms for a Label move that is really 4.61 — dirty-region state carries
between runs. Interleaving three passes made every number stable to 0.01 ms.

**Two things not to "tidy" in `font.py`.** The `# fmt: off` around `SHAPES` is
what stops a formatter squashing each letter onto one line. And the glyphs are
tuples of short strings rather than triple-quoted blocks because the indentation
inside a triple-quoted block is real bytes — 2.2 KB of RAM for the same picture.
Dropping `SHAPES` after building the sheet does not reclaim it either; string
literals live in the module's constant pool. Measured both ways.

A cell is **4x5**: one blank column to the right of each letter, and *no* blank
row underneath. The horizontal gap has to be in the sheet or words run together;
a vertical one does not, because a lesson positions each line itself.

**Draw order is creation order and never changes on its own.** Lighting a
different pooled object does *not* bring it forward. `screen.bring_to_front()`
removes and re-appends it to the group, which is the only way to reorder.

**It is the one thing `screen.py` returns without a pixel `.width`.**
`TileGrid.width` counts *tiles*, so it reads 1 — `tile_width` holds the pixels.
`vectorio.Rectangle.width` is pixels. A lesson using a circle must therefore keep
its size in a variable rather than reaching for `.width`, or
`max_x = screen.WIDTH - ball.width` silently lets the ball overhang the edge.

`adafruit_display_shapes` is **not** installed and should not be — `vectorio`
already does this for free, and `Rect` would collide with `screen.block()` for
no gain.

**Type hints in board-side code are safe.** `screen.py` carries
`def tilt() -> tuple[float, float, float]` and `width: int` parameters, verified
running on hardware 2026-08-13. CircuitPython's compiler discards function
annotations rather than evaluating them, so `tuple[...]` never executes even
though CircuitPython has no `tuple.__class_getitem__`. They still cost a little
compile time on every reload, since source is recompiled each time — worth it in
`screen.py`, not worth it in a lesson file.

**They earn their place by catching lesson traps early.** L04 asks the student
to delete an `int()`; because `block()` is annotated, Pylance red-squiggles it
in the editor and says why, *before* the board ever runs it. Keep `screen.py`
annotated for this reason, not just for autocomplete.

## Colour

There is no `enum` module in CircuitPython, and no `typing` either — both
checked on the board, both absent.

**For an enum-ish set of choices, use a plain class plus a `Literal` annotation.**
`screen.Fonts` is the worked example. Verified on hardware 2026-08-27: a plain
class with attributes works, *annotated* class attributes work, and a `Literal`
annotation on a parameter works — because CircuitPython discards annotations
instead of evaluating them, exactly as it does for `tuple[float, float, float]`.
The `typing` import has to be guarded, which is the standard Adafruit idiom:

    try:
        from typing import Literal
    except ImportError:
        pass

    class Fonts:
        NORMAL: 'Literal["normal"]' = "normal"
        SMALL: 'Literal["small"]' = "small"

    def text(..., font: 'Literal["normal", "small"]' = Fonts.NORMAL):

That gets autocomplete in *both* places — `screen.Fonts.` lists the names, and
typing `font=` offers the values — while the annotations on the constants are
what stop a type checker complaining that a `str` was passed where a `Literal`
was wanted. Anything that only accepts a fixed set of values should also **raise
on a bad one**; without that, a typo silently falls through to the default.

- **`rainbowio.colorwheel(0..255)` is built into the firmware.** 0.1 ms to
  import, returns a packed `0xRRGGBB` int. Use it for anything that cycles.
  Values above 255 **wrap** rather than raising — verified to 1000 — so a lesson
  can hand it `index * 30` without bounds-checking. Negative values return a
  negative int, which is not a usable colour.
- **`lessons\colors.py` owns the names** — `RED`, `CYAN`, `AMBER`, `GOLD`,
  `JADE`, `OLD_LACE`, `RAINBOW`. It lives at the board root, so `import colors`
  works from inside any lesson folder even though a lesson's own siblings do
  not. Values are packed ints, matching `colorwheel` and the hex literals a
  student sees everywhere else.
- **`adafruit_led_animation` was tried and dropped.** 25 KB and 18.6 ms of
  NeoPixel strip-animation machinery to get a list of constants, versus 15.7 ms
  for a file a student can open and extend. If it ever comes back: its constants
  are RGB tuples, not ints, and that is fine — measured on hardware, `displayio`
  converts tuples itself, so `Label(color=RED)` lands in the palette as
  `0xff0000`, byte-identical to passing the int. Do not write conversion helpers.
  (`Label.color` does return whatever you set, so reading it back gives a tuple.)
- **Prose in a board-side `.py` is not free.** `colors.py` imports in 15.7 ms
  with its docstring and 9.4 ms without — ~6 ms to compile the comments, because
  source is compiled on the board every reload while a `.mpy` is not. Keep lesson
  docstrings regardless, since 6 ms is under 1% of a save, but weigh it before
  adding prose to something *every* lesson imports.

Board root is on `sys.path`, so a shared module next to `code.py` — a project
`colors.py`, say — is importable as `import colors` from inside a lesson folder,
even though a lesson's own siblings are not. Verified on hardware.

## Status

Dev environment: done, verified end to end on hardware (2026-08-10).

`lessons\` now holds the board image and one placeholder lesson
(`L00_does_it_work\main.py`, the old `device\code.py`) proving the launcher
works. The `device\` folder is gone; it was renamed, not copied, so
`git log --follow` still tracks the history.

**The sequence, the `screen.py` API, and the house style for lesson code live in
`docs\lesson-plan-notes.md` — read it before writing a lesson.** Keep it true:
it drifted badly once and had to be re-audited against the files.

`docs\lesson-plan.md` is a different document — one page for students and
parents, listing what each lesson builds. It carries no internals, and it does
not mention `L99_breakout_done`.

**Lessons 01–12 are written and verified on hardware**, plus
`L99_breakout_done`, a worked answer to the capstone. 12 ships as a working
scaffold: the wall, the paddle, the score and a four-wall bounce all run, and
five `TODO`s add the collisions, the losing condition and the next level.
`L00_does_it_work` has been deleted; L01 took over its smoke-test job.

The accelerometer lessons are groundwork for students eventually using an
accelerometer to **self-level an ROV**, which is why `screen.tilt()` returns all
three axes rather than the two the matrix needs.

**Audience, decided:** high school students, most with *some* programming
experience — a class, a little Python or Java, some Scratch — but not to be
relied on. Start from the basics and move quickly. The test for a lesson is that
nobody is lost at lesson 1 and nobody is bored by lesson 3. Assume no prior
knowledge of hardware, `displayio`, or the board.

Scope is the 64x32 matrix and the onboard LIS3DH accelerometer. No WiFi — the
ESP32 co-processor would have to be driven over SPI by hand, which is a long way
past the point of this course.
