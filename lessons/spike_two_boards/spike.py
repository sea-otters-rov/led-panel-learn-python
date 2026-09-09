"""Two-board spike. NOT a lesson -- see docs/lesson-plan-notes.md, Part 2.

Everything about Part 2 so far was measured with one board and a laptop
standing in for the second. A laptop is the wrong stand-in in three ways: it
has recvfrom, it does not have the ESP32SPI send-buffer bug, and it never
reboots when someone presses Ctrl+S. This runs the same code on both boards
and answers the questions a laptop could not.

The entry file is deliberately NOT called main.py. tools/lesson.py lists every
folder that holds one, so a spike named main.py would appear in the student
picker between lesson 112 and the capstone.

Both boards run this identical file. Nothing is configured per board: a board
takes its id from the address the router gives it, and finds its partner by
listening. Run it
with

    .\\.venv\\Scripts\\python.exe .\\tools\\watch_both.py --reload

so both consoles land on one timeline.

Stages, in order, each printing a line that starts with its own name so the
output can be filtered:

    id     who this board is, and what its radio is running
    join   associate, and report how long it took
    hear   broadcast heartbeats and build a roster from what arrives
    ping   unicast round trip, board to board
    load   both boards broadcasting flat out, to price a frame
"""

import time

import microcontroller

import colors
import network
import screen

HEARTBEAT = 1.0  # seconds between "here" broadcasts
FORGET = 3.0  # drop a board we have not heard from in this long
PINGS = 25  # round trips to measure before reporting
LOAD_FRAMES = 120  # frames of both-boards-talking to price


def show(sign, message):
    """Put a line on the panel and on the console at the same time."""
    sign.text = message
    screen.draw()


def stage_join(sign):
    """Join, then report who this board turned out to be.

    The name comes FROM the address, so there is no name until this has run.
    That ordering is the one cost of naming a board from its IP rather than
    its chip: a board cannot label itself during the five seconds it spends
    joining. The panel shows a placeholder until then.
    """
    show(sign, "wifi")
    start = time.monotonic()
    name = network.start()
    took = time.monotonic() - start
    address = network.my_address

    # If this says anything below 3.3.0, stop: the board will associate and
    # then fail every socket_open, which reads like a bug in the spike.
    print(
        "join   %s at %s in %.2f s, nina-fw %s"
        % (name, address, took, network.firmware_version())
    )
    print(
        "id     board %s  uid %s"
        % (name, "".join("%02x" % b for b in microcontroller.cpu.uid))
    )
    show(sign, name)
    return name, address


def stage_echo(name, sign):
    """Does a board hear its OWN messages? Broadcast and unicast separately.

    Lesson 201 is "nudge your board and your words appear on your friend's
    panel". Whether they also appear on the sender's own panel decides what
    the lesson can claim, so it has to be known before the lesson is written.

    EVERY message carries the sender's id and is counted against it. The first
    version of this stage counted any message starting with "echo" and reported
    the PARTNER's message as its own echo -- both boards run this stage at the
    same moment, so "nothing else is talking" was simply false. Attribute by
    sender or do not bother.
    """
    show(sign, "eko")
    while network.receive():
        pass  # drain whatever the earlier stages left in the buffer

    network.send_to_everyone("echo %s bcast" % name)
    network.send(name, "echo %s unicast" % name)  # to our own id

    mine = {"bcast": 0, "unicast": 0}
    theirs = 0
    end = time.monotonic() + 2.0
    while time.monotonic() < end:
        message = network.receive()
        if not message:
            continue
        word = message.split()
        if len(word) != 3 or word[0] != "echo":
            continue
        if word[1] == name:
            mine[word[2]] = mine.get(word[2], 0) + 1
        else:
            theirs += 1

    print(
        "echo   %s own broadcast %d, own unicast %d, partner's %d"
        % (name, mine["bcast"], mine["unicast"], theirs)
    )
    return mine["bcast"] > 0


def stage_hear(name, sign, seconds=12.0, seen=None):
    """Broadcast a heartbeat and print everything that arrives.

    This is the roster from the design notes, reduced to its smallest form.
    Absence is the disconnect signal: a board that reboots stops broadcasting,
    ages out of `seen`, and reappears by itself. There is no detection logic
    anywhere, which is the whole point.

    The heartbeat is "here <id>" and nothing else. It used to carry the
    sender's address as well, because a receiver never learns who sent a
    datagram -- but an id IS an address with the prefix left off, so the
    address field was saying the same thing twice.

    Pass seconds=None to stay here forever. That is the reboot test: press
    Ctrl+S on one board and watch the other print LOST and then NEW without
    being told anything happened.
    """
    if seconds is None:
        print("hear   %s roster, staying up -- Ctrl+S the other board" % name)
    else:
        print("hear   %s listening for %.0f s" % (name, seconds))
    if seen is None:
        seen = {}
    known = set(seen)
    beat = 0.0
    end = None if seconds is None else time.monotonic() + seconds

    while end is None or time.monotonic() < end:
        now = time.monotonic()
        if now >= beat:
            network.send_to_everyone("here " + name)
            beat = now + HEARTBEAT

        message = network.receive()
        while message:
            word = message.split()
            if len(word) == 2 and word[0] == "here" and word[1] != name:
                if word[1] not in known:
                    print("hear   %s <- NEW %s" % (name, word[1]))
                    known.add(word[1])
                seen[word[1]] = now
            message = network.receive()

        for other in list(seen):
            if now - seen[other] > FORGET:
                print(
                    "hear   %s -- LOST %s (silent %.1f s)"
                    % (name, other, now - seen[other])
                )
                del seen[other]
                known.discard(other)

        show(sign, str(len(seen) + 1))
        time.sleep(0.02)

    if not seen:
        print("hear   %s heard NOBODY -- is the other board running this too?" % name)
        return None
    partner = sorted(seen)[0]
    print(
        "hear   %s partner is %s at %s" % (name, partner, network.address_of(partner))
    )
    return partner


def stage_ping(name, partner, sign):
    """Unicast round trip, board to board.

    Symmetric on purpose: both boards ping and both answer, so neither has to
    be told it is the server. A reply carries the original sender's id because
    there is no recvfrom -- a receiver never learns who sent anything.
    """
    show(sign, "png")
    trips = []
    lost = 0

    for seq in range(PINGS):
        network.send(partner, "ping %s %d" % (name, seq))
        sent = time.monotonic_ns()
        deadline = time.monotonic() + 0.5
        got = False

        while time.monotonic() < deadline:
            message = network.receive()
            if not message:
                continue
            word = message.split()
            if len(word) == 3 and word[0] == "ping":
                # Answer the other board's ping while waiting for our own.
                network.send(word[1], "pong %s %s" % (name, word[2]))
            elif len(word) == 3 and word[0] == "pong" and int(word[2]) == seq:
                trips.append((time.monotonic_ns() - sent) / 1000000)
                got = True
                break

        if not got:
            lost += 1
        time.sleep(0.01)

    if trips:
        trips.sort()
        print(
            "ping   %s best %.1f  median %.1f  worst %.1f ms, lost %d/%d"
            % (name, trips[0], trips[len(trips) // 2], trips[-1], lost, PINGS)
        )
    else:
        print("ping   %s got NOTHING back from %s" % (name, partner))


def stage_load(name, partner, sign):
    """Both boards broadcasting every frame, to price a frame honestly.

    Every network number in CLAUDE.md was taken with one board talking. Two
    boards talking is the first time a board pays to parse traffic it did not
    ask for, which is the cost that decides whether six players is possible.
    """
    show(sign, "ld")
    worst = 0.0
    total = 0
    heard = 0

    for frame in range(LOAD_FRAMES):
        start = time.monotonic_ns()

        network.send(partner, "ball %d %d %s" % (frame % 64, frame % 32, name))
        while network.receive():
            heard += 1

        screen.draw()
        spent = (time.monotonic_ns() - start) / 1000000
        total += spent
        if spent > worst:
            worst = spent

    print(
        "load   %s %.2f ms/frame average, worst %.2f, heard %d in %d frames"
        % (name, total / LOAD_FRAMES, worst, heard, LOAD_FRAMES)
    )


# The panel comes up FIRST and stays up. network.start() blocks for seconds and
# a dark screen through that reads as a dead board -- which is exactly the
# lesson-13 problem this spike is here to shape.
sign = screen.text("...", colors.AMBER, 2, 16)
screen.draw()

name, address = stage_join(sign)
stage_echo(name, sign)
partner = stage_hear(name, sign)

if partner:
    stage_ping(name, partner, sign)
    stage_load(name, partner, sign)
    print("done   %s" % name)

# Never stop. The measured stages above are the easy half; the half that
# cannot be faked with a laptop is what a reboot does to the other board, and
# a reboot is what every single Ctrl+S causes. Staying in the roster is how
# that gets watched.
stage_hear(name, sign, seconds=None)
