"""Tilt the board and make the block follow.

Lay the board down flat, like a tray. screen.tilt() tells you which way it is
tipped, and the block shifts that way.
"""

import time

import colors
import screen

block = screen.block(4, 4, colors.AMBER, 32, 16)

# Get the center of the screen
screen_center_x = screen.WIDTH // 2
screen_center_y = screen.HEIGHT // 2

# and the center of the block.
block_center_x = block.width // 2  # // divides and throws away the remainder
block_center_y = block.height // 2

# Previously we used a for loop to repeat a fixed number of times. Now we want to
# keep going forever, so we use `while True:` instead. The indented lines run
# over and over.
while True:
    # tilt amount, each -1.0 to 1.0. Perfectly flat is 0,0,1
    tilt_x, tilt_y, tilt_z = screen.tilt()

    # tilt is -1..1, but the screen is 0..63 across and 0..31 down. Multiplying
    # stretches the tilt out to fill the screen. int() throws away the decimals --
    # there is no such thing as half a pixel.
    tilt_x_pixels = int(tilt_x * screen_center_x)
    tilt_y_pixels = int(tilt_y * screen_center_y)

    # We want the block to move from the center of the screen, so we add the screen center to the
    # tilt. But the block's .x and .y are its top-left corner, not its middle, so we subtract half the
    # block's width and height.
    block.x = tilt_x_pixels + screen_center_x - block_center_x
    block.y = tilt_y_pixels + screen_center_y - block_center_y

    print(f"tilt {tilt_x:+.2f}, {tilt_y:+.2f}, {tilt_z:+.2f}")

    time.sleep(0.05)


# Try these:
#   - Try tilting and also gently shaking it. What happens to the block? What is "tilt" actually measuring?
#   - Swap tilt_x and tilt_y between the two lines. Now which way does it roll?
#   - Remove an 'int(' and the matching ')'. Read the error carefully.
#   - How would the serial print be helpful if the block wasn't where you expect?
#   - Where does the block go if you turn it upside down? What happens to tilt_z?
