"""Bump your two boards together and they pair up, with nothing to type.

The two previous lessons had a line where you type your partner's id. This one
does not. Instead: simply tap your board to your partners!

The idea behind it is worth more than the trick. Neither board can see the
room, and neither can tell who sent a message. All they have is this: something
happened to me just now, and something happened to you at almost the same
moment. That is enough. Two events close together in time are treated as one
event that touched both boards.

Your board is always in one of two states, and that is most of this lesson:

    ON YOUR OWN   shouting when knocked, and listening for a knock -- or for
                  somebody who still thinks you are their partner
    PAIRED        deaf to knocks. Only your partner's moves get through

The second state is what makes this work in a real room. Six boards being
fidgeted with means knocks flying about constantly, and a board that still
listened to them while paired would be stolen away every few seconds. Once you
have a partner, knocks stop being interesting.

Your board still forgets everything when it restarts. But it does not have to
be knocked again, because of a detail worth noticing: a move is sent straight
to one board, never shouted at the room. So if a move arrives while you are on
your own, whoever sent it must still think you are their partner -- and they
can only think that if you were. Picking the pairing back up is safe in a way
that trusting a knock is not, because a knock is shouted at everybody and a
move is addressed to you.

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

# One knock reaches both boards at the same instant, and a message crosses the
# room in well under a tenth of a second. Be strict: the wider this is, the more
# likely two people fidgeting at the same moment get paired by accident.
pair_window = 0.3

# Quiet for this long and we give up on our partner. It has to be longer than a
# save takes, which is about five and a half seconds -- your board is off the
# air for all of it. Any shorter and a partner who saves is dropped before they
# can get back, and the resume below never gets a chance to happen.
forget_after = 8.0

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

    # Only shout about a knock while we are on our own. A board that already
    # has a partner keeps quiet, so it cannot be stolen and it is not adding to
    # the noise while five other people fidget with their boards.
    if partner_id is None and screen.force() > tap_force:
        network.send_to_everyone(f"{tap_kind} {my_id}")
        my_tap_time = now

    if partner_id is not None:
        network.send(partner_id, f"{move_kind} {my_id} {tilt_x} {tilt_y}")

    # Whoever we decide to pair with this time round, if anyone.
    new_partner = None

    for msg in network.receive_all():
        msg_parts = msg.split(" ")

        if partner_id is None:
            # ON OUR OWN. Two ways out of here.
            if len(msg_parts) == 2 and msg_parts[0] == tap_kind:
                # Somebody was knocked. Whether it was OUR knock is decided
                # below, by looking at when it happened.
                their_tap_id = msg_parts[1]
                their_tap_time = now

            elif len(msg_parts) == 4 and msg_parts[0] == move_kind:
                # A move is only ever sent straight to a partner, never to the
                # whole room. So whoever sent this still believes we are theirs
                # -- which means we were paired before we restarted. Pick the
                # pairing back up rather than making them knock again.
                new_partner = msg_parts[1]

        elif (
            len(msg_parts) == 4
            and msg_parts[0] == move_kind
            and msg_parts[1] == partner_id
        ):
            # PAIRED. Nothing but our partner's moves gets a look in -- not
            # even a knock. That is what stops a roomful of people banging
            # their boards about from stealing us away.
            heard_from_partner = now
            theirs.x = tilt_to_x(float(msg_parts[2]), their_size)
            theirs.y = tilt_to_y(float(msg_parts[3]), their_size)

    # Two knocks at about the same moment: that was one knock, and it touched
    # both boards. abs() throws away the sign, so it does not matter whose
    # message got there first.
    if (
        partner_id is None
        and their_tap_id is not None
        and abs(my_tap_time - their_tap_time) < pair_window
    ):
        new_partner = their_tap_id
        their_tap_id = None  # used up; pairing again takes two fresh knocks

    if new_partner is not None:
        partner_id = new_partner
        heard_from_partner = now
        theirs.hidden = False
        sign.text = "with " + partner_id
        print(f"paired with board {partner_id}")

    # Our partner has gone quiet for longer than a save could explain. They
    # switched off, or wandered away, or paired with somebody else. Either way
    # we are on our own again, and free to be knocked.
    if partner_id is not None and now - heard_from_partner > forget_after:
        print(f"lost board {partner_id}")
        partner_id = None
        theirs.hidden = True
        sign.text = "tap!"

    mine.x = tilt_to_x(tilt_x, my_size)
    mine.y = tilt_to_y(tilt_y, my_size)

    screen.draw()

# Try these:
#   - Pair up, then press Ctrl+S on your board. It restarts knowing nothing at
#     all -- and picks your partner straight back up without being knocked.
#     Which line does that, and how does it know it is safe to?
#   - Now set forget_after to 3.0 and save again. This time your partner gives
#     up on you while you are still restarting, so nobody is sending moves when
#     you come back and you have to knock after all. A save takes about five and
#     a half seconds off the air. Why does that number decide this one?
#   - Pair up, then get a third person to knock their board against yours.
#     Nothing happens at all. Take the `partner_id is None` off the tap line and
#     try it again. Which of those two do you want in a room of six?
#   - Set pair_window to 10.0 and get someone across the room to knock their
#     board at roughly the same time as you. Who are you paired with? Put it
#     back to 0.3 and try the same thing.
#   - Three pairs in the room all knock at the same moment. Who ends up paired
#     with whom? Try it. Is there any way your board could have known?
#   - Set forget_after to 60. Switch your partner's board off. Your panel still
#     says you have a partner. For how long is that a lie?
#   - How do you break up? Work out what has to be true for your board to let go
#     of a partner, then get two pairs to swap partners. Is it fiddly? What
#     would you add to make it easy, and what would that cost you?
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
#   - Find somebody who is on their own and send them `move <your id> 0 0`,
#     with nobody knocking anything. They pair with you. Picking a pairing back
#     up trusts a move because only a real partner would send one -- which is
#     true right up until somebody sends one on purpose.
#   - Once your partner has paired with you, send them
#     `move <a third board's id> 0.9 0.9`. They ignore it. Now send them
#     `move <your own id> 0.9 0.9` twenty times a second while your board sits
#     still. What does their screen show, and what would it take for them to
#     notice you were lying?
