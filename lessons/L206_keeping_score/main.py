"""Play a real match: miss the ball and your partner's score goes up.

Everything from the last lesson still works. What is new is that there is now
something both boards have to AGREE about, and neither of them can see it.

A ball you can watch. A score is just a number in memory, and each board has
its own copy -- so the only way they stay the same is if the boards tell each
other. The question this lesson is really about is WHICH board gets to say.

The answer is the board that missed. When the ball goes past your paddle, your
board is the only one that knows: your partner cannot see your panel, your
paddle, or the ball at that moment. So the board that loses the point is the
one that announces it. That is a strange rule the first time you read it --
the loser reports -- but it is the only board with the evidence, and it is not
a rule anybody is tempted to break in their own favour.

One new message:

    point <my id> <your score> <my score>    I missed. Here are both scores.

Notice what it does NOT say. It does not say "add one to your score." It says
what both scores ARE. That matters, because -- exactly like the "give" in the
last lesson -- this message is repeated until the partner answers, and the
answer is the partner serving the next ball. If a repeat arrives late, or
twice, "add one" would count the point twice. "Your score is 4" is still true
however many times it turns up.

And the scores are the other way round on purpose, yours first: the message is
addressed to you, so it is written from your side. The "give" message does the
same thing with the ball's position.
"""

import random

import colors
import interactions
import network
import screen

have_kind = "have"
give_kind = "give"
wait_kind = "wait"
point_kind = "point"

ball_size = 4
paddle_width = 14
paddle_height = 2
serve_speed_x = 0.6
serve_speed_y = 0.8

stall_after = 2.0  # nobody has had the ball this long -> a new one is served
forget_after = 15.0  # partner silent this long -> they have gone

my_color = colors.JADE
their_color = colors.MAGENTA

my_id = interactions.join_wifi()
pairing_kinds = [have_kind, give_kind, wait_kind, point_kind]
partner_id = interactions.tap_to_pair(pairing_kinds)

paddle_y = screen.HEIGHT - paddle_height
paddle_max_x = screen.WIDTH - paddle_width
ball_max_x = screen.WIDTH - ball_size
screen_center_x = screen.WIDTH // 2

paddle = screen.block(paddle_width, paddle_height, my_color, 0, paddle_y)
ball = screen.circle(ball_size, colors.CYAN)
ball.hidden = True

# Both scores, on both panels, in the top corners. Yours is the color of your
# own paddle.
my_score = 0
their_score = 0
my_sign = screen.text("0", my_color, 1, 3, font=screen.Fonts.SMALL)
their_sign = screen.text("0", their_color, 60, 3, font=screen.Fonts.SMALL)

state = wait_kind

ball_x = 0.0
ball_y = 0.0
speed_x = 0.0
speed_y = 0.0

screen.timer_reset("ball")
screen.timer_reset("partner")


def show_the_score():
    my_sign.text = str(my_score)
    their_sign.text = str(their_score)
    # Theirs is in the right-hand corner, so it has to move left as it grows:
    # a small letter is 4 pixels wide, and anything past the edge is simply
    # not drawn.
    their_sign.x = screen.WIDTH - 4 * len(their_sign.text)
    print(f"me {my_score}, them {their_score}")


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


def lost_the_point():
    # It went past us. We are the only board that saw that, so we are the one
    # who has to say it -- and we keep saying it until they serve again.
    global state, their_score
    their_score = their_score + 1
    state = point_kind
    ball.hidden = True
    show_the_score()
    print("missed")


def won_the_point(msg):
    # They missed. Believe both numbers exactly as sent: we do not add one to
    # anything, so hearing this twice cannot score the point twice.
    global my_score, their_score
    my_score = int(msg[2])
    their_score = int(msg[3])
    show_the_score()
    serve()


def steer_the_paddle(tilt_x):
    # Exactly as in lesson 109.
    paddle.x = int(tilt_x * screen_center_x) + screen_center_x - paddle_width // 2
    if paddle.x > paddle_max_x:
        paddle.x = paddle_max_x
    elif paddle.x < 0:
        paddle.x = 0


def get_partner_msg(kinds):
    """The newest message from our partner, if it is one of these kinds."""
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
    global ball_y, speed_y

    # Listen for your partner's waiting messages. We don't need to do anything
    # with them, but get_partner_msg resets the lost partner timer any time it
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
        # Past the paddle. This is the whole lesson: we are the only board that
        # can possibly know this just happened.
        lost_the_point()
    elif ball_y < -ball_size:
        # Over the top: it is theirs now.
        give_away()


def while_we_are_giving_it():
    """The ball has gone over the top. Say so until they say they have it."""
    global state

    # Listen for the message that means it arrived -- or, if we never heard
    # that one, for them having already taken it AND missed it.
    msg = get_partner_msg([have_kind, point_kind])
    if msg is not None and msg[0] == have_kind and len(msg) == 5:
        state = wait_kind
        print("they got it")
        return
    if msg is not None and msg[0] == point_kind and len(msg) == 4:
        won_the_point(msg)
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

    # Say we are waiting. Even with nothing to report, silence is how a board
    # decides its partner has gone.
    network.send(partner_id, f"{wait_kind} {my_id}")

    # Listen for the ball arriving, for our partner saying they still have it,
    # or for them admitting they missed.
    msg = get_partner_msg([give_kind, have_kind, point_kind])
    if msg is not None:
        screen.timer_reset("ball")
        if msg[0] == give_kind and len(msg) == 6:
            take(msg)
        elif msg[0] == point_kind and len(msg) == 4:
            won_the_point(msg)


def while_we_are_reporting_a_point():
    """We missed. Keep saying so until they serve the next ball."""
    global state

    # Their serve is the answer. Anything that means the ball is alive again
    # means they heard us -- exactly the way "have" answered a "give".
    msg = get_partner_msg([have_kind, give_kind])
    if msg is not None:
        state = wait_kind
        screen.timer_reset("ball")
        print("they know")
        return

    # Say it again, with both scores as they stand. Repeating this is safe
    # BECAUSE it says what the scores are instead of asking them to add one.
    network.send(partner_id, f"{point_kind} {my_id} {their_score} {my_score}")


def ball_has_gone_missing():
    # Nobody has had the ball for a while: a "give" never got through, or
    # someone saved in the middle of a rally and took it with them. Nobody
    # scores for this. Both boards follow the same rule, so they never both
    # serve: the one with the lower id does.
    global state
    if state == give_kind:
        print("they never took it")
    state = wait_kind
    if int(my_id) < int(partner_id):
        serve()
    screen.timer_reset("ball")


def lost_our_partner():
    # A new partner is a new match, so the scores go back to nothing.
    global state, partner_id, my_score, their_score
    print(f"lost board {partner_id}")
    state = wait_kind
    ball.hidden = True
    partner_id = interactions.tap_to_pair(pairing_kinds)
    my_score = 0
    their_score = 0
    show_the_score()
    screen.timer_reset("partner")
    screen.timer_reset("ball")


while True:
    tilt_x, tilt_y, tilt_z = interactions.smoothed_tilt()
    steer_the_paddle(tilt_x)

    # Exactly one of these runs each time, depending on our state.
    if state == have_kind:
        while_we_have_it(tilt_x)
    elif state == give_kind:
        while_we_are_giving_it()
    elif state == point_kind:
        while_we_are_reporting_a_point()
    else:
        while_we_are_waiting()

    # A ball nobody has is a ball that went missing -- unless we are in the
    # middle of reporting a point, where nobody is meant to have it yet.
    if (
        state != have_kind
        and state != point_kind
        and screen.timer_elapsed("ball") > stall_after
    ):
        ball_has_gone_missing()

    if screen.timer_elapsed("partner") > forget_after:
        lost_our_partner()

    screen.draw()

# Try these:
#
#   - Play to five. Nothing in here ever ends a match, so add it: when a score
#     reaches 5, stop serving and put something on the screen to say who won.
#   - Make the point message say "add one" instead of saying both scores: send
#     "point <my id> 1", and have the board that receives it do
#     their_score + 1. Then put back the deliberate losses from the last
#     lesson. Sooner or later one miss gets counted twice, and the two panels
#     disagree for the rest of the match. That is the difference between
#     saying what IS and saying what CHANGED.
#   - In while_we_are_reporting_a_point(), stop repeating: send the point once
#     and go straight to wait_kind. Now a single lost message is a point
#     nobody scored -- and again the panels disagree, with nothing on either
#     screen to say which one is right.
#   - Winning the point also wins the serve, which is an advantage. Change
#     won_the_point() so the winner hands the ball straight over the top
#     instead of playing it first.
#
# And the mischief -- you finally have something worth cheating at:
#
#   - Never admit you missed. In while_we_have_it(), serve a new ball instead
#     of calling lost_the_point(). Your partner's score never moves again.
#   - Award yourself the point: call lost_the_point() when you HIT the ball,
#     and swap the two scores in the message you send.
#   - Now sit on the other side of it. Your partner's board believes every
#     number you send and has no way to check a single one of them -- but it
#     is not as blind as it looks. It hears where your ball is, and how you
#     are tilting, every frame you have it. What could it work out for itself,
#     and what would it have to remember in order to do it?
