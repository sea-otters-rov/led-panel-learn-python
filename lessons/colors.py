"""Colour names you can use from any lesson.

A colour here is one number written as 0xRRGGBB -- two hex digits of red, then
green, then blue, each from 00 (none) to FF (all of it). So 0xFF0000 is red
turned all the way up with no green and no blue.

Use it from a lesson like this:

    import colors
    text = label.Label(terminalio.FONT, text="hi", color=colors.CYAN)

For a colour that keeps changing, the board has a colour wheel built in. Give
it a number from 0 to 255 and it hands back a colour:

    import rainbowio
    text.color = rainbowio.colorwheel(n)

Add your own -- a colour is just a name and a number. Pick one at
https://www.google.com/search?q=color+picker and drop the leading # .
"""

BLACK = 0x000000
WHITE = 0xFFFFFF

RED = 0xFF0000
ORANGE = 0xFF2800
AMBER = 0xFF6400
YELLOW = 0xFF9600
GOLD = 0xFFDE1E
GREEN = 0x00FF00
JADE = 0x00FF28
TEAL = 0x00FF78
CYAN = 0x00FFFF
AQUA = 0x32FFFF
BLUE = 0x0000FF
PURPLE = 0xB400FF
MAGENTA = 0xFF0014
PINK = 0xF25AFF
OLD_LACE = 0xFDF5E6

# Handy for stepping through a rainbow one colour at a time.
RAINBOW = (RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE)


def dim(color, level):
    """The same colour, only darker. level 1.0 is full, 0.0 is off.

    A colour is one number holding three, so this pulls red, green and blue
    apart, shrinks each of them, and packs them back together. Keep dimming and
    it eventually lands exactly on BLACK.
    """
    red = (color >> 16) & 0xFF
    green = (color >> 8) & 0xFF
    blue = color & 0xFF
    return (int(red * level) << 16) + (int(green * level) << 8) + int(blue * level)
