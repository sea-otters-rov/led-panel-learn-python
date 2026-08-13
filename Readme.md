# Learning Python on an LED Matrix

You have a small computer with a 64×32 grid of coloured LEDs on the front. You
are going to write Python that makes it do things — words, colours, pictures,
and later on, reacting to being tilted and shaken.

The lessons are already on the board. You do not have to install anything, copy
anything, or press a Run button. You edit a file, you save it, it runs.

Everything you need is below. If you are setting up a laptop for the first time,
that lives in [MAINTAINING.md](MAINTAINING.md) instead.

---

## Switching lessons

**Press Ctrl+Shift+B.**

A list appears with every lesson and a one-line description of what it does. The
one running right now is marked with a `*`. Type its number and press Enter.

That is the whole thing. The board restarts into the new lesson straight away.

You can also open **Task Explorer** in the sidebar and click *Lessons: choose
one*, along with every other task in this project.

---

## Working on a lesson

Each lesson is a folder inside `lessons/` with a `main.py` in it. That file is
where you work. Open it, change something, save.

Saving copies the file to the board, which makes the board restart and run it.
About a second later, the change is on the LEDs. There is no separate "run"
step — **saving is running**.

Files also save on their own when you click away from the editor, so switching
to another tab will not lose your work.

To see what your program prints, open the **Serial Monitor** panel, pick the
board's port, and press **Start Monitoring**. Anything you `print()` shows up
there, and so does the error message if your program breaks:

```
Traceback (most recent call last):
  File "code.py", line 8, in <module>
  File "L00_does_it_work/main.py", line 27, in <module>
NameError: name 'MESSSAGE' isn't defined
```

That says the problem is in `main.py`, on line 27, and that `MESSSAGE` is
misspelled. Fix it, save, and the board recovers by itself. **You cannot break
the board by writing bad code.** The worst that happens is the LEDs go dark and
an error appears in the console.

A lesson folder can also hold pictures, fonts, or extra code files. Keeping them
together in the lesson's own folder is why each lesson is a folder rather than a
single file.

---

## When something goes wrong

**Saving stopped doing anything.**
Almost always the console. Pressing any key in the Serial Monitor drops you into
the REPL, which switches off the board's auto-reload. Press **Ctrl+D** to start
it again.

**Nothing on the LEDs, and an error in the console.**
Read the last line. It names the file and the line number. This is normal and it
is how you find mistakes — see the example above.

**The board is not showing up at all.**
Usually the USB cable. Some cables only carry power and no data; try another
one. Otherwise press the reset button on the board once.

**The console will not connect.**
Only one program can use the board's port at a time. If you started the *Board:
serial console* task, close it before using the Serial Monitor panel, and the
other way round.

**The console went quiet and will not come back.**
Pressing reset or unplugging the board disconnects the port completely. Press
**Start Monitoring** again. (Saving a file does a gentler restart that keeps the
connection.)

**Is it my lesson or my board?**
Run the **Board: verify** task. It restarts the board and prints exactly what
came back, which tells you which one is broken. Stop Monitoring first — the port
only allows one program at a time.

**Weird errors that will not go away.**
Sometimes the board's storage gets damaged — a file shows in the file browser
but will not open, or saving fails with `[Errno 22]`. Run the **Board: erase a
corrupted filesystem** task, then **Board: sync all files (clean)**. Nothing is
lost; every lesson is copied back from this folder.

**Out of space.** The board holds about 2 MB. The sync task prints how much is
left.

**Do not "safely eject" the board.** It is meant to stay connected. Ejecting it
just stops saving from working.
