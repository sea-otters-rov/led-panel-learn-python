"""Put a live score on the screen while you play.

Words on the screen are something you can change, the same way you change a
block's .x. Set .text and they swap, right in the middle of the game.
"""

import random
import time
import interactions
import colors
import screen
from displayio import TileGrid

screen.FULL_TILT = 4.0

paddle_width = 12
paddle_height = 2
bad_dot_count = 1
bad_dot_size = 3
dot_count = 4
dot_size = 4
fall_speed = 1

screen_center_x = screen.WIDTH // 2
paddle_center_x = paddle_width // 2

paddle_y = screen.HEIGHT - paddle_height
paddle_max_x = screen.WIDTH - paddle_width
dot_max_x = screen.WIDTH - dot_size

paddle = screen.block(paddle_width, paddle_height, colors.CYAN, 0, paddle_y)

dots: list[TileGrid] = []
for index in range(dot_count):
    if index % 2:
        dot = screen.circle(dot_size, (colors.GREEN))
    else:
        dot = screen.circle(bad_dot_size, (colors.RED))

    dot.x = random.randint(0, dot_max_x)
    dot.y = index * -10  # spread out, so they arrive one at a time
    dots.append(dot)

caught = 0
missed = 0
bad_caught = 0

# Made last of everything, so the numbers draw on top of the dots instead of
# disappearing behind them. Remember .y is the MIDDLE of the text.
caught_sign = screen.text("0", colors.GREEN, 1, 4, "small")
bad_caught_sign = screen.text("0", colors.YELLOW, 31, 4, "small")
missed_sign = screen.text("0", colors.RED, 60, 4, "small")


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


count = 0
while True:
    count = count + 1
    tilt_x, tilt_y, tilt_z = interactions.smoothed_tilt()
    paddle.x = int(tilt_x * screen_center_x) + screen_center_x - paddle_center_x
    if paddle.x > paddle_max_x:
        paddle.x = paddle_max_x
    elif paddle.x < 0:
        paddle.x = 0

    if count % 2 == 0:
        for dot in dots:
            dot.y = dot.y + fall_speed

            if on_the_paddle(dot):
                if dot.tile_width == dot_size:
                    caught = caught + 1
                    caught_sign.text = str(caught)
                else:
                    bad_caught = bad_caught + 1
                    bad_caught_sign.text = str(bad_caught)
                    missed = missed + 1
                    missed_sign.text = str(missed)
                    if bad_caught > 9:
                        bad_caught_sign.x = 29

                drop(dot)

                print(f"caught! the gold sign now reads {caught_sign.text}")
            elif dot.y > screen.HEIGHT:
                if dot.tile_width == dot_size:
                    missed = missed + 1
                    if missed > 9:
                        missed_sign.x = 56
                    if missed > 99:
                        screen.text("GAME OVER!", colors.RED, 3, 16)
                        screen.text(
                            f"Score: {caught - bad_caught}",
                            colors.YELLOW,
                            15,
                            26,
                            "small",
                        )
                        for dot in dots:
                            dot.hidden = True
                        screen.draw()

                        screen.hold()
                drop(dot)
                missed_sign.text = str(missed)
                print(f"missed. the red sign now reads {missed_sign.text}")

    screen.draw()

    time.sleep(0.01)

# Try these:
#   - Turn caught_sign green once you get past 10.
#   - What happens if you miss more than 99? How would you fix that?
#   - Speed the game up every time you catch one, so it gets harder as you go.
#   - A miss costs you nothing right now. Make it reset your count and speed.
