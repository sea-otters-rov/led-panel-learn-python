"""Throwaway: can a board afford more than one ball's worth of talking a frame?

206 is being reworked so that ownership belongs to the BALL, not the board --
a list of balls, each with its own owner. The cost question that decides the
design: a board that owns two balls wants to send two messages a frame, and a
send is ~7.8 ms of a 33 ms frame. Two might be fine, or might be visibly slow.

Run the same file on both boards with `tools\\watch_both.py --reload`. The entry
file is not main.py, so the student picker never lists it.

Both boards simulate two balls locally and both listen. There is no real
handoff here on purpose: this measures the COST of the traffic a multi-ball
206 would generate, not the correctness of handing a ball over (spike_handoff
already settled that). Four ways of saying the same thing, cycled several times
so a slow patch of network cannot flatter one of them:

    one          1 send/frame, one ball's worth   -- what 205 and 206 do today
    two          2 sends/frame, one per ball      -- the obvious multi-ball code
    roundrobin   1 send/frame, alternating balls  -- each ball at half rate
    packed       1 send/frame, both balls in it   -- one message, fixed shape
    batched      1 send/frame, 2 messages in it    -- network.send() takes a list
    batched5     1 send/frame, 5 messages in it    -- does a bigger trip cost more?

What to read off it:

    ms/frame     33 is the budget. `two` is the number that decides whether the
                 obvious version is allowed.
    heard/frame  messages arriving from the partner per frame. If `two` sends
                 twice as much but the partner hears proportionally less, the
                 radio is the limit and packing wins regardless of ms/frame.
    failed       network.send() returned False -- the radio refused it.

Uses the throwaway kinds `here`, `ball` and `pack`. None of them is a lesson
kind; `pack` is new to this file.
"""

import time

import colors
import network
import screen

seconds_per_mode = 6.0
rounds = 3
modes = ["one", "batched", "batch2cheap", "onecheap"]

size = 4
ball_max = screen.WIDTH - size

here_kind = "here"
ball_kind = "ball"
pack_kind = "pack"

my_id = network.start()

sign = screen.text("pair", colors.AMBER, 1, 3, font=screen.Fonts.SMALL)
shapes = [
    screen.circle(size, colors.CYAN, 0, 8),
    screen.circle(size, colors.MAGENTA, 0, 20),
]
screen.draw()

# --- find the partner ---------------------------------------------------------
# Same handshake as handoff.py: shout until somebody answers, then keep shouting
# a little longer so they are sure to have heard us too.
partner = None
next_here = 0.0
heres_after = 0
while partner is None or heres_after < 5:
    now = time.monotonic()
    if now >= next_here:
        network.send_to_everyone(f"{here_kind} {my_id}")
        next_here = now + 0.3
        if partner is not None:
            heres_after += 1
    for text in network.receive_all():
        parts = text.split(" ")
        if len(parts) >= 2 and parts[1] != my_id and parts[0] in (here_kind, ball_kind):
            if partner is None:
                partner = parts[1]
                print(f"multi  {my_id} partner is {partner}")

# --- two balls, moving ---------------------------------------------------------
x = [4.0, 40.0]
y = [8.0, 20.0]
speed_x = [0.7, -0.5]

# Built once, so a mode using these pays no string-building cost in the loop.
ready_one = f"{ball_kind} {my_id} 0 12.345 8.0"
ready_two = [f"{ball_kind} {my_id} {n} 12.345 8.0" for n in (0, 1)]

tally = {}
for name in modes:
    tally[name] = {"frames": 0, "ms": 0.0, "sent": 0, "failed": 0, "heard": 0}

mode_index = 0
round_number = 0
mode_ends = time.monotonic() + seconds_per_mode
turn = 0

print(f"multi  {my_id} {seconds_per_mode} s per mode, {rounds} rounds")

while round_number < rounds:
    start_ns = time.monotonic_ns()
    mode = modes[mode_index]
    seen = tally[mode]

    # --- listen ---------------------------------------------------------------
    for text in network.receive_all():
        parts = text.split(" ")
        if len(parts) >= 2 and parts[1] == partner:
            if parts[0] == ball_kind or parts[0] == pack_kind:
                seen["heard"] += 1

    # --- move both balls ------------------------------------------------------
    for n in (0, 1):
        x[n] = x[n] + speed_x[n]
        if x[n] > ball_max:
            x[n] = ball_max - (x[n] - ball_max)
            speed_x[n] = -speed_x[n]
        elif x[n] < 0:
            x[n] = -x[n]
            speed_x[n] = -speed_x[n]
        shapes[n].x = int(x[n])

    # --- talk -----------------------------------------------------------------
    if mode == "one":
        seen["sent"] += 1
        if not network.send(partner, f"{ball_kind} {my_id} 0 {x[0]} {y[0]}"):
            seen["failed"] += 1
    elif mode == "two":
        for n in (0, 1):
            seen["sent"] += 1
            if not network.send(partner, f"{ball_kind} {my_id} {n} {x[n]} {y[n]}"):
                seen["failed"] += 1
    elif mode == "roundrobin":
        turn = 1 - turn
        seen["sent"] += 1
        if not network.send(partner, f"{ball_kind} {my_id} {turn} {x[turn]} {y[turn]}"):
            seen["failed"] += 1
    elif mode == "packed":
        seen["sent"] += 1
        if not network.send(
            partner, f"{pack_kind} {my_id} {x[0]} {y[0]} {x[1]} {y[1]}"
        ):
            seen["failed"] += 1
    elif mode == "batch2cheap":
        # Two messages again, but built once before the loop. Whatever is left
        # of the difference against "one" is the radio, not Python.
        seen["sent"] += 2
        if not network.send(partner, ready_two):
            seen["failed"] += 2
    elif mode == "onecheap":
        # One pre-built message: the floor, with no string work at all.
        seen["sent"] += 1
        if not network.send(partner, ready_one):
            seen["failed"] += 1
    elif mode == "batched":
        # Two ordinary messages, one trip. They arrive as two messages.
        seen["sent"] += 2
        if not network.send(
            partner,
            [f"{ball_kind} {my_id} {n} {x[n]} {y[n]}" for n in (0, 1)],
        ):
            seen["failed"] += 2
    else:
        # Five, to see whether a bigger trip costs more than a small one.
        seen["sent"] += 5
        if not network.send(
            partner,
            [f"{ball_kind} {my_id} {n} {x[n % 2]} {y[n % 2]}" for n in range(5)],
        ):
            seen["failed"] += 5

    sign.text = mode[:4]
    screen.draw()

    seen["ms"] += (time.monotonic_ns() - start_ns) / 1000000
    seen["frames"] += 1

    now = time.monotonic()
    if now >= mode_ends:
        mode_ends = now + seconds_per_mode
        mode_index = mode_index + 1
        if mode_index >= len(modes):
            mode_index = 0
            round_number += 1
            print(f"multi  {my_id} finished round {round_number}")

for name in modes:
    seen = tally[name]
    frames = seen["frames"]
    print(
        f"multi  {my_id} {name:<11}"
        f" {seen['ms'] / frames:5.1f} ms/frame"
        f"  {frames / (seconds_per_mode * rounds):5.1f} fps"
        f"  sent {seen['sent']:5d}"
        f"  failed {seen['failed']:4d}"
        f"  heard {seen['heard']:5d}"
        f"  heard/frame {seen['heard'] / frames:4.2f}"
    )

sign.text = "done"
screen.draw()
while True:
    time.sleep(1)
