"""Send two numbers at once, so their block moves in both directions.

Lesson 202 sent one number and their block could only slide left and right.
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
up-and-down number all the way to one end, so your block sits pinned to the
bottom edge and the new half of this lesson is invisible.

Remember what happened in lesson 202 when someone in the room switched back to
201: their nudge arrived at your board, your code called float() on the word
"hello!", and your board stopped dead. It stopped because it believed
everything it was handed. This lesson is where you stop doing that.
"""

import colors
import network
import screen

##############################################
# The id of the board you are talking to. It is the number in the corner of
# your partner's panel -- ask them, and type it here.
##############################################

partner_id = 4

my_color = colors.JADE
their_color = colors.MAGENTA

# The word every one of our messages starts with. Your board only believes a
# message that begins with this, so a message meant for a different lesson --
# or for a different game -- gets quietly ignored instead of crashing you.
MESSAGE_KIND = "tilt"

sign = screen.text("Connecting", colors.AMBER, 2, 16)
screen.draw()

my_id = network.start()
print(f"I am board {my_id}, talking to board {partner_id}")

sign.hidden = True

# Your own id in the corner, so your partner can read it from across the room.
text_x = screen.WIDTH - 4 * len(my_id)
screen.text(my_id, colors.AMBER, text_x, 3, font=screen.Fonts.SMALL)

# Theirs is bright, yours is dim. Both can now go anywhere on the screen, so
# without the difference in brightness you would not know which one you were
# steering.
theirs = screen.block(4, 4, their_color, 0, 0)
mine = screen.block(4, 4, colors.dim(my_color, 0.25), 0, 0)

screen_center_x = screen.WIDTH // 2
screen_center_y = screen.HEIGHT // 2
block_center_x = theirs.width // 2
block_center_y = theirs.height // 2


def tilt_to_x(tilt):
    # Scale the tilt (-1.0 .. 1.0) to the screen width and centre it.
    return int(tilt * screen_center_x) + screen_center_x - block_center_x


def tilt_to_y(tilt):
    # The same again for up and down. The screen is half as tall as it is wide,
    # so the same tilt moves you half as far.
    return int(tilt * screen_center_y) + screen_center_y - block_center_y


def tilt_to_message(x, y):
    # Three words with a space between each: what kind of message this is,
    # then the two numbers. The spaces are the whole trick -- they are what
    # .split() looks for at the other end.
    return f"{MESSAGE_KIND} {x} {y}"


def get_newest_message():
    # Exactly as in lesson 202: take everything waiting and keep the last one.
    newest_msg = None
    while True:
        msg = network.receive()
        if msg is not None:
            newest_msg = msg
        else:
            return newest_msg


while True:
    tilt_x, tilt_y, tilt_z = screen.tilt()

    network.send(partner_id, tilt_to_message(tilt_x, tilt_y))

    msg = get_newest_message()
    if msg is not None:
        # Chop the message into its words.
        word = msg.split()

        # And now CHECK it before believing a single thing in it.
        #
        # Two questions, and you need both. Is it the right shape -- exactly
        # three words, so word[1] and word[2] are really there? And is it the
        # right kind -- does it start with our word?
        #
        # Anything else falls straight through and is ignored. A "hello!" from
        # someone still on lesson 201 is the wrong kind. A message that got cut
        # short is the wrong shape. Neither one can stop your board any more.
        if len(word) == 3 and word[0] == MESSAGE_KIND:
            theirs.x = tilt_to_x(float(word[1]))
            theirs.y = tilt_to_y(float(word[2]))

    mine.x = tilt_to_x(tilt_x)
    mine.y = tilt_to_y(tilt_y)

    screen.draw()

# Try these:
#   - Get someone to switch a board back to lesson 201 and nudge it. In lesson
#     202 that stopped your board. Now nothing happens at all. Which line is
#     doing that?
#   - Delete `word[0] == MESSAGE_KIND` and leave the length check. Have them
#     nudge again. It crashes -- but only sometimes. What is it about "hello!"
#     that decides whether you get away with it?
#   - Change MESSAGE_KIND to "wiggle" on YOUR board only. Nothing crashes and
#     nothing complains. Both of you stop moving. How long would it take you to
#     work out why, if you had not just done it on purpose?
#
# And now the interesting part. You decide what to send:
#
#   - Make tilt_to_message always send 0.9 as the x, whatever your board is
#     actually doing. Your partner's screen shows you pinned to the right and
#     they cannot tell. They believe your numbers because nothing in their
#     program is in a position to doubt them.
#   - Send a number far bigger than 1.0. Where does your block go on their
#     screen? Could their program have noticed that you sent something no real
#     tilt could produce?
#   - Get your partner to send `tilt banana 0.5`. Three words, right first
#     word -- so it passes both checks, and still stops your board. Checking
#     the SHAPE of a message is not the same as checking what is IN it.
#     Hold on to that one.
