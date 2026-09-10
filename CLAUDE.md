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

- **Board-to-board is now verified.** Measured 2026-08-27 with two real boards
  on nina-fw 3.3.0, both running the same file (`lessons\spike_two_boards`),
  captured on one clock with `tools\watch_both.py`:

        connect_AP, board to board          3.1 - 5.2 s
        unicast round trip     best 18.7  median 24-30  worst 267-407 ms
        unicast loss                        0-4 per 25, run to run
        both boards broadcasting each frame 14.8-15.1 ms/frame avg, 28 worst
        messages received                   ~1 per frame, 119-121 per 120

  **The round trip is roughly double the laptop number** in the table above
  (median 24-30 ms against 16.0), and the tail is far worse. Some of that is
  the partner's own polling interval rather than the network — a board only
  answers when its loop next calls `receive()` — but that is exactly what a
  game pays, so it is the number to design against. **The 33 ms frame still
  holds** with both boards talking flat out, with ~18 ms of headroom.

- **A board does NOT hear its own broadcast. It DOES hear its own unicast.**
  Measured on both boards, each message tagged with its sender's id:

        own broadcast    0
        own unicast      1     (sent to the board's own address)
        partner's        1     (so a zero is not a dead network)

  So `send_to_everyone()` means everyone *else*. Anything that must show what
  this board just said has to update itself locally — lesson 201 does exactly
  that, and without it a nudge produces nothing visible on the sender.

  **An earlier version of this note claimed the opposite**, from a test that
  counted any message starting with `echo` without checking whose it was. Both
  boards ran that stage at the same instant, so each counted the *partner's*
  message as its own echo. Attribute every test message to its sender, or the
  second board silently answers the question you meant to ask the first.

  **Why the two differ: the IP stack loops one back and not the other.**
  Measured 2026-09-09, `lessons\spike_two_boards\measure_loopback.py`, five
  interleaved pairs on one board:

        unicast to own id    best 2.93  median 2.93  worst 3.05 ms, 5/5
        broadcast            never arrived, 5/5, 1.0 s each

  2.93 ms with a 0.12 ms spread is not a network trip. It is one
  `socket_available()` poll (1.2 ms) plus one `socket_read`, so the datagram
  was **already waiting before the first poll** -- lwIP saw a destination equal
  to the interface's own address, short-circuited it, and never handed it to
  the radio. An over-the-air hop would add ~9-15 ms on top (CLAUDE.md's
  board-to-board round trip, halved) and would carry the jitter that whole
  range shows; this has none.

  Broadcast gets no such short-circuit. lwIP hands it straight to the radio,
  and 802.11 does the rest: a station's frame goes *to the AP*, which relays it
  to the other associated stations and does not reflect it back to the sender.
  So neither layer ever gives the sender a copy.

  **This is stack policy, not a law of networking** -- Linux does deliver a UDP
  broadcast to local sockets bound to that port. Do not carry an intuition
  built on a laptop over to this board.

  The interleaving is what makes the null result trustworthy: a self-unicast
  succeeded immediately before and after every failed broadcast, so `receive()`
  was demonstrably alive throughout and "never arrived" cannot be a dead
  socket.

- **`microcontroller.cpu.uid` is 16 bytes, but it is not 16 bytes of serial
  number.** Across the two boards here only 6 of the 16 vary:

        byte     0  1  2  3   4  5  6  7   8  9 10 11  12 13 14 15
        A       97 22 d1 0f  36 4d 47 53  20 20 20 4d  34 16 02 ff
        B       27 e8 91 51  36 4d 47 53  20 20 20 4d  36 04 02 ff
        differs  ^  ^  ^  ^                             ^  ^

  Bytes 4-11 are ASCII (`6MGS   M`), a lot code shared by chips off the same
  wafer run; 14-15 are fixed. **Hash all 16, never slice.** A name taken off
  either end collides, and with the self-echo above two boards then filter each
  other out and the network looks dead while both radios are fine. Slicing the
  tail is what the first spike run did.

- **A board's id is the last octet of its address, in DECIMAL** —
  `network.my_id`, so `192.168.1.11` is `"11"`. **The id is the primary
  handle**, not the address: `network.send(their_id, msg)` takes an id,
  `network.start()` returns this board's id, and `network.address_of(id)` is
  exposed only so a lesson can show the expansion once. A student never types
  a dotted quad.

  **Hex was tried first and was a mistake.** With six boards on DHCP the
  addresses land around `.10`–`.15`, whose hex ids are `0a`–`0f` — *letters*,
  which destroys the "an id is just a simplified address" framing the whole
  Part 2 design leans on, and `.20` displaying as `14` is worse than useless.
  Decimal costs the fixed two-character width, which nothing depended on.
  `address_of()` parses with `int()`, so `"7"`, `"07"` and `" 7"` are the same
  board when a student types one in, and it raises a named error outside
  1–254 rather than silently building a bogus address.

  **A hash of the CPU UID was built first and dropped.** It worked (board A
  `1u`, board B `x3`, matching a host calculation byte for byte) but two
  characters is only 1296 names, so *some* pair in a room collides ~1% of the
  time at six boards and 28% at thirty — and a collision is silent and total,
  because a roster that skips its own name skips its twin with it and the two
  boards sit ignoring each other. Detecting it was possible — since a board
  never hears its own broadcast, hearing your own name *at all* proves a twin,
  and the heartbeat's address field says which one; verified on hardware, the
  higher address stepped aside with no master — but the address makes the whole
  problem vanish instead:
  **two boards can never share an address**, and `0` and `255` are the network
  and broadcast addresses so neither is ever a real board.

  It costs one thing: **the name does not exist until the join finishes**, so a
  board cannot label itself during its own five-second startup. Show a
  placeholder. This also assumes a /24, which `network.py` already assumed —
  it builds the broadcast address by swapping the last octet for 255.

- **A save costs ~5.7 s from a partner's point of view, not 4.5.** The 4.5 s
  below is the board's own downtime; what matters to anything watching is the
  gap from its last message to its next one. Measured 2026-09-10 on L204:
  last message 32.71, back on the network 38.05, first message out 38.37 —
  **5.66 s of silence**. Any timeout that is meant to survive a save has to
  clear that, which is why `forget_after` in L204 is 8.0 and not 3.0.

- **Every Ctrl+S takes a board off the network for ~4.5 s**, measured twice:
  0.9 s to the soft reboot, 0.4 s to running again, then 3.1-3.5 s to rejoin.
  The partner notices by heartbeat timeout and recovers **with no detection
  logic at all** — it printed LOST after 3.0 s of silence and NEW when the
  board came back, and never crashed, hung, or saw a torn message. The
  "absence is the disconnect signal" design in the lesson notes is confirmed
  on hardware.

- **A board that stops broadcasting gets declared dead even while it is alive.**
  Seen when the spike went quiet during a measurement stage: its partner aged
  it out after 3 s and reported LOST while it was busily running. So the
  heartbeat cannot be a separate phase that gameplay interrupts — the
  every-frame state broadcast has to *be* the heartbeat. Another argument for
  "send state every frame, never a one-shot event".

- **Board-side code cannot write the board's filesystem.** Measured on
  hardware 2026-09-08 (`lessons\spike_two_boards\measure_write.py`):

        open("/pair_test.txt", "w")   OSError [Errno 30] Read-only filesystem
        storage.getmount("/").readonly            True

  CircuitPython gives the filesystem to exactly one writer, and while USB
  mass storage is mounted that writer is the laptop. A `boot.py` calling
  `storage.remount("/", readonly=False)` would flip it — and would make
  CIRCUITPY read-only *to the host*, which destroys save-as-deploy, the one
  thing this whole course is built on. So this is a permanent no, not a
  configuration we have not got round to.

  **Consequence for Part 2: a pairing cannot survive a reboot**, and every
  Ctrl+S is a reboot. There is nowhere to persist it. So a pairing lives in
  RAM and has to be made again — and lesson 204 settles what "again" means:
  **knock the boards together**. That is better than recovering it from a
  partner, because it is physical and the student can see it happen, where
  silent recovery is machinery they would never meet.

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

**With two boards attached, every one-board command above refuses rather than
guessing.** Drive letters are not stable — the two boards here swapped E: and
G: inside a single session — so "the first CIRCUITPY" silently addresses
whichever enumerated first, and a save that lands on the board you were not
watching costs an afternoon. Boards are named in `tools\boards.json` (per
machine, gitignored) by CPU UID, which is in `boot_out.txt` and is also the USB
serial number. These are the invariant strings, two per board:

    .\.venv\Scripts\python.exe .\tools\boards.py
    & .\tools\sync.ps1 -Board A
    & .\tools\sync.ps1 -Board B
    & .\tools\sync.ps1 -Board A -Clean
    & .\tools\sync.ps1 -Board B -Clean
    .\.venv\Scripts\python.exe .\tools\verify_board.py --board A
    .\.venv\Scripts\python.exe .\tools\verify_board.py --board B
    .\.venv\Scripts\python.exe .\tools\watch_both.py --reload

`sync.py` — the Ctrl+S path — takes the label from the `LEARNPY_BOARD`
environment variable instead of an argument, so the VS Code task string never
changes. Unset with two boards attached, it refuses.

**`watch_both.py` is the instrument that makes Part 2 debuggable.** "The serial
port is exclusive" is about one port; two boards have two, so one process can
hold both and print them on a shared clock. A networking bug is a disagreement
between two boards, and one board's console only ever tells you what that board
believed.

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
- **One folder per lesson, always with a `main.py`.** `L101_say_something\main.py`,
  imported as `from L101_say_something import main`. A lesson that grows a bitmap,
  a font, or a helper module keeps them in its own folder instead of scattering
  them across the board root. Folder names must be valid Python identifiers,
  which is why they lead with a letter, and they sort into teaching order, which
  is why the number is fixed-width.
- **The number is `L<part><lesson>`: `L101`–`L112` for Part 1, `L201`+ for
  Part 2**, with the worked capstone answer as `L199`. Three digits, so plain
  lexicographic sort is teaching order across both parts, and a lesson's part
  is readable from its name alone. Prose in lessons and docs uses the same
  numbers — "lesson 110", not "lesson 10" — so there is exactly one name for
  each lesson. Renumbered from the flat `L01`–`L14` on 2026-09-08.
- **The first docstring line of `main.py` is the lesson's catalogue entry.**
  `tools\lesson.py` scans for folders holding a `main.py` and lists that line, so
  a new lesson appears in the picker with no catalogue file to update. Keep that
  line short and say what the student will *do*, not what the lesson covers.
- **A lesson folder is not on `sys.path`, and the cwd is `/`.** So the two forms
  a student would guess both fail, measured on hardware 2026-08-10:

        from . import helper                 works, no __init__.py needed
        import helper                        ImportError: no module named 'helper'
        open("/L101_say_something/data.txt")   works
        open("data.txt")                     OSError: No such file/directory

  Use `from . import helper` for a sibling module and a leading-slash absolute
  path for data files. Deriving the path from `__file__` also works and survives
  a folder rename, but it is too much machinery to put in front of a beginner.
- **A message kind names exactly one shape, course-wide, forever.** The word
  on the front of a message is only worth having if it is unique: the moment
  two lessons use one word for two different layouts, the word stops carrying
  information and the receiver is back to guessing from the length. Never
  reuse a kind for a new shape — give the new shape a new name.

  The kinds in use, and their exact layouts:

        tilt <x> <y>            L203   anonymous, two numbers
        tap <id>                L204   I have just been knocked
        move <id> <x> <y>       L204   signed: who, and where they point

  204's signed tilt is called `move` for exactly this reason — 203 had already
  spent the word `tilt` on a different layout. Caught 2026-09-09, after both
  lessons shipped. **It was safe only by accident**: every check is
  `len(parts) == N and parts[0] == kind`, so the differing lengths happened to
  reject each other. A later `tilt <x> <y> <z>` would have been read by 204 as
  a tilt *from board `<x>`* — silently wrong, which is the exact failure the
  tag was introduced to prevent. Add a row above before inventing a kind.

  `spike_two_boards` also uses `here`, `ping`, `pong`, `ball` and `echo`. It is
  a maintainer throwaway and never runs beside a lesson, but **205 will want
  `ball`** — check this list first.

- **American spellings, and no SCREAMING_CAPS in lesson code.** `color`, not
  `colour`; `center`, not `centre`. And a value a lesson defines and a student
  might edit stays `snake_case` — `tap_force`, `message_kind` — because naming
  conventions for constants were never taught and nothing enforces them.
  `colors.RED`, `screen.WIDTH` and `screen.Fonts.SMALL` keep their caps: those
  are library surface a student reads rather than writes.
- **Lesson content stays OS-neutral.** A lesson may end up running on a Linux
  laptop, and rewriting twelve lessons is the expensive kind of port. Inside
  `lessons\`, never write:

        E:\ or any drive letter          the mount point differs per OS
        backslash paths                  CircuitPython itself uses /
        PowerShell or bash commands      point at a VS Code task instead
        "the CIRCUITPY drive"            say "the board"

  Board paths are absolute with forward slashes — `/L103_bitmaps/logo.bmp` —
  which is what CircuitPython wants anyway. VS Code UI *is* fine: Ctrl+S, the
  Serial Monitor panel, and the task list are identical on Windows and Linux.
  (Only macOS differs, with Cmd+S, and no Mac is in scope.) Anything genuinely
  per-OS goes in `Readme.md`, which can grow a Linux section without touching a
  single lesson.
- **Ruff formats on save, and must never fix on save.** `setup.ps1` installs
  the Ruff extension on *every* machine, students included, so `ruff.toml` is
  not a maintainer-only file -- an earlier note here claimed it was, and that
  was simply wrong. The formatter is the safe half of ruff; the fixer is not.
  The launcher's import looks unused to F401, and `ruff --fix` or
  `codeActionsOnSave` would delete the only functional line in `code.py` and
  leave the board running nothing. `ruff.toml` exempts that file, but do not
  add a fix pass on top of it.

  Format-on-save is set in `.vscode\settings.json` under `[python]`, and
  **works only because `files.autoSave` is `onFocusChange`** -- VS Code
  silently skips `formatOnSave` when autoSave is `afterDelay`, so the two
  settings are coupled and neither can move alone.

  Cost on the save path: **~54 ms** for a cold `ruff format --check` of one
  lesson, measured five times on this machine. That is the pessimistic number
  -- it is a whole process spawn plus config discovery, where the extension
  keeps a server alive and pays far less. Against the ~430 ms host-side save
  budget it is affordable either way, but it is the first thing to re-measure
  if saves start feeling slow on a student laptop.

  Nothing installs ruff into `.venv`, deliberately: the extension carries its
  own binary, so `.venv` stays exactly what `setup.ps1` builds. A maintainer
  who wants the CLI can `pip install ruff` ad hoc -- just do not let a tool or
  task come to depend on `.venv\Scriptsuff.exe`, which students will not have.

  Verified 2026-09-08: all twelve Part 1 lessons were **already** conformant,
  so the house style and ruff's defaults agree and a student editing a lesson
  sees nothing jump. Line length is 88 in `ruff.toml`, matching
  `editor.rulers`; 88 characters passes and 89 wraps. And `font.py`'s
  `# fmt: off` is load-bearing -- without it the formatter squashes `SHAPES`
  from 300 lines to 48 and the glyph pictures stop being pictures.
- **Save = deploy.** Writing to CIRCUITPY is what triggers auto-reload, so
  copying a file *is* running it. Autosave is `onFocusChange`, deliberately and
  specifically: `afterDelay` would fire on every pause in typing and push
  half-written files to the board mid-edit, while `off` loses work when you
  alt-tab away. (This bullet used to say autosave was off; the setting has been
  `onFocusChange` for as long as `.vscode\settings.json` has explained why.)
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

**`.color` does NOT short-circuit the way `.text` does.** Measured 2026-08-27,
a 10-character Label, three interleaved passes of 60 frames:

    no colour set, static screen                  0.09
    Label .color = the SAME int                   8.88
    Label .color = a NEW int                      8.87

Assigning a colour dirties the label whether or not the value changed, so an
unchanged `.color` costs the same 8.9 ms as a new one — where an unchanged
`.text` costs 0.39. **Do not mirror the `sign.text = str(score)` advice above
onto colour.** A fade that writes `.color` every frame pays 8.9 ms forever,
including after it has finished fading; L201 accepts that (it has ~19 ms of
frame to spare and the simplicity is worth more), but anything with a real
frame budget should only write the colour on the frames it actually changes.

The 0.09 ms line is also worth knowing on its own: `displayio` only
recomposites dirty regions, so refreshing a screen where nothing moved is
free.

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

**`float()` accepts more than numbers, so `try`/`except` alone is not a safe
parse.** Measured on hardware 2026-09-09:

    'banana' '' '0x10'      ValueError                    <- try/except catches
    'inf' 'Infinity' 'nan'  parse fine, then int() raises
    '1e400'                 parses as inf, then int() raises

    int(inf * 32)   OverflowError: can't convert inf to int
    int(nan * 32)   ValueError: can't convert NaN to int

So wrapping `float()` moves the crash rather than removing it, and into a
different function with a different exception — strictly harder to debug than
the honest failure. **The range check is what actually closes it**, and it
catches all of them, `nan` included, because `nan` fails every comparison:

    -1.0 <= float('inf') <= 1.0   is False
    -1.0 <= float('nan') <= 1.0   is False

Which is why validation lands with the ball in 205 and not earlier: a bounds
check has a gameplay reason to exist there, and it is the same check that later
catches a partner sending numbers their board never measured.

**`screen.delete_shape()` takes a shape out of the group; it does not free it.**
Verified on hardware 2026-09-09 for `block`, `circle`, `burst` and `text` in
both fonts. Two things the one-line docstring does not have room for:

    delete_shape(x) twice     ValueError: object not in sequence
    x.x = 30 after deleting   works -- the object is still alive

So it is `_group.remove()` and nothing more. A lesson that makes shapes in a
loop must also drop its own reference, or it still accumulates them — deleting
is necessary but not sufficient, which is the other half of the Label-leak note
above. And the double-delete `ValueError` is the same species of cryptic
message as `tile must be 0--1`; if a lesson ever invites students to delete
things they might already have deleted, give it a named error first.

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

**They earn their place by catching lesson traps early.** L104 asks the student
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
not mention `L199_breakout_done`.

**Part 2, networked multiplayer, is under way.** `network.py` and `font.py` are
built and verified. The two-board spike is **done and board-to-board is now
verified** — see the networking notes above and the "Part 2: two panels"
section at the end of `docs\lesson-plan-notes.md`, which records what the spike
changed.

**Lessons 201, 202 and 203 are written and verified on both boards.** 202 is
`L202_move_their_block`: type your partner's id, unicast your tilt every frame,
their block moves on your panel — 17.7–18.4 ms/frame all in, against a 33 ms
budget. 203 is `L203_two_numbers`: `tilt <x> <y>` in one message, `.split()` to
take it apart, and a tag check so a message from a board still on 201 is
ignored instead of stopping the board. 204 is `L204_tap_to_pair`: knock two
boards together and they pair, because both were knocked at the same moment —
no typed id, and presence kept as one partner plus one timestamp. 205–207 are
not written, and the ball handoff (205) is the one piece still unspiked.

**The roster lesson was designed, written, verified, and then cut** on
2026-09-09. Nothing else in the arc needs a dict, knocking beats a roster for
discovery, and six boards would not fit its five-line display. It is in git
history if it is ever wanted; do not reintroduce it without a reason the
pairing does not already cover.

**202 crashes on purpose and must stay that way.** A board on 202 dies the
moment anyone in the room nudges a board still on 201 — `float("5: hello!")`.
That is the motivating problem for 203's tag, and the first move in a
deliberate thread about trusting input: 202's "nothing bad happens when you
assume things, right?!" is the setup, 203's closing exercises invite a student
to send numbers their board never measured, and cheat-detection is meant to
follow later. Do not "fix" 202 by hardening it.

**Lessons 101–112 are written and verified on hardware**, plus
`L199_breakout_done`, a worked answer to the capstone. 112 ships as a working
scaffold: the wall, the paddle, the score and a four-wall bounce all run, and
five `TODO`s add the collisions, the losing condition and the next level.
`L00_does_it_work` has been deleted; L101 took over its smoke-test job.

The accelerometer lessons are groundwork for students eventually using an
accelerometer to **self-level an ROV**, which is why `screen.tilt()` returns all
three axes rather than the two the matrix needs.

**Audience, decided:** high school students, most with *some* programming
experience — a class, a little Python or Java, some Scratch — but not to be
relied on. Start from the basics and move quickly. The test for a lesson is that
nobody is lost at lesson 101 and nobody is bored by lesson 103. Assume no prior
knowledge of hardware, `displayio`, or the board.

Scope is the 64x32 matrix and the onboard LIS3DH accelerometer. No WiFi — the
ESP32 co-processor would have to be driven over SPI by hand, which is a long way
past the point of this course.
