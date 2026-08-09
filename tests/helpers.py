"""Deterministic synthetic hands for tests.

Points are built in hand units (wrist to middle MCP = 1, "up" is positive v),
then rotated, scaled, and placed into normalized image coordinates (y down).
"""

from __future__ import annotations

import math

import numpy as np

from gesture_mouse.gesture_recognizer import HandObservation

WRIST_AT = (0.5, 0.75)
HAND_SIZE = 0.15

OPEN_HAND: dict[int, tuple[float, float]] = {
    0: (0.0, 0.0),
    1: (-0.35, 0.25),
    2: (-0.6, 0.5),
    3: (-0.8, 0.75),
    4: (-0.95, 0.95),
    5: (-0.3, 1.0),
    6: (-0.35, 1.45),
    7: (-0.37, 1.75),
    8: (-0.4, 2.0),
    9: (0.0, 1.0),
    10: (0.0, 1.5),
    11: (0.0, 1.85),
    12: (0.0, 2.1),
    13: (0.25, 0.95),
    14: (0.3, 1.4),
    15: (0.32, 1.7),
    16: (0.35, 1.95),
    17: (0.48, 0.85),
    18: (0.58, 1.2),
    19: (0.63, 1.4),
    20: (0.68, 1.6),
}
FINGERS = {"index": (5, 7, 8), "middle": (9, 11, 12), "ring": (13, 15, 16), "pinky": (17, 19, 20)}
THUMB_TUCKED = {2: (-0.4, 0.45), 3: (-0.3, 0.65), 4: (-0.15, 0.85)}
PINCH_POINT = (-0.5, 1.3)


def _fold(points: dict[int, tuple[float, float]], finger: str) -> None:
    mcp, dip, tip = FINGERS[finger]
    u, v = points[mcp]
    points[dip] = (u, v + 0.2)
    points[tip] = (u, v - 0.05)


def _units(pose: str, ratio: float) -> dict[int, tuple[float, float]]:
    p = dict(OPEN_HAND)
    tx, ty = PINCH_POINT
    if pose == "open":
        pass
    elif pose == "fist":
        p.update(THUMB_TUCKED)
        for finger in FINGERS:
            _fold(p, finger)
    elif pose == "point":
        p.update(THUMB_TUCKED)
        for finger in ("middle", "ring", "pinky"):
            _fold(p, finger)
    elif pose == "two_finger":
        p.update(THUMB_TUCKED)
        _fold(p, "ring")
        _fold(p, "pinky")
    elif pose in ("pinch_left", "half_pinch"):
        p[4] = (tx, ty)
        p[8] = (tx + ratio, ty)
        p[7] = (tx + ratio + 0.05, ty + 0.15)
    elif pose == "pinch_right":
        p[4] = (tx, ty)
        p[12] = (tx + ratio, ty)
        p[11] = (tx + ratio + 0.1, ty + 0.2)
    else:
        raise ValueError(f"unknown pose {pose}")
    return p


def make_landmarks(
    pose: str,
    ratio: float = 0.05,
    scale: float = 1.0,
    offset: tuple[float, float] = (0.0, 0.0),
    rotation: float = 0.0,
) -> np.ndarray:
    """Return a (21, 3) array. ratio sets the pinch gap in hand units."""
    units = _units(pose, ratio)
    cos_r, sin_r = math.cos(rotation), math.sin(rotation)
    size = HAND_SIZE * scale
    out = np.zeros((21, 3))
    for i, (u, v) in units.items():
        ru = u * cos_r - v * sin_r
        rv = u * sin_r + v * cos_r
        out[i] = (WRIST_AT[0] + offset[0] + ru * size, WRIST_AT[1] + offset[1] - rv * size, 0.0)
    return out


def make_hand(
    pose: str,
    ratio: float = 0.05,
    scale: float = 1.0,
    offset: tuple[float, float] = (0.0, 0.0),
    rotation: float = 0.0,
) -> HandObservation:
    return HandObservation(make_landmarks(pose, ratio, scale, offset, rotation))


def both_pinch(ratio_ti: float, ratio_tm: float) -> HandObservation:
    p = _units("open", 0.0)
    tx, ty = PINCH_POINT
    p[4] = (tx, ty)
    p[8] = (tx + ratio_ti, ty)
    p[12] = (tx, ty + ratio_tm)
    out = np.zeros((21, 3))
    for i, (u, v) in p.items():
        out[i] = (WRIST_AT[0] + u * HAND_SIZE, WRIST_AT[1] - v * HAND_SIZE, 0.0)
    return HandObservation(out)
