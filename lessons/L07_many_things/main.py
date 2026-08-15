"""Fill the screen with falling stars.

One name, many stars. A list holds as many as you want, and a single for loop
moves every one of them.
"""

import random
import time

import colors
import screen
from displayio import TileGrid

star_count = 100
fall_speed = 1

# Stars come in a few sizes. The edges are worked out from the biggest one, so
# that even a big star cannot end up hanging off the side.
biggest_star = 4

star_min_y = -5  # off the top, so bigger stars do not pop into view
star_max_x = screen.WIDTH - biggest_star
star_max_y = screen.HEIGHT - biggest_star

# A list of TileGrids (shapes, like circles). The [] means "nothing in here yet".
stars: list[TileGrid] = []

# Make the stars once, before the loop. append() puts one more on the end.
for index in range(star_count):
    size = 1

    # Make the big ones last. Things are drawn in the order they are made, so
    # going last is what puts them on top of all the little ones.
    if index >= star_count - 1:
        size = biggest_star
    elif index >= star_count - 3:
        size = 3
    elif index >= star_count - 5:
        size = 2

    star = screen.circle(size, random.choice(colors.RAINBOW))
    star.x = random.randint(0, star_max_x)
    star.y = random.randint(star_min_y, star_max_y)
    stars.append(star)

print(f"made {len(stars)} stars")

while True:
    # Runs once per star. Each time round, star is the next one in the list.
    for star in stars:
        star.y = star.y + fall_speed

        # Fallen off the bottom? Put it back at the top, somewhere new.
        if star.y > screen.HEIGHT:
            star.y = star_min_y
            star.x = random.randint(0, star_max_x)

    # Every star has moved now, so redraw. Without this the screen picks its own
    # moment, and with this many stars it often picks the middle of the loop
    # above -- so half of them jump and half of them do not.
    screen.draw()

    # Because draw() sets the pace, there is no need to pause -- this runs as
    # fast as the board can manage. Put the pause back to slow it down.
    # time.sleep(0.02)

    # stars[0] is the first one since lists count from 0.
    print(f"first star at y {stars[0].y}   stars in the list {len(stars)}")


# Try these:
#   - Set star_count to 500. Then to 3. Which breaks first, the screen or you?
#   - In the print, change stars[0] to stars[1000] and read the error.
#   - Delete the stars.append(star) line and read the error. Every block still
#     gets made, exactly as before. So what was the list actually doing?
#   - Make bigger stars move faster, without adding more lists. Use
#     star.tile_width as the fall speed instead of fall_speed. Now big ones drop
#     faster. Does that look like some are closer?
#     (A circle keeps its size in .tile_width, because it is drawn from a small
#     picture -- a "tile" -- rather than being a plain block.)
