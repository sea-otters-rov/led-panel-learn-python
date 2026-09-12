"""Bump your two boards together and they pair up, with nothing to type.

The two previous lessons had a line where you type your partner's id. This one
does not. Instead: simply tap your board to your partner's!

The trick is combining the knowledge that your board was tapped and you got a message
that another board was tapped at almost the same time. Two events close together in
time are treated as one event that touched both boards.

Your board is always in one of two states, and that is most of this lesson:

    UNPAIRED      broadcasting when tapped, and listening for a tap or for
                  somebody who still thinks you are their partner
    PAIRED        Ignores taps. Only your partner's moves get through

The second state is what makes this work with more than two boards. Otherwise,
everyone's messages would be jumbled together!

Two message kinds now, which is the first time the word on the front of a
message really matters:

    tap <my id>                     I have just been tapped
    move <my id> <tilt x> <tilt y>  This is my current tilt value

Notice the move message says who it is from. It has to, since a board cannot tell who
sent it anything. Without that, it could not reconnect to the right partner.
"""

import colors
import interactions
import network
import screen
import random

tap_kind = "tap"
move_kind = "move"

tap_force = 1.4  # 1.0 is sitting still; a firm tap on the desk is about 1.4

# One tap reaches both boards at nearly the same instant, and a message crosses the
# room in under a tenth of a second. If this is too large, the more
# likely two people fidgeting at the same moment get paired by accident.
pair_window = 0.3

# Quiet for this long and we give up on our partner. It has to be longer than a save
# takes, which can be up to 10 seconds. Any shorter and a partner who saves is dropped
# before they can get back, and the resume below never gets a chance to happen.
forget_after = 15.0

my_color = colors.JADE
their_color = colors.MAGENTA
my_size = 2
their_size = 4

my_id = interactions.join_wifi()
print(f"I am board {my_id}")

tap_sign = screen.text("", colors.AMBER, 1, 3, font=screen.Fonts.SMALL)

theirs = screen.circle(their_size, their_color, 0, 0)
mine = screen.circle(my_size, my_color, 0, 0)

screen_center_x = screen.WIDTH // 2
screen_center_y = screen.HEIGHT // 2

# Who we are paired with, or None when we are on our own. This controls what state
# we're in: paired or unpaired
partner_id = None


def tilt_to_x(tilt, size):
    return int(tilt * screen_center_x) + screen_center_x - size // 2


def tilt_to_y(tilt, size):
    return int(tilt * screen_center_y) + screen_center_y - size // 2


def get_newest_message(kinds: list[str]):
    # Same as 203, now there are two different kinds we care about
    newest_msg = None
    for msg_text in network.receive_all():
        # First, chop the message into its parts by splitting it by space
        msg_parts = msg_text.split(" ")

        # See if the first part is a message we care about
        if msg_parts[0] in kinds:
            newest_msg = msg_parts  # Just keep overwriting our variable with messages
            # Note this only grabs the latest of any type. If we're looking for
            # two different types and we get one of each in a single cycle,
            # we'll only get whichever one arrived last. Later we'll see how to
            # keep the latest of each

    # No more waiting messages, return what we got. If we didn't get
    # anything that matched, newest_msg will still be None
    return newest_msg


def send_pairing_broadcast():
    network.send_to_everyone(f"{tap_kind} {my_id}")


def send_move_msg(partner_id, tilt_x, tilt_y):
    network.send(partner_id, f"{move_kind} {my_id} {tilt_x} {tilt_y}")


def pair_to_partner(new_partner_id):
    global partner_id
    partner_id = new_partner_id
    screen.timer_reset()  # pairing counts as hearing from them: start the clock
    theirs.hidden = False
    tap_sign.text = "Pair " + partner_id
    tap_sign.color = colors.GREEN
    print(f"paired with board {partner_id}")


def unpair():
    global partner_id
    if partner_id is not None:
        print(f"unpaired from {partner_id}")
    partner_id = None
    theirs.hidden = True
    tap_sign.text = "Tap to pair"
    tap_sign.color = colors.AMBER


# Call this at the beginning to setup everything so it's ready to pair
unpair()

while True:
    # Two different modes, either we're waiting to pair or we're paired and
    # exchanging tilt info movement
    tilt_x, tilt_y, tilt_z = interactions.smoothed_tilt()
    mine.x = tilt_to_x(tilt_x, my_size)
    mine.y = tilt_to_y(tilt_y, my_size)

    if partner_id is None:
        # Only do this when we're trying to pair.
        if screen.force() > tap_force:
            # Did we see a tap? Tell everyone! Then see if someone else saw one too.
            send_pairing_broadcast()
            # Start our timer so we can see how long a response takes
            screen.timer_reset()

            # Change the top text so they know they tapped successfully
            tap_sign.text = "tapped"
            tap_sign.color = colors.PURPLE

        elif screen.timer_elapsed() < 1:
            tap_sign.color = colors.dim(colors.PURPLE, 1 - screen.timer_elapsed())
        else:
            tap_sign.text = "Tap to pair"
            tap_sign.color = colors.AMBER

        # Pairing can happen two ways...
        # Tap-to-pair:  A tap message received soon after a tap pairs to the sender.
        # Move: If we receive a move message, assume it is our previous partner and
        # resume the pairing.
        msg = get_newest_message([tap_kind, move_kind])
        if msg is not None:  # did we get one of the types we care about?
            kind = msg[0]
            if (
                kind == tap_kind  # did we get a tap message?
                and len(msg) == 2  # and was it the right length?
                and screen.timer_elapsed() < pair_window  # and it arrived quickly?
            ):
                # We matched! This is our new partner id
                pair_to_partner(msg[1])
            elif (
                kind == move_kind  # did we get a move message?
                and len(msg) == 4  # and was it the right length?
            ):
                # We resumed a previous match!
                pair_to_partner(msg[1])

    else:
        # We have a partner, send our movements and receive theirs

        send_move_msg(partner_id, tilt_x, tilt_y)

        msg = get_newest_message([move_kind])
        if (
            msg is not None  # did we get the right kind of message?
            and len(msg) == 4  # and was it the right length?
            and msg[1] == partner_id  # and was it from our partner?
        ):
            screen.timer_reset()
            theirs.x = tilt_to_x(float(msg[2]), their_size)
            theirs.y = tilt_to_y(float(msg[3]), their_size)

        elif screen.timer_elapsed() > forget_after:
            # Our partner has gone quiet for too long
            unpair()

    screen.draw()


# Try these:
#   - Pair up, then press Ctrl+S on your board. It restarts knowing nothing at
#     all -- and picks your partner straight back up without being tapped.
#     What does that, and how does it know it is safe?
#   - Now set forget_after to 1.0 and have your partner save. This time your board
#     gives up. How important is reconnecting automatically?
#   - Set pair_window to 10.0 and get a third person to tap their board at roughly
#     the same time as you and your partner. Who are you paired with? Put it
#     back to 0.3 and try the same thing.
#   - How do you break up? Work out what has to be true for your board to let go
#     of a partner, then get two pairs to swap partners. Is it fiddly? What
#     would you add to make it easy, and what would that cost you?
#
# And the mischief:
#
#   - Change send_pairing_broadcast to someone else's id. You are telling the
#     room that a different board was tapped. What happens to your partner's
#     board?
#   - Change send_pairing_broadcast to *your partner's* id. Now what happens to
#     your partner's board?
#   - Change send_move_msg to other values besides your tilt_x and tilt_y, for
#     example, random numbers between -1 and 1, eg random.uniform(-1,1)
#     What does their screen show, and what would it take for them to
#     notice you were lying?
