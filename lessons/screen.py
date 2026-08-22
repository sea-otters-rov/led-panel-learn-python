"""The matrix and the motion sensor, already set up for you.

    import screen
    dot = screen.block(3, 3, 0x00FFFF)
    dot.x = 30

Everything here hands back an ordinary displayio object, so anything you
read about displayio elsewhere still works on it.
"""

import time

import displayio
import vectorio
from adafruit_matrixportal.matrix import Matrix

WIDTH = 64
HEIGHT = 32

_display = Matrix(width=WIDTH, height=HEIGHT, bit_depth=4).display
_group = displayio.Group()
_display.root_group = _group

# UUsed for timer_elapsed and timer_reset
_timer = time.monotonic()


# Filled in the first time something asks for a tilt reading, so lessons that
# never touch the sensor don't pay to import it.
_sensor = None

# How far you have to tip the board before tilt() reads a full 1.0, measured in
# the sensor's own units where gravity is about 9.8. Lower means a smaller tilt
# goes further. A lesson can change it for itself:
#
#     screen.FULL_TILT = 3.0    # about 19 degrees instead of the usual 76
#
FULL_TILT = 7.0

# The sensor never reads exactly zero, even sitting still. Anything smaller than
# this counts as "not moving" so nothing drifts on its own. In sensor units, NOT
# a fraction of _FULL_TILT -- otherwise turning the sensitivity up would quietly
# shrink the noise floor and everything would start twitching at rest.
_DEADZONE = 0.3


def block(width: int, height: int, color: int, x: int = 0, y: int = 0):
    """A solid rectangle. Set top-left corner location now, or set .x and .y later."""
    palette = displayio.Palette(1)
    palette[0] = color
    shape = vectorio.Rectangle(
        pixel_shader=palette, width=width, height=height, x=x, y=y
    )
    _group.append(shape)
    return shape


def circle(size: int, color: int, x: int = 0, y: int = 0):
    """A round blob filling a size x size box, with the corners left off.

    Positioned by its top-left corner, the same as block(). Unlike block() it
    has no .width, so keep the size you asked for in a variable if you need it.
    Sizes 4, 6 and 8 look roundest; 3 comes out as a plus.
    """
    bitmap = displayio.Bitmap(size, size, 2)
    palette = displayio.Palette(2)
    palette[0] = 0x000000
    palette[1] = color
    palette.make_transparent(0)  # corners show whatever is behind, not black

    # Light a pixel if its middle is inside the circle. The spare 0.5 is what
    # keeps a 4x4 from collapsing to a 2x2 square.
    edge = (size - 1) / 2
    limit = edge * edge + 0.5
    for row in range(size):
        for column in range(size):
            across = column - edge
            down = row - edge
            if across * across + down * down <= limit:
                bitmap[column, row] = 1

    shape = displayio.TileGrid(bitmap, pixel_shader=palette, x=x, y=y)
    _group.append(shape)
    return shape


_sheets = {}


def burst(size: int, color: int, frames: int = 10, x: int = 0, y: int = 0):
    """An expanding ring, held as `frames` pictures in one strip.

    Starts as a spark and grows to a hollow ring. Move between the pictures
    with set_frame(). Positioned by its top-left corner, like block().
    """
    if frames < 1:
        raise ValueError("burst() needs at least 1 frame -- check the argument order")

    key = (size, frames)
    if key not in _sheets:
        sheet = displayio.Bitmap(size * frames, size, 2)
        centre = (size - 1) / 2
        biggest = size / 2
        for frame in range(frames):
            outer = biggest * (frame + 1) / frames
            inner = outer - 1.6  # ring thickness; below zero means a solid blob
            for row in range(size):
                for column in range(size):
                    across = column - centre
                    down = row - centre
                    away = across * across + down * down
                    if away > outer * outer + 0.5:
                        continue
                    if inner > 0 and away <= inner * inner + 0.5:
                        continue
                    sheet[frame * size + column, row] = 1
        _sheets[key] = sheet  # built once, then shared by every burst this size

    palette = displayio.Palette(2)
    palette[0] = 0x000000
    palette[1] = color
    palette.make_transparent(0)

    shape = displayio.TileGrid(
        _sheets[key],
        pixel_shader=palette,
        tile_width=size,
        tile_height=size,
        x=x,
        y=y,
    )
    _group.append(shape)
    return shape


def bring_to_front(shape):
    """Draw this shape on top of all the others from now on.

    Things are drawn in the order they were made, so the newest is normally on
    top. This moves an older one back to the end of the queue.
    """
    _group.remove(shape)
    _group.append(shape)


def set_frame(shape, frame: int):
    """Show one picture from an animated shape. 0 is the first."""
    shape[0] = frame


def frame_of(shape) -> int:
    """Which picture an animated shape is showing."""
    return shape[0]


def recolor(shape, color: int):
    """Change the color of a block or circle you already made."""
    palette = shape.pixel_shader
    palette[len(palette) - 1] = color


def color_of(shape) -> int:
    """What color a block or circle is right now."""
    palette = shape.pixel_shader
    return palette[len(palette) - 1]


def text(message: str, color: int, x: int = 0, y: int = 0):
    """Words on the screen. x,y is the left _center_ of the text."""
    import terminalio
    from adafruit_display_text import label

    sign = label.Label(terminalio.FONT, text=message, color=color, x=x, y=y)
    _group.append(sign)
    return sign


def tilt() -> tuple[float, float, float]:
    """How far the board is tipped, as (x, y, z), each from -1.0 to 1.0.

    Lay the board flat and tilt it like a tray. x is right, y is down, z is forward --
    the same directions the screen uses.
    """
    x, y, z = _readings()
    return (_scale(x), _scale(y), _scale(-z))


def force() -> float:
    """How hard the board is being moved. About 1.0 sitting still, more if shaken."""
    x, y, z = _readings()
    return (x * x + y * y + z * z) ** 0.5 / 9.8


def draw():
    """Redraw the screen now, once you have finished moving things.

    Normally the screen redraws itself whenever it likes, which can catch your
    loop half way through and show some things moved and some not. Calling this
    hands you the timing: nothing appears until you say so.
    """
    _display.auto_refresh = False
    _display.refresh()


def hold():
    """Keep what you drew on the screen."""
    while True:
        time.sleep(1)


def timer_reset() -> None:
    """Start timer_elapsed over from zero"""
    global _timer
    _timer = time.monotonic()


def timer_elapsed() -> float:
    """Seconds since last call to timer_reset"""
    return time.monotonic() - _timer


def _readings() -> tuple[float, float, float]:
    global _sensor
    if _sensor is None:
        import adafruit_lis3dh
        import board

        _sensor = adafruit_lis3dh.LIS3DH_I2C(board.I2C(), address=0x19)
    return _sensor.acceleration


def _scale(value: float) -> float:
    if -_DEADZONE < value < _DEADZONE:
        return 0.0
    value = value / FULL_TILT
    if value > 1.0:
        return 1.0
    if value < -1.0:
        return -1.0
    return value
