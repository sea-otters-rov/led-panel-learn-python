"""Hit the ball over the top of your panel and it lands on your partner's.

Lay both boards flat on the table with their TOPS touching, so the two panels
make one long court. Each of you has a paddle along your own bottom edge. When
the ball goes off the top of your panel, it comes in at the top of theirs.

The ball only exists in one place at a time, so exactly one board is in charge
of it -- moving it, bouncing it, drawing it. The new idea is how it gets from one
board to the other without ever being lost or ending up on both. Every board
says one of three things, every single time round the loop:

    have <my id> <x> <y> <tilt x>            I have the ball: where it is on
                                             my panel, and how I am tilting
    give <my id> <x> <y> <speed x> <speed y> the ball is yours now
    wait <my id>                             I am waiting for the ball

Handing the ball over means saying "give" -- and KEEPING ON saying it until your
partner says "have". Their "have" is the only proof they got it. Messages do go
missing, and if you said "give" once and moved on, every lost message would be
a ball that nobody has, frozen in the gap between two panels.

Notice that even the board waiting for the ball says something every time. That
is how the other board knows it is still there. Without it, the board with the
ball would hear nothing from its partner for as long as the ball stayed on its
side -- and silence is exactly how a board decides its partner has gone.
"""

import random

import colors
import interactions
import network
import screen

have_kind = "have"
give_kind = "give"
wait_kind = "wait"

ball_size = 4
paddle_width = 14
paddle_height = 2
serve_speed_x = 0.6
serve_speed_y = 0.8

stall_after = 2.0  # nobody has had the ball this long -> a new one is served
forget_after = 15.0  # partner silent this long -> they have gone

my_id = interactions.join_wifi()

# Lesson 204's tap-to-pair, packed up in interactions. It also picks a pairing
# back up after a save, if it hears any of these from a board that still thinks
# we are its partner.
partner_id = interactions.tap_to_pair([have_kind, give_kind, wait_kind])

paddle_y = screen.HEIGHT - paddle_height
paddle_max_x = screen.WIDTH - paddle_width
ball_max_x = screen.WIDTH - ball_size
screen_center_x = screen.WIDTH // 2

paddle = screen.block(paddle_width, paddle_height, colors.JADE, 0, paddle_y)
ball = screen.circle(ball_size, colors.CYAN)
ball.hidden = True

# Which of the three we are right now -- the same word we send. We start out
# waiting: nobody has served yet.
state = wait_kind

ball_x = 0.0
ball_y = 0.0
speed_x = 0.0
speed_y = 0.0

# Two clocks, each with its own name: how long since anybody had the ball, and
# how long since our partner said anything at all.
screen.timer_reset("ball")
screen.timer_reset("partner")


def serve():
    # A new ball in the middle of our panel, heading over the top to them.
    global state, ball_x, ball_y, speed_x, speed_y
    ball_x = (screen.WIDTH - ball_size) / 2
    ball_y = (screen.HEIGHT - ball_size) / 2
    speed_x = random.choice([-serve_speed_x, serve_speed_x])
    speed_y = -serve_speed_y
    state = have_kind
    ball.hidden = False
    print("serving")


def give_away():
    # The ball is going over the top.
    global state
    state = give_kind
    ball.hidden = True
    print("giving it to them")


def take(msg):
    # They gave us the ball. Their message already says where it is on OUR
    # panel, so just believe it.
    global state, ball_x, ball_y, speed_x, speed_y
    ball_x = float(msg[2])
    ball_y = float(msg[3])
    speed_x = float(msg[4])
    speed_y = float(msg[5])
    state = have_kind
    ball.hidden = False
    print("got it")


def steer_the_paddle(tilt_x):
    # Exactly as in lesson 109.
    paddle.x = int(tilt_x * screen_center_x) + screen_center_x - paddle_width // 2
    if paddle.x > paddle_max_x:
        paddle.x = paddle_max_x
    elif paddle.x < 0:
        paddle.x = 0


def get_partner_msg(kinds):
    """The newest message from our partner, if it is one of these kinds.

    It asks for EVERY kind, not just the ones we want, because anything at all
    from our partner means they are still there. Ask only for the kinds this
    state cares about and a partner sitting quietly in "wait" would be declared
    gone, while they were talking to us the whole time.
    """
    msg = interactions.get_newest_message(kinds)
    if msg is None or msg[1] != partner_id:
        return None

    screen.timer_reset("partner")
    return msg


def move_the_ball():
    # One step, then bounce off the side walls the way lesson 106 does it.
    global ball_x, ball_y, speed_x, speed_y
    ball_x = ball_x + speed_x
    ball_y = ball_y + speed_y

    if ball_x > ball_max_x:
        ball_x = ball_max_x - (ball_x - ball_max_x)
        speed_x = -speed_x
    elif ball_x < 0:
        ball_x = -ball_x
        speed_x = -speed_x

    ball.x = int(ball_x)
    ball.y = int(ball_y)


def paddle_caught_it():
    # The way lesson 109 tests a catch, plus one more question: was the ball
    # still above the paddle a moment ago? Without it, a ball that has already
    # slipped past can drift sideways into the paddle and be caught from behind.
    return (
        speed_y > 0
        and ball_y + ball_size >= paddle_y
        and ball_y + ball_size - speed_y <= paddle_y
        and ball_x + ball_size >= paddle.x
        and ball_x <= paddle.x + paddle_width
    )


def while_we_have_it(tilt_x):
    """The ball is ours: nobody else moves it, draws it, or decides about it."""
    global state, ball_y, speed_x, speed_y

    # Listen for your partner's waiting messages. We don't need to do anything with
    # them, but get_partner_msg resets the lost partner timer any time it
    # receives something
    get_partner_msg([wait_kind])

    # Say where the ball is and how we are tilting.
    network.send(partner_id, f"{have_kind} {my_id} {ball_x} {ball_y} {tilt_x}")

    # Update: move it, bounce it, and see where that leaves us.
    screen.timer_reset("ball")
    move_the_ball()

    if paddle_caught_it():
        # Line the ball to the top of the paddle
        ball_y = paddle_y - ball_size - (ball_y + ball_size - paddle_y)
        # And reverse vertical speed
        speed_y = -speed_y
    elif ball_y > screen.HEIGHT:
        # Missed it. Nobody has the ball now, so after a moment one of us
        # serves a new one.
        state = wait_kind
        ball.hidden = True
        print("missed")
    elif ball_y < -ball_size:
        # Over the top: it is theirs now.
        give_away()


def while_we_are_giving_it():
    """The ball has gone over the top. Say so until they say they have it."""
    global state

    # Listen for the one message that means it arrived.
    msg = get_partner_msg([have_kind])
    if msg is not None and len(msg) == 5:
        state = wait_kind
        print("they got it")
        return

    # Say it again. Their panel is turned right round from ours -- the tops are
    # touching -- so left and right swap, and both speeds flip: a ball going up
    # and to the left here is going down and to the right there.
    their_x = screen.WIDTH - ball_size - ball_x
    their_y = -ball_size  # always start the ball just off screen so it doesn't pop in
    network.send(
        partner_id, f"{give_kind} {my_id} {their_x} {their_y} {-speed_x} {-speed_y}"
    )

    # Nothing to update. The ball is not ours to move any more.


def while_we_are_waiting():
    """Nobody here has the ball: listen for it, and keep saying we are here."""
    # Listen for the ball arriving, or for our partner saying they still have it.
    msg = get_partner_msg([give_kind, have_kind])

    # Say we are waiting. Even with nothing to report, silence is how a board
    # decides its partner has gone.
    network.send(partner_id, f"{wait_kind} {my_id}")

    # Update.
    if msg is not None:
        if msg[0] == give_kind and len(msg) == 6:
            take(msg)
            screen.timer_reset("ball")
        elif msg[0] == have_kind and len(msg) == 5:
            screen.timer_reset("ball")  # they have it, so the ball still exists


def ball_has_gone_missing():
    # Nobody has had the ball for a while: it was missed, or a "give" never got
    # through, or someone saved in the middle of a rally and took it with them.
    # Both boards follow the same rule, so they never both serve: the one with
    # the lower id does.
    global state
    if state == give_kind:
        print("they never took it")
    state = wait_kind
    if int(my_id) < int(partner_id):
        serve()
    screen.timer_reset("ball")


def lost_our_partner():
    global state, partner_id
    print(f"lost board {partner_id}")
    state = wait_kind
    ball.hidden = True
    partner_id = interactions.tap_to_pair([have_kind, give_kind, wait_kind])
    screen.timer_reset("partner")
    screen.timer_reset("ball")


while True:
    tilt_x, tilt_y, tilt_z = interactions.smoothed_tilt()
    steer_the_paddle(tilt_x)

    # Exactly one of these runs each time, depending on our state.
    # Each listens for the messages that matter to it, says what we are doing,
    # and updates whatever it is in charge of.
    if state == have_kind:
        while_we_have_it(tilt_x)
    elif state == give_kind:
        while_we_are_giving_it()
    else:
        while_we_are_waiting()

    # Two things worth checking whatever state we are in.
    if state != have_kind and screen.timer_elapsed("ball") > stall_after:
        ball_has_gone_missing()

    if screen.timer_elapsed("partner") > forget_after:
        lost_our_partner()

    screen.draw()

# Try these:
#
#   - Every serve is one of the same two angles. In serve(), pick the sideways
#     speed at random instead: random.uniform(-0.9, 0.9). Now no two rallies
#     start the same way.
#   - Let the paddle aim. Where the ball lands on the paddle should decide where
#     it goes: hit it with the left end and it should fly left, dead centre and
#     it should come straight back. In while_we_have_it(), when the paddle
#     catches it, work out how far the middle of the ball is from the middle of
#     the paddle, and set speed_x from that.
#   - Make a rally get harder. Multiply speed_x and speed_y by 1.05 every time
#     the paddle catches it. How many hits before it is impossible?
#   - Try a larger or smaller ball size. What happens if you and your partner
#     don't have the same settings?
#
# Now break the rules and see what the messages are really for:
#
#   - Make it send the give once and set state to wait_kind straight afterwards,
#     instead of repeating. It will still work most of the time since wifi usually
#     only loses <1% of messages (aka packet loss). If you go very far from the router
#     this will get worse and you'll notice the ball getting lost.
#     Now, lose half the handovers on purpose. In while_we_are_giving_it(), just
#     after the listen, add:
#
#         if random.random() < 0.5:
#             return
#
#     Now about half of your shots vanish over the top and a
#     new ball has to be served after a few seconds. That is why it repeats.
#
# And a bit of mischief:
#
#   - Change their_y from -ball_size to 20, so the ball arrives most of the way down
#     their panel. Play a rally each way. Is it still a fair game?
#   - Never give the ball away: when it goes over the top, keep saying "have"
#     instead. Your partner's panel stays empty forever -- and they will not
#     serve a new one either, because your "have" keeps telling them the ball
#     is alive and well.
#   - Give the ball away with a speed of 3 instead of the real one.
#   - How could your partner detect any of the above and disqualify you?
