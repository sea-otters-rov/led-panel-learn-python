"""Put a live score on the screen while you play.

Words on the screen are something you can change, the same way you change a
block's .x. Set .text and they swap, right in the middle of the game.
"""

import random
import time

import colors
import screen
from displayio import TileGrid

screen.FULL_TILT = 4.0

paddle_width = 12
paddle_height = 2
dot_count = 3
dot_size = 4
fall_speed = 1
wait_time = 0.1

screen_center_x = screen.WIDTH // 2
paddle_center_x = paddle_width // 2

paddle_y = screen.HEIGHT - paddle_height
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

# Made last of everything, so the numbers draw on top of the dots instead of
# disappearing behind them. Remember .y is the MIDDLE of the text.
caught_sign = screen.text("0", colors.GOLD, 1, 6)
missed_sign = screen.text("0", colors.RED, 52, 6)


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
            # .text works like .x did -- hand it something new and the screen
            # changes. str() turns the number into letters first, because a
            # sign on the screen only knows how to show letters.
            caught_sign.text = str(caught)
            print(f"caught! the gold sign now reads {caught_sign.text}")
        elif dot.y > screen.HEIGHT:
            missed = missed + 1
            drop(dot)
            missed_sign.text = str(missed)
            print(f"missed. the red sign now reads {missed_sign.text}")

    screen.draw()

    time.sleep(wait_time)

# Try these:
#   - Turn caught_sign green once you get past 10.
#   - What happens if you miss more than 99? How would you fix that?
#   - Speed the game up every time you catch one, so it gets harder as you go.
#   - A miss costs you nothing right now. Make it reset your count and speed.
