"""Nudge your board and your words land on everybody else's screen.

Lesson 101 put your words on YOUR screen. This puts them on your friend's, over
the wifi. Same idea, one board further away.

Three new things, and only one of them is really new:

  network.start()                 join the wifi, and find out who you are
  network.send_to_everyone(...)   say something to every board in the room
  network.receive()               the next thing anybody said, or ""

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
# network.start() takes about five seconds -- the radio is a whole second chip
# that has to be woken up and then talked round to joining your network. Five
# seconds of a dark panel looks exactly like a board that has died, so say what
# is happening first. Every networked program you write should do this.
sign = screen.text("Connecting", colors.AMBER, 2, 16)
screen.draw()

# start() hands back this board's id: a small number that means THIS board and
# no other. Every board in the room gets a different one, which is how a class
# running the identical program stops being anonymous.
#
# Notice that the id arrives FROM start(). You do not get to pick it, and it
# does not exist until the wifi join has finished -- the network is what hands
# it out. That is also why the panel says "Connecting" first and cannot show
# your number yet.
my_id = network.start()
print(f"I am board {my_id}")

# Your own id, small, in the top right corner. Each small letter takes 4 pixels
# across counting the gap after it, so this pushes the number up to the edge
# whether the id is one digit or three.
badge = screen.text(
    my_id, colors.AMBER, 64 - 4 * len(my_id), 3, font=screen.Fonts.SMALL
)

sign.text = "nudge"
sign.color = my_color

# Start the fade clock HERE, not earlier. It starts running the moment screen
# is imported, and joining the wifi ate five seconds of it -- so without this
# the word "nudge" would already have faded away before you ever saw it.
screen.timer_reset()
screen.draw()

while True:
    # Nudge the board and everyone hears about it. Your id goes on the front,
    # so what arrives at the other end says who sent it -- otherwise a room
    # where everybody kept my_message as "hello!" is a room where every screen
    # says "hello!" and nobody can tell who nudged.
    if screen.force() > nudge_force:
        said = my_id + ": " + my_message
        network.send_to_everyone(said)

        # And show it here too. send_to_everyone means everyone ELSE: your own
        # board does not hear it, so without this line a nudge does nothing you
        # can see, and you would have to trust that it worked.
        sign.text = said
        screen.timer_reset()  # back to full brightness
        print(f"sent {said}")

    # What somebody else said. receive() never waits: if nothing has arrived it
    # hands back "" straight away and the loop keeps going. That is what stops
    # your screen freezing whenever the room goes quiet.
    heard = network.receive()
    if heard:
        sign.text = heard
        screen.timer_reset()
        print(f"heard {heard}")

    # Fade whatever is showing down to nothing over fade_seconds.
    #
    # This is what makes a second nudge visible when it says exactly the same
    # words as the first: the words do not change, but the brightness jumps
    # back to full and starts falling again. Without it, nudging twice looks
    # identical to nudging once.
    brightness = 1.0 - screen.timer_elapsed() / fade_seconds
    if brightness < 0:
        brightness = 0  # faded right out. Do not go negative -- dim() needs 0..1
    sign.color = colors.dim(my_color, brightness)

    screen.draw()

# Try these:
#   - Change my_message to your name, save, and nudge. Whose board changed?
#   - Delete the `sign.text = said` line and nudge again. Your own screen stops
#     changing, even though your partner's still does. "Everyone" turns out to
#     mean everyone else -- a board does not hear its own broadcast.
#   - Set fade_seconds to 30. Now nudge twice in a row. Can you still tell it
#     happened twice? What is the shortest fade that still reads clearly?
#   - Move the screen.timer_reset() out of the `if heard:` block. The message
#     from your partner arrives, but it does not brighten. Why not?
#   - Look at the address your board printed next to its id. Which part of the
#     address is your id? Now work out your neighbour's address from the number
#     on their panel, and check it against what theirs printed. (This is all
#     network.address_of(their_id) does -- lesson 202 uses it.)
#   - Two people nudge at the same moment. What does your screen end up
#     showing? Is it the same as what your neighbour's shows?
#   - Send my_message WITHOUT the id on the front. With three boards going, can
#     you still tell who said what?
#   - Take the screen.draw() out of the loop and put it inside the `if heard:`
#     instead. The screen stops updating. (draw() has to run every time round
#     the loop, not sometimes.)
#   - Press Ctrl+S while your partner watches their screen. Their board keeps
#     going -- but yours is off the network for about four seconds while it
#     restarts and re-joins. Count it.
