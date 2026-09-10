"""See who else is in the room, and watch them come and go.

Every board shouts its own id about once a second. Every board listens, and
keeps a list of who it has heard from lately. That list is the roster, and it
appears on your panel: press Ctrl+S on your board and watch your id vanish
from everyone else's panel, then come back a few seconds later.

The new idea is the dictionary.

A list remembers things in order, and you get one out by its position --
stars[0]. A dictionary remembers things by NAME, and you get one out by that
name -- last_heard["4"]. Here the name is a board id, and the thing remembered
is the clock reading when we last heard from that board.

That is really what this lesson is about: keeping your own copy of something
that lives somewhere else. Your roster is a guess about the room, built out of
messages, and it is always a little bit out of date.

One thing to notice before you start. Nothing here sends a "goodbye". A board
that is switched off, or is busy restarting after a save, simply stops
shouting -- and going quiet IS the message. That is why the roster forgets
anyone it has not heard from for a few seconds.
"""

import time

import colors
import interactions
import network
import screen

# Every message we send looks like:  here 4
MESSAGE_KIND = "here"

HEARTBEAT = 1.0  # seconds between shouts
FORGET_AFTER = 3.0  # gone quiet this long and we assume they have left

# show_id=False, because this lesson puts our own id in the list instead of
# tucking it in the corner.
my_id = interactions.join_wifi(show_id=False)
print(f"I am board {my_id}")

# Five lines of the small font, top to bottom. The small letters are 5 tall and
# y is the middle of a line, so 6 pixels apart gives five lines that fit.
# Colours are set once, HERE, and never touched again in the loop -- changing a
# colour is slow even when the new colour is the same as the old one.
lines = []
for row in range(5):
    color = colors.AMBER if row == 0 else colors.JADE
    lines.append(screen.text("", color, 1, 3 + row * 6, font=screen.Fonts.SMALL))

# The roster. Empty to start with, because we have not heard anyone yet.
last_heard = {}

last_shout = 0.0

while True:
    now = time.monotonic()

    # Shout, but not every time round the loop -- once a second is plenty, and
    # six boards all shouting flat out would be a lot of noise for nothing.
    if now - last_shout > HEARTBEAT:
        network.send_to_everyone(f"{MESSAGE_KIND} {my_id}")
        last_shout = now

    # Read EVERY message, not just the newest one.
    #
    # This is the opposite of lesson 203. There, every message came from your
    # one partner and only the newest was worth having. Here each message is a
    # different board saying "I am still here", so throwing away all but the
    # last would mean forgetting everyone except whoever shouted most recently.
    msg = network.receive()
    while msg is not None:
        msg_parts = msg.split(" ")

        # The same check as lesson 203: right length, right kind, or ignore it.
        if len(msg_parts) == 2 and msg_parts[0] == MESSAGE_KIND:
            their_id = msg_parts[1]

            # `in` asks a dictionary whether it already has that name.
            if their_id not in last_heard:
                print(f"new board {their_id}")

            # Either way, write down that we heard from them just now. If they
            # were already in the roster this just overwrites the old time.
            last_heard[their_id] = now

        msg = network.receive()

    # Forget anyone who has gone quiet.
    #
    # list(last_heard) takes a snapshot of the names first. You are not allowed
    # to remove things from a dictionary while you are walking through it --
    # walk the snapshot, change the dictionary.
    for their_id in list(last_heard):
        if now - last_heard[their_id] > FORGET_AFTER:
            del last_heard[their_id]
            print(f"lost board {their_id}")

    # Build the list to show: you first, then everyone else.
    #
    # You are not in last_heard and never will be, because a board does not
    # hear its own shout -- lesson 201 again.
    showing = [my_id + " you"]
    for their_id in sorted(last_heard):
        showing.append(their_id)

    for row in range(len(lines)):
        if row < len(showing):
            lines[row].text = showing[row]
        else:
            lines[row].text = ""

    screen.draw()

# Try these:
#   - Press Ctrl+S on your board while your neighbour watches their panel. Your
#     id disappears from their list, then comes back. Count the seconds. What is
#     your board doing for all that time?
#   - Set FORGET_AFTER to 30. Switch a board off. How long does the room go on
#     believing it is there? Now set it to 0.5 and put the board back. Why does
#     everyone start flickering in and out?
#   - Set HEARTBEAT to 5.0 on YOUR board only. Everyone else's panel starts
#     losing you and finding you again. Whose setting is wrong -- yours, or
#     theirs?
#   - Take out the `del last_heard[their_id]` line. Now nobody is ever
#     forgotten. Switch a board off and watch: is the roster still true?
#   - Print len(last_heard) each time round the loop. Add a board, remove a
#     board. Does the number ever disagree with what is on the screen?
#   - Your own id is not in last_heard. Add a line that puts it in, then take
#     the `my_id + " you"` line out. Does the list still look right? Is it?
#
# And more mischief:
#
#   - Send `here 99` as well as your own id, once a second. A board that is not
#     in the room appears on everyone's roster, and stays there as long as you
#     keep saying it. Nothing anywhere checks that a name belongs to whoever
#     sent it.
#   - Send `here <your neighbour's id>` after they switch their board off. They
#     never leave the roster. Who would notice, and how?
