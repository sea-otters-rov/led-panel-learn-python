"""Build the whole game: tilt, bounce, bricks and a score.

Nothing in here is new. The wall is lesson 11, the paddle is lessons 4 and 5,
the bouncing is lesson 6, the score is lesson 10. Four pieces are missing --
search for TODO and fill them in, in order.

Right now the ball just rattles around the box. By the end it should be a game.
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

paddle_width = 14
paddle_height = 2

ball_size = 3
ball_speed = 0.7

screen_center_x = screen.WIDTH // 2
paddle_center_x = paddle_width // 2
paddle_y = screen.HEIGHT - paddle_height
paddle_max_x = screen.WIDTH - paddle_width

min_x = 0
min_y = 0
max_x = screen.WIDTH - ball_size
max_y = screen.HEIGHT - ball_size

# The wall, straight out of lesson 11.
bricks: list[Rectangle] = []
for row in range(brick_rows):
    for column in range(brick_columns):
        brick = screen.block(brick_width, brick_height, rainbowio.colorwheel(row * 30))
        brick.x = column * (brick_width + brick_gap)
        brick.y = row * (brick_height + brick_gap)
        bricks.append(brick)

paddle = screen.block(paddle_width, paddle_height, colors.CYAN, 0, paddle_y)
ball = screen.circle(ball_size, colors.WHITE)

# The ball's real position, with decimals, and how far it moves each loop.
ball_x = 30.0
ball_y = 20.0
ball_speed_x = ball_speed
ball_speed_y = -ball_speed

score = 0
score_sign = screen.text("0", colors.OLD_LACE, 26, 20)

print(f"{len(bricks)} bricks up. Fill in the TODOs to turn this into a game.")


def ball_hits(thing):
    """True when the ball is overlapping this block.

    TODO 1: this is lesson 11's touching(), with one change. Use thing.width and
    thing.height instead of the brick sizes, and it will work for the paddle as
    well as for a brick. Everything below needs this, so do it first.
    """
    return False


while True:
    # The paddle, from lessons 4 and 5.
    tilt_x, tilt_y, tilt_z = screen.tilt()
    paddle.x = int(tilt_x * screen_center_x) + screen_center_x - paddle_center_x
    if paddle.x > paddle_max_x:
        paddle.x = paddle_max_x
    elif paddle.x < 0:
        paddle.x = 0

    # Move the ball, from lesson 6.
    ball_x = ball_x + ball_speed_x
    ball_y = ball_y + ball_speed_y

    # Bounce off all four walls, also lesson 6. Reflecting the overshoot rather
    # than just stopping at the wall is what keeps the ball lively.
    if ball_x > max_x:
        ball_x = max_x - (ball_x - max_x)
        ball_speed_x = -ball_speed_x
    elif ball_x < min_x:
        ball_x = min_x + (min_x - ball_x)
        ball_speed_x = -ball_speed_x

    if ball_y > max_y:
        ball_y = max_y - (ball_y - max_y)
        ball_speed_y = -ball_speed_y
    elif ball_y < min_y:
        ball_y = min_y + (min_y - ball_y)
        ball_speed_y = -ball_speed_y

    ball.x = int(ball_x)
    ball.y = int(ball_y)

    # TODO 2: bounce the ball off the paddle.
    #   ball_hits(paddle) tells you when they are touching. Send the ball back
    #   upwards. Careful: if you only flip the speed, the ball can get stuck
    #   inside the paddle and flip again next loop. What else does it need?

    # TODO 3: knock out any brick the ball touches.
    #   Loop over bricks like lesson 11, hide the one it hits, add 1 to score,
    #   and put the new score on score_sign like lesson 10. The ball should
    #   turn around too.

    # TODO 4: right now the bottom wall saves you every time. Take that bounce
    #   away and decide what a miss should cost -- back to the middle? a life?
    #   game over? It is your game.

    screen.draw()

    time.sleep(0.03)

# Once it plays, make it yours:
#   - Speed the ball up a little with every brick, so it gets harder.
#   - Give the ball a colour that changes with how fast it is going.
#   - Hit the paddle near the edge and send the ball off at a steeper angle.
#   - Three lives, shown as three small blocks in a corner.
#   - Clear the wall and put it straight back up, one row faster.
