# What you will build

You have a microcontroller with a 64×32 grid of colored LEDs on the front and an
accelerometer. Over the next 18 lessons, you'll learn how to use both together to
build a simple game while learning the fundamentals of Python -- and then a
second board joins in, and the game gets to be a game against somebody.

Each lesson is a folder with one file in it. Open the file, change something,
press Ctrl+S, and about a second later it is running on the LEDs. There is no
Run button: **saving is running**.

## Part 1 -- one board

| # | What you make | What you learn |
| --- | --- | --- |
| 101 | Your own words on the screen, in a color you pick | Variables -- names that hold something you can change |
| 102 | A colored block, anywhere you want it | Coordinates -- the screen is a grid, 64 across and 32 down |
| 103 | A block that walks across the screen | Loops -- doing something over and over |
| 104 | A block that follows the board as you tilt it | Reading a sensor, and turning its numbers into positions |
| 105 | A block that stops dead at the walls, with a warning light | `if` and `else` -- letting the program decide |
| 106 | A ball you shove around a box by tilting it | Speed as a number you can change, and what a bounce really is |
| 107 | A hundred stars falling down the screen | Lists -- one name holding many things at once |
| 108 | Fireworks that burst and fade when you nudge the board | Functions -- writing your own commands |
| 109 | A game: catch the falling dots on a paddle | Collisions -- working out when two things are touching |
| 110 | The same game, with the score up on the screen | Changing what the screen says while the game runs |
| 111 | A wall of bricks you can knock down | Loops inside loops, to build a whole grid |
| 112 | **Breakout** -- paddle, ball, bricks, score and lives | Putting all of it together |

## Part 2 -- two boards

Now the boards can talk to each other, and everything gets harder in an
interesting way. Your board can no longer see what your partner's board sees, so
the two of them have to *tell* each other -- and messages sometimes go missing,
and your partner might not be telling the truth.

| # | What you make | What you learn |
| --- | --- | --- |
| 201 | Nudge your board and your words land on everybody else's screen | Two boards can talk. Every board has a number, and you can say things to all of them |
| 202 | Tilt your board and move a block on your *partner's* screen | Saying which one board you mean, and turning a message back into a number |
| 203 | Two numbers in one message, so their block moves both ways | Taking a message apart, and checking it is the kind you wanted before you trust it |
| 204 | Bump your two boards together and they pair up | Two things happening at the same moment must be the same event. Nothing to type |
| 205 | Hit the ball over the top and it lands on your partner's panel | Who owns a thing. Handing it over so it is never lost and never in two places |
| 206 | Two balls and a score both panels agree on | Classes -- a ball that knows its own everything. And who is allowed to say what is true |

Every lesson ends with a short list of *Try these* -- small changes to make and
questions to answer. They are the best part, and there are no marks for them.
Part 2's end with a few ways to cheat, which are there to be tried.

**You will need a partner and their board from lesson 201 onwards.** Lay the two
boards flat with their top edges touching: that is one long court, and the ball
crosses the join.

**You cannot break the board by writing bad code** but you can by shaking it
_too_ much. These are meant to be tilted, not hit or dropped.
