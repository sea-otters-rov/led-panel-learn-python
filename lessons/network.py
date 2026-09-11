"""Talking to the other boards.

    import network

    network.start()                      # join the wifi -- takes a few seconds
    network.my_id                        # the number that means THIS board
    network.send_to_everyone("hello")    # every board hears it
    network.send(their_id, "hi")         # just that one board hears it
    message = network.receive()          # None when nothing has arrived

Every board has an **id**: a small number that you say out loud and type in.
It is the only handle you need -- send() takes one, and nothing in a lesson
ever types a full address. Two boards can never end up with the same id, so
"what if we clash?" is a question this course never has to answer.

Messages are plain text. Whatever you send is exactly what comes out the other
end, so it is up to your lesson to decide what the words mean.
"""

import time

import board
from digitalio import DigitalInOut

import adafruit_esp32spi.adafruit_esp32spi as esp32spi

PORT = 5007  # every board listens here

# nina-fw's "set power mode" command. adafruit_esp32spi does not wrap it, so
# start() sends it by number. A 0 means WIFI_PS_NONE: the radio listens all
# the time. See start() for why that matters.
_SET_POWER_MODE = 0x17

my_id = ""  # filled in by start(), e.g. "11". What you call this board
my_address = ""  # filled in by start(), e.g. "192.168.1.11"

_esp = None
_listen = None
_everyone = ""
_prefix = ""
_inbox = ""
_talk = None
_INBOX_CAP = 512


def start(tries: int = 8) -> str:
    """Join the wifi and get ready to send and receive.

    This takes a few seconds, and there is no way around that: the radio has to
    be reset and then join the network. Put something on the screen first so
    nobody thinks the board has died.
    """
    global _esp, _listen, _everyone, _prefix, my_address, my_id

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

    # Keep the radio listening. nina-fw starts the ESP32 in WIFI_PS_MIN_MODEM,
    # which switches the receiver off between the access point's beacons to
    # save power -- and the access point drops much of what it was holding for
    # a dozing board. A board that was only listening missed most of what was
    # sent to it, for seconds at a time. Nobody here runs on a battery, so the
    # saving is worth nothing and the cost is lost messages.
    reply = _esp._send_command_get_response(_SET_POWER_MODE, ((0,),))
    if reply[0][0] != 1:
        print("network: the radio would not turn power saving off")

    my_address = _esp.pretty_ip(_esp.ip_address)

    # Every board here shares the first three numbers of its address and
    # differs only in the last, so the last number on its own is enough to
    # name a board -- that is exactly what an id is.
    piece = my_address.split(".")
    _prefix = piece[0] + "." + piece[1] + "." + piece[2] + "."
    _everyone = _prefix + "255"
    my_id = str(int(piece[3]))

    _listen = _esp.get_socket()
    _esp.start_server(PORT, _listen, conn_mode=_esp.UDP_MODE)

    print("network: board", my_id, "ready at", my_address)
    return my_id


def address_of(board_id) -> str:
    """The full address of the board with this id, e.g. 11 -> "192.168.1.11".

    You do not need this to send -- send() takes the id and does this for you.
    It is here so a lesson can show the expansion once, because it is the whole
    trick: every board in the room shares the first three numbers, so the last
    one on its own is enough to say which board you mean. An id is an address
    with the boring part left off.

    The id may be a number or something the student typed, so "7", "07" and
    " 7" all mean the same board.
    """
    if not _prefix:
        raise RuntimeError("network: call start() before address_of()")
    try:
        number = int(board_id)
    except (TypeError, ValueError):
        raise ValueError(
            f"network: {board_id} is not a board id. An id is a number like 11 -- if you "
            "have a whole address, the id is its last number."
        )
    if not 1 <= number <= 254:
        raise ValueError(
            f"network: board id {number} does not exist. Ids run 1 to 254 -- 0 and 255 "
            "are the network and everyone, so no board is ever called those."
        )
    return _prefix + str(number)


def firmware_version() -> str:
    """What version the radio is running. Only useful when something is wrong.

    Old nina-fw associates and resolves names perfectly well and then fails
    every single socket_open, which looks like a bug in your code and is not.
    3.3.0 or newer is what this course expects. Check this first when a board
    joins the wifi and then cannot send anything.
    """
    if _esp is None:
        raise RuntimeError("network: call start() first")
    return str(_esp.firmware_version, "utf-8").strip("\x00")


def send(board_id, message: str) -> bool:
    """Send one message to one board, by its id. True if it went out.

    Only that board hears it. Everybody else on the network carries on
    unbothered, which is why a game uses this and not send_to_everyone().
    """
    return _send_to(address_of(board_id), message)


def send_to_everyone(message: str) -> bool:
    """Send one message to every board on the network.

    Everyone ELSE, that is: a board does not hear its own broadcast. If your
    own screen has to show what you just said, say it locally as well.
    """
    return _send_to(_everyone, message)


def _send_to(address: str, message: str) -> bool:
    """Put one message on the wire. Lessons use send() instead.

    socket_open has to be called before EVERY message, not just the first one.
    The radio keeps what you write in a buffer and only empties it when the
    socket is opened again -- so without this, the second message arrives with
    the first one stuck to the front of it, and the third with both. That is a
    known bug in the library:
    github.com/adafruit/Adafruit_CircuitPython_ESP32SPI/issues/135
    """
    global _talk

    if _esp is None:
        raise RuntimeError("network: call start() first")

    if not isinstance(message, str):
        raise TypeError("network: message must be a string")

    data = (message + "\n").encode()
    if _talk is None:
        _talk = _esp.get_socket()

    try:
        _esp.socket_open(_talk, address, PORT, conn_mode=_esp.UDP_MODE)
        _esp.socket_write(_talk, data, conn_mode=_esp.UDP_MODE)
        return True
    except Exception:  # noqa: BLE001, S110
        pass

    # The radio jammed. Throw the socket away, take a fresh one, try once more.
    try:
        _esp.socket_close(_talk)
    except Exception:  # noqa: BLE001, S110
        pass
    try:
        _talk = _esp.get_socket()
        _esp.socket_open(_talk, address, PORT, conn_mode=_esp.UDP_MODE)
        _esp.socket_write(_talk, data, conn_mode=_esp.UDP_MODE)
        return True
    except Exception:  # noqa: BLE001
        # One lost message is not worth stopping a game for.
        return False


def receive() -> str | None:
    """The next message that arrived, or None if nothing is waiting.

    This never waits. Call it once per loop and carry on either way, so the
    screen keeps moving whether or not anyone is talking.
    """
    global _inbox

    if _esp is None:
        raise RuntimeError("network: call start() first")

    waiting = _esp.socket_available(_listen)
    if waiting:
        _inbox = _inbox + str(_esp.socket_read(_listen, waiting), "utf-8")
    elif not _inbox:
        return None

    cut = _inbox.find("\n")
    if cut < 0:
        if len(_inbox) > _INBOX_CAP:
            _inbox = ""  # something is sending junk; do not grow forever
        return None

    message = _inbox[:cut]
    _inbox = _inbox[cut + 1 :]
    return message if message else None


def receive_all():
    """Yield every message currently waiting, oldest first, then stop."""
    while True:
        msg = receive()
        if msg is None:
            return
        yield msg
