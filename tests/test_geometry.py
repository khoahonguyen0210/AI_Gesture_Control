from __future__ import annotations

import numpy as np
import pytest

from gesture_mouse.config import GestureConfig
from gesture_mouse.geometry import (
    INDEX_PIP,
    INDEX_TIP,
    MIDDLE_PIP,
    MIDDLE_TIP,
    PINKY_PIP,
    PINKY_TIP,
    RING_PIP,
    RING_TIP,
    THUMB_TIP,
    CursorFilter,
    Intent,
    Pose,
    apply_dead_zone,
    classify_pose,
    distance,
    finger_extended,
    hand_scale,
    intent_for,
    map_to_screen,
    pinch_ratio,
)
from helpers import make_landmarks

CFG = GestureConfig()
FINGERS = [
    (INDEX_TIP, INDEX_PIP),
    (MIDDLE_TIP, MIDDLE_PIP),
    (RING_TIP, RING_PIP),
    (PINKY_TIP, PINKY_PIP),
]


def extended(lm: np.ndarray) -> list[bool]:
    return [finger_extended(lm, tip, pip, CFG.finger_extended_margin) for tip, pip in FINGERS]


def test_u_geo_01_distance_and_hand_scale() -> None:
    assert distance(np.array([0.0, 0.0, 9.0]), np.array([3.0, 4.0, -9.0])) == pytest.approx(5.0)
    assert hand_scale(make_landmarks("open")) == pytest.approx(0.15)


def test_degenerate_hand_does_not_divide_by_zero() -> None:
    lm = np.zeros((21, 3))
    assert hand_scale(lm) > 0
    assert pinch_ratio(lm, THUMB_TIP, INDEX_TIP) == 0.0


@pytest.mark.parametrize("rotation", [0.0, 0.6, -0.9, np.pi])
def test_u_geo_02_finger_extended(rotation: float) -> None:
    assert extended(make_landmarks("open", rotation=rotation)) == [True] * 4
    assert extended(make_landmarks("fist", rotation=rotation)) == [False] * 4
    assert extended(make_landmarks("point", rotation=rotation)) == [True, False, False, False]
    assert extended(make_landmarks("two_finger", rotation=rotation)) == [True, True, False, False]


@pytest.mark.parametrize(
    ("scale", "offset", "rotation"),
    [(0.5, (0.0, 0.0), 0.0), (2.0, (0.0, 0.0), 0.0), (1.0, (0.2, -0.1), 0.0), (1.0, (0, 0), 1.2)],
)
def test_u_geo_03_pinch_ratio_invariant(
    scale: float, offset: tuple[float, float], rotation: float
) -> None:
    base = pinch_ratio(make_landmarks("pinch_left", ratio=0.2), THUMB_TIP, INDEX_TIP)
    moved = make_landmarks("pinch_left", ratio=0.2, scale=scale, offset=offset, rotation=rotation)
    assert base == pytest.approx(0.2)
    assert pinch_ratio(moved, THUMB_TIP, INDEX_TIP) == pytest.approx(base)


def test_u_geo_04_map_to_screen() -> None:
    m = 0.15
    assert map_to_screen(m, m, m) == pytest.approx((0.0, 0.0))
    assert map_to_screen(1 - m, 1 - m, m) == pytest.approx((1.0, 1.0))
    assert map_to_screen(0.5, 0.5, m) == pytest.approx((0.5, 0.5))
    assert map_to_screen(0.0, 1.0, m) == (0.0, 1.0)
    assert map_to_screen(-3.0, 7.0, m) == (0.0, 1.0)
    assert map_to_screen(0.25, 0.5, 0.0) == pytest.approx((0.25, 0.5))


def test_u_geo_05_cursor_filter_converges_and_resets() -> None:
    f = CursorFilter(0.5)
    assert f.update(0.0, 0.0) == (0.0, 0.0)
    assert f.update(1.0, 1.0) == pytest.approx((0.5, 0.5))
    for _ in range(30):
        x, y = f.update(1.0, 1.0)
    assert (x, y) == pytest.approx((1.0, 1.0), abs=1e-6)
    f.reset()
    assert f.update(0.2, 0.3) == (0.2, 0.3)
    f.reset(0.9, 0.9)
    assert f.update(0.1, 0.1) == pytest.approx((0.5, 0.5))


def test_alpha_one_follows_input_exactly() -> None:
    f = CursorFilter(1.0)
    f.update(0.1, 0.1)
    assert f.update(0.7, 0.2) == (0.7, 0.2)


def test_u_geo_06_dead_zone() -> None:
    assert apply_dead_zone(None, (10, 10), 3) == (10, 10)
    assert apply_dead_zone((10, 10), (11, 12), 3) == (10, 10)
    assert apply_dead_zone((10, 10), (13, 10), 3) == (13, 10)
    assert apply_dead_zone((10, 10), (11, 11), 0) == (11, 11)


@pytest.mark.parametrize(
    ("pose", "ratio", "expected"),
    [
        ("open", 0.05, Intent.NONE),
        ("fist", 0.05, Intent.NONE),
        ("point", 0.05, Intent.POINT),
        ("two_finger", 0.05, Intent.SCROLL),
        ("pinch_left", 0.05, Intent.LEFT_PINCH),
        ("pinch_right", 0.05, Intent.RIGHT_PINCH),
        ("half_pinch", 0.38, Intent.UNSURE),
        ("half_pinch", 0.60, Intent.NONE),
    ],
)
def test_intent_for_each_pose(pose: str, ratio: float, expected: Intent) -> None:
    pose_info = classify_pose(make_landmarks(pose, ratio=ratio), CFG)
    assert intent_for(pose_info, CFG) is expected


def test_active_pinch_holds_until_pinch_off() -> None:
    pose = classify_pose(make_landmarks("half_pinch", ratio=0.40), CFG)
    assert intent_for(pose, CFG) is Intent.UNSURE
    assert intent_for(pose, CFG, left_active=True) is Intent.LEFT_PINCH


def test_curled_fingers_cannot_pinch() -> None:
    pose = classify_pose(make_landmarks("fist"), CFG)
    assert pose.ratio_ti < CFG.pinch_on or pose.ratio_tm < CFG.pinch_on
    assert not pose.index_can_pinch
    assert not pose.middle_can_pinch


def test_pinch_tie_goes_left() -> None:
    pose = Pose(False, False, False, False, 0.1, 0.1, True, True)
    assert intent_for(pose, CFG) is Intent.LEFT_PINCH
