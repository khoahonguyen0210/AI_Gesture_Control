"""Pure landmark geometry. Coordinates are normalized to the mirrored frame: x right, y down."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import numpy as np

from gesture_mouse.config import GestureConfig

WRIST = 0
THUMB_TIP = 4
INDEX_MCP, INDEX_PIP, INDEX_TIP = 5, 6, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP = 9, 10, 12
RING_PIP, RING_TIP = 14, 16
PINKY_PIP, PINKY_TIP = 18, 20

MIN_HAND_SCALE = 1e-6


class Intent(Enum):
    """What a single frame looks like, before any debouncing."""

    NONE = "none"
    POINT = "point"
    LEFT_PINCH = "left_pinch"
    RIGHT_PINCH = "right_pinch"
    SCROLL = "scroll"
    UNSURE = "unsure"


@dataclass(frozen=True)
class Pose:
    index_ext: bool
    middle_ext: bool
    ring_ext: bool
    pinky_ext: bool
    ratio_ti: float
    ratio_tm: float
    index_can_pinch: bool
    middle_can_pinch: bool


def distance(a: np.ndarray, b: np.ndarray) -> float:
    """2D distance; z is ignored."""
    return math.hypot(float(a[0] - b[0]), float(a[1] - b[1]))


def hand_scale(lm: np.ndarray) -> float:
    """Wrist to middle-finger MCP distance, with a small floor for degenerate hands."""
    return max(distance(lm[WRIST], lm[MIDDLE_MCP]), MIN_HAND_SCALE)


def pinch_ratio(lm: np.ndarray, a: int, b: int) -> float:
    return distance(lm[a], lm[b]) / hand_scale(lm)


def reach(lm: np.ndarray, tip: int, pip: int) -> float:
    """Tip-to-wrist distance divided by PIP-to-wrist distance. Above 1 means straight."""
    return distance(lm[WRIST], lm[tip]) / max(distance(lm[WRIST], lm[pip]), MIN_HAND_SCALE)


def finger_extended(lm: np.ndarray, tip: int, pip: int, margin: float) -> bool:
    return reach(lm, tip, pip) > margin


def map_to_screen(x: float, y: float, margin: float) -> tuple[float, float]:
    """Map the active region [margin, 1 - margin] to [0, 1] and clamp."""
    span = 1.0 - 2.0 * margin

    def one(v: float) -> float:
        return min(max((v - margin) / span, 0.0), 1.0)

    return one(x), one(y)


class CursorFilter:
    """Exponential smoothing: s = alpha * new + (1 - alpha) * s."""

    def __init__(self, alpha: float) -> None:
        self.alpha = alpha
        self._state: tuple[float, float] | None = None

    def update(self, x: float, y: float) -> tuple[float, float]:
        if self._state is None:
            self._state = (x, y)
        else:
            sx, sy = self._state
            a = self.alpha
            self._state = (a * x + (1 - a) * sx, a * y + (1 - a) * sy)
        return self._state

    def reset(self, x: float | None = None, y: float | None = None) -> None:
        self._state = None if x is None or y is None else (x, y)


def apply_dead_zone(
    prev_px: tuple[int, int] | None, new_px: tuple[int, int], dead_px: int
) -> tuple[int, int]:
    """Keep the previous point when the new one is closer than dead_px."""
    if prev_px is None:
        return new_px
    if math.hypot(new_px[0] - prev_px[0], new_px[1] - prev_px[1]) < dead_px:
        return prev_px
    return new_px


def classify_pose(lm: np.ndarray, cfg: GestureConfig) -> Pose:
    m = cfg.finger_extended_margin
    return Pose(
        index_ext=finger_extended(lm, INDEX_TIP, INDEX_PIP, m),
        middle_ext=finger_extended(lm, MIDDLE_TIP, MIDDLE_PIP, m),
        ring_ext=finger_extended(lm, RING_TIP, RING_PIP, m),
        pinky_ext=finger_extended(lm, PINKY_TIP, PINKY_PIP, m),
        ratio_ti=pinch_ratio(lm, THUMB_TIP, INDEX_TIP),
        ratio_tm=pinch_ratio(lm, THUMB_TIP, MIDDLE_TIP),
        index_can_pinch=reach(lm, INDEX_TIP, INDEX_PIP) >= cfg.pinch_min_reach,
        middle_can_pinch=reach(lm, MIDDLE_TIP, MIDDLE_PIP) >= cfg.pinch_min_reach,
    )


def intent_for(
    pose: Pose, cfg: GestureConfig, left_active: bool = False, right_active: bool = False
) -> Intent:
    """Frame-level intent. An active pinch stays on until its ratio passes pinch_off."""
    left_limit = cfg.pinch_off if left_active else cfg.pinch_on
    right_limit = cfg.pinch_off if right_active else cfg.pinch_on
    left = pose.index_can_pinch and pose.ratio_ti < left_limit
    right = pose.middle_can_pinch and pose.ratio_tm < right_limit
    if left and right:
        return Intent.LEFT_PINCH if pose.ratio_ti <= pose.ratio_tm else Intent.RIGHT_PINCH
    if left:
        return Intent.LEFT_PINCH
    if right:
        return Intent.RIGHT_PINCH

    near_left = pose.index_can_pinch and pose.ratio_ti <= cfg.pinch_off
    near_right = pose.middle_can_pinch and pose.ratio_tm <= cfg.pinch_off
    if near_left or near_right:
        return Intent.UNSURE

    folded_rest = not pose.ring_ext and not pose.pinky_ext
    if pose.index_ext and pose.middle_ext and folded_rest:
        return Intent.SCROLL
    if pose.index_ext and not pose.middle_ext and folded_rest:
        return Intent.POINT
    return Intent.NONE
