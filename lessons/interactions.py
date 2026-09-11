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
