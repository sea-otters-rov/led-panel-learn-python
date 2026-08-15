"""Put your own words on the matrix.

Change text_message and text_color below, then press Ctrl+S. The board restarts on its
own and your words show up. There is no Run button -- saving is running.
"""

import colors
import screen

# Both of these are variables -- a name you pick, holding a value you can change.
# Change one, save, and the screen changes with it. Right now you are the only
# thing that changes them. Soon the board will change them while it runs, and
# that is the whole trick behind everything that moves.
text_message = "hi!"
text_color = colors.CYAN

sign = screen.text(text_message, text_color)
sign.x = 2  # how far across. 0 is the far left edge.
sign.y = 16  # how far down. For text this is the MIDDLE of the line rather than
# its top, which is why 16 sits it neatly in the middle of a 32-tall screen.

# Shows up in the serial console. Useful for debugging!
# The f before the quote means "swap every {...} for its real value".
# :06X after a number shows it as hex -- 6 digits, zero-padded, capital letters --
# so CYAN prints as 00FFFF, exactly how it is written in colors.py.
print(f"showing:{text_message} in color:{text_color:06X} at x:{sign.x}, y:{sign.y}")

screen.hold()  # halt with your words up, or the console takes the screen back

# Try these:
#   - your own name in text_message
#   - colors.GOLD, colors.PINK, colors.JADE -- open colors.py for the whole list
#   - sign.x = 0 and sign.y = 4. Part of the text goes missing. Why?
#   - a really long message.
