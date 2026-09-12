"""Two balls at once, a score, and a new way to keep track of it all.

Last lesson your board was in one of three states -- it had the ball, it was
giving it away, or it was waiting. That worked because there was exactly one
ball. Add a second and the question "what state is this board in?" stops having
an answer: you might have one ball while the other is still crossing over.

So the state moves off the board and onto the ball. Each ball knows where it
is, where it is going, and whose it is. And that is what a **class** is for: a
way to say "a ball is these things" once, and then have as many as you like.

    class Ball:
        def __init__(self, ...):
            self.x = 0.0
            ...

`self` is the particular ball being talked about. `balls[0].x` and `balls[1].x`
are different numbers living in different objects, and neither one needs a
global.

The messages carry a ball number now, so each one says which ball it is about:

    mine <my id> <ball> <your score> <x> <y> <tilt x>
                                               I have this ball, and by the
                                               way, your score is this
    over <my id> <ball> <x> <y> <sx> <sy>      this ball is going over to you
    wait <my id>                               I have no balls at all

New words, not last lesson's `have` and `give`, because they are not the same
messages any more -- a word has to mean exactly one shape or it means nothing.

When you miss, the ball does NOT go anywhere: you keep it and serve it again
from your own end, so you get to watch it come back and set off towards your
partner. What crosses over is only the news that they scored.

**And that news is not a message of its own.** Look where the score lives: on
`mine`, which you are already sending every frame anyway. That makes the two
halves of this lesson behave completely differently, on purpose:

    the ball    an EVENT. It happens once. If the message is lost the ball is
                lost, so `over` is repeated until they answer with `mine`.
    the score   a STATE. It is simply true. You say it on every message, so a
                lost one costs nothing at all -- the next one says the same
                thing, and any board that fell behind catches up by itself.

A thing that is true does not need to be acknowledged. That is worth more than
it looks: no acknowledgement means no waiting, no retrying, and no way for the
two panels to end up permanently disagreeing.

Notice the score on your `mine` is THEIRS, not yours. Your own score is never
something your board writes -- it changes only when your partner admits they
missed. Every number has exactly one board allowed to say it, which is what
makes it safe when you both miss at the same instant. With two balls in play,
that is a matter of time rather than a curiosity.

One last thing, and it is why all of this fits in a frame: **all of it goes in
one trip.** Sending is the expensive part of a loop, and it costs about the
same whatever you put in it, so the board builds a list of everything it has to
say and hands the whole list to network.send() at once.
"""

import random

import colors
import rainbowio
import interactions
import network
import screen

mine_kind = "mine"
over_kind = "over"
wait_kind = "wait"

ball_count = 2
ball_size = 4
serve_speed_y = 0.8
serve_spread_x = 0.9  # a serve goes sideways somewhere between -this and this

stall_after = 2.0  # nobody has touched a ball this long -> serve it again
forget_after = 15.0  # partner silent this long -> they have gone

my_color = colors.JADE
their_color = colors.MAGENTA

my_id = interactions.join_wifi(show_id=False)
partner_kinds = [mine_kind, over_kind, wait_kind]
partner_id = interactions.tap_to_pair(partner_kinds)

screen_center_x = screen.WIDTH // 2
ball_max_x = screen.WIDTH - ball_size


class Paddle:
    """Your paddle. There is only one, but it reads better like this than a bunch of
    variables sprawled all over"""

    def __init__(self, color):
        self.width = 14
        self.height = 2
        self.shape = screen.block(
            self.width, self.height, color, 0, screen.HEIGHT - self.height
        )

    def steer(self, tilt_x):
        # Exactly as in lesson 109.
        x = int(tilt_x * screen_center_x) + screen_center_x - self.width // 2
        if x > screen.WIDTH - self.width:
            x = screen.WIDTH - self.width
        elif x < 0:
            x = 0
        self.shape.x = x

    def catches(self, ball):
        # Lesson 109's test, plus one more question: was the ball still above
        # the paddle a moment ago? Without it, a ball that has already slipped
        # past can drift sideways into the paddle and be caught from behind.
        return (
            ball.speed_y > 0
            and ball.y + ball_size >= self.shape.y
            and ball.y + ball_size - ball.speed_y <= self.shape.y
            and ball.x + ball_size >= self.shape.x
            and ball.x <= self.shape.x + self.width
        )


class Ball:
    """One ball. Everything about it lives in here, including whose it is."""

    def __init__(self, number, color):
        self.number = number
        self.timer = "ball" + str(number)  # its own clock, under its own name
        self.state = wait_kind
        self.x = 0.0
        self.y = 0.0
        self.speed_x = 0.0
        self.speed_y = 0.0
        self.shape = screen.circle(ball_size, color)
        self.shape.hidden = True

    def hold(self):
        # It is ours: we are the only board that may move it or draw it.
        self.state = mine_kind
        self.shape.hidden = False
        screen.timer_reset(self.timer)

    def let_go(self, new_state):
        self.state = new_state
        self.shape.hidden = True
        screen.timer_reset(self.timer)

    def serve(self):
        # A fresh ball. Sideways is random, so no two rallies start the same.
        self.x = screen_center_x
        self.y = paddle.shape.y - ball_size - 4
        self.speed_x = random.uniform(-serve_spread_x, serve_spread_x)
        self.speed_y = -serve_speed_y

    def take_from(self, msg, first):
        # Their message already says where it is on OUR panel, so believe it.
        self.x = float(msg[first])
        self.y = float(msg[first + 1])
        self.speed_x = float(msg[first + 2])
        self.speed_y = float(msg[first + 3])
        self.hold()

    def move(self):
        # One step, then bounce off the side walls the way lesson 106 does it.
        self.x = self.x + self.speed_x
        self.y = self.y + self.speed_y

        if self.x > ball_max_x:
            self.x = ball_max_x - (self.x - ball_max_x)
            self.speed_x = -self.speed_x
        elif self.x < 0:
            self.x = -self.x
            self.speed_x = -self.speed_x

        self.shape.x = int(self.x)
        self.shape.y = int(self.y)

    def on_their_panel(self):
        """Where this ball is and where it is going, from THEIR side.

        Their panel is turned right round from ours -- the tops are touching --
        so left and right swap and both speeds flip: a ball going up and to the
        left here is going down and to the right there.
        """
        return (
            screen.WIDTH - ball_size - self.x,
            -ball_size,  # just off the top, so it slides on instead of popping
            -self.speed_x,
            -self.speed_y,
        )


paddle = Paddle(my_color)

balls = []
for index in range(ball_count):
    balls.append(Ball(index, rainbowio.colorwheel(index * 25)))

my_score = 0
their_score = 0
my_score_text = screen.text("0", my_color, 1, 3, font=screen.Fonts.SMALL)
their_score_text = screen.text("0", their_color, 60, 3, font=screen.Fonts.SMALL)

screen.timer_reset("partner")


def show_the_score():
    my_score_text.text = str(my_score)
    their_score_text.text = str(their_score)
    # Theirs is in the right-hand corner, so it has to move left as it grows:
    # a small letter is 4 pixels wide, and anything past the edge is not drawn.
    their_score_text.x = screen.WIDTH - 4 * len(their_score_text.text)
    print(f"me {my_score}, them {their_score}")


def is_ours_to_serve(ball):
    # Both boards work this out the same way from the same two ids, so they
    # never both serve the same ball and never both leave it to the other.
    # One ball each at the start, and the same board looks after it all game.
    i_am_lower = int(my_id) < int(partner_id)
    if ball.number == 0:
        return i_am_lower
    return not i_am_lower


def listen_to_our_partner():
    """Everything they said this time round, oldest first.

    Oldest first matters now that two balls are talking. Keeping only the
    newest message of all -- which is what the last few lessons did -- would
    throw away a whole ball's news whenever both balls spoke at once.
    """
    global my_score

    for msg in interactions.get_messages(partner_kinds):
        if msg[1] != partner_id:
            continue

        # Anything at all from them means they are still there.
        screen.timer_reset("partner")

        if msg[0] == wait_kind:
            continue  # ignore wait messages, continue to the next message in the list

        ball = balls[int(msg[2])]
        screen.timer_reset(ball.timer)

        if msg[0] == mine_kind and len(msg) == 7:
            # Our score is theirs to say, and never ours. They say it on every
            # message they send, so one going missing costs nothing: the next
            # one says the same thing. Only act when the number is news.
            if int(msg[3]) != my_score:
                my_score = int(msg[3])
                show_the_score()

            # They have this ball. If we were still handing it over, that is
            # them answering us, and we can stop saying it.
            if ball.state != mine_kind:
                ball.let_go(wait_kind)
        elif msg[0] == over_kind and len(msg) == 7:
            if ball.state != mine_kind:
                ball.take_from(msg, 3)


def play_the_ball(ball, tilt_x):
    """Move a ball we own, and work out what to say about it."""
    global their_score

    screen.timer_reset(ball.timer)
    ball.move()

    if paddle.catches(ball):
        # Line it up with the top of the paddle and send it back. Where it hits
        # decides where it goes: the end of the paddle throws it sideways, the
        # middle sends it straight back.
        ball.y = paddle.shape.y - ball_size - 1
        ball.speed_y = -ball.speed_y
        middle = paddle.shape.x + paddle.width / 2
        ball.speed_x = (ball.x + ball_size / 2 - middle) / paddle.width * 2

    elif ball.y > screen.HEIGHT:
        # Past the paddle. Since we know it, we're going to say it and serve.
        # We keep the ball: you watch it come back at your own end and set off
        # towards your partner, instead of vanishing onto their panel.
        their_score = their_score + 1
        show_the_score()
        ball.serve()
        print(f"missed ball {ball.number}")

    elif ball.y < -ball_size:
        # Over the top: it is theirs now.
        ball.let_go(over_kind)
        print(f"ball {ball.number} goes over")

    return f"{mine_kind} {my_id} {ball.number} {their_score} {ball.x} {ball.y} {tilt_x}"


def what_we_have_to_say(tilt_x):
    """One list holding everything this board owes its partner this frame."""
    saying = []
    for ball in balls:
        if ball.state == mine_kind:
            saying.append(play_the_ball(ball, tilt_x))
        elif ball.state == over_kind:
            x, y, speed_x, speed_y = ball.on_their_panel()
            saying.append(
                f"{over_kind} {my_id} {ball.number} {x} {y} {speed_x} {speed_y}"
            )

    if not saying:
        # Nothing to report -- but silence is how a board decides its partner
        # has gone, so say something anyway.
        saying.append(f"{wait_kind} {my_id}")

    return saying


def nobody_has_this_ball(ball):
    # A handoff never got through, or somebody saved in the middle of a rally
    # and took the ball with them. Nobody scores for this.
    print(f"ball {ball.number} went missing")
    if is_ours_to_serve(ball):
        ball.serve()
        ball.hold()
    else:
        ball.let_go(wait_kind)


def lost_our_partner():
    # A new partner is a new match, so the scores go back to nothing.
    global partner_id, my_score, their_score
    print(f"lost board {partner_id}")
    for ball in balls:
        ball.let_go(wait_kind)
    partner_id = interactions.tap_to_pair(partner_kinds)
    my_score = 0
    their_score = 0
    show_the_score()
    screen.timer_reset("partner")
    for ball in balls:
        screen.timer_reset(ball.timer)


# Every clock starts now. tap_to_pair() may have sat waiting for a knock for
# a long time, and a ball whose clock was still running would be declared
# missing on the first frame.
screen.timer_reset("partner")
for ball in balls:
    screen.timer_reset(ball.timer)

# One ball each to start with, and both boards work out which is whose.
for ball in balls:
    if is_ours_to_serve(ball):
        ball.serve()
        ball.hold()

while True:
    tilt_x, tilt_y, tilt_z = interactions.smoothed_tilt()
    paddle.steer(tilt_x)

    listen_to_our_partner()

    # Everything we have to say, in one trip. Two separate sends would cost
    # nearly twice as much of the frame as one send carrying both.
    network.send(partner_id, what_we_have_to_say(tilt_x))

    for ball in balls:
        if ball.state != mine_kind and screen.timer_elapsed(ball.timer) > stall_after:
            nobody_has_this_ball(ball)

    if screen.timer_elapsed("partner") > forget_after:
        lost_our_partner()

    screen.draw()

# Try these:
#
#   - Add a third ball: set ball_count to 3.
#     Everything else already works, because nothing in the loop knows how many
#     there are. Then watch the frame rate: every extra ball adds a message to
#     every trip, and messages are what a frame pays for.
#   - What happens if you and your partner have ball_count set differently? Why?
#   - Play to ten. Nothing here ever ends a match, so add it: when a score
#     reaches 10, stop serving and put the winner up on the screen.
#   - Give the two balls different sizes. ball_size will have to belong to the
#     Ball instead of being one number shared by all of them -- which is
#     exactly the sort of thing a class is for.
#
# And a bit of fun:
#
#   - Never admit you missed: when a ball goes past your paddle, serve it again
#     on your own panel instead of letting go of it. Your partner's score never
#     moves again.
#   - Freeze your partner's score: send the same number in `mine` forever,
#     whatever really happens. Then try sending a number that goes DOWN.
#   - Now sit on the other side of it. Your partner's board believes every
#     number you send and checks none of them. However,
#     it hears where each ball is and how you are tilting, every frame
#     you hold one. What could it work out for itself, and what would it have
#     to remember in order to do it?
