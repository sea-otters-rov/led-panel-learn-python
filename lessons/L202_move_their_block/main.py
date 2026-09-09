"""Tilt your board and move a block on your partner's screen.

Lesson 201 sent words to everybody. This sends a number to ONE board -- the one
whose id you type in below -- and it does it every single time round the loop,
so your partner's block follows your board as you tilt it.

The new idea is small: float(). Lesson 110 used str() to turn a number into
words so it could go on the screen. A message is words too, so a number has to
become words to be sent -- and then turn back into a number at the far end.
That is what float() is for. It is str() run backwards.

Your screen shows two blocks:

    bright   your partner, moved by THEIR board
    dim      you, moved by YOUR board

so you can see your own tilt working even before your partner has their board
running.
"""

import colors
import network
import screen

# The id of the board you are playing with. It is the number in the corner of
# your partner's panel -- ask them, and type it here.
#
# This is the only line that is different on the two boards. Everything else
# below is identical, which is worth noticing: "who am I talking to" is the
# whole of the configuration.
partner_id = 11

my_color = colors.JADE
their_color = colors.MAGENTA

# Say something before joining, because joining takes about five seconds and a
# dark panel looks like a dead board. Lesson 201 did this too.
sign = screen.text("Connecting", colors.AMBER, 2, 16)
screen.draw()

my_id = network.start()
print(f"I am board {my_id}, talking to board {partner_id}")

# The full address of the board you are sending to. You do not need this line
# to play -- network.send() works out the address from the id by itself -- but
# print it once and you can see what an id really is:
#
#     board 4  ->  192.168.1.4
#
# Every board in the room shares the first three numbers. Only the last one
# says which board, so the last one on its own is enough to name it. That is
# all an id is: an address with the boring part left off.
print(f"board {partner_id} is at {network.address_of(partner_id)}")

sign.hidden = True

# Your own id in the corner, the same as lesson 201 -- this is the number your
# partner has to type into THEIR copy of this file, so it has to be readable
# from across the room.
badge = screen.text(
    my_id, colors.AMBER, 64 - 4 * len(my_id), 3, font=screen.Fonts.SMALL
)

# Their block is bright and yours is dim, so there is never any doubt which is
# which -- and a dim block that still answers your tilt tells you your own
# board is fine when nothing is arriving.
theirs = screen.block(4, 4, their_color, 30, 8)
mine = screen.block(4, 4, colors.dim(my_color, 0.2), 30, 20)

# The same centring arithmetic as lesson 104. Nothing about it changes just
# because one of the blocks is being driven from across the room.
screen_center_x = screen.WIDTH // 2
block_center_x = theirs.width // 2

# Where your partner was the last time they said anything. It starts in the
# middle, because until a message arrives you genuinely do not know.
their_tilt_x = 0.0

while True:
    tilt_x, tilt_y, tilt_z = screen.tilt()

    # Send how far you are tilted, as words. str() is doing the same job it did
    # in lesson 110 -- it is just going down a wire instead of onto a screen.
    network.send(partner_id, str(tilt_x))

    # Read EVERYTHING that has arrived, not just one message, and keep the last
    # one. Your partner sends once per turn and so do you, but the two boards
    # never run at exactly the same speed -- so if you only took one message
    # per turn, the spare ones would pile up and their block would drift
    # further and further behind what their board is actually doing.
    #
    # Nothing arriving is not a problem. their_tilt_x simply keeps the value it
    # already had, so their block stays where they left it.
    heard = network.receive()
    while heard:
        their_tilt_x = float(heard)  # words back into a number
        heard = network.receive()

    mine.x = int(tilt_x * screen_center_x) + screen_center_x - block_center_x
    theirs.x = int(their_tilt_x * screen_center_x) + screen_center_x - block_center_x

    screen.draw()

# Try these:
#   - Get the id wrong on purpose -- use a board that is not there. Your block
#     still moves and theirs never does. Nothing crashes and nothing tells you.
#     Sending is like posting a letter: you find out it arrived by getting a
#     reply, not by posting it.
#   - Put your partner's id in as "4" with the quotes instead of 4 without
#     them. It still works. Now try their whole address, "192.168.1.4". Read
#     the error -- it says what an id is.
#   - Take the str() off the network.send() line. What does the error say, and
#     why can a message only ever be words?
#   - Take the float() off instead, so you assign the words straight to
#     their_tilt_x. This one does not crash on that line. Where does it break?
#   - Swap `while heard:` for `if heard:` and play for a minute or two, tilting
#     constantly. Does their block keep up, or does it start lagging?
#   - Send tilt_y as well and move the blocks up and down too. You will find
#     you cannot -- not with what you know yet. One message carries one number.
#     That is exactly what lesson 203 is about.
#   - Three people, one triangle: you send to A, A sends to B, B sends to you.
#     Whose tilt is your bright block following?
#   - Both of you set partner_id to the SAME board. What does that board see?
