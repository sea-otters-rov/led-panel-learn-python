"""Throwaway: why is a board's own unicast heard but its own broadcast not?

A board sending to its OWN address receives the message. The same board sending
to the broadcast address does not, even though every other board does. Both
facts are measured and in CLAUDE.md; this asks which layer is responsible.

Two candidates:

  the IP stack     lwIP short-circuits a packet addressed to the interface's
                   own address and delivers it internally, never handing it to
                   the radio. It does NOT do this for broadcast.
  the access point a station's frame goes to the AP, which re-broadcasts it to
                   the OTHER stations. An AP does not reflect a frame back to
                   the station that sent it.

The timing separates them. A packet that never reaches the radio comes back in
about as long as one socket_available() poll. A packet that goes out to the AP
and back is a full over-the-air hop -- CLAUDE.md has the board-to-board ROUND
trip at best 18.7 ms, median 24-30, so one hop is roughly 9-15 ms.

Run this on ONE board. Leave the other running anything that sends (L202 will
do), because its traffic arriving during the broadcast window is the control:
it proves the receive path is alive while the broadcast fails to show up.
"""

import time

import network

TRIES = 5
WAIT = 1.0  # how long to wait for a message to come back


def drain():
    while network.receive():
        pass


def probe(label, send_it, tag):
    """Send one tagged message, then wait for it to come back to us.

    Counts anything else that arrives while waiting, so a silent result can be
    told apart from a dead socket.
    """
    drain()
    send_it(tag)
    sent_at = time.monotonic_ns()

    others = 0
    deadline = time.monotonic() + WAIT
    while time.monotonic() < deadline:
        message = network.receive()
        if message is None:
            continue
        if message == tag:
            back = (time.monotonic_ns() - sent_at) / 1000000
            print(
                "%-18s back in %6.2f ms   (%d other messages meanwhile)"
                % (label, back, others)
            )
            return back
        others += 1

    print(
        "%-18s NEVER came back in %.1f s   (%d other messages meanwhile)"
        % (label, WAIT, others)
    )
    return None


network.start()
print("loop   board %s at %s" % (network.my_id, network.my_address))
print("loop   sending to self as id %s, and to everyone" % network.my_id)

self_times = []
for n in range(TRIES):
    got = probe(
        "unicast to self", lambda m: network.send(network.my_id, m), "probe-self-%d" % n
    )
    if got is not None:
        self_times.append(got)
    probe("broadcast", network.send_to_everyone, "probe-bcast-%d" % n)

if self_times:
    self_times.sort()
    print(
        "loop   unicast to self: best %.2f  median %.2f  worst %.2f ms over %d"
        % (
            self_times[0],
            self_times[len(self_times) // 2],
            self_times[-1],
            len(self_times),
        )
    )
    print("loop   one over-the-air hop is ~9-15 ms (CLAUDE.md round trip / 2)")

print("Code done running.")
