# Lesson plan

The shape of the course, decided before any lesson code exists. Written for
whoever writes the lessons, not for students.

Constraints this plan is held to, from `CLAUDE.md` and the brief:

- One new idea per lesson.
- Every lesson ends with something visibly different on the matrix.
- The first docstring line is the picker entry, and says what the student *does*.
- 9th graders. Short prose, comments in the code, informal tone.
- Interactivity early. The accelerometer is the hook, not a reward at the end.
- Lessons are building blocks for games.

**Decided:** the display and sensor setup lives in a board-root `screen.py`,
hidden from lesson one. `L00_does_it_work` gets deleted once L01 and L02 are
verified; `L01_say_something` becomes what `code.py` loads by default, and
inherits L00's job of proving the board works.

---

## `screen.py` — write this first

A board-root module next to `colors.py`, so `import screen` works from inside
any lesson folder. It owns every line a student never has to see: `Matrix`, the
`Group`, `Bitmap`/`Palette`/`TileGrid`, `root_group`, and the I2C accelerometer.

**It hands back real `displayio` objects, not wrappers.** That is the whole
design rule. A student sets `.x`, `.y`, `.text`, `.color`, `.hidden` on the
thing they get, and those are the genuine attributes — nothing invented, nothing
that has to be un-learned, and anything `displayio` can do still works.

| Call | Returns | Notes |
| --- | --- | --- |
| `screen.block(w, h, color)` | `TileGrid` | Already on screen. `.x` / `.y` / `.hidden` |
| `screen.circle(size, color)` | `TileGrid` | Round blob, corners off. **No pixel `.width`** |
| `screen.text(message, color)` | `Label` | Already on screen. `.text` / `.color` / `.x` / `.y` |
| `screen.tilt()` | `(tx, ty)` floats | Clipped −1.0..1.0. `+x` right, `+y` down — **matching screen coordinates** |
| `screen.force()` | float | Total acceleration, ~1.0 at rest. For shake |
| `screen.draw()` | — | Redraw now. Opt-in; see below |
| `screen.hold()` | — | Blocks forever. Retired in 04 |
| `screen.WIDTH`, `screen.HEIGHT` | `64`, `32` | |

**`hold()` was not in the original plan and had to be added.** Without it a
lesson's program *ends*, the console reclaims the display, and lesson 01 has
nothing on the matrix. The alternative was an unexplained `while True` in the
first file. It stays through 01–03 and **lesson 04 deletes it** — swapping the
`for` loop for `while True` is exactly what `hold()` was standing in for, which
turns three lessons of small magic into a payoff.

**`draw()` was added at lesson 07, and is opt-in on purpose.** `displayio`
auto-refreshes in the background, so with ~100 moving objects a refresh lands
*inside* the move loop and the frame tears — half the stars jump, half don't.
Reported from the board 2026-08-13, and worse with no `time.sleep` because the
loop then runs back-to-back. `draw()` sets `auto_refresh = False` **on its first
call** and refreshes explicitly.

Opt-in matters: lessons 01–06 never call it, so they keep auto-refresh and
cannot freeze. Only a lesson that asks for frame control gets it, and no earlier
lesson needed retrofitting. The trap to avoid when writing later lessons: call
`draw()` unconditionally once per frame. Putting it inside an `if` disables
auto-refresh and then redraws only sometimes, which looks like a hang.

**`text()` and `block()` disagree about `y`, deliberately.** Measured on
hardware: a Label's `bounding_box` is `(0, -6, 12, 12)`, so `y` is the text's
vertical **centre**, while a block's `y` is its **top** edge. Both docstrings say
so. Consequence for 09: a score Label needs `y >= 6` or it clips at the top.

Things that got decided along with the API:

- **Creating a thing shows it.** No `screen.show(x)` step. Creation order is
  z-order, which is all the layering this course needs.
- **`tilt()` is clipped and pre-oriented.** The axis, the sign and the resting
  jitter get fixed once, on hardware, inside `screen.py`. Previously those were
  three unknowns that leaked into lesson 04.
- **Clipping is what keeps lesson 04 ahead of `if`.** `x = 32 + int(tx * 29)`
  lands in 3..61 for every possible input, provably, with no bounds test in the
  lesson. The TileGrid clipping off-screen instead of raising `IndexError` is
  the backstop.
- **`force()`, not `shake()`.** Shake detection stays in the lesson as
  `if screen.force() > 2.0:` — one comparison, and a threshold a student can
  tune for fun. A `shake()` that returned a bool would move real logic into the
  magic file.
- **Lazy-import `adafruit_display_text` and `adafruit_lis3dh`** inside `text()`
  and `tilt()`. `display_text` alone is 34.8 ms, ~4% of a save, and most lessons
  never call `text()`. Only `Matrix` and `displayio` go at module level.
- **Keep the docstring to a few lines.** Per `CLAUDE.md`, prose in a module every
  lesson imports is ~6 ms a save. `screen.py` is bigger than `colors.py`, so
  measure the import once it exists — it should roughly cancel out against the
  setup code it removes from each lesson file, but that is an assumption, not a
  measurement.
- `Matrix()` calls `release_displays()` itself, so `screen.py` is safe across
  reloads. Keep `from adafruit_matrixportal.matrix import Matrix` — see
  `CLAUDE.md` for why going direct to `rgbmatrix` is a trap.

---

## The sequence

| # | Folder | Picker line | The one new idea | On the matrix when they're done | Min |
| --- | --- | --- | --- | --- | --- |
| 01 | `L01_say_something` | Put your own words on the matrix. | Variables | Their name, their colour, where they put it | 10 |
| 02 | `L02_your_first_dot` | Light up a block and put it anywhere. | The 64×32 grid: `.x` / `.y` | A coloured block they placed | 15 |
| 03 | `L03_make_it_move` | Send your block walking across the screen. | `for` + `range` + `time.sleep` | Block glides across and stops | 20 |
| 04 | `L04_tilt_to_steer` | Tilt the board and make the block follow. | **The accelerometer** | Block chases gravity, forever | 25 |
| 05 | `L05_hit_the_wall` | Stop the block at the walls and light a warning. | `if` / `elif` / `else` | Block pins to the edge, red light comes on | 25 |
| 06 | `L06_bounce` | Tilt the board to push a bouncing ball around. | Speed as a variable, and tilt changes speed not position | Ball you shove around a box | 30 |
| 07 | `L07_many_things` | Fill the screen with falling stars. | Lists | Starfield falling, all at once | 25 |
| 08 | `L08_your_own_commands` | Shake the board to spawn more stars. | Functions (`def`, arguments, `return`) | Shake it, stars appear | 30 |
| 09 | `L09_catch_it` | Catch the falling dots before they land. | Collision — two objects comparing positions | A real, playable game | 35 |
| 10 | `L10_keep_score` | Put a live score on the screen. | Numbers into text | Game + score counting up | 25 |
| 11 | `L11_brick_wall` | Build a wall of bricks and knock one out. | Nested loops → a grid of things | Rainbow brick wall, bricks vanish | 25 |
| 12 | `L12_breakout` | Build the whole game: tilt, bounce, bricks, score. | *(assembly)* | Breakout | 60–90 |

**Total: ~4h30 of lessons 01–11, plus 60–90 min for the capstone. ~5h45.**
Roughly 8 class periods.

**Lesson 05 was split in two, 2026-08-13**, exactly as the Pushback section
predicted. `if` and direction-as-a-variable were never one idea, and writing 04
settled it: the house style — name every number, one transformation per line —
makes a combined lesson far too long. 05 is now `if` alone, applied to a wart
the student already felt in 04 (the block hanging off the edge). 06 inherits the
bounce with `if` already in hand.

The old lesson 10 (loading a `.bmp`) is **cut**. It was the only lesson that
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
| Text that changes while running (`.text = `) | 10 | 12 |
| Nested loops, a list built in a loop | 11 | 12 |

**Nothing is used before it's taught.** The one place that came close:

- **`while True` in lesson 04.** Lesson 03 uses `for x in range(64)`. Lesson 04
  swaps that one line for `while True:` — presented as "same loop, no end", one
  word of new syntax, not a lesson's worth of idea.

Bounds-checking used to be the other one. `screen.tilt()` clipping removed it.

---

## Lesson 01 also has to be the smoke test

`L00_does_it_work` is going away, so L01 inherits three jobs beyond teaching
variables: prove the LEDs light, prove a save reaches the board, and prove the
Serial Monitor works. All three fall out of the lesson naturally — change
`MESSAGE`, press Ctrl+S, the words on the matrix change and a `print()` line
appears in the console. The change *is* the proof.

**L01 is static — no animation.** L00 colour-cycled, which also proved the board
wasn't frozen, but that needs a loop and loops are lesson 03. A student who
typed a new message and sees it on the LEDs has all the proof they need. Don't
put an unexplained `while True` in the first file.

`code.py` becomes `from L01_say_something import main`.

---

## The accelerometer

**Lesson 04, and it can't come sooner.** A sensor read with no loop around it
reads once at boot and never again — you tilt the board and nothing happens,
which is worse than not having it at all. The floor is:

1. Something on screen to move (02)
2. `.x` / `.y` you can assign to (02)
3. A loop to read it in (03)

`if` is *not* required, because `screen.tilt()` clips. Lesson 04 is the 4th file
and about 45 minutes in.

**What lesson 04 actually teaches, now that setup is hidden:** mapping one range
of numbers onto another. `screen.tilt()` gives −1.0..1.0 and the screen wants
0..63, so `x = 32 + int(tx * 29)` — centre, scale, round off. That is a more
useful hour than three lines of I2C boilerplate would have been, and it is the
same move again in 08 and 11.

Second appearance is lesson 07, as shake: `if screen.force() > 2.0:`. It reuses
the sensor to demo functions rather than introducing a new toy.

**To verify on hardware while writing `screen.py`:** which axis is left/right
with the matrix upright and the USB socket where a student actually holds it,
which sign each way, and the resting jitter. All three are now `screen.py`'s
problem, and a deadzone can live in `tilt()` without any lesson knowing.

---

## The drawing model

**Every visible thing is its own movable object, positioned with `.x` / `.y`.**
Not one full-screen bitmap with `bitmap[x, y] = 1`.

Off-screen `.x` clips silently on a moved object and is an `IndexError` on a
bitmap — that alone is worth the choice, and it's what lets lesson 04 arrive
before `if`. Moving is free, so no lesson has to explain why a moving block
leaves a smear behind it.

Backed by `vectorio.Rectangle` since 2026-08-13 — 37% less RAM and 24% faster
than `Bitmap` + `TileGrid`, measured at lesson 06's workload. `Circle` and
`Polygon` were measured and rejected; see `CLAUDE.md` for the numbers. None of
this is visible in a lesson, which is the point of `screen.py`.

The knock-on wins:

- Bricks are a list of TileGrids, and a hit brick is `brick.hidden = True`.
  Hiding is easier than deleting, and it's reversible.
- A per-row `Palette` gives the rainbow brick wall straight from
  `colors.RAINBOW`, with no palette lecture.

With `screen.py` and the `.bmp` lesson cut, **`bitmap[x, y]` never appears in
the course at all.** That is the intended trade.

---

## Capstone: Breakout

Tilt-steered paddle, bouncing ball, a wall of bricks, a score. It fits 64×32
comfortably: 8 columns × 3 rows of 8×2 bricks across the top 6 rows, a 1-pixel
ball, an 8×1 paddle.

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

Lesson 12 ships as a **scaffold with `TODO`s**, not an empty file. The wall, the
paddle and the score come pre-wired from 10 and 11; the student fills in the
ball's bounce and the brick collision — the two things they have already
written once each. Then the *make it yours* list: speed up on each hit, lives, a
win screen, colour the ball by speed, swap the paddle for a `.bmp`.

Budget 60–90 minutes and expect two sittings. Say so in the lesson rather than
pretending it's one period.

Alternates if Breakout doesn't land with a group: **Snake** (better for lists,
worse for bounce and collision) or **dodge the falling blocks** (a straight
extension of 08, but too small to feel like a capstone).

---

## House style for lesson code

Derived from the rewrites L02 and L04 got on 2026-08-13. Write lessons this way
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

**`screen.py` makes lessons 01 and 02 very short — three or four lines each.**
That is a feature at lesson 01 and a question at lesson 02. I'd still keep them
separate: 01 is where nobody can get lost, and 02 is where the coordinate grid
lands, which is the single most-used idea in the course. But 02 needs real
exercises to fill its 15 minutes — put a block in each corner, find the centre,
work out what `.y = 0` means — not more reading.

**The escape hatch needs to exist and doesn't need to be advertised.** A student
who wants something `screen.py` doesn't offer isn't stuck: the returned objects
are ordinary `displayio` objects, and `screen.py` itself is a readable file
sitting next to `colors.py`. Nothing about the design has to be un-learned
later. Worth one sentence somewhere in `Readme.md`, not in a lesson.

**~~Lesson 05 is doing the most work.~~ Split, 2026-08-13.** It was `if`, `else`,
comparisons and direction-as-a-variable at once, which is one idea only if you
squint. Now 05 is `if` alone and 06 is the bounce. Evidence that decided it: the
house style adds ~8 lines of named intermediates to any lesson, so a combined
one would have run past 40 lines.

**Lesson 09 is the thinnest and might be half a lesson.** Keep it separate
anyway: `str(score)` vs `score` is a real error students hit, and a score on
screen is the best motivation-per-minute in the course. If you ever need to drop
to ten lessons, this is the one to fold into 08.

**Lesson 12 is not one lesson and the plan shouldn't pretend it is.** See above.

**Deliberately not in the course:** classes, dictionaries, `try`/`except`, list
comprehensions, `%`, file I/O, and now per-pixel drawing. None are needed for
Breakout, and each is a lesson that ends with nothing new on the matrix.

**`print()` gets no lesson of its own.** It's introduced in 01 alongside the
Serial Monitor and used everywhere after as the debugging move. A lesson about
output that appears in a panel rather than on the LEDs would break the
visible-payoff rule.

---

## Writing order

1. **`screen.py`**, verified on hardware. Everything imports it, and it holds all
   three accelerometer unknowns. Nothing else can be written honestly first.
2. **L01**, then **L02**. Verify both on the board.
3. **Delete `L00_does_it_work`**, point `code.py` at L01, full sync.
4. **L04** next, out of order, as a spike — it's the last place hardware can
   surprise us, and what it needs from `screen.tilt()` may still move.
5. Then 03, 05, 06, … in order. Everything from 05 on is ordinary Python.
