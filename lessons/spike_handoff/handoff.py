"""Throwaway: can a ball be handed between two boards without ever being lost?

Run the same file on both boards, with `tools\\watch_both.py --reload`. The entry
file is not main.py, so the student picker never lists it.

One board owns the ball and simulates it. When the ball leaves the top edge, the
owner hands it to its partner: it converts the position to the partner's panel
(tops touching, so the far panel is turned round) and names the partner as the
new owner. Every ball message carries a sequence number that goes up by one on
every handoff:

    ball <sender> <owner> <seq> <x> <y> <vx> <vy>

The three ways this can go wrong, and what the spike counts for each:

    NEITHER OWNS  the handoff message is lost, the sender has stopped, and the
                  receiver never heard. Silent: the ball just stops. Counted as
                  a stall -- nobody has sent a ball for stall_after seconds.
    BOTH OWN      two boards simulating at once. Visible, and self-correcting
                  here: the lower id keeps it.
    STALE         an old message arriving late -- an old handoff, or an old
                  "I own it" that would look like an acknowledgement. The
                  sequence number is what spots these.

`mode` picks the handoff rule:

    once    send the handoff once and stop at once -- the obvious version
    repeat  keep sending the handoff every frame until the partner's own
            "I own it" message comes back, which is the acknowledgement

`loss` throws away that fraction of ball messages on purpose, on top of
whatever the network loses by itself, so a rare failure shows up in a minute
instead of in a lesson.
"""

import random
import time

import colors
import network
import screen

mode = "repeat"  # "once" or "repeat"
loss = 0.3  # fraction of ball messages deliberately not sent
stall_after = 2.0  # no ball message from the partner this long -> ball is lost
report_every = 15.0

# Does a board that sends nothing still hear reliably? With this False the
# watching board is silent and the owner's messages are the only traffic. With
# it True the watcher sends a small "here" every frame, which the owner ignores.
# If the watcher's radio dozes while it is not transmitting, True fixes it.
watcher_talks = False

# The other explanation for a silent watcher going deaf: it is not the radio
# dozing, it is the loop. A board that sends nothing runs its loop in ~3 ms and
# hammers socket_available() over SPI 300 times a second; one that sends runs
# in ~15 ms. This makes a silent watcher sleep instead, so it polls at about the
# talking rate while still transmitting nothing. If the losses vanish, it was
# the polling. If they stay, it was the silence.
watcher_idle = 0  # seconds; 0 turns it off

# The first explanation, tested directly. nina-fw has a power-mode command,
# 0x17, that adafruit_esp32spi does not wrap: a nonzero byte is WIFI_PS_MIN_MODEM
# (the radio dozes between beacons), zero is WIFI_PS_NONE (always listening).
# None leaves the firmware's own default alone.
power_save = None  # True, False, or None -- network.start() already turns it off

size = 2
serve_vx = 0.7
serve_vy = -0.9

ball_kind = "ball"
here_kind = "here"

my_id = network.start()

if power_save is not None:
    resp = network._esp._send_command_get_response(0x17, ((int(power_save),),))
    print(f"hand   {my_id} power_save={power_save} -> nina-fw replied {resp[0][0]}")
sign = screen.text("pair", colors.AMBER, 1, 3, font=screen.Fonts.SMALL)
ball = screen.block(size, size, colors.JADE, 0, 0)
ball.hidden = True
screen.draw()

# --- find the partner ---------------------------------------------------------
# Shout until we hear somebody, then keep shouting a little longer so they are
# sure to hear us too. A ball message counts as hearing them.
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
        if len(parts) >= 2 and parts[0] in (here_kind, ball_kind) and parts[1] != my_id:
            if partner is None:
                partner = parts[1]
                print(
                    f"hand   {my_id} partner is {partner}, mode={mode} "
                    f"loss={loss} watcher_talks={watcher_talks} "
                    f"watcher_idle={watcher_idle} power_save={power_save}"
                )

lower = int(my_id) < int(partner)

# --- state --------------------------------------------------------------------
seq = 0
x = (screen.WIDTH - size) / 2
y = (screen.HEIGHT - size) / 2
vx = serve_vx
vy = serve_vy
state = "own" if lower else "watch"
state_since = time.monotonic()
last_heard = time.monotonic()
serve_at = time.monotonic() + 1.5  # give the partner time to finish pairing
handoff = None  # (seq, x, y, vx, vy) while handing off
hand_frames = 0

count = {
    "handoffs": 0,  # we handed the ball over
    "takes": 0,  # we took it from a handoff
    "acks": 0,  # repeat mode: partner confirmed they own it
    "stalls": 0,  # nobody owned it
    "both_own": 0,  # both of us owned it at once
    "stale": 0,  # old message ignored thanks to seq
    "yields": 0,  # partner held a newer claim while we owned
    "sent": 0,
    "dropped": 0,  # thrown away on purpose
    "send_failed": 0,  # network.send() said it did not go out
    "heard": 0,  # ball messages that arrived from the partner
}
ack_frames = []  # frames spent handing off before each ack
frame_ms_total = 0.0
frames = 0
next_report = time.monotonic() + report_every


def set_state(new):
    global state, state_since
    if new != state:
        state = new
        state_since = time.monotonic()
        ball.hidden = state != "own"


def send_ball(owner, s, bx, by, bvx, bvy):
    count["sent"] += 1
    if random.random() < loss:
        count["dropped"] += 1
        return
    if not network.send(
        partner, f"{ball_kind} {my_id} {owner} {s} {bx} {by} {bvx} {bvy}"
    ):
        count["send_failed"] += 1


def to_partner(bx, by, bvx, bvy):
    # Tops touching: the far panel is turned round, so both x and the direction
    # of travel flip. `screen.WIDTH - size - x`, not `WIDTH - 1 - x`.
    return screen.WIDTH - size - bx, -by, -bvx, -bvy


set_state(state)
ball.hidden = state != "own"

while True:
    start_ns = time.monotonic_ns()
    now = time.monotonic()

    # --- listen ---------------------------------------------------------------
    for text in network.receive_all():
        p = text.split(" ")
        if len(p) != 8 or p[0] != ball_kind or p[1] != partner:
            continue
        owner = p[2]
        s = int(p[3])
        last_heard = now
        count["heard"] += 1

        if owner == my_id:
            if s > seq:
                # A newer handoff, to us. Take it.
                seq = s
                x, y, vx, vy = float(p[4]), float(p[5]), float(p[6]), float(p[7])
                count["takes"] += 1
                set_state("own")
            elif s < seq:
                count["stale"] += 1
            # s == seq: the partner repeating a handoff we already took. Normal.

        elif owner == partner:
            if s < seq:
                count["stale"] += 1  # e.g. an old "I own it" that is not an ack
            elif state == "hand":
                # The partner owns it at our handoff's seq or later: that is the
                # acknowledgement. Stop repeating.
                count["acks"] += 1
                ack_frames.append(hand_frames)
                seq = s
                set_state("watch")
            elif state == "own":
                if s == seq:
                    count["both_own"] += 1
                    print(f"hand   {my_id} BOTH OWN at seq {seq}")
                    if not lower:
                        set_state("watch")
                else:
                    count["yields"] += 1
                    seq = s
                    set_state("watch")
            else:
                seq = max(seq, s)

    # --- simulate ---------------------------------------------------------------
    if state == "own" and now >= serve_at:
        x += vx
        y += vy
        if x < 0:
            x = -x
            vx = -vx
        elif x > screen.WIDTH - size:
            x = 2 * (screen.WIDTH - size) - x
            vx = -vx
        if y > screen.HEIGHT - size:
            y = 2 * (screen.HEIGHT - size) - y
            vy = -vy
        elif y < 0:
            # Off the top edge: it belongs to the partner now.
            seq += 1
            handoff = (seq,) + to_partner(x, y, vx, vy)
            count["handoffs"] += 1
            hand_frames = 0
            if mode == "once":
                send_ball(partner, *handoff)
                set_state("watch")
            else:
                set_state("hand")

    # --- talk -------------------------------------------------------------------
    if state == "own":
        send_ball(my_id, seq, x, y, vx, vy)
        ball.x = int(x)
        ball.y = int(y)
    elif state == "hand":
        hand_frames += 1
        send_ball(partner, *handoff)
    elif watcher_talks:
        network.send(partner, f"{here_kind} {my_id}")
    elif watcher_idle:
        time.sleep(watcher_idle)

    # --- nobody has the ball ----------------------------------------------------
    quiet = now - max(last_heard, state_since)
    if state != "own" and quiet > stall_after:
        count["stalls"] += 1
        print(f"hand   {my_id} STALL in {state} at seq {seq}, quiet {quiet:.1f} s")
        if lower:
            # Both boards agree the lower id serves again.
            seq += 1
            x = (screen.WIDTH - size) / 2
            y = (screen.HEIGHT - size) / 2
            vx, vy = serve_vx, serve_vy
            serve_at = now + 0.5
            set_state("own")
        else:
            set_state("watch")
            state_since = now

    sign.text = f"{state} {seq}"
    screen.draw()

    frame_ms_total += (time.monotonic_ns() - start_ns) / 1000000
    frames += 1

    if now >= next_report:
        next_report = now + report_every
        worst = max(ack_frames) if ack_frames else 0
        mean = sum(ack_frames) / len(ack_frames) if ack_frames else 0
        print(
            f"hand   {my_id} {mode} loss={loss}  "
            + " ".join(f"{k}={v}" for k, v in count.items())
            + f"  ack_frames mean={mean:.1f} worst={worst}"
            + f"  {frame_ms_total / frames:.1f} ms/frame"
        )
