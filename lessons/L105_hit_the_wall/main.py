"""Stop the block at the walls and light up a warning when it gets there.

`if` is how the board decides. This one decides whether the block has run past
the edge of the screen, and puts it back if it has.
"""

import time

import colors
import screen

block = screen.block(4, 4, colors.AMBER, 32, 16)

# A warning light in the top-left corner. hidden=True means "don't draw it".
warning = screen.block(3, 3, colors.RED, 0, 0)
warning.hidden = True

screen_center_x = screen.WIDTH // 2
screen_center_y = screen.HEIGHT // 2
block_center_x = block.width // 2
block_center_y = block.height // 2

# The block's .x is its left edge, so this is as far right as it can go before
# it starts hanging off the screen.
max_x = screen.WIDTH - block.width
min_x = 0

max_y = screen.HEIGHT - block.width
min_y = 0


while True:
    tilt_x, tilt_y, tilt_z = screen.tilt()

    block.x = int(tilt_x * screen_center_x) + screen_center_x - block_center_x
    block.y = int(tilt_y * screen_center_y) + screen_center_y - block_center_y

    # Only ONE of these three runs. Python checks them from the top and stops at
    # the first test that is true. else is what happens when none of them were.
    if block.x > max_x:  # ran off the right
        block.x = max_x
        warning.hidden = False
    elif block.x < min_x:  # ran off the left
        block.x = min_x
        warning.hidden = False
    elif block.y > max_y:  # ran off the right
        block.y = max_y
        warning.hidden = False
    elif block.y < min_y:  # ran off the left
        block.y = min_y
        warning.hidden = False
    else:  # somewhere in the middle, so no warning
        warning.hidden = True

    print(f"block.x {block.x:3}   ({min_x} to {max_x})")

    time.sleep(0.005)

# Try these:
#   - The block still escapes off the top and bottom. Fix it the same way.
#     What is max_y?
#   - Change > to >= in the first test. Does anything look different? Why not?
#   - Swap the first two branches. Does it still work? Why?
#   - Delete the else and the line under it. What gets stuck on?
#   - Can you make the warning light turn on 5px from the wall?
