"""Breakout with all five TODOs filled in -- one way it can be finished.

This is lesson 12 with the blanks completed. It is a worked answer, not THE
answer: TODO 4 and TODO 5 are design questions, and yours can look different.
Have a go at lesson 12 first, then come back and compare.
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
speed_up = 0.15  # how much faster each new level is

starting_lives = 3

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

# One small block per life, tucked in above the paddle where nothing else goes.
lives = starting_lives
life_blocks: list[Rectangle] = []
for index in range(starting_lives):
    life_blocks.append(screen.block(2, 2, colors.RED, index * 3, screen.HEIGHT - 6))

score = 0
level = 1
score_sign = screen.text("0", colors.OLD_LACE, 26, 20)

ball_x = 30.0
ball_y = 20.0
ball_speed_x = ball_speed
ball_speed_y = -ball_speed

print(f"{len(bricks)} bricks, {lives} lives. Go.")


# TODO 1 -- lesson 11's touching(), reading the size off whatever it is handed
# so that one function covers both the bricks and the paddle.
def ball_hits(thing):
    """True when the ball is overlapping this block."""
    if thing.hidden:
        return False  # already knocked out, nothing left to hit
    elif ball.x + ball_size < thing.x:
        return False  # ball is off to its left
    elif ball.x > thing.x + thing.width:
        return False  # off to its right
    elif ball.y + ball_size < thing.y:
        return False  # above it
    elif ball.y > thing.y + thing.height:
        return False  # below it
    return True


def serve():
    """Put the ball back in the middle of the screen, heading upwards."""
    global ball_x, ball_y, ball_speed_x, ball_speed_y
    ball_x = float(screen_center_x)
    ball_y = 20.0
    ball_speed_x = ball_speed
    ball_speed_y = -ball_speed


def bricks_standing():
    """How many bricks have not been knocked out yet."""
    standing = 0
    for brick in bricks:
        if not brick.hidden:
            standing = standing + 1
    return standing


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

    # Bounce off the sides and the top. The bottom is gone -- see TODO 4.
    if ball_x > max_x:
        ball_x = max_x - (ball_x - max_x)
        ball_speed_x = -ball_speed_x
    elif ball_x < min_x:
        ball_x = min_x + (min_x - ball_x)
        ball_speed_x = -ball_speed_x

    if ball_y < min_y:
        ball_y = min_y + (min_y - ball_y)
        ball_speed_y = -ball_speed_y

    ball.x = int(ball_x)
    ball.y = int(ball_y)

    # TODO 2 -- bounce off the paddle. Lifting the ball clear first is what
    # stops it sinking in and flipping again on the very next loop.
    if ball_hits(paddle):
        ball_y = paddle_y - ball_size
        ball_speed_y = -ball_speed_y

    # TODO 3 -- knock out every brick the ball is touching, but only turn the
    # ball around once. A 3-pixel ball can straddle a gap and clip two bricks in
    # the same loop; flipping twice would cancel out and it would sail through.
    hit_something = False
    for brick in bricks:
        if ball_hits(brick):
            brick.hidden = True
            score = score + 1
            score_sign.text = str(score)
            hit_something = True
    if hit_something:
        ball_speed_y = -ball_speed_y
        print(f"brick -- score {score}, {bricks_standing()} left")

    # TODO 4 -- the bottom costs a life instead of bouncing.
    if ball_y > max_y:
        lives = lives - 1
        print(f"missed -- {lives} lives left")
        if lives > 0:
            life_blocks[lives].hidden = True  # counts down 2, 1, 0
            serve()
        else:
            life_blocks[0].hidden = True
            screen.text("DONE", colors.RED, 16, 16)
            print(f"game over on level {level} with {score} bricks")
            screen.draw()
            screen.hold()

    # TODO 5 -- wall cleared, so put it straight back up and speed it up.
    if bricks_standing() == 0:
        level = level + 1
        ball_speed = ball_speed + speed_up
        for brick in bricks:
            brick.hidden = False
        serve()
        print(f"level {level} -- ball speed now {ball_speed:.2f}")

    screen.draw()

    time.sleep(0.03)
