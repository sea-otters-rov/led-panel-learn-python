"""Build a wall of bricks, then knock it down.

A loop inside a loop. The outer one walks down the rows, and for every single
row the inner one runs all the way across. Two loops, a whole grid.
"""

import time

import colors
import rainbowio
import screen
from vectorio import Rectangle

screen.FULL_TILT = 4.0

brick_rows = 3
brick_columns = 8
brick_width = 7
brick_height = 3
brick_gap = 1

ball_size = 4

screen_center_x = screen.WIDTH // 2
screen_center_y = screen.HEIGHT // 2
ball_center = ball_size // 2
ball_max_x = screen.WIDTH - ball_size
ball_max_y = screen.HEIGHT - ball_size

bricks: list[Rectangle] = []

# The inner loop finishes completely for EVERY step of the outer one. Three rows
# times eight columns is twenty-four trips through the middle.
for row in range(brick_rows):
    for column in range(brick_columns):
        color = rainbowio.colorwheel(row * 30)
        brick = screen.block(brick_width, brick_height, color)
        brick.x = column * (brick_width + brick_gap)
        brick.y = row * (brick_height + brick_gap)
        bricks.append(brick)

print(f"built {len(bricks)} bricks: {brick_rows} rows of {brick_columns}")

# Made after the wall, so it rolls over the top of the bricks rather than under.
ball = screen.circle(ball_size, colors.WHITE)

knocked = 0
score = screen.text("0", colors.OLD_LACE, 26, 26)


def touching(brick):
    """True when the ball is on top of this brick and it is still standing.

    Same idea as catching a dot, but a brick can be missed on four sides now
    instead of three, so there is one more way to rule it out.
    """
    if brick.hidden:
        return False  # already knocked out, nothing left to hit
    elif ball.x + ball_size < brick.x:
        return False  # ball is off to the left of it
    elif ball.x > brick.x + brick_width:
        return False  # off to the right
    elif ball.y + ball_size < brick.y:
        return False  # above it
    elif ball.y > brick.y + brick_height:
        return False  # below it
    return True


while True:
    tilt_x, tilt_y, tilt_z = screen.tilt()

    ball.x = int(tilt_x * screen_center_x) + screen_center_x - ball_center
    ball.y = int(tilt_y * screen_center_y) + screen_center_y - ball_center
    if ball.x > ball_max_x:
        ball.x = ball_max_x
    elif ball.x < 0:
        ball.x = 0
    if ball.y > ball_max_y:
        ball.y = ball_max_y
    elif ball.y < 0:
        ball.y = 0

    # One loop over the whole wall, however many rows and columns it has.
    for brick in bricks:
        if touching(brick):
            brick.hidden = True  # hiding it is enough -- it stops being drawn
            knocked = knocked + 1
            score.text = str(knocked)
            print(f"knocked one out -- {knocked} of {len(bricks)}")

    screen.draw()

    time.sleep(0.03)

# Try these:
#   - Try having the colors change by column instead of by row. Now try to make every block be a different color!
#   - Swap the row and columns loops around on line 34,35. The wall still builds -- so what changed?
#     Hint: What if the bricks overlapped?
#   - Set brick_gap to 2. The right-hand column falls off the screen. What else
#     has to change so eight bricks still fit?
#   - Once the wall is gone, bring it all back with a loop of your own.
#   - Count the bricks still standing instead of the ones you have knocked out.
