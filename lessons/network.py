"""Talking to the other boards.

    import network

    network.start()                      # join the wifi -- takes a few seconds
    network.send_to_everyone("hello")    # every board hears it
    network.send(their_address, "hi")    # just that one board hears it
    message = network.receive()          # "" when nothing has arrived

Messages are plain text. Whatever you send is exactly what comes out the other
end, so it is up to your lesson to decide what the words mean.
"""

import time

import board
from digitalio import DigitalInOut

import adafruit_esp32spi.adafruit_esp32spi as esp32spi

PORT = 5007  # every board listens here

my_address = ""  # filled in by start(), e.g. "192.168.1.3"

_esp = None
_listen = None
_everyone = ""
_inbox = ""
_talk = None
_INBOX_CAP = 512


def start(tries: int = 8) -> str:
    """Join the wifi and get ready to send and receive.

    This takes a few seconds, and there is no way around that: the radio has to
    be reset and then join the network. Put something on the screen first so
    nobody thinks the board has died.
    """
    global _esp, _listen, _everyone, my_address

    import os

    _esp = esp32spi.ESP_SPIcontrol(
        board.SPI(),
        DigitalInOut(board.ESP_CS),
        DigitalInOut(board.ESP_BUSY),
        DigitalInOut(board.ESP_RESET),
    )

    for attempt in range(tries):
        if _esp.is_connected:
            break
        try:
            _esp.connect_AP(os.getenv("WIFI_SSID"), os.getenv("WIFI_PASSWORD"))
        except Exception:  # noqa: BLE001
            print("network: join attempt", attempt + 1, "did not take, trying again")
            time.sleep(1)

    if not _esp.is_connected:
        raise RuntimeError("network: could not join the wifi -- check settings.toml")

    my_address = _esp.pretty_ip(_esp.ip_address)

    # The broadcast address is our own with the last number swapped for 255.
    piece = my_address.split(".")
    _everyone = piece[0] + "." + piece[1] + "." + piece[2] + ".255"

    _listen = _esp.get_socket()
    _esp.start_server(PORT, _listen, conn_mode=_esp.UDP_MODE)


    print("network: ready at", my_address)
    return my_address


def send(address: str, message: str) -> bool:
    """Send one message to one board. True if it went out.

    socket_open has to be called before EVERY message, not just the first one.
    The radio keeps what you write in a buffer and only empties it when the
    socket is opened again -- so without this, the second message arrives with
    the first one stuck to the front of it, and the third with both. That is a
    known bug in the library, not something you did:
    github.com/adafruit/Adafruit_CircuitPython_ESP32SPI/issues/135
    """
    global _talk

    data = (message + "\n").encode()
    if _talk is None:
        _talk = _esp.get_socket()

    try:
        _esp.socket_open(_talk, address, PORT, conn_mode=_esp.UDP_MODE)
        _esp.socket_write(_talk, data, conn_mode=_esp.UDP_MODE)
        return True
    except Exception:  # noqa: BLE001
        pass

    # The radio jammed. Throw the socket away, take a fresh one, try once more.
    try:
        _esp.socket_close(_talk)
    except Exception:  # noqa: BLE001
        pass
    try:
        _talk = _esp.get_socket()
        _esp.socket_open(_talk, address, PORT, conn_mode=_esp.UDP_MODE)
        _esp.socket_write(_talk, data, conn_mode=_esp.UDP_MODE)
        return True
    except Exception:  # noqa: BLE001
        # One lost message is not worth stopping a game for.
        return False


def send_to_everyone(message: str) -> bool:
    """Send one message to every board on the network."""
    return send(_everyone, message)


def receive() -> str:
    """The next message that arrived, or "" if nothing is waiting.

    This never waits. Call it once per loop and carry on either way, so the
    screen keeps moving whether or not anyone is talking.
    """
    global _inbox

    waiting = _esp.socket_available(_listen)
    if waiting:
        _inbox = _inbox + str(_esp.socket_read(_listen, waiting), "utf-8")

    cut = _inbox.find("\n")
    if cut < 0:
        if len(_inbox) > _INBOX_CAP:
            _inbox = ""  # something is sending junk; do not grow forever
        return ""

    message = _inbox[:cut]
    _inbox = _inbox[cut + 1 :]
    return message
