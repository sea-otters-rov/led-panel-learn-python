"""Tilt your board and move a block on your partner's screen.

Lesson 201 sent words to everybody. This sends a number to ONE board -- the one
whose id you type in below -- and it does it every single time through the loop,
so your partner's block follows your board as you tilt it.

The new idea is small: float(). Lesson 110 used str() to turn a number into
words so it could go on the screen. A message is words too, so a number has to
become words to be sent -- and then turn back into a number at the far end.
That is what float() is for. It is str() run backwards.

Your screen shows two blocks:

    top:         your partner, moved by THEIR board
    bottom:      you, moved by YOUR board

so you can see your own tilt working even before your partner has their board
running.
"""

import colors
import network
import screen

##############################################
# The id of the board you are talking to. It is the number in the corner of
# your partner's panel -- ask them, and type it here.
##############################################

# This is the only line that is different on the two boards. Everything else
# below is identical, which is worth noticing: "who am I talking to" is the
# whole of the configuration.
partner_id = 4

my_color = colors.JADE
their_color = colors.MAGENTA

# Say something before joining, because joining takes about five seconds and a
# dark panel looks like a dead board. Lesson 201 did this too.
wifi_connecting = screen.text("Connecting", colors.AMBER, 2, 16)
screen.draw()

my_id = network.start()
screen.delete_shape(wifi_connecting)

print(f"I am board {my_id}, talking to board {partner_id}")

# The full address of the board you are sending to. You do not need this line
# to play -- network.send() works out the address from the id by itself -- but
# print it once and you can see what an address really is:
#
#     board 4  ->  192.168.1.4
#
# Every board in the room shares the first three numbers. Only the last one
# says which board, so the last one on its own is enough to name it. That is
# all an id is: an address with the boring part left off.
print(f"board {partner_id} is at {network.address_of(partner_id)}")


# Your own id in the corner, the same as lesson 201 -- this is the number your
# partner has to type into THEIR copy of this file.
text_x = screen.WIDTH - 4 * len(my_id)
screen.text(my_id, colors.AMBER, text_x, 3, font=screen.Fonts.SMALL)

# Their block is top and yours is bottom.
theirs = screen.block(4, 4, their_color, 0, 8)
mine = screen.block(4, 4, my_color, 0, 20)

# The same centring arithmetic as lesson 104. Nothing about it changes just
# because one of the blocks is being driven from across the room.
screen_center_x = screen.WIDTH // 2
block_center_x = theirs.width // 2


# Return the newest message. Each board is sending messages as fast as
# it can, so multiple messages may have arrived since last time we checked.
# Since the newsest one is the best indication of what the tilt actually is,
# just use that and ignore old messages.
def get_newest_message():
    newest_msg = None
    for msg in network.receive_all():
        newest_msg = msg  # Just keep overwriting our variable with messages

    # No more waiting messages, return what we got. If we didn't get
    # anything, newest_msg will still be None
    return newest_msg


def message_to_number(text):
    # We have to turn the message back into a number before we can do any
    # math with it.

    # Just assume the message only has a number. Nothing bad happens when you
    # assume things, right?!
    return float(text)


def number_to_message(num):
    # str() is doing the same job it did in lesson 110 -- it is just going
    # across a network instead of to a screen.
    return str(num)


def tilt_to_x(tilt):
    # Scale the tilt (-1.0 .. 1.0) to the screen width (0 .. 64) and center it
    return int(tilt * screen_center_x) + screen_center_x - block_center_x


while True:
    tilt_x, tilt_y, tilt_z = screen.tilt()

    # Send how far you are tilted, as a message, which is just text.
    network.send(partner_id, number_to_message(tilt_x))

    msg = get_newest_message()
    if msg is not None:
        # If we got a message, update their block location

        their_tilt_x = message_to_number(msg)
        theirs.x = tilt_to_x(their_tilt_x)

    mine.x = tilt_to_x(tilt_x)

    screen.draw()

# Try these -- one partner at a time:
#   - Change partner_id to 1, which isn't one of the boards. You still receive their
#     messages addressed to you, and your block still moves, but now your
#     partner stops receiving your messages. Nothing crashes and
#     nothing tells you if you send to the wrong address. Sending a message is
#     like talking: you don't know if they heard you unless they reply.
#   - Set partner_id to your own id. What happens?
#   - Make sure you and your partner have the serial console open, then switch
#     one board back to L201. What do they see? What happens if they nudge?
