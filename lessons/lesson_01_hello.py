"""Lesson 1 - does the loop work?

Change MESSAGE or COLOR below and press Ctrl+S. The board restarts on its own
and the matrix updates. Nothing else to click.

Watch the serial console while you do it: you should see the reload banner and
then the new "showing:" line.

This file only runs because code.py says `import lesson_01_hello`. That is how
you move between lessons.
"""

import random
import time

import displayio
import terminalio
from adafruit_display_text import label
from adafruit_matrixportal.matrix import Matrix

MESSAGE = "hello"
COLOR = 0x00A0FF

# The MatrixPortal drives the panel from the board's own pins, so there is no
# wiring to describe here -- just the panel's size.
matrix = Matrix(width=64, height=32, bit_depth=4)
display = matrix.display

text = label.Label(terminalio.FONT, text=MESSAGE, color=COLOR)
text.x = 2
text.y = display.height // 2


group = displayio.Group()
group.append(text)
display.root_group = group

print("showing:", MESSAGE)

while True:
    time.sleep(1)
    text.color = random.randint(0, 0xFFFFFF)
