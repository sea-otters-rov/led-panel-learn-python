"""Catch the falling dots before they reach the bottom.

Two things are touching when they overlap across AND down at the same time.
That one test is what turns a few moving shapes into a game.
"""

import random
import time

import colors
import screen
from displayio import TileGrid

# Normally the board has to be tipped a long way to reach the edge of the screen.
# Lowering it can make it easier to control, but too low and it gets twitchy
screen.FULL_TILT = 4.0

paddle_width = 12
paddle_height = 2
dot_count = 3
dot_size = 4
fall_speed = 1
starting_wait_time = 0.1
wait_time = starting_wait_time

screen_center_x = screen.WIDTH // 2
paddle_center_x = paddle_width // 2

paddle_y = screen.HEIGHT - paddle_height  # sits along the bottom edge
paddle_max_x = screen.WIDTH - paddle_width
dot_max_x = screen.WIDTH - dot_size

paddle = screen.block(paddle_width, paddle_height, colors.CYAN, 0, paddle_y)

dots: list[TileGrid] = []
for index in range(dot_count):
    dot = screen.circle(dot_size, random.choice(colors.RAINBOW))
    dot.x = random.randint(0, dot_max_x)
    dot.y = index * -10  # spread out, so they arrive one at a time
    dots.append(dot)

caught = 0
missed = 0

print(f"catch them! reaching the edge takes a tilt of {screen.FULL_TILT}")


def drop(dot):
    """Send one dot back above the top of the screen, somewhere new."""
    dot.x = random.randint(0, dot_max_x)
    dot.y = -dot_size


def on_the_paddle(dot):
    """True when this dot and the paddle are in the same place.

    Each test rules the dot OUT. Survive all three and it must be a catch.
    """
    if dot.y + dot_size < paddle_y:
        return False  # still falling, not at the paddle yet
    elif dot.x + dot_size < paddle.x:
        return False  # past the left end of the paddle
    elif dot.x > paddle.x + paddle_width:
        return False  # past the right end
    return True


while True:
    # Steer the paddle, exactly like lesson 104, then keep it on screen like lesson 105.
    tilt_x, tilt_y, tilt_z = screen.tilt()
    paddle.x = int(tilt_x * screen_center_x) + screen_center_x - paddle_center_x
    if paddle.x > paddle_max_x:
        paddle.x = paddle_max_x
    elif paddle.x < 0:
        paddle.x = 0

    for dot in dots:
        dot.y = dot.y + fall_speed

        if on_the_paddle(dot):
            caught = caught + 1
            drop(dot)
            print(f"caught it!   {caught} caught, {missed} missed")
        elif dot.y > screen.HEIGHT:
            missed = missed + 1
            drop(dot)
            print(f"missed that one.   {caught} caught, {missed} missed")

    screen.draw()

    time.sleep(0.01)

# Try these:
#   - screen.FULL_TILT sets how far you have to tip to reach the edge. Try 9,
#     which is a full tilt, then try 1.5. Can you think of a better way to
#     make it responsive without it getting twitchy?
#   - Make paddle_width smaller. How narrow before it stops being fun?
#   - Raise dot_count. How many can you actually track at once?
#   - Delete the first test in on_the_paddle. What does it catch now, and where?
