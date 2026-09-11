"""Hit the ball over the top of your panel and it lands on your partner's.

Lay both boards flat on the table with their TOPS touching, so the two panels
make one long court. Each of you has a paddle along your own bottom edge. When
the ball goes off the top of your panel, it comes in at the top of theirs.

The ball only exists in one place at a time, so exactly one board is in charge
of it -- moving it, bouncing it, drawing it. The new idea is how it gets from one
board to the other without ever being lost or ending up on both. Every board
says one of three things, every single time round the loop:

    have <my id>                             I have the ball
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
import time

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
give_message = ""  # what we keep sending while we hand the ball over

last_saw_ball = time.monotonic()  # when anybody last had the ball
heard_from_partner = time.monotonic()


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
    # The ball is going over the top. Work out where it lands on THEIR panel.
    #
    # With the tops touching, their panel is turned right round compared to
    # ours. So left and right swap, and both speeds flip: a ball going up and
    # to the left here is going down and to the right there.
    #
    # It is WIDTH - ball_size - x, not WIDTH - 1 - x. The ball is ball_size
    # wide, and x is its left edge, so the mirror has to leave room for it.
    global state, give_message
    their_x = screen.WIDTH - ball_size - ball_x
    their_y = -ball_y  # however far past our top edge, that far into theirs
    give_message = f"{give_kind} {my_id} {their_x} {their_y} {-speed_x} {-speed_y}"
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


while True:
    now = time.monotonic()

    # Steer the paddle, exactly as in lesson 109.
    tilt_x, tilt_y, tilt_z = interactions.smoothed_tilt()
    paddle.x = int(tilt_x * screen_center_x) + screen_center_x - paddle_width // 2
    if paddle.x > paddle_max_x:
        paddle.x = paddle_max_x
    elif paddle.x < 0:
        paddle.x = 0

    # --- listen -------------------------------------------------------------
    msg = interactions.get_newest_message([have_kind, give_kind, wait_kind])
    if msg is not None and msg[1] == partner_id:
        heard_from_partner = now
        kind = msg[0]

        if kind == give_kind and len(msg) == 6 and state != have_kind:
            # They are giving us the ball, and we do not have one. Take it.
            # (If we already have it, this is them repeating a "give" we have
            # already taken -- they just have not heard our "have" yet.)
            take(msg)
            last_saw_ball = now

        elif kind == have_kind and len(msg) == 2:
            last_saw_ball = now
            if state == give_kind:
                # They have it. That is the answer we were waiting for, so we
                # can stop saying "give".
                state = wait_kind
                print("they got it")
            elif state == have_kind and int(my_id) > int(partner_id):
                # We BOTH think we have it. It should never happen, but if it
                # does, both boards follow the same rule: the lower id keeps it.
                state = wait_kind
                ball.hidden = True
                print("we both had it -- letting them keep it")

    # --- move the ball, if it is ours ---------------------------------------
    if state == have_kind:
        last_saw_ball = now
        ball_x = ball_x + speed_x
        ball_y = ball_y + speed_y

        # Side walls, bounced the way lesson 106 does it.
        if ball_x > ball_max_x:
            ball_x = ball_max_x - (ball_x - ball_max_x)
            speed_x = -speed_x
        elif ball_x < 0:
            ball_x = -ball_x
            speed_x = -speed_x

        # The paddle, tested the way lesson 109 tests a catch -- plus one more
        # question: was the ball still above the paddle a moment ago? Without
        # it, a ball that has already slipped past can drift sideways into the
        # paddle and get "caught" from behind.
        on_paddle = (
            speed_y > 0
            and ball_y + ball_size >= paddle_y
            and ball_y + ball_size - speed_y <= paddle_y
            and ball_x + ball_size >= paddle.x
            and ball_x <= paddle.x + paddle_width
        )

        if on_paddle:
            ball_y = paddle_y - ball_size - (ball_y + ball_size - paddle_y)
            speed_y = -speed_y
        elif ball_y > screen.HEIGHT:
            # Missed it. Nobody has the ball now, so after a moment one of us
            # serves a new one.
            state = wait_kind
            ball.hidden = True
            print("missed")
        elif ball_y < 0:
            # Over the top: it is theirs now.
            give_away()

        ball.x = int(ball_x)
        ball.y = int(ball_y)

    # --- say what we are doing, every single time ---------------------------
    if state == have_kind:
        network.send(partner_id, f"{have_kind} {my_id}")
    elif state == give_kind:
        network.send(partner_id, give_message)
    else:
        network.send(partner_id, f"{wait_kind} {my_id}")

    # --- when the ball goes missing -------------------------------------------
    # Nobody has had the ball for a while: it was missed, or a "give" never got
    # through, or someone saved in the middle of a rally and took it with them.
    # Both boards follow the same rule, so they never both serve: the one with
    # the lower id does.
    if state != have_kind and now - last_saw_ball > stall_after:
        if state == give_kind:
            print("they never took it")
        state = wait_kind
        if int(my_id) < int(partner_id):
            serve()
        last_saw_ball = now

    # Our partner has gone quiet for longer than a save could explain.
    if now - heard_from_partner > forget_after:
        print(f"lost board {partner_id}")
        state = wait_kind
        ball.hidden = True
        partner_id = interactions.tap_to_pair([have_kind, give_kind, wait_kind])
        heard_from_partner = time.monotonic()
        last_saw_ball = time.monotonic()

    screen.draw()

# Try these:
#   - Make give_away() send the "give" once and go straight back to waiting,
#     instead of repeating it. Play for a while. Every so often the ball goes
#     over the top and simply never arrives. How often? (About as often as a
#     message gets lost -- which is not often, but a game lasts a long time.)
#   - Stop sending "wait" -- delete that send, so a waiting board says nothing.
#     Keep a long rally going on one side. What happens after forget_after
#     seconds, even though your partner is sitting right there?
#   - Change the mirror to screen.WIDTH - 1 - ball_x. Hit the ball straight up
#     near one edge and watch where it comes in on the other panel.
#   - Set stall_after to 0.1. What goes wrong, and why does it depend on how
#     long a "give" takes to be answered?
#   - Both boards keep a ball_x and a ball_y. At any moment, only one board's
#     numbers mean anything. Which one, and how does the other board know?
#
# And the mischief:
#
#   - Send "have" every time, whatever is really going on. Your partner never
#     serves and never gets the ball. Is there any way for them to tell you are
#     lying?
#   - When you give the ball away, give it a speed of 5 instead of the real one.
#     Your partner's board believes you completely. Should it?
