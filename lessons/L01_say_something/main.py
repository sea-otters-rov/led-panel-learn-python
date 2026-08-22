"""Put your own words on the matrix.

Change text_message and text_color below, then press Ctrl+S. The board restarts on its
own and your words show up. There is no Run button -- saving is running.
"""

import colors
import screen

# These are variables -- a name you pick, holding a value you can change.
# Change one, save, and the screen changes with it. Right now you are changing
# them manually, but soon the board will change them while it runs, and
# that is the whole trick behind everything that moves.
text_message = "hi!"  # This is a string, a sequence of characters
text_x = 2  # These are integers, single value
text_y = 16

# Colors are created by mixing red, green, and blue from 0-255. Some examples:
# Black: 0,0,0
# White: 255,255,255
# Blue: 0,0,255
# Light blue: 64,64,255
# Purple: 255,0,255
text_color = colors.color_from_components(0, 255, 255)

sign = screen.text(text_message, text_color)
sign.x = text_x  # how far across. 0 is the far left edge.
sign.y = text_y  # how far down. For text this is the MIDDLE of the line rather than
# its top, which is why 16 sits it neatly in the middle of a 32-tall screen.

# Shows up in the serial console. Useful for debugging!
# The f before the quote means "swap every {...} for its real value".
print(f"showing:{text_message} at x:{sign.x}, y:{sign.y}")

screen.hold()  # halt with your words up, or the console takes the screen back

# Try these:
#   - Make text_message your name
#   - Change the color components. What makes yellow?
#   - Set `text_x = 0` and `text_y = 4`. Part of the text goes missing. Why?
#   - Try a really long message.
#   - Where will `text_x = 2+3` end up? What will `text_message = "hi!"+"bye!"` do?
#      What is going on if you try `text_message = "hi!"+3`?
