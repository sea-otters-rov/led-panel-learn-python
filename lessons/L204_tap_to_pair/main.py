"""Bump your two boards together and they pair up, with nothing to type.

The two previous lessonss had a line where you type your partner's id. This one
does not. Instead: simply tap your board to your partners!

The idea behind it is worth more than the trick. Neither board can see the
room, and neither can tell who sent a message. All they have is this: something
happened to me just now, and something happened to you at almost the same
moment. That is enough. Two events close together in time are treated as one
event that touched both boards.

It is also why the pairing does not survive a save. Your board forgets
everything when it restarts, so after a save you need to tap them again.

Two message kinds now, which is the first time the word on the front of a
message really earns its keep:

    tap 4              I have just been knocked
    move 4 0.12 -0.44  this is board 4, and this is where it is pointing

Notice the move message says who it is from. It has to. A board cannot tell who
sent it anything, so if the message does not say, nobody knows.

And notice it is called `move`, not `tilt`, even though it is carrying a tilt.
Lesson 203 already used the word `tilt` for a message with only two numbers in
it and nobody's name on the front. A kind has to mean exactly one thing: the
moment two different messages share a word, the word stops telling you anything
and you are back to guessing from the length. So each new shape gets a new
name, and old names are never reused for something else.
"""

import time

import colors
import interactions
import network
import screen

tap_kind = "tap"
move_kind = "move"

tap_force = 1.4  # 1.0 is sitting still; a knock on the desk is about 1.4
pair_window = 1.0  # two knocks this close together count as the same knock
forget_after = 3.0  # partner quiet this long and we are on our own again

my_color = colors.JADE
their_color = colors.MAGENTA
my_size = 2
their_size = 4

my_id = interactions.join_wifi()
print(f"I am board {my_id}")

sign = screen.text("tap!", colors.AMBER, 1, 3, font=screen.Fonts.SMALL)

theirs = screen.circle(their_size, their_color, 0, 0)
mine = screen.circle(my_size, my_color, 0, 0)
theirs.hidden = True  # nothing to show until somebody is there

screen_center_x = screen.WIDTH // 2
screen_center_y = screen.HEIGHT // 2

# Who we are paired with, or None when we are on our own. Everything below
# hangs off this one variable.
partner_id = None

# The two knocks we are comparing: ours, and the last one we heard about.
my_tap_time = 0.0
their_tap_id = None
their_tap_time = 0.0

# When our partner last said anything. Going quiet is how we find out they
# have gone -- nobody ever sends a goodbye.
heard_from_partner = 0.0


def tilt_to_x(tilt, size):
    return int(tilt * screen_center_x) + screen_center_x - size // 2


def tilt_to_y(tilt, size):
    return int(tilt * screen_center_y) + screen_center_y - size // 2


while True:
    now = time.monotonic()
    tilt_x, tilt_y, tilt_z = interactions.smoothed_tilt()

    # Were we just knocked? Tell the whole room, and remember when.
    if screen.force() > tap_force:
        network.send_to_everyone(f"{tap_kind} {my_id}")
        my_tap_time = now

    msg = network.receive()
    while msg is not None:
        msg_parts = msg.split(" ")

        if len(msg_parts) == 2 and msg_parts[0] == tap_kind:
            # Somebody was knocked. Not necessarily our somebody -- we find
            # that out below, by looking at when it happened.
            their_tap_id = msg_parts[1]
            their_tap_time = now

        elif (
            len(msg_parts) == 4
            and msg_parts[0] == move_kind
            and msg_parts[1] == partner_id
        ):
            # A tilt, and it says it is from our partner. Anyone else's is
            # ignored -- which is the whole point of having a partner.
            heard_from_partner = now
            theirs.x = tilt_to_x(float(msg_parts[2]), their_size)
            theirs.y = tilt_to_y(float(msg_parts[3]), their_size)

        msg = network.receive()

    # Two knocks at about the same moment: that was one knock, and it touched
    # both boards. abs() throws away the sign, so it does not matter whose
    # message got there first.
    if their_tap_id is not None and abs(my_tap_time - their_tap_time) < pair_window:
        # A knock lasts a few times round the loop, so only say something the
        # first time, or when we have swapped to a different partner.
        if partner_id != their_tap_id:
            print(f"paired with board {their_tap_id}")

        partner_id = their_tap_id
        heard_from_partner = now
        theirs.hidden = False
        sign.text = "with " + partner_id

        # Used up. Pairing again takes two fresh knocks, or a board that
        # rebooted would silently re-pair off the knocks from last time.
        their_tap_id = None

    # Our partner has gone quiet. They saved, or switched off, or wandered off
    # with the board. Either way we are on our own until somebody knocks.
    if partner_id is not None and now - heard_from_partner > forget_after:
        print(f"lost board {partner_id}")
        partner_id = None
        theirs.hidden = True
        sign.text = "tap!"

    if partner_id is not None:
        network.send(partner_id, f"{move_kind} {my_id} {tilt_x} {tilt_y}")

    mine.x = tilt_to_x(tilt_x, my_size)
    mine.y = tilt_to_y(tilt_y, my_size)

    screen.draw()

# Try these:
#   - Pair up, then press Ctrl+S on your board. Watch your partner's panel: you
#     vanish, and you do not come back on your own. Why not? What do you have to
#     do, and does that seem right?
#   - Set pair_window to 0.05. Try to pair. How good do your reflexes have to
#     be? Now set it to 10.0 and get someone across the room to knock their
#     board. Who are you paired with?
#   - Three pairs in the room all knock at the same moment. Who ends up paired
#     with whom? Try it. Is there any way your board could have known?
#   - Set forget_after to 60. Switch your partner's board off. Your panel still
#     says you have a partner. For how long is that a lie?
#   - Take `and msg_parts[1] == partner_id` out of the move check. Now get a
#     third board to send you a move. Whose shape is on your screen?
#   - Change move_kind back to "tilt" on both boards. It still works! Now get a
#     third board running lesson 203 to send you one of ITS tilt messages. Why
#     does that one still get ignored, and what would have to be true about the
#     numbers for it to sneak through?
#
# And the mischief:
#
#   - Send `tap <someone else's id>` instead of your own. You are telling the
#     room that a board you are not was knocked. What happens to the person who
#     knocked at that moment?
#   - Once your partner has paired with you, send them
#     `move <a third board's id> 0.9 0.9`. They ignore it. Now send them
#     `move <your own id> 0.9 0.9` twenty times a second while your board sits
#     still. What does their screen show, and what would it take for them to
#     notice you were lying?
