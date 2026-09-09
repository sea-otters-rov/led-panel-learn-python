"""Light up a block and put it anywhere on the screen.

The screen is a grid: 64 across, 32 down. Everything you put on it has an .x
and a .y that say where it sits.
"""

import colors
import screen

# screen.block(width, height, color, x, y) makes a solid rectangle and puts it up.
# You can hand it a spot right away, like this red one marking where the grid starts.
first_block = screen.block(2, 2, colors.RED, 0, 0)

# Or leave the spot off and set it afterwards. Same block either way -- but this
# is the version you can keep moving, which is how everything moves in lesson 103.
second_block = screen.block(3, 3, colors.CYAN)
# .x and .y are the block's top-left corner, not its middle.
second_block.x = 30  # across: 0 is the far left, 63 is the far right
second_block.y = 14  # down:   0 is the top, 31 is the bottom. Further down is bigger!

print(
    f"second_block at x:{second_block.x}, y:{second_block.y} on a {screen.WIDTH} x {screen.HEIGHT} screen"
)

screen.hold()  # halt with your block up, or the console takes the screen back

# Try these:
#   - Set second_block.y = 0, save, then second_block.y = 31. What happened to it?
#   - Move the second_block to different corners. What are the four pairs of numbers?
#       Does the first_block sit on top or get hidden underneath?
#   - Change screen.block(3, 3, ...) to screen.block(20, 2, ...) for a long bar
#   - What would have to happen to make 10 blocks? 20 blocks? 100 blocks?
