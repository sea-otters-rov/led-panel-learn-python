"""Nudge your board and your words land on everybody else's screen.

Lesson 101 put your words on YOUR screen. This puts them on your friend's, over
the wifi. Same idea, one board further away.

Three new things, and only one of them is really new:

  network.start()                 join the wifi, and find out who you are
  network.send_to_everyone(...)   say something to every board in the room
  network.receive()               the next thing someone sent, or None

Everything else you already know: a while loop, an if, and screen.text.
"""

import colors
import network
import screen

my_message = "hello!"  # what your board says when you nudge it
my_color = colors.CYAN
nudge_force = 1.3  # 1.0 is sitting still. A tap on the desk is about 1.4
fade_seconds = 5.0  # how long a message takes to fade away to nothing

# Put something on the screen BEFORE joining the wifi.
#
# network.start() takes about five seconds -- the Wifi is a whole second chip
# that has to be woken up and then told to join the network. Five
# seconds of a dark panel isn't great, better to have some indication whats
# happening.
sign = screen.text("Connecting", colors.AMBER, 2, 16)
screen.draw()

# start() hands back this board's id, which is the address other boards can
# use if they want to send a message to us directly (L202).
#
# Notice that the id comes from start(). You do not get to pick it, and it
# does not exist until the wifi join has finished -- the network is what hands
# it out. That is also why the panel says "Connecting" first and cannot show
# your number yet.
my_id = network.start()
print(f"I am board {my_id}")

# Your id in the top right corner. Each small letter takes 4 pixels
# across counting the gap after it, so this pushes the number up to the edge
# whether the id is one digit or three.
# len gives the "length" of whatever you pass in. That length depends on the
# type you pass in. For example, passing a list returns the count of items. Passing
# in a string like my_id returns the number of characters.
text_x = screen.WIDTH - 4 * len(my_id)
screen.text(my_id, colors.AMBER, text_x, 3, font=screen.Fonts.SMALL)

sign.text = "nudge"
sign.color = my_color

# Make sure the timer starts fresh.
screen.timer_reset()
screen.draw()

while True:
    if screen.force() > nudge_force:
        # The board was nudged, prepare a message
        msg_to_send = my_id + ": " + my_message

        # Now send it to everyone
        network.send_to_everyone(msg_to_send)

        # And show it here too
        sign.text = msg_to_send
        screen.timer_reset()  # back to full brightness
        print(f"sent {msg_to_send}")

    # What somebody sent. receive() never waits: if nothing has arrived it
    # hands back `None` right away and the loop keeps going.
    heard = network.receive()
    if heard is not None:  # Check if heard has a value
        sign.text = heard
        screen.timer_reset()
        print(f"heard {heard}")

    # Fade whatever is showing down to nothing over fade_seconds so new
    # messages arriving are noticable.
    brightness = 1.0 - screen.timer_elapsed() / fade_seconds
    if brightness < 0:
        brightness = 0  # faded right out. Do not go negative -- dim() needs 0..1
    sign.color = colors.dim(my_color, brightness)

    screen.draw()

# Try these:
#   - Change my_message to your name, save, and nudge. Whose board changed?
#   - Delete the `sign.text = msg_to_send` line and nudge again. Your own screen stops
#     changing, even though your partner's still does. "Everyone" turns out to
#     mean everyone else -- a board does not hear its own broadcast.
#  ** At least two people nudge at the same moment. What does your screen end up
#     showing? Do all the boards match? Is it consistent? Why do you think?
