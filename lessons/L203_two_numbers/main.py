"""Send two numbers at once, so their shape moves in both directions.

Lesson 202 sent one number and their shape could only slide left and right.
A message can carry more than that -- but only if the far end knows how to take
it apart again.

The new idea is .split(). It chops a message up wherever there is a space and
hands you a list of the pieces, the same kind of list you made in lesson 107:

    "tilt 0.12 -0.44".split()   ->   ["tilt", "0.12", "-0.44"]

Three pieces. The last two are the numbers. The first one is a word we put
there ourselves to say what KIND of message this is -- and that turns out to
matter more than the extra number does.

Lay your board down FLAT for this one, like a tray, the way you did in lesson
104. Stood upright on a desk it still works, but gravity is already pulling the
up-and-down number all the way to one end, so your shape sits pinned to the
bottom edge and the new half of this lesson is invisible.

Remember what happened in lesson 202 when someone in the room switched back to
201: their nudge arrived at your board, your code called float() on the word
"hello!", and your board stopped dead. It stopped because it believed
everything it was handed. This lesson is where you stop doing that.
"""

import colors
import network
import screen
import interactions

##############################################
# The id of the board you are talking to. It is the number in the corner of
# your partner's panel -- ask them, and type it here.
##############################################

partner_id = 4

my_color = colors.JADE
my_size = 2
their_color = colors.MAGENTA
their_size = 4

# The word every one of our messages starts with. Your board only believes a
# message that begins with this, so a message meant for a different lesson --
# or for a different game -- gets quietly ignored instead of crashing you.
message_kind = "tilt"

# All the same wifi connection code tucked away in a function we can reuse
my_id = interactions.join_wifi()

print(f"I am board {my_id}, talking to board {partner_id}")

theirs = screen.circle(their_size, their_color, 0, 0)
mine = screen.circle(my_size, my_color, 0, 0)

screen_center_x = screen.WIDTH // 2
screen_center_y = screen.HEIGHT // 2


def tilt_to_x(tilt, size):
    # Scale the tilt (-1.0 .. 1.0) to the screen width, then shift back by half
    # the shape so it is the MIDDLE of the shape that lands on the spot, not
    # its top-left corner. The two shapes are different sizes, so each needs
    # its own half -- otherwise they never quite sit on top of each other.
    return int(tilt * screen_center_x) + screen_center_x - size // 2


def tilt_to_y(tilt, size):
    # The same again for up and down. The screen is half as tall as it is wide,
    # so the same tilt moves you half as far.
    return int(tilt * screen_center_y) + screen_center_y - size // 2


def tilt_to_message(x, y):
    # Three parts with a space between each: what kind of message this is,
    # then the two numbers. The spaces are what .split() looks for at the other end.
    return f"{message_kind} {x} {y}"


def get_newest_message():
    # Exactly as in lesson 202: take everything waiting and keep the last one.
    newest_msg = None
    for newest_msg in network.receive_all():
        pass  # Do nothing, just keep overwriting our variable with messages

    # No more waiting messages, return what we got. Note if we didn't get
    # anything, newest_msg will still be None
    return newest_msg


while True:
    tilt_x, tilt_y, tilt_z = interactions.smoothed_tilt()

    msg_to_send = tilt_to_message(tilt_x, tilt_y)
    network.send(partner_id, msg_to_send)
    print(f"Sent: {msg_to_send}")

    msg = get_newest_message()
    if msg is not None:
        print(f"Received: {msg}")
        # Chop the message into its parts by splitting it by space
        msg_parts = msg.split(" ")

        # And now CHECK it before trusting it.
        #
        # It needs to start with the right `kind` and have the right length
        # Anything else is ignored. A "hello!" from someone still on lesson 201 is
        # the wrong `kind` and wrong length. Neither can crash you now!
        if len(msg_parts) == 3 and msg_parts[0] == message_kind:
            theirs.x = tilt_to_x(float(msg_parts[1]), their_size)
            theirs.y = tilt_to_y(float(msg_parts[2]), their_size)

    mine.x = tilt_to_x(tilt_x, my_size)
    mine.y = tilt_to_y(tilt_y, my_size)

    screen.draw()

# Try these:
#   - Get someone to switch a board back to lesson 201 and nudge it. In lesson
#     202 that crashed your board. Now nothing happens at all. Why?
#   - Change message_kind to "moo" on YOUR board only. Nothing crashes and
#     nothing complains. Both of you stop moving. How long would it take you to
#     work out why, if you had not just done it on purpose?
#   - Just for fun, how hard is it to follow your partner? Would a game that measured
#     time spent covering your partner's shape be fair?
#
# Time for mischief: Your partner can't actually tell if you're sending real tilts!
#
#   - Make tilt_to_message always send 0.9 as the x, whatever your board is
#     actually doing. Your partner's screen shows you pinned to the right and
#     they cannot tell.
#   - Send a number far bigger than 1.0. Where does your shape go on their
#     screen? Could their program have noticed that you sent something no real
#     tilt could produce?
#   - Get your partner to send `tilt banana 0.5`. Three parts and right
#     kind, so it passes both checks, but it crashes. Checking
#     the SHAPE of a message is not the same as checking what is IN it.
#     We'll improve this later!
#   - Instead of sending your tilt values, send them back the ones they sent you!
#     Does a game measuring time covering your partner's shape seem more unfair?
