from __future__ import annotations

import random
import subprocess
import sys

import pytest

from gesture_mouse.config import CursorConfig, GestureConfig
from gesture_mouse.gesture_recognizer import (
    Action,
    ActionType,
    GestureRecognizer,
    GestureState,
    HandObservation,
    RecognizerOutput,
)
from helpers import both_pinch, make_hand

A = ActionType
FRAME_MS = 33


class Driver:
    def __init__(self, **gesture: float) -> None:
        self.r = GestureRecognizer(GestureConfig(**gesture), CursorConfig())
        self.t = 0
        self.last: RecognizerOutput | None = None

    def feed(self, obs: HandObservation | None, n: int = 1, enabled: bool = True) -> list[Action]:
        actions: list[Action] = []
        for _ in range(n):
            self.t += FRAME_MS
            self.last = self.r.update(obs, self.t, enabled)
            actions.extend(self.last.actions)
        return actions

    @property
    def state(self) -> GestureState:
        return self.r.state


def kinds(actions: list[Action]) -> list[ActionType]:
    return [a.type for a in actions]


def count(actions: list[Action], kind: ActionType) -> int:
    return sum(1 for a in actions if a.type is kind)


POINT = make_hand("point")
OPEN = make_hand("open")
PINCH = make_hand("pinch_left")
RIGHT = make_hand("pinch_right")
TWO = make_hand("two_finger")


def test_u_gr_01_no_hand_emits_nothing() -> None:
    d = Driver()
    assert d.feed(None, 10) == []
    assert d.state is GestureState.NO_HAND
    assert d.last is not None and d.last.label == "NO HAND"


def test_u_gr_02_pointing_needs_enter_frames() -> None:
    d = Driver()
    assert d.feed(POINT, 2) == []
    assert kinds(d.feed(POINT)) == [A.MOVE]
    assert kinds(d.feed(POINT, 3)) == [A.MOVE] * 3


def test_u_gr_03_short_pointing_emits_nothing() -> None:
    d = Driver()
    actions = d.feed(POINT, 2) + d.feed(OPEN, 5) + d.feed(POINT, 2) + d.feed(OPEN)
    assert actions == []


def test_u_gr_04_short_pinch_is_one_click_on_release() -> None:
    d = Driver()
    d.feed(POINT, 5)
    pinch = d.feed(PINCH, 4)
    assert pinch == []
    release = d.feed(OPEN, 3)
    assert kinds(release) == [A.LEFT_CLICK]


def test_click_lands_on_the_frozen_cursor() -> None:
    d = Driver()
    moves = d.feed(POINT, 5)
    d.feed(make_hand("pinch_left", offset=(0.1, 0.05)), 4)
    click = d.feed(OPEN, 3)[0]
    assert (click.x, click.y) == (moves[-1].x, moves[-1].y)


def test_u_gr_05_held_pinch_is_one_drag() -> None:
    d = Driver()
    d.feed(POINT, 5)
    actions = d.feed(PINCH, 20) + d.feed(OPEN, 3)
    assert count(actions, A.DRAG_START) == 1
    assert count(actions, A.DRAG_END) == 1
    assert count(actions, A.LEFT_CLICK) == 0
    assert kinds(actions).index(A.DRAG_START) < kinds(actions).index(A.DRAG_END)
    assert d.state is GestureState.IDLE


def test_drag_moves_with_the_pinch() -> None:
    d = Driver()
    d.feed(POINT, 5)
    d.feed(PINCH, 12)
    assert d.state is GestureState.DRAGGING
    moves = [a for a in d.feed(make_hand("pinch_left", offset=(0.1, 0.0)), 20) if a.x is not None]
    assert moves[-1].x is not None and moves[0].x is not None
    assert moves[-1].x > moves[0].x


def test_u_gr_06_long_hold_never_repeats_clicks() -> None:
    d = Driver()
    actions = d.feed(PINCH, 300)
    assert count(actions, A.LEFT_CLICK) == 0
    assert count(actions, A.DRAG_START) == 1


def test_u_gr_07_hysteresis_prevents_extra_clicks() -> None:
    d = Driver()
    flicker = [make_hand("half_pinch", ratio=r) for r in (0.28, 0.35)] * 5
    actions: list[Action] = []
    for obs in flicker:
        actions += d.feed(obs)
    assert actions == []

    d = Driver()
    actions = d.feed(make_hand("pinch_left", ratio=0.1), 4)
    for r in (0.35, 0.42, 0.36, 0.40, 0.38, 0.41):
        actions += d.feed(make_hand("half_pinch", ratio=r))
    actions += d.feed(OPEN, 3)
    assert count(actions, A.LEFT_CLICK) + count(actions, A.DRAG_START) == 1


def test_u_gr_08_cooldown_merges_fast_double_pinch() -> None:
    d = Driver()
    actions = d.feed(PINCH, 3) + d.feed(OPEN, 2) + d.feed(PINCH, 3) + d.feed(OPEN, 2)
    assert count(actions, A.LEFT_CLICK) == 1
    actions = d.feed(OPEN, 10) + d.feed(PINCH, 3) + d.feed(OPEN, 2)
    assert count(actions, A.LEFT_CLICK) == 1


def test_u_gr_09_right_pinch_clicks_once() -> None:
    d = Driver()
    actions = d.feed(RIGHT, 30)
    assert kinds(actions) == [A.RIGHT_CLICK]
    assert d.state is GestureState.RIGHT_LATCHED
    assert d.feed(OPEN, 10) == []
    assert kinds(d.feed(RIGHT, 5)) == [A.RIGHT_CLICK]


@pytest.mark.parametrize(
    ("ti", "tm", "state"),
    [
        (0.10, 0.20, GestureState.PINCH_PENDING),
        (0.20, 0.10, GestureState.RIGHT_LATCHED),
    ],
)
def test_u_gr_10_both_pinches_smaller_ratio_wins(ti: float, tm: float, state: GestureState) -> None:
    d = Driver()
    d.feed(both_pinch(ti, tm), 3)
    assert d.state is state


def test_u_gr_11_two_finger_scroll() -> None:
    d = Driver()
    d.feed(TWO, 3)
    assert d.state is GestureState.SCROLLING
    up = []
    for i in range(1, 6):
        up += d.feed(make_hand("two_finger", offset=(0.0, -0.05 * i)))
    assert up and all(a.type is A.SCROLL and a.amount > 0 for a in up)

    down = []
    for i in range(4, -1, -1):
        down += d.feed(make_hand("two_finger", offset=(0.0, -0.05 * i)))
    assert down and all(a.amount < 0 for a in down)

    still = []
    for i in range(10):
        still += d.feed(make_hand("two_finger", offset=(0.0, 0.004 * (i % 2))))
    assert still == []


def test_scroll_step_is_capped() -> None:
    d = Driver(scroll_max_step=2)
    d.feed(TWO, 3)
    actions = d.feed(make_hand("two_finger", offset=(0.0, -0.3)))
    assert [a.amount for a in actions] == [2]


def test_u_gr_12_hand_lost_mid_drag_releases_after_grace() -> None:
    d = Driver()
    d.feed(PINCH, 15)
    assert d.state is GestureState.DRAGGING
    grace = GestureConfig().lost_hand_grace_frames
    assert d.feed(None, grace - 1) == []
    assert kinds(d.feed(None)) == [A.DRAG_END]
    assert d.feed(None, 10) == []


def test_hand_back_within_grace_keeps_drag() -> None:
    d = Driver()
    d.feed(PINCH, 15)
    actions = d.feed(None, 2) + d.feed(PINCH, 3)
    assert d.state is GestureState.DRAGGING
    assert count(actions, A.DRAG_END) == 0


def test_hand_lost_while_pending_drops_without_click() -> None:
    d = Driver(drag_hold_ms=5000)
    d.feed(PINCH, 4)
    assert d.state is GestureState.PINCH_PENDING
    actions = d.feed(None, 10) + d.feed(OPEN, 5)
    assert actions == []


def test_u_gr_13_pause_ends_drag_once_and_emits_nothing() -> None:
    d = Driver()
    d.feed(PINCH, 15)
    actions = d.feed(PINCH, 10, enabled=False)
    assert kinds(actions) == [A.DRAG_END]
    assert d.state is GestureState.PAUSED
    assert d.feed(POINT, 10, enabled=False) == []
    assert d.feed(None, 3, enabled=False) == []
    assert d.last is not None and d.last.state is GestureState.PAUSED


def test_pause_without_hand_still_ends_drag() -> None:
    d = Driver()
    d.feed(PINCH, 15)
    assert kinds(d.feed(None, 1, enabled=False)) == [A.DRAG_END]


def test_paused_preview_still_shows_label() -> None:
    d = Driver()
    d.feed(POINT, 1, enabled=False)
    assert d.last is not None and d.last.label == "POINT"


def test_resume_after_pause_needs_fresh_gesture() -> None:
    d = Driver()
    d.feed(POINT, 5, enabled=False)
    assert d.feed(POINT, 2) == []
    assert kinds(d.feed(POINT)) == [A.MOVE]


def test_u_gr_14_states_are_exclusive() -> None:
    d = Driver(drag_hold_ms=5000)
    d.feed(TWO, 3)
    assert d.state is GestureState.SCROLLING
    d.feed(PINCH, 3)
    assert d.state is GestureState.PINCH_PENDING
    actions = d.feed(PINCH, 2) + d.feed(POINT) + d.feed(PINCH, 2)
    assert count(actions, A.MOVE) == 0
    assert count(actions, A.SCROLL) == 0
    assert count(actions, A.LEFT_CLICK) == 0
    assert d.state is GestureState.PINCH_PENDING


def test_u_gr_15_open_palm_and_fist_do_nothing() -> None:
    d = Driver()
    assert d.feed(OPEN, 30) == []
    assert d.feed(make_hand("fist"), 30) == []
    assert d.feed(make_hand("fist", rotation=0.8), 30) == []


def test_unsure_label_between_thresholds() -> None:
    d = Driver()
    d.feed(make_hand("half_pinch", ratio=0.38), 3)
    assert d.last is not None and d.last.label == "UNSURE"


def test_random_sequences_keep_invariants() -> None:
    poses = [POINT, OPEN, PINCH, RIGHT, TWO, make_hand("fist"), None]
    rng = random.Random(7)
    for _ in range(50):
        d = Driver()
        actions: list[Action] = []
        for _ in range(400):
            obs = rng.choice(poses)
            n = rng.randint(1, 15)
            actions += d.feed(obs, n, enabled=rng.random() > 0.05)
        actions += d.feed(None, 10)
        held = 0
        for a in actions:
            if a.type is A.DRAG_START:
                assert held == 0
                held = 1
            elif a.type is A.DRAG_END:
                assert held == 1
                held = 0
            elif a.type in (A.LEFT_CLICK, A.MOVE, A.SCROLL, A.RIGHT_CLICK):
                assert held == 0
        assert held == 0


def test_recognizer_imports_no_hardware_library() -> None:
    code = (
        "import sys, gesture_mouse.gesture_recognizer, gesture_mouse.geometry;"
        "print([m for m in ('cv2','mediapipe','pyautogui') if m in sys.modules])"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"
