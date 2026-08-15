"""Send your block walking across the screen.

A for loop repeats lines for you. This one counts 0, 1, 2 ... 63, and nudges
the block one step further across each time round.
"""

import time

import colors
import screen

block = screen.block(3, 3, colors.JADE, 0, 14)

# range(64) counts from 0 up to 63 -- one number for every column on the screen.
# The indented lines run once for each of those numbers. Unindent, and they only
# run once at the end.
for step in range(64):
    block.x = step  # step is 0 the first time round, then 1, then 2...
    time.sleep(0.5)  # seconds to wait before the next step. Smaller = faster.

    # Also write to the serial console for each step. These prints are optional, but handy when debugging.
    print(f"walked to x:{block.x}")

screen.hold()  # freeze on the last step, or the screen clears

# Try these:
#   - Change 0.5 to 0.2, then to 0.005. Save after each one.
#   - Adjust range(64) -> range(20). Where does it stop?
#   - Add  block.y = step  inside the loop for a diagonal walk.
#   - What if you set the width to step instead of x?
#   - Make a second block above the loop, then move it the opposite way inside
#     the loop:  other_block.x = 63 - step
