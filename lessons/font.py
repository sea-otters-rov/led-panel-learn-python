"""A tiny 3x5 font, for when terminalio is too big.

Every letter is drawn below as five rows of three characters. A "#" is a lit
pixel and a "." is an empty one, so you can read the shapes straight off the
page -- and add your own. They are laid out one row per line on purpose, and
the formatter-off comment above them is what keeps them that way.

There is a one pixel gap built in to the RIGHT of every letter, so words do not
run together. There is deliberately no gap underneath: a line of this text is
exactly 5 pixels tall, and if you stack two lines you choose the space between
them yourself by putting the second one 6 or 7 pixels further down.

You do not use this file directly. screen.text(..., font=screen.SMALL) does.
"""

CELL_W = 4  # 3 pixels of letter, then 1 blank column between letters
CELL_H = 5  # 5 pixels of letter, and no blank row -- you space lines yourself

ORDER = " 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ.:-!?"

# fmt: off
SHAPES = {
    " ": (
        "...",
        "...",
        "...",
        "...",
        "..."
    ),
    "0": (
        "###",
        "#.#",
        "#.#",
        "#.#",
        "###"
    ),
    "1": (
        ".#.",
        "##.",
        ".#.",
        ".#.",
        "###"
    ),
    "2": (
        "###",
        "..#",
        "###",
        "#..",
        "###"
    ),
    "3": (
        "###",
        "..#",
        "###",
        "..#",
        "###"
    ),
    "4": (
        "#.#",
        "#.#",
        "###",
        "..#",
        "..#"
    ),
    "5": (
        "###",
        "#..",
        "###",
        "..#",
        "###"
    ),
    "6": (
        "###",
        "#..",
        "###",
        "#.#",
        "###"
    ),
    "7": (
        "###",
        "..#",
        "..#",
        "..#",
        "..#"
    ),
    "8": (
        "###",
        "#.#",
        "###",
        "#.#",
        "###"
    ),
    "9": (
        "###",
        "#.#",
        "###",
        "..#",
        "###"
    ),
    "A": (
        "###",
        "#.#",
        "###",
        "#.#",
        "#.#"
    ),
    "B": (
        "##.",
        "#.#",
        "##.",
        "#.#",
        "##."
    ),
    "C": (
        "###",
        "#..",
        "#..",
        "#..",
        "###"
    ),
    "D": (
        "##.",
        "#.#",
        "#.#",
        "#.#",
        "##."
    ),
    "E": (
        "###",
        "#..",
        "##.",
        "#..",
        "###"
    ),
    "F": (
        "###",
        "#..",
        "##.",
        "#..",
        "#.."
    ),
    "G": (
        "###",
        "#..",
        "#.#",
        "#.#",
        "###"
    ),
    "H": (
        "#.#",
        "#.#",
        "###",
        "#.#",
        "#.#"
    ),
    "I": (
        "###",
        ".#.",
        ".#.",
        ".#.",
        "###"
    ),
    "J": (
        "..#",
        "..#",
        "..#",
        "#.#",
        "###"
    ),
    "K": (
        "#.#",
        "#.#",
        "##.",
        "#.#",
        "#.#"
    ),
    "L": (
        "#..",
        "#..",
        "#..",
        "#..",
        "###"
    ),
    "M": (
        "#.#",
        "###",
        "###",
        "#.#",
        "#.#"
    ),
    "N": (
        "##.",
        "#.#",
        "#.#",
        "#.#",
        "#.#"
    ),
    "O": (
        "###",
        "#.#",
        "#.#",
        "#.#",
        "###"
    ),
    "P": (
        "###",
        "#.#",
        "###",
        "#..",
        "#.."
    ),
    "Q": (
        "###",
        "#.#",
        "#.#",
        "###",
        "..#"
    ),
    "R": (
        "###",
        "#.#",
        "##.",
        "#.#",
        "#.#"
    ),
    "S": (
        "###",
        "#..",
        "###",
        "..#",
        "###"
    ),
    "T": (
        "###",
        ".#.",
        ".#.",
        ".#.",
        ".#."
    ),
    "U": (
        "#.#",
        "#.#",
        "#.#",
        "#.#",
        "###"
    ),
    "V": (
        "#.#",
        "#.#",
        "#.#",
        "#.#",
        ".#."
    ),
    "W": (
        "#.#",
        "#.#",
        "###",
        "###",
        "#.#"
    ),
    "X": (
        "#.#",
        "#.#",
        ".#.",
        "#.#",
        "#.#"
    ),
    "Y": (
        "#.#",
        "#.#",
        ".#.",
        ".#.",
        ".#."
    ),
    "Z": (
        "###",
        "..#",
        ".#.",
        "#..",
        "###"
    ),
    ".": (
        "...",
        "...",
        "...",
        "...",
        ".#."
    ),
    ":": (
        "...",
        ".#.",
        "...",
        ".#.",
        "..."
    ),
    "-": (
        "...",
        "...",
        "###",
        "...",
        "..."
    ),
    "!": (
        ".#.",
        ".#.",
        ".#.",
        "...",
        ".#."
    ),
    "?": (
        "###",
        "..#",
        ".##",
        "...",
        ".#."
    ),
}
# fmt: on


_sheet = None


def sheet():
    """One wide bitmap holding every letter, built once and then shared."""
    global _sheet
    if _sheet is None:
        import displayio

        _sheet = displayio.Bitmap(CELL_W * len(ORDER), CELL_H, 2)
        for slot in range(len(ORDER)):
            rows = SHAPES[ORDER[slot]]
            for row in range(CELL_H):
                line = rows[row]
                for column in range(3):
                    if line[column] == "#":
                        _sheet[slot * CELL_W + column, row] = 1
    return _sheet


def slot_for(letter: str) -> int:
    """Which picture in the sheet draws this letter. Unknown letters go blank."""
    found = ORDER.find(letter.upper())
    if found < 0:
        return 0  # a space
    return found


class _SmallFont:
    """Enough of a font for adafruit_display_text to draw with our sheet.

    A real font hands back a Glyph for each letter -- which bitmap to look in,
    which picture in it, and how far to step along afterwards. Ours are all the
    same size, so they are made once and then kept.
    """

    def __init__(self):
        self._made = {}

    def get_bounding_box(self):
        return (CELL_W, CELL_H)

    def get_glyph(self, codepoint):
        glyph = self._made.get(codepoint)
        if glyph is None:
            import fontio

            glyph = fontio.Glyph(
                sheet(), slot_for(chr(codepoint)), CELL_W, CELL_H, 0, 0, CELL_W, 0
            )
            self._made[codepoint] = glyph
        return glyph


SMALL = _SmallFont()
