"""color names you can use from any lesson.

A color here is one number written as 0xRRGGBB -- two hex digits of red, then
green, then blue, each from 00 (none) to FF (all of it). So 0xFF0000 is red
turned all the way up with no green and no blue.

Use it from a lesson like this:

    import colors
    text = label.Label(terminalio.FONT, text="hi", color=colors.CYAN)

For a color that keeps changing, the board has a color wheel built in. Give
it a number from 0 to 255 and it hands back a color:

    import rainbowio
    text.color = rainbowio.colorwheel(n)

Add your own -- a color is just a name and a number. Pick one at
https://www.google.com/search?q=color+picker and drop the leading # .
"""


def color_from_components(red: int, green: int, blue: int) -> int:
    """Create a color from it's component parts. Each value goes 0-255"""
    if red > 255 or green > 255 or blue > 255:
        raise ValueError("Color components must be between 0-255")

    return (red << 16) + (green << 8) + blue


BLACK = color_from_components(0, 0, 0)  # 0x000000
WHITE = color_from_components(255, 255, 255)  # 0xFFFFFF

RED = color_from_components(255, 0, 0)  # 0xFF0000
ORANGE = color_from_components(255, 40, 0)  # 0xFF2800
AMBER = color_from_components(255, 100, 0)  # 0xFF6400
YELLOW = color_from_components(255, 150, 0)  # 0xFF9600
GOLD = color_from_components(255, 222, 30)  # 0xFFDE1E
GREEN = color_from_components(0, 255, 0)  # 0x00FF00
JADE = color_from_components(0, 255, 40)  # 0x00FF28
TEAL = color_from_components(0, 255, 120)  # 0x00FF78
CYAN = color_from_components(0, 255, 255)  # 0x00FFFF
AQUA = color_from_components(50, 255, 255)  # 0x32FFFF
BLUE = color_from_components(0, 0, 255)  # 0x0000FF
PURPLE = color_from_components(180, 0, 255)  # 0xB400FF
MAGENTA = color_from_components(255, 0, 20)  # 0xFF0014
PINK = color_from_components(242, 90, 255)  # 0xF25AFF
OLD_LACE = color_from_components(253, 245, 230)  # 0xFDF5E6

# Handy for stepping through a rainbow one color at a time.
RAINBOW = (RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE)


def dim(color, level):
    """The same color, only darker. level 1.0 is full, 0.0 is off.

    A color is one number holding three, so this pulls red, green and blue
    apart, shrinks each of them, and packs them back together. Keep dimming and
    it eventually lands exactly on BLACK.
    """
    # Make sure level is between 0..1
    level = max(0, min(1.0, level))

    red = (color >> 16) & 0xFF
    green = (color >> 8) & 0xFF
    blue = color & 0xFF
    return (
        ((int(red * level) & 0xFF) << 16)
        + ((int(green * level) & 0xFF) << 8)
        + (int(blue * level) & 0xFF)
    )
