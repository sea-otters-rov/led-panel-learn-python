# Lesson plan

The shape of the course, and why it is shaped that way. Written for whoever
maintains the lessons, not for students.

**Status: lessons 101–112 are written and verified on hardware**, plus
`L199_breakout_done`, a worked answer to the capstone. This started as a plan and
is now a record — where the two disagreed, the lessons won and this file was
corrected.

**Part 2 — networked multiplayer — is designed but not written.** The plumbing
(`network.py`, `font.py`) is built and verified; lessons 201–207 are not. See
[Part 2: two panels](#part-2-two-panels) at the end.

Constraints this plan is held to, from `CLAUDE.md` and the brief:

- One new idea per lesson.
- Every lesson ends with something visibly different on the matrix.
- The first docstring line is the picker entry, and says what the student *does*.
- 9th graders. Short prose, comments in the code, informal tone.
- Interactivity early. The accelerometer is the hook, not a reward at the end.
- Lessons are building blocks for games.

**Decided:** the display and sensor setup lives in a board-root `screen.py`,
hidden from lesson one. `L101_say_something` is what `code.py` loads by default,
and it inherited `L00_does_it_work`'s job of proving the board works — L00 has
since been deleted.

---

## `screen.py` — write this first

A board-root module next to `colors.py`, so `import screen` works from inside
any lesson folder. It owns every line a student never has to see: `Matrix`, the
`Group`, `Bitmap`/`Palette`/`TileGrid`, `root_group`, and the I2C accelerometer.

**It hands back real `displayio` objects, not wrappers.** That is the whole
design rule. A student sets `.x`, `.y`, `.text`, `.color`, `.hidden` on the
thing they get, and those are the genuine attributes — nothing invented, nothing
that has to be un-learned, and anything `displayio` can do still works.

All calls take an optional `x, y` and put the thing on screen immediately.

| Call | Returns | Notes |
| --- | --- | --- |
| `screen.block(w, h, color)` | `vectorio.Rectangle` | `.x` / `.y` / `.width` / `.height` / `.hidden` |
| `screen.circle(size, color)` | `TileGrid` | Round blob, corners transparent. **No pixel `.width`** — see below |
| `screen.burst(size, color, frames)` | `TileGrid` | Expanding-ring animation. Step it with `set_frame()` |
| `screen.text(message, color)` | `Label` | `.text` / `.color` / `.x` / `.y` |
| `screen.recolor(shape, color)` | — | Blocks and circles have no `.color`; only `Label` does |
| `screen.color_of(shape)` | int | Reads it back — which is how L108 stores brightness without a second list |
| `screen.set_frame(shape, n)` | — | Which picture an animated shape shows |
| `screen.frame_of(shape)` | int | Reads back, so the frame index doubles as state |
| `screen.bring_to_front(shape)` | — | Re-appends to the group. The only way to reorder |
| `screen.tilt()` | `(tx, ty, tz)` floats | Clipped −1.0..1.0. `+x` right, `+y` down, `+z` out of the face |
| `screen.force()` | float | Total acceleration, ~0.95 at rest. For nudge detection |
| `screen.draw()` | — | Redraw now. Opt-in; see below |
| `screen.hold()` | — | Blocks forever. Retired in 04 |
| `screen.WIDTH`, `screen.HEIGHT` | `64`, `32` | |
| `screen.FULL_TILT` | `9.0` | **Writable.** A lesson lowers it for more sensitivity |
| `colors.dim(color, level)` | int | In `colors.py`. Reaches exactly `BLACK`, so "burnt out" is `== BLACK` |

**`tilt()` returns three axes, not two.** Nothing on the matrix uses `z`, but it
is what builds the orientation model for the ROV work this course feeds. Lessons
unpack all three with real names even when only two are used.

**`FULL_TILT` is public and per-lesson.** The default 9.0 needs roughly 76° to
reach the edge of the screen — fine for gentle lessons, useless for a game, and
asking for a big tilt just gets the board waved about. Lesson 109 sets it to 3–4
for itself. It cannot leak between lessons: `screen.py` is re-imported on every
reload, so the default resets on every save. The deadzone is deliberately in raw
sensor units rather than a fraction of `FULL_TILT`, or turning sensitivity up
would silently shrink the noise floor and everything would twitch at rest.

**`hold()` was not in the original plan and had to be added.** Without it a
lesson's program *ends*, the console reclaims the display, and lesson 101 has
nothing on the matrix. The alternative was an unexplained `while True` in the
first file. It stays through 01–03 and **lesson 104 deletes it** — swapping the
`for` loop for `while True` is exactly what `hold()` was standing in for, which
turns three lessons of small magic into a payoff.

**`draw()` was added at lesson 107, and is opt-in on purpose.** `displayio`
auto-refreshes in the background, so with ~100 moving objects a refresh lands
*inside* the move loop and the frame tears — half the stars jump, half don't.
Reported from the board 2026-08-13, and worse with no `time.sleep` because the
loop then runs back-to-back. `draw()` sets `auto_refresh = False` **on its first
call** and refreshes explicitly.

Opt-in matters: lessons 101–106 never call it, so they keep auto-refresh and
cannot freeze. Only a lesson that asks for frame control gets it, and no earlier
lesson needed retrofitting. The trap to avoid when writing later lessons: call
`draw()` unconditionally once per frame. Putting it inside an `if` disables
auto-refresh and then redraws only sometimes, which looks like a hang.

**`text()` and `block()` disagree about `y`, deliberately.** Measured on
hardware: a Label's `bounding_box` is `(0, -6, 12, 12)`, so `y` is the text's
vertical **centre**, while a block's `y` is its **top** edge. Both docstrings say
so. Consequence for 10: a score Label needs `y >= 6` or it clips at the top.

Things that got decided along with the API:

- **Creating a thing shows it.** No `screen.show(x)` step. Creation order is
  z-order, which is all the layering this course needs.
- **`tilt()` is clipped and pre-oriented.** The axis, the sign and the resting
  jitter get fixed once, on hardware, inside `screen.py`. Previously those were
  three unknowns that leaked into lesson 104.
- **Clipping is what keeps lesson 104 ahead of `if`.** `x = 32 + int(tx * 29)`
  lands in 3..61 for every possible input, provably, with no bounds test in the
  lesson. The TileGrid clipping off-screen instead of raising `IndexError` is
  the backstop.
- **`force()`, not `shake()`.** Detection stays in the lesson as
  `if screen.force() > nudge_force:` — one comparison, and a threshold a student
  can tune. A `shake()` returning a bool would move real logic into the magic
  file. **The threshold is 1.3, and the lesson calls it a nudge, not a shake.**
  Resting force is ~0.95, so a tap on the desk is enough — deliberately, because
  a lesson that rewards hard shaking is a lesson that breaks LED panels and
  ribbon cables.
- **Lazy-import `adafruit_display_text` and `adafruit_lis3dh`** inside `text()`
  and `tilt()`. `display_text` alone is 34.8 ms, ~4% of a save, and most lessons
  never call `text()`. Only `Matrix` and `displayio` go at module level.
- **Keep the docstring to a few lines.** Per `CLAUDE.md`, prose in a module every
  lesson imports is ~6 ms a save. Measured on hardware: `import screen` is 66 ms,
  `import colors` 22 ms, the first `text()` 44 ms and the first `tilt()` 63 ms.
  Most of the 66 ms is constructing `Matrix()`, which every lesson paid before
  `screen.py` existed — so the assumption that it roughly cancels out held. The
  lazy imports are worth keeping: a lesson that never tilts saves 63 ms a save.
- `Matrix()` calls `release_displays()` itself, so `screen.py` is safe across
  reloads. Keep `from adafruit_matrixportal.matrix import Matrix` — see
  `CLAUDE.md` for why going direct to `rgbmatrix` is a trap.

---

## The sequence

| # | Folder | Picker line | The one new idea | On the matrix when they're done | Min |
| --- | --- | --- | --- | --- | --- |
| 101 | `L101_say_something` | Put your own words on the matrix. | Variables | Their name, their colour, where they put it | 10 |
| 102 | `L102_your_first_dot` | Light up a block and put it anywhere on the screen. | The 64×32 grid: `.x` / `.y` | A coloured block they placed | 15 |
| 103 | `L103_make_it_move` | Send your block walking across the screen. | `for` + `range` + `time.sleep` | Block glides across and stops | 20 |
| 104 | `L104_tilt_to_steer` | Tilt the board and make the block follow. | **The accelerometer** | Block chases gravity, forever | 25 |
| 105 | `L105_hit_the_wall` | Stop the block at the walls and light up a warning when it gets there. | `if` / `elif` / `else` | Block pins to the edge, red light comes on | 25 |
| 106 | `L106_bounce` | Tilt the board to push a bouncing ball around. | Speed as a variable, and tilt changes speed not position | Ball you shove around a box | 30 |
| 107 | `L107_many_things` | Fill the screen with falling stars. | Lists | Starfield falling, all at once | 25 |
| 108 | `L108_your_own_commands` | Nudge the board to set off fireworks. | Functions (`def`, arguments, `return`) | Rings expanding and fading, on demand | 30 |
| 109 | `L109_catch_it` | Catch the falling dots before they reach the bottom. | Collision — two objects comparing positions | A real, playable game | 35 |
| 110 | `L110_keep_score` | Put a live score on the screen while you play. | Text that changes while running | Game, plus two counters on the matrix | 25 |
| 111 | `L111_brick_wall` | Build a wall of bricks, then knock it down. | Nested loops → a grid of things | Striped brick wall, bricks vanish | 25 |
| 112 | `L112_breakout` | Build the whole game: tilt, bounce, bricks and a score. | *(assembly, five `TODO`s)* | Breakout | 60–90 |
| 199 | `L199_breakout_done` | Breakout with all five TODOs filled in -- one way it can be finished. | *(worked answer)* | A finished game | — |

**Total: ~4h30 of lessons 101–111, plus 60–90 min for the capstone. ~5h45.**
Roughly 8 class periods.

**`L199_breakout_done` shows up in the student picker**, because `tools\lesson.py`
lists any folder holding a `main.py`. If the answers should not be one keystroke
away, either move it out of `lessons\` (losing the ability to run it) or rename
its file so the scan misses it.

Rough effort on lesson 112's five TODOs, for planning a session: **1** `ball_hits`
10 min, near-transcription of 11; **2** paddle bounce 10–15 min, where the
first attempt sticks; **3** bricks 20–30 min and the hardest, because a 3 px ball
straddling a 1 px gap clips two bricks in one loop and a naive double flip
cancels out; **4** the bottom 20–30 min, the only one that starts by *deleting*
given code; **5** level clear 15–20 min, whose accumulator loop is a shape that
appears nowhere earlier.

**Lesson 105 was split in two, 2026-08-13**, exactly as the Pushback section
predicted. `if` and direction-as-a-variable were never one idea, and writing 04
settled it: the house style — name every number, one transformation per line —
makes a combined lesson far too long. 05 is now `if` alone, applied to a wart
the student already felt in 04 (the block hanging off the edge). 06 inherits the
bounce with `if` already in hand.

The old lesson 110 (loading a `.bmp`) is **cut**. It was the only lesson that
built nothing the capstone needed, and with `screen.py` in place it no longer
even carries the "here's how displayio really works" justification. `.bmp`
loading survives as an extension idea in the capstone's *make it yours* list.
`adafruit_imageload` and `adafruit_bitmap_font` stay in `lib` — flash headroom
is not tight, and `bitmap_font` may be reachable from `display_text`.

---

## Where each concept first appears

| Concept | First taught | Needed by |
| --- | --- | --- |
| Variables, ints, strings | 01 | everything |
| f-strings (in `print` only) | 01 | 10, 12 |
| Coordinates, objects with attributes (`block.x = 5`) | 02 | 03, 04, 05 |
| `for` / `range` | 03 | 07, 11 |
| `time.sleep`, frame pacing | 03 | 04, 05, 06, 09, 12 |
| `while True` | 04 | 05, 06, 09, 12 |
| Reading a sensor | 04 | 05, 09, 12 |
| Floats, mapping a reading onto pixels | 04 | 05, 09, 12 |
| `//` integer division | 04 | 05, 11, 12 |
| `if` / `elif` / `else`, comparisons | 05 | 06, 07, 08, 09, 11, 12 |
| Boolean state (`.hidden`) | 05 | 09, 11, 12 |
| Negative numbers as direction (`ball_speed_x`) | 06 | 09, 12 |
| Acceleration — tilt changes speed, not position | 06 | 12, ROV work |
| Floats for position, `int()` only when drawing | 06 | 09, 12 |
| Lists, indexing, `for x in list` | 07 | 08, 11, 12 |
| `random` | 07 | 08, 12 |
| Functions: `def`, arguments, `return` | 08 | 09, 11, 12 |
| Reading state back off an object (colour, frame) | 08 | 12 |
| `time.monotonic()` as a clock | 08 | — |
| `global`, to reassign a module variable inside a function | 08 | 99 |
| Setting `screen.FULL_TILT` for a lesson | 09 | 10, 11, 12 |
| Text that changes while running (`.text = `) | 10 | 12 |
| `str()`, because a Label will not take a number | 10 | 12 |
| Nested loops, a list built in a loop | 11 | 12 |
| `not`, and counting with an accumulator | 12 | — |

**Nothing is used before it's taught.** The one place that came close:

- **`while True` in lesson 104.** Lesson 103 uses `for x in range(64)`. Lesson 104
  swaps that one line for `while True:` — presented as "same loop, no end", one
  word of new syntax, not a lesson's worth of idea.

Bounds-checking used to be the other one. `screen.tilt()` clipping removed it.

---

## Lesson 101 also has to be the smoke test

`L00_does_it_work` is going away, so L101 inherits three jobs beyond teaching
variables: prove the LEDs light, prove a save reaches the board, and prove the
Serial Monitor works. All three fall out of the lesson naturally — change
`MESSAGE`, press Ctrl+S, the words on the matrix change and a `print()` line
appears in the console. The change *is* the proof.

**L101 is static — no animation.** L00 colour-cycled, which also proved the board
wasn't frozen, but that needs a loop and loops are lesson 103. A student who
typed a new message and sees it on the LEDs has all the proof they need. Don't
put an unexplained `while True` in the first file.

`code.py` becomes `from L101_say_something import main`.

---

## The accelerometer

**Lesson 104, and it can't come sooner.** A sensor read with no loop around it
reads once at boot and never again — you tilt the board and nothing happens,
which is worse than not having it at all. The floor is:

1. Something on screen to move (02)
2. `.x` / `.y` you can assign to (02)
3. A loop to read it in (03)

`if` is *not* required, because `screen.tilt()` clips. Lesson 104 is the 4th file
and about 45 minutes in.

**What lesson 104 actually teaches, now that setup is hidden:** mapping one range
of numbers onto another. `screen.tilt()` gives −1.0..1.0 and the screen wants
0..63, so scale by the half-width, add the centre, subtract half the block, and
`int()` off the decimals. That is a more useful hour than three lines of I2C
boilerplate, and it is the same move again in 05, 09, 10, 11 and 12.

Second appearance is lesson 108, as a nudge: `if screen.force() > nudge_force:`.
It reuses the sensor to demo functions rather than introducing a new toy.

**The three unknowns are settled.** Measured on hardware 2026-08-13 from two
poses that fit a geometric model to within 0.05: `x` is screen-horizontal, `y` is
screen-vertical and needs no sign flip, `z` is the screen's own up. Resting
jitter is ±0.15 in sensor units, comfortably inside the 0.3 deadzone.

**The one thing still open is levelling.** A board resting on cables sits a few
degrees off, which at lesson 109's sensitivity puts the paddle ~9 px off centre.
The fix would be `screen.level()`, recording the resting vector as the new zero —
which is also exactly the ROV self-levelling idea, so it would earn its place
twice. Deferred: a printed holder may make it moot.

---

## The drawing model

**Every visible thing is its own movable object, positioned with `.x` / `.y`.**
Not one full-screen bitmap with `bitmap[x, y] = 1`.

Off-screen `.x` clips silently on a moved object and is an `IndexError` on a
bitmap — that alone is worth the choice, and it's what lets lesson 104 arrive
before `if`. Moving is free, so no lesson has to explain why a moving block
leaves a smear behind it.

Blocks are `vectorio.Rectangle` since 2026-08-13 — 37% less RAM and 24% faster
than `Bitmap` + `TileGrid`, measured at lesson 107's workload. **Circles are a
`Bitmap` after all**, added at lesson 107 once it turned out `vectorio.Circle`
rasterises to a diamond below about 7 px. The earlier "don't use circles" note
was a speed argument generalised from a 40-object benchmark; per object the cost
is ~0.2 ms, so speed was never the real objection — shape was. `Polygon` stays
rejected at 6–9× a rectangle. See `CLAUDE.md` for the numbers.

The knock-on wins:

- Bricks are a list of `Rectangle`, and a hit brick is `brick.hidden = True`.
  Hiding is easier than deleting, and it's reversible — which is what makes
  lesson 112's "put the wall back for level 2" a three-line TODO.
- `rainbowio.colorwheel(row * 30)` stripes the wall with no palette lecture, and
  wraps rather than raising above 255, so a student can hand it any multiplier.

With `screen.py` and the `.bmp` lesson cut, **`bitmap[x, y]` never appears in
the course at all.** That is the intended trade.

---

## Capstone: Breakout

Tilt-steered paddle, bouncing ball, a wall of bricks, a score. As built: 8
columns × 3 rows of 7×3 bricks with a 1 px gap across the top 11 rows, a 3 px
ball, a 14×2 paddle.

It was chosen because it needs **every** concept in the course and nothing
outside it. Nothing in 01–11 is dead weight, and nothing new is introduced in
12.

What the last few lessons exist to deliver:

| Lesson | What the capstone takes from it |
| --- | --- |
| 06 Bounce | The wall reflection — **reflect the overshoot, never clamp** |
| 09 Catch it | Collision, and the ball-vs-paddle test essentially unchanged |
| 10 Keep score | The score Label sitting over the play field |
| 11 Brick wall | The nested loop that builds the wall, and `hidden` to clear a brick |

Lesson 112 ships as a **working scaffold with five `TODO`s**, not an empty file.
The wall, the paddle, the score and a four-wall bounce all run on first load, so
the board does something the moment it opens. The TODOs are: the shared
collision test, the paddle bounce, the brick knockout, what a miss costs, and
what happens when the wall is cleared. The last two are design questions with no
single right answer. Then the *make it yours* list: speed up per brick, colour
the ball by speed, angle off the paddle edge, three lives in a corner.

`L199_breakout_done` is one worked answer, verified end to end on hardware. Two
things in it are worth reading before teaching the lesson: the brick loop knocks
out every brick touched but flips the speed **once**, because a 3 px ball
straddling a gap clips two bricks in a single loop and a double flip cancels
out — confirmed, the first collision of a normal game scores two. And the paddle
bounce lifts the ball clear before flipping, or it sinks in and flips again next
loop.

Budget 60–90 minutes and expect two sittings. Say so in the lesson rather than
pretending it's one period.

Alternates if Breakout doesn't land with a group: **Snake** (better for lists,
worse for bounce and collision) or **dodge the falling blocks** (a straight
extension of 08, but too small to feel like a capstone).

---

## House style for lesson code

Derived from the rewrites L102 and L104 got on 2026-08-13. Write lessons this way
from the start rather than waiting to be corrected.

**Name every number.** No bare literal unless it is self-evident. Put it on its
own line above the loop:

    screen_center_x = screen.WIDTH // 2      not  block.x = 32 + ...

**Derive from the source of truth**, so the try-these actually work.
`block.width // 2`, never a hardcoded `2` — otherwise "make the block bigger"
silently breaks the centring, and the student learns the wrong lesson from it.

**One transformation per line.** Scale on one line, centre on the next. Never
compose two ideas into one expression:

    tilt_x_pixels = int(tilt_x * screen_center_x)
    block.x = tilt_x_pixels + screen_center_x - block_center_x

**Comments say *why*, not *what*, and call back.** "the block's .x and .y are
its top-left corner, not its middle" earns its line; "# set x" does not.

**Show more than the lesson needs.** `tilt()` returns z even though nothing on
the matrix uses it — the third axis is what builds the orientation model, and
it is groundwork for the ROV self-levelling project this course feeds. Unpack
all three with real names even when unused; do not teach `_`.

**Keep the debug `print()` live in the loop.** It is the instrument, not
decoration. Budget the loop's `time.sleep` around it — see the note below.

**Try-these ask questions, not instructions.** "What is tilt actually
measuring?" beats "change 29 to 10". Prefer why / what-happens over do-X, and
make at least one of them a deliberate trap with a readable error.

## Pushback

**`screen.py` makes lessons 101 and 102 very short — three or four lines each.**
That is a feature at lesson 101 and a question at lesson 102. I'd still keep them
separate: 01 is where nobody can get lost, and 02 is where the coordinate grid
lands, which is the single most-used idea in the course. But 02 needs real
exercises to fill its 15 minutes — put a block in each corner, find the centre,
work out what `.y = 0` means — not more reading.

**The escape hatch needs to exist and doesn't need to be advertised.** A student
who wants something `screen.py` doesn't offer isn't stuck: the returned objects
are ordinary `displayio` objects, and `screen.py` itself is a readable file
sitting next to `colors.py`. Nothing about the design has to be un-learned
later. Worth one sentence somewhere in `Readme.md`, not in a lesson.

**~~Lesson 105 is doing the most work.~~ Split, 2026-08-13.** It was `if`, `else`,
comparisons and direction-as-a-variable at once, which is one idea only if you
squint. Now 05 is `if` alone and 06 is the bounce. Evidence that decided it: the
house style adds ~8 lines of named intermediates to any lesson, so a combined
one would have run past 40 lines.

**Lesson 110 is the thinnest and might be half a lesson.** Kept separate anyway,
and it held up: a score on screen is the best motivation-per-minute in the
course. If you ever need to drop to eleven lessons, this is the one to fold into
09. Note its `str()` exercise — the only one testing its own new idea — was
dropped when try-thats were redistributed between 09 and 10, so what remains is
all about game behaviour rather than what a Label will accept.

**Lesson 112 is not one lesson and the plan shouldn't pretend it is.** See above.

**Deliberately not in the course:** classes, dictionaries, `try`/`except`, list
comprehensions, `%`, file I/O, index-based iteration (`for i in range(len(x))`),
and per-pixel drawing. None are needed for Breakout, and each is a lesson that
ends with nothing new on the matrix.

**Index iteration was designed around, not forgotten.** Every place that wanted
per-object state found it on the object instead: the palette holds a firework's
brightness, the tile index holds its animation frame, `.width` holds a star's
fall speed, `.hidden` holds whether a brick is standing. That is why no lesson
ever needs two parallel lists kept in step — and it is worth preserving, because
the first thing a parallel list forces is exactly the `range(len(...))` shape
this course does without.

**`print()` gets no lesson of its own.** It's introduced in 01 alongside the
Serial Monitor and used everywhere after as the debugging move. A lesson about
output that appears in a panel rather than on the LEDs would break the
visible-payoff rule.

---

## How it was written, and what that taught

The order was `screen.py` first, then 01 and 02, then **04 out of sequence as a
hardware spike**, then the rest in order. That held up: 04 was the last place the
board could surprise us, and everything from 05 on is ordinary Python.

Three habits are worth keeping for whoever edits these next.

**Verify every claim on the board, including the try-thats.** Several exercises
asked students to observe things that did not happen. "Speed it up until the ball
skips past the walls" — it cannot, the reflection catches every overshoot.
"Change `int` to `round` and see the difference" — no visible difference, though
running it revealed a real asymmetry worth keeping instead. If an exercise claims
something is observable, observe it first.

**A lesson's own numbers are load-bearing.** `star_size` quietly became a lie
when stars gained random sizes, and the margins computed from it let a big star
hang off the edge. Deriving from the source of truth is not style; it is what
keeps the try-thats honest.

**Measurement beats reasoning about this board, repeatedly.** The fade rate, the
circle shapes, the sprite-sheet frames, the tearing threshold, `colorwheel`
wrapping past 255, whether `block.width = 0` is legal — every one was cheaper to
run than to argue about, and several came out against the prediction.

Still open:

- `L199_breakout_done` shows in the picker; see the note under the sequence.
- `screen.level()` is unbuilt. See the accelerometer section.
- Lesson 103 runs at `time.sleep(0.5)`, which is 32 seconds to cross the screen —
  good for reading the per-step prints, slow as a first taste of motion.


---

## Part 2: two panels

Designed, plumbing built and verified on hardware, **no lesson written yet**.
The target: two boards with their tops facing each other, a ball that leaves the
top of one panel and arrives at the top of the other with mirrored velocity, and
a score both panels agree on. Then more than two players.

This feeds two things beyond itself — the ROV self-levelling project, and
eventually a board talking to an RP2350 over ethernet. **That second one is why
the abstraction matters more than the transport.**

### What is already built

| | |
| --- | --- |
| `network.start()` | Joins the wifi. Returns this board's id. **Blocks 3–7 s** |
| `network.my_id` | `"11"` — the last number of this board's address |
| `network.send(board_id, message)` | One board, addressed by id |
| `network.send_to_everyone(message)` | Broadcast |
| `network.receive()` | Next message, or `""`. Never waits |
| `network.address_of(board_id)` | The expansion, for showing once in a lesson |
| `network.my_address` | Rarely wanted now the id is the handle |
| `screen.text(..., font=screen.Fonts.SMALL)` | 3x5 letters — 16 across, five lines |

Costs, measured: round trip ~19 ms with no loss, send 7.8 ms, receive 1.7 ms,
**~9 ms of network per frame** — 28% of a 33 ms frame. `CLAUDE.md` has the rest,
including two landmines that are commented in `network.py` and must not be
"tidied": `socket_open` before *every* write, and `receive()` on the raw
`esp32spi` API rather than the socketpool.

### Decisions already made, and why

**Router-primary, every board an equal peer.** Not AP mode. An AP board reboots
on every Ctrl+S and takes its partner down with it — with three pairs that is
three single points of failure, each held by a student who is actively editing.

**A heartbeat roster, not a pairing handshake.** Each board broadcasts
`here <name> <ip>` about once a second; each keeps whoever it heard from in the
last ~3 s. **Absence is the disconnect signal**, so a rebooting board simply
drops off and reappears with no detection logic anywhere. Put the roster on the
matrix and students *watch each other save* — which turns the most annoying
property of this workflow into the clearest demo in the unit.

**Broadcast to discover, unicast to play.** WiFi broadcast goes out at the
lowest basic rate with no link-layer acknowledgement; unicast uses the
negotiated rate and gets 802.11 retries for free. Keep the heartbeat on
broadcast — it is how new boards appear and how a partner's reboot is noticed.

**Send state every frame; never send a one-shot event.** The ball's owner
broadcasts position, velocity and owner continuously. A handoff is just changing
the owner field, and the acknowledgement is the other board's own next
broadcast — so there is no ack channel and no retransmit logic. A lost packet
costs one frame, not the ball. Score is state too, so both panels self-correct.
This is also the answer to "do we need acks, or TCP?": no, and TCP would be
actively worse here because every save kills its connections.

**Mirroring on handoff**, tops touching so the far panel is 180° rotated:

    x_new  = screen.WIDTH - ball_size - x     # not WIDTH - 1 - x
    vx_new = -vx
    vy_new = -vy

That off-by-one is the one they will write first, and it rhymes with the
`max_x = WIDTH - size` idiom from lesson 105.

**Serve by tilt-off.** Both players tilt, both boards send their tilt value, and
*both compute the same winner from the same two numbers* — no clocks, no race,
and the winner's angle sets the ball's direction. The obvious "first to nudge
wins" is a trap worth letting them try: A hears B while B misses A, and the two
boards disagree. That is the honest content of lesson 207.

### The arc

| # | What they make | New idea |
| --- | --- | --- |
| 201 | Nudge your board, your words appear on everyone else's panel | Two boards can talk. Mirrors L101. **Written** |
| 202 | Your tilt moves a block on *their* screen | `float()` on a received string — the reverse of L110's `str()`. **Written** |
| 203 | Several numbers in one message, and checking one before trusting it | `.split()`, which returns a list they know from L107. **Written** |
| 204 | Knock two boards together and they pair up | Two events close in time are one event. No typed id, no dict. **Written** |
| 205 | **The ball crosses between panels** | Ownership and handoff. The hard one |
| 206 | Both panels agree on the score | One side is the authority; the other is told |
| 207 | The serve, and the finished game | Protocol, and what to do when two boards disagree |

Roughly 4–5 hours. It is a genuine Part 2, not an extension: it widens the
language surface with `.split()` and probably `try`/`except`, and it needs a
second board and a router per pair.

### The spike: done, 2026-08-27

`lessons\spike_two_boards\spike.py` runs the same file on both boards and works
through id, join, echo, roster, ping and load. Its entry file is deliberately
not `main.py`, so the picker does not list it. Run it with
`tools\watch_both.py --reload`, which holds both consoles on one clock.

**The design survived contact.** Every decision above held, and two of them are
now confirmed rather than reasoned:

- **A reboot needs no detection logic.** Board A was saved mid-run twice. B
  printed LOST after 3.0 s of silence and NEW when A returned, and never
  crashed, hung, or read a torn message. Absence really is enough.
- **The heartbeat must be the gameplay traffic.** When the spike stopped
  broadcasting during a measurement stage, its partner declared it dead while
  it was plainly alive. A separate heartbeat that gameplay can interrupt is a
  liveness signal that lies. This is a second, independent argument for "send
  state every frame".

Three things the one-board work had wrong, all now in `CLAUDE.md`:

- **A board does not hear its own broadcast** — `send_to_everyone()` means
  everyone else — though it does hear a unicast sent to its own address. So a
  lesson that shows what this board just said has to say it locally as well as
  send it, or a nudge with no partner in the room does nothing at all.
- **A board's id is the last octet of its address, in decimal** —
  `network.my_id`, `192.168.1.11` → `"11"`, and the id is the handle every
  lesson uses: `network.send(their_id, msg)`. (The spike shipped it in hex;
  that was corrected on 2026-09-08, because six boards on DHCP get ids like
  `0a`–`0f` and letters wreck the framing.) Uniqueness is
  then a property of the network rather than a probability, which matters more
  than it sounds: the alternative, a two-character hash of the CPU UID, is 1296
  names and collides for some pair ~1% of the time in a room of six. A name
  collision is silent and total: a roster that skips its own name skips its
  twin along with it, so the two boards sit ignoring each other and look like
  dead hardware. "Unlikely" is the wrong safety margin for that.

  The UID hash was built, verified, and deleted; the reasoning is in
  `CLAUDE.md` in case someone reaches for it again. Two smaller notes: the id
  **does not exist until the join finishes**, so a board cannot label itself
  during its own five-second startup, and it assumes a /24, which `network.py`
  already assumed when it builds the broadcast address.

  The id is the *default*, not the point. The roster lesson (204) wants the
  student's own name on the panel; the id is what a board calls itself before
  anybody types one, and what lets three boards running the identical unedited
  lesson still tell each other apart.
- **Board-to-board round trip is about double the laptop figure** — median
  24–30 ms against 16 — with a much worse tail. The 33 ms frame still holds
  with both boards broadcasting flat out: 14.8–15.1 ms/frame, ~18 ms spare.

And the number that shapes every networked lesson: **every Ctrl+S costs ~4.5 s
off the network**, mostly the wifi rejoin. A lesson whose partner vanishing for
four seconds looks like a failure is a lesson that fails constantly.

### Lesson 202, written and verified 2026-09-08

`L202_move_their_block`. You type your partner's id, unicast your tilt to them
every frame, and their tilt moves the bright block on your panel; your own
block is drawn dim from your own tilt, so a board with no partner still does
something. Verified on two boards: `str(0.12178392)` went out and came back as
`+0.122` at the far end, both directions.

**Frame cost 17.7–18.4 ms** (tilt read, one unicast, drain-to-newest receive,
two block moves, `screen.draw()`), against the spike's 15.3 ms for network
alone. ~15 ms of headroom in a 33 ms frame. Message flow was 200–206 received
per 240 frames — under one per frame, and not growing, so the inbox does not
back up.

Two things it does that the arc did not call for, both earned:

- **It drains the inbox to the newest message** rather than taking one per
  turn. Two boards never run at exactly the same speed, so one-per-turn lets
  the spare messages pile up and the partner's block falls permanently behind.
  The drain is `while heard:` around the `float()`, and `their_tilt_x` simply
  keeps its old value when nothing arrives — which is also the honest
  behaviour, and a first taste of 16's "keep a copy of something that lives
  elsewhere".
- **It prints `network.address_of(partner_id)` once at startup**, which is the
  only place in the course a student sees an id expand into an address. That
  is the whole justification for exposing `address_of` at all.

`str(tilt_x)` sends 8 significant digits — about 10 characters for a value a
64-pixel screen can only use 6 bits of. Nothing to fix at 18 ms/frame, but it
is the obvious thing to trim if 17's ball message ever gets tight.

### Lesson 203, written and verified 2026-09-09

`L203_two_numbers`. Tilt goes out as `tilt <x> <y>`, so the partner's block
moves in both directions, and the receiver checks
`len(word) == 3 and word[0] == MESSAGE_KIND` before believing any of it.

**The tag was the point, not the second number.** 202 crashes whenever anyone
in the room is still on 201, because `float("5: hello!")` stops the board --
and `try`/`except` would have been the wrong fix. It patches one direction
only, leaves the receiver silently eating data it cannot use, and teaches
nothing about *why* the message was wrong. A tag fixes both ends and costs no
extra new idea, because `.split()` was already this lesson's content. It also
degrades gracefully against every earlier lesson: a bare `0.128` from an
un-updated 202 has `word[0] == "0.128"`, matches no tag, and is ignored.

Verified end to end: board A on 201 broadcasting `5: hello!` flat out, board B
on 203. **B ran 600 frames, ignored 195 of them, accepted 0, never stopped.**
The same traffic killed 202 on the first message. (201 in the other direction
just shows `tilt 0.07 0.96` as text -- noise, not a crash, and unchanged.)

Two things the hardware run turned up:

- **Lay the board FLAT.** Stood upright, the measured `tilt_y` sat at
  0.959-0.970 for the whole run -- gravity pins the up-and-down number to one
  end, the block sits on the bottom edge, and the entire new half of the
  lesson is invisible. Said in the docstring now.
- The remaining hole is a *correctly shaped* message with a bad number:
  `tilt banana 0.5` passes both checks and still stops the board. Left in
  deliberately as the last try-these item -- checking the shape of a message
  is not the same as checking what is in it.

**The security thread is deliberate.** The "just assume the message only has a
number -- nothing bad happens when you assume things, right?!" comment in 202
is the setup, and 203's closing exercises are the payoff: a student is invited
to send a fixed `0.9` regardless of their real tilt, or a number no real tilt
could produce, and asked whether their partner could possibly tell. That is
the seed for cheating and cheat-detection later, and it is why 202 is left
crashing rather than hardened.

### Lesson 204, written and verified 2026-09-09

`L204_tap_to_pair`. Knock the two boards together; both feel it, both broadcast
`tap <id>`, and each pairs with whoever was knocked at the same moment. Then
tilt drives the partner's shape, as in 203, but with nothing typed anywhere.

**The roster was cut, and the dictionary with it.** It had been the plan since
the original arc, and it did not survive contact with two questions: does
anything else need a dict, and does the roster earn a whole lesson? No to both.
205 is two-board ball state, 206 is two scores, 207 is two tilts -- no mapping
anywhere. The roster's real job was discovery, and knocking does that better,
physically, and with no new data structure. Presence survives as **one partner
and one timestamp** -- a float -- which keeps "absence is the disconnect
signal" without the dict.

The layout was the tell. Six boards need six lines; the small font is 5 rows
tall with no built-in gap, so at the 6px spacing the roster used, the sixth
board's line starts at y=33 on a 32-row screen and vanishes silently. Five
lines fit, six do not. A display that cannot show the class is a sign the
feature was carrying weight it had not earned.

Verified on hardware, both directions:

        6.0  B  paired with board 5
        6.3  A  paired with board 4

       35.7  B  Code stopped by auto-reload
       36.9  B  soft reboot
       38.7  A  lost board 4        <- 3.0 s after B's last message
       41.2  B  network: board 4 ready

**Pairing has to be symmetric, and the naive version is not.** If A knocks
first, A's message reaches B before B has knocked, so B discards it; B then
knocks, A pairs, and B never does. Storing the last heard tap and comparing
`abs(my_tap_time - their_tap_time)` fixes it, because both boards evaluate the
same condition whichever order the messages arrived in.

`their_tap_id` is cleared once used. Without that, the two stored times stay
close forever, so a board that timed out its partner would silently re-pair off
the knocks from several minutes ago instead of waiting for a fresh one.

**The signed tilt carries its sender: `move <id> <x> <y>`.** Without the id,
pairing is decorative -- any board could drive your shape, since a receiver
never learns who sent a datagram. This is also the first lesson where the
message kind on the front does real work, because there are finally two kinds.

**It is `move` and not `tilt` because 203 already spent that word** on a
three-part, unsigned message. Caught after both lessons had shipped. It was
safe only by accident: every check is `len(parts) == N and parts[0] == kind`,
so the differing lengths rejected each other. A later `tilt <x> <y> <z>` would
have been read by 204 as a tilt *from board `<x>`* -- silently wrong, and
exactly the failure the tag was introduced to prevent. `CLAUDE.md` now carries
the registry of kinds and their layouts; check it before inventing one.

**A pairing still cannot survive a save**, and the answer is now better than
the roster's: knock the boards together again. That is honest, physical, and
visible, where "recover the pairing from your partner" was machinery a student
would never see.

Still unspiked: **the handoff itself** (arc item 205). That is the one remaining
place where two boards can disagree, and it wants doing before 17 is written,
not while.

**A pairing cannot be remembered across a reboot.** Tested on hardware
2026-09-08: board-side code cannot write the board's filesystem at all
(`Errno 30`, `readonly` is `True`), and the only way to change that would make
CIRCUITPY read-only to the laptop and kill save-as-deploy. See `CLAUDE.md`. So
there is no "remember my partner" file, and a board that reboots must rebuild
its pairing from what it hears — the roster again. Tap-to-pair therefore has to
sit *after* presence exists, which is why it lands as an extension of 16 rather
than as its own lesson before 14.

Also unresolved:

- `network.start()` blocks 3–7 s, so a lesson must draw something first and
  connect behind a status pixel. There is no way around it: the reset is
  mandatory (see `CLAUDE.md`) and the association cannot survive a reload.
- `screen.level()` is still unbuilt, and Part 2 is where it starts to matter —
  it is also exactly the ROV self-levelling idea, so it may deserve its own
  lesson rather than being hidden in `screen.py`.
- **The classroom setup wants doing before the first networked class**: DHCP
  reservations pinning the six boards to `.11`–`.16`, so every id is a stable
  two-digit number all term, and a sticker on each panel to match. Without the
  reservations a board's id changes when the lease does, and a student's
  written-down partner id goes stale between lessons.
- Six boards all broadcasting at frame rate is ~180 packets/sec, and each board
  pays to parse all of them. Unicast-after-pairing is the fix, but the limit is
  worth measuring before designing a six-player game around it.
