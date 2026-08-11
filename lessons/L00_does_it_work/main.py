"""Lesson 00 - does the board work?

This just makes sure your board is working and when you make changes, it shows up automatically.

Change MESSAGE or COLOR below and press Ctrl+S. The board should restart on its own
and the matrix updates. Nothing else to click.

Also make sure the serial console works by opening the bottom Serial Monitor tab
and click Start Monitoring. Change the MESSAGE and when you save, you should see the reload
banner and then the new "showing:" line.

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
