"""Nudge the board to set off fireworks.

A function is a command you write yourself. This lesson has two, and the whole
show is built out of calling them at the right moments.
"""

import random
import time

import colors
import rainbowio
import screen
from displayio import TileGrid

firework_count = 50
firework_size = 11
burst_frames = 40  # how many pictures the expanding ring is made of
fade_rate = 0.9  # how much brightness survives each loop. Lower burns out faster.

# A gentle nudge is plenty.
# Do not shake the board hard -- the LED panel and its USB cable do not enjoy it.
nudge_force = 1.1
quiet_seconds = 2.0  # if nobody nudges it, send one up anyway

max_x = screen.WIDTH - firework_size
max_y = screen.HEIGHT - firework_size

# Every firework is made once, up front, and reused forever. Making new ones in
# the loop instead would fill the board's memory until it exploded, too.
fireworks: list[TileGrid] = []
for index in range(firework_count):
    firework = screen.burst(firework_size, colors.BLACK, burst_frames)
    firework.hidden = True
    fireworks.append(firework)


# Functions can return a value you can reuse elsewhere
def get_random_color() -> int:
    """Pick a random color from the rainbow."""
    return rainbowio.colorwheel(random.randint(0, 255))


firework_index = 0  # which firework to light next, start at the beginning of the list


# Show a firework somewhere on the screen, and give it a random color
def light():
    global firework_index
    firework_index += 1
    if firework_index >= firework_count:
        firework_index = 0
    firework = fireworks[firework_index]

    if firework.hidden:
        firework.x = random.randint(0, max_x)
        firework.y = random.randint(0, max_y)
        screen.recolor(firework, get_random_color())
        screen.set_frame(firework, 0)  # back to the smallest picture
        screen.bring_to_front(firework)  # so this one draws over the older ones
        firework.hidden = False


# It takes a firework and changes it.
def step(firework):
    # Grow the ring until it reaches its last picture, then leave it there.
    frame = screen.frame_of(firework)
    if frame < burst_frames - 1:
        screen.recolor(firework, get_random_color())
        screen.set_frame(firework, frame + 1)
    else:
        color = colors.dim(screen.color_of(firework), fade_rate)
        screen.recolor(firework, color)
        if color == colors.BLACK:
            firework.hidden = True


print(f"nudge the board -- {firework_count} fireworks ready")

while True:
    # Stepping a burnt-out one costs nothing, so there is no need to check first.
    for firework in fireworks:
        if not firework.hidden:
            step(firework)

    # A nudge sets off everything that has already burnt out.
    force = screen.force()
    if force > nudge_force:
        light()
        screen.timer_reset()
        print(f"nudge {force:.1f}")

    # Nothing for a while? Send one up on its own so the screen is never empty.
    # timer_elapsed gives the number to seconds since we called timer_reset.
    if screen.timer_elapsed() > quiet_seconds:
        light()
        screen.timer_reset()  # resets timer_elapsed to 0
        print("quiet -- sent one up")

    screen.draw()

    time.sleep(0.03)

# Try these:
#   - Change fade_rate to 0.99, then 0.75. How long does a firework last?
#   - Set burst_frames to 2. The ring still fades, but what did you lose?
#   - Make a nudge set off five fireworks instead of just one.
#   - Make the fireworks random sizes.
#   - Try turning quiet_seconds down to 0.2 for a nice ambient show. What do you
#      think would happen if you turned it all the way down to 0?
