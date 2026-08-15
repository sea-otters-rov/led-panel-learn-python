"""Tilt the board to push a bouncing ball around.

Tilting does not move the ball. It changes the ball's speed, a little bit every
time round the loop -- which is what pushing something actually means.
"""

import time

import colors
import screen

# A circle is drawn from a little picture rather than a plain shape, so it has
# no .width to ask for -- keep the size in a variable instead.
ball_size = 4
ball = screen.circle(ball_size, colors.CYAN)

min_x = 0
min_y = 0
max_x = screen.WIDTH - ball_size
max_y = screen.HEIGHT - ball_size

# The ball's real position, with decimals. A speed of 0.4 has to be able to add
# up over several loops, and whole numbers would throw that away every time.
ball_x = 10.0
ball_y = 6.0

# How far the ball moves each loop. Positive goes right and down, negative goes
# left and up.
ball_speed_x = 0.1
ball_speed_y = 0.1

tilt_push = 0.01  # how much a full tilt adds to the speed each loop

while True:
    tilt_x, tilt_y, tilt_z = screen.tilt()

    # Tilt changes the SPEED, not the position. Hold a tilt and the ball keeps
    # getting faster that way, the same as pushing a real ball for longer.
    ball_speed_x = ball_speed_x + tilt_x * tilt_push
    ball_speed_y = ball_speed_y + tilt_y * tilt_push

    # Adding the speed to the position is what makes it move.
    ball_x = ball_x + ball_speed_x
    ball_y = ball_y + ball_speed_y

    # A bounce is more than flipping the speed. One loop is a jump, not a glide,
    # so the ball lands PAST the wall. However far it went over, it has to come
    # back that far on the near side -- otherwise every bounce quietly steals a
    # little distance, and a ball that should bounce forever slowly dies out.
    if ball_x > max_x:
        overshoot = ball_x - max_x
        ball_x = max_x - overshoot
        ball_speed_x = -ball_speed_x
    elif ball_x < min_x:
        overshoot = min_x - ball_x
        ball_x = min_x + overshoot
        ball_speed_x = -ball_speed_x

    # And the same again for up and down -- the answer to lesson 5's try-this.
    if ball_y > max_y:
        overshoot = ball_y - max_y
        ball_y = max_y - overshoot
        ball_speed_y = -ball_speed_y
    elif ball_y < min_y:
        overshoot = min_y - ball_y
        ball_y = min_y + overshoot
        ball_speed_y = -ball_speed_y

    # The screen only has whole pixels, so chop off the decimals.
    ball.x = int(ball_x)
    ball.y = int(ball_y)

    print(
        f"ball {ball.x:3},{ball.y:3}   speed {ball_speed_x:+5.2f},{ball_speed_y:+5.2f}"
    )

    time.sleep(0.001)

# Try these:
#   - Tilt hard and hold it there. The ball speeds up going one way and slows
#     down coming back, so it settles into a rhythm instead of getting faster
#     and faster. Why does holding a tilt not keep adding speed?
#   - Now shake in time with the bounces, like pushing someone on a swing. That
#     does build speed up. How fast can you get it before you lose track of it?
#   - Raise tilt_push to 0.1. Is the ball easier or harder to control?
#   - Set tilt_push to 0. What does that do?
#   - Replace the two overshoot lines for y with just  ball_y = max_y  and hold
#     the board still. The ball sinks to the bottom and stays there. Why?
#   - Why do ball_x and ball_y exist at all, when the ball already has a .x and
#     a .y? Find out: delete an int( ) call so the line reads ball.x = ball_x.
#     Read the error. Then work out where a speed of 0.1 would end up if .x (an
#     integer) was the only place the position was kept.
#   - FIND THE BUG: Notice the ball never reaches the bottom or right edge. Why not?
#     How would you fix it?
#   - Four of the if blocks above are nearly identical. Count how many lines you
#     would save if you could write that once and reuse it.
