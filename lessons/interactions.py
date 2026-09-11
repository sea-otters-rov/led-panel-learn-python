import time

import colors
import network
import screen


def join_wifi(show_id: bool = True) -> str:
    """
    Wifi connection, message, and optional ID label at the top-right
    """

    import os

    wifi_connecting = (
        screen.text("Connecting", colors.AMBER, 2, 16),
        screen.text(
            os.getenv("WIFI_SSID") or "Err", colors.GOLD, 2, 28, screen.Fonts.SMALL
        ),
    )
    screen.draw()

    my_id = network.start()
    for line in wifi_connecting:
        screen.delete_shape(line)

    if show_id:
        # Your own id in the corner.
        text_x = screen.WIDTH - 4 * len(my_id)
        screen.text(my_id, colors.AMBER, text_x, 3, font=screen.Fonts.SMALL)

    screen.draw()

    return my_id


prev_tilt = None


def smoothed_tilt():
    """
    Tilt with Emrys' jitter correction. It takes the average of the current tilt
    with the previous value.
    """
    global prev_tilt
    if prev_tilt is None:
        # If this is our first time through, just use the current tilt
        prev_tilt = screen.tilt()

    raw_tilt = screen.tilt()

    adjusted_tilt = (
        (raw_tilt[0] + prev_tilt[0]) / 2,
        (raw_tilt[1] + prev_tilt[1]) / 2,
        (raw_tilt[2] + prev_tilt[2]) / 2,
    )
    prev_tilt = adjusted_tilt
    return adjusted_tilt


def get_newest_message(kinds: list[str]):
    """The newest waiting message of one of these kinds, split into its parts.

    The same as lessons 203 and 204, kept here now that every lesson needs it.
    None if nothing of those kinds has arrived.
    """
    newest_msg = None
    for msg_text in network.receive_all():
        msg_parts = msg_text.split(" ")
        if msg_parts[0] in kinds:
            newest_msg = msg_parts
    return newest_msg


def tap_to_pair(resume_kinds: list[str], tap_force=1.4, pair_window=0.3) -> str:
    """Wait until we have a partner, then return their id. Lesson 204, packed up.

    Two ways to get one, the same two as 204:

      tap     both boards knocked at nearly the same moment
      resume  a message arrives from a board that still thinks we are its
              partner. resume_kinds are the kinds your lesson sends straight
              to its partner -- never to everyone -- so only a real partner
              ever sends us one.

    Every message kind in the course puts the sender's id second, which is what
    lets this work for any lesson.
    """
    sign = screen.text("Tap to pair", colors.AMBER, 1, 3, font=screen.Fonts.SMALL)
    screen.draw()
    my_tap_time = None

    while True:
        now = time.monotonic()

        if screen.force() > tap_force:
            network.send_to_everyone(f"tap {network.my_id}")
            my_tap_time = now
            sign.text = "tapped"
        elif my_tap_time is not None and now - my_tap_time > 1:
            sign.text = "Tap to pair"

        for msg_text in network.receive_all():
            msg_parts = msg_text.split(" ")
            if len(msg_parts) < 2 or msg_parts[1] == network.my_id:
                continue

            tapped_together = (
                msg_parts[0] == "tap"
                and len(msg_parts) == 2
                and my_tap_time is not None
                and now - my_tap_time < pair_window
            )
            if tapped_together or msg_parts[0] in resume_kinds:
                partner_id = msg_parts[1]
                screen.delete_shape(sign)
                print(f"paired with board {partner_id}")
                return partner_id

        screen.draw()
