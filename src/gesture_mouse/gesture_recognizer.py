"""Rule-based gesture state machine: landmarks and a timestamp in, mouse actions out.

It never reads a clock and imports no camera, model, or mouse library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from gesture_mouse.config import CursorConfig, GestureConfig
from gesture_mouse.geometry import (
    INDEX_TIP,
    MIDDLE_TIP,
    THUMB_TIP,
    CursorFilter,
    Intent,
    classify_pose,
    intent_for,
    map_to_screen,
)


@dataclass(frozen=True)
class HandObservation:
    landmarks: np.ndarray
    handedness: str | None = None
    score: float | None = None


class ActionType(Enum):
    MOVE = "move"
    LEFT_CLICK = "left_click"
    RIGHT_CLICK = "right_click"
    DRAG_START = "drag_start"
    DRAG_MOVE = "drag_move"
    DRAG_END = "drag_end"
    SCROLL = "scroll"


@dataclass(frozen=True)
class Action:
    type: ActionType
    x: float | None = None
    y: float | None = None
    amount: int = 0


class GestureState(Enum):
    PAUSED = "paused"
    NO_HAND = "no_hand"
    IDLE = "idle"
    POINTING = "pointing"
    PINCH_PENDING = "pinch_pending"
    DRAGGING = "dragging"
    RIGHT_LATCHED = "right_latched"
    SCROLLING = "scrolling"


@dataclass(frozen=True)
class RecognizerOutput:
    actions: tuple[Action, ...]
    state: GestureState
    label: str
    debug: dict[str, float] = field(default_factory=dict)


INTENT_LABELS = {
    Intent.NONE: "IDLE",
    Intent.POINT: "POINT",
    Intent.LEFT_PINCH: "PINCH",
    Intent.RIGHT_PINCH: "RIGHT PINCH",
    Intent.SCROLL: "SCROLL",
    Intent.UNSURE: "UNSURE",
}
STATE_LABELS = {
    GestureState.NO_HAND: "NO HAND",
    GestureState.PINCH_PENDING: "PINCH",
    GestureState.DRAGGING: "DRAG",
    GestureState.RIGHT_LATCHED: "RIGHT CLICK",
    GestureState.SCROLLING: "SCROLL",
}
HELD_STATES = (GestureState.PINCH_PENDING, GestureState.DRAGGING, GestureState.RIGHT_LATCHED)
START_INTENTS = {
    GestureState.IDLE: {Intent.POINT, Intent.LEFT_PINCH, Intent.RIGHT_PINCH, Intent.SCROLL},
    GestureState.POINTING: {Intent.LEFT_PINCH, Intent.RIGHT_PINCH, Intent.SCROLL},
    GestureState.SCROLLING: {Intent.LEFT_PINCH},
}


class GestureRecognizer:
    def __init__(self, gesture: GestureConfig, cursor: CursorConfig) -> None:
        self.g = gesture
        self.c = cursor
        self.state = GestureState.IDLE
        self._filter = CursorFilter(cursor.smoothing_alpha)
        self._cursor: tuple[float, float] | None = None
        self._candidate = Intent.NONE
        self._candidate_count = 0
        self._candidate_start_ms = 0
        self._away_count = 0
        self._missing = 0
        self._pinch_start_ms = 0
        self._anchor: tuple[float, float] = (0.5, 0.5)
        self._drag_origin: tuple[float, float] = (0.0, 0.0)
        self._scroll_prev_y = 0.0
        self._scroll_accum = 0.0
        self._last_left_click_ms: int | None = None
        self._last_right_click_ms: int | None = None

    def update(self, obs: HandObservation | None, t_ms: int, enabled: bool) -> RecognizerOutput:
        if not enabled:
            actions = self._pause()
            if obs is None:
                return RecognizerOutput(actions, self.state, "NO HAND")
            intent, debug = self._read(obs.landmarks)
            return RecognizerOutput(actions, self.state, INTENT_LABELS[intent], debug)
        if obs is None:
            return self._no_hand()

        self._missing = 0
        lm = obs.landmarks
        intent, debug = self._read(lm)

        if self.state in (GestureState.PAUSED, GestureState.NO_HAND):
            self.state = GestureState.IDLE
            self._reset_candidate()

        step_actions = self._step(lm, intent, t_ms)
        label = STATE_LABELS.get(self.state, INTENT_LABELS[intent])
        if intent is Intent.UNSURE and self.state in (GestureState.IDLE, GestureState.POINTING):
            label = "UNSURE"
        return RecognizerOutput(tuple(step_actions), self.state, label, debug)

    def _read(self, lm: np.ndarray) -> tuple[Intent, dict[str, float]]:
        pose = classify_pose(lm, self.g)
        intent = intent_for(
            pose,
            self.g,
            left_active=self.state in (GestureState.PINCH_PENDING, GestureState.DRAGGING),
            right_active=self.state is GestureState.RIGHT_LATCHED,
        )
        return intent, {"ratio_ti": pose.ratio_ti, "ratio_tm": pose.ratio_tm}

    def _no_hand(self) -> RecognizerOutput:
        self._missing += 1
        actions: tuple[Action, ...] = ()
        if self.state in HELD_STATES and self._missing < self.g.lost_hand_grace_frames:
            return RecognizerOutput(actions, self.state, "NO HAND")
        if self.state is GestureState.DRAGGING:
            actions = (Action(ActionType.DRAG_END),)
        self.state = GestureState.NO_HAND
        self._reset_candidate()
        self._filter.reset()
        return RecognizerOutput(actions, self.state, "NO HAND")

    def _pause(self) -> tuple[Action, ...]:
        actions: tuple[Action, ...] = ()
        if self.state is GestureState.DRAGGING:
            actions = (Action(ActionType.DRAG_END),)
        self.state = GestureState.PAUSED
        self._reset_candidate()
        self._filter.reset()
        return actions

    def _step(self, lm: np.ndarray, intent: Intent, t_ms: int) -> list[Action]:
        if self.state is GestureState.PINCH_PENDING:
            return self._pinch_pending(lm, intent, t_ms)
        if self.state is GestureState.DRAGGING:
            return self._dragging(lm, intent)
        if self.state is GestureState.RIGHT_LATCHED:
            return self._right_latched(intent)

        self._track_candidate(intent, t_ms)
        stable = self._candidate_count >= self.g.enter_frames
        if stable and self._candidate in START_INTENTS[self.state]:
            return self._enter(self._candidate, lm, t_ms)

        if self.state is GestureState.SCROLLING:
            return self._scrolling(lm, intent)
        if intent is Intent.POINT and self.state is GestureState.POINTING:
            self._away_count = 0
            return [self._move(lm)]
        if self.state is GestureState.POINTING:
            self._away_count += 1
            if self._away_count >= self.g.exit_frames:
                self.state = GestureState.IDLE
        return []

    def _enter(self, intent: Intent, lm: np.ndarray, t_ms: int) -> list[Action]:
        self._away_count = 0
        if intent is Intent.POINT:
            self.state = GestureState.POINTING
            return [self._move(lm)]
        if intent is Intent.LEFT_PINCH:
            self.state = GestureState.PINCH_PENDING
            self._pinch_start_ms = self._candidate_start_ms
            self._anchor = self._cursor or self._screen_point(lm, INDEX_TIP)
            return []
        if intent is Intent.RIGHT_PINCH:
            self.state = GestureState.RIGHT_LATCHED
            last = self._last_right_click_ms
            if last is None or t_ms - last >= self.g.click_cooldown_ms:
                self._last_right_click_ms = t_ms
                return [Action(ActionType.RIGHT_CLICK)]
            return []
        self.state = GestureState.SCROLLING
        self._scroll_prev_y = self._scroll_y(lm)
        self._scroll_accum = 0.0
        return []

    def _pinch_pending(self, lm: np.ndarray, intent: Intent, t_ms: int) -> list[Action]:
        if intent is Intent.LEFT_PINCH:
            self._away_count = 0
            if t_ms - self._pinch_start_ms >= self.g.drag_hold_ms:
                self.state = GestureState.DRAGGING
                self._drag_origin = self._pinch_mid(lm)
                self._filter.reset(*self._anchor)
                x, y = self._anchor
                return [Action(ActionType.DRAG_START, x, y)]
            return []
        self._away_count += 1
        if self._away_count < self.g.exit_frames:
            return []
        self._finish_pinch()
        last = self._last_left_click_ms
        if last is not None and t_ms - last < self.g.click_cooldown_ms:
            return []
        self._last_left_click_ms = t_ms
        x, y = self._anchor
        return [Action(ActionType.LEFT_CLICK, x, y)]

    def _dragging(self, lm: np.ndarray, intent: Intent) -> list[Action]:
        if intent is Intent.LEFT_PINCH:
            self._away_count = 0
            mx, my = self._pinch_mid(lm)
            span = 1.0 - 2.0 * self.c.margin
            tx = self._anchor[0] + (mx - self._drag_origin[0]) / span
            ty = self._anchor[1] + (my - self._drag_origin[1]) / span
            x, y = self._filter.update(min(max(tx, 0.0), 1.0), min(max(ty, 0.0), 1.0))
            self._cursor = (x, y)
            return [Action(ActionType.DRAG_MOVE, x, y)]
        self._away_count += 1
        if self._away_count < self.g.exit_frames:
            return []
        self._finish_pinch()
        return [Action(ActionType.DRAG_END)]

    def _right_latched(self, intent: Intent) -> list[Action]:
        if intent is Intent.RIGHT_PINCH:
            self._away_count = 0
            return []
        self._away_count += 1
        if self._away_count >= self.g.exit_frames:
            self._finish_pinch()
        return []

    def _scrolling(self, lm: np.ndarray, intent: Intent) -> list[Action]:
        if intent is not Intent.SCROLL:
            self._away_count += 1
            if self._away_count >= self.g.exit_frames:
                self.state = GestureState.IDLE
            return []
        self._away_count = 0
        y = self._scroll_y(lm)
        delta = self._scroll_prev_y - y
        self._scroll_prev_y = y
        if abs(delta) < self.g.scroll_dead_zone:
            return []
        self._scroll_accum += delta * self.g.scroll_gain
        units = int(self._scroll_accum)
        if units == 0:
            return []
        units = max(-self.g.scroll_max_step, min(self.g.scroll_max_step, units))
        self._scroll_accum -= units
        return [Action(ActionType.SCROLL, amount=units)]

    def _finish_pinch(self) -> None:
        self.state = GestureState.IDLE
        self._away_count = 0
        self._reset_candidate()

    def _move(self, lm: np.ndarray) -> Action:
        x, y = self._filter.update(*self._screen_point(lm, INDEX_TIP))
        self._cursor = (x, y)
        return Action(ActionType.MOVE, x, y)

    def _track_candidate(self, intent: Intent, t_ms: int) -> None:
        if intent is self._candidate:
            self._candidate_count += 1
        else:
            self._candidate = intent
            self._candidate_count = 1
            self._candidate_start_ms = t_ms

    def _reset_candidate(self) -> None:
        self._candidate = Intent.NONE
        self._candidate_count = 0

    def _screen_point(self, lm: np.ndarray, idx: int) -> tuple[float, float]:
        return map_to_screen(float(lm[idx][0]), float(lm[idx][1]), self.c.margin)

    @staticmethod
    def _pinch_mid(lm: np.ndarray) -> tuple[float, float]:
        return (
            float(lm[THUMB_TIP][0] + lm[INDEX_TIP][0]) / 2,
            float(lm[THUMB_TIP][1] + lm[INDEX_TIP][1]) / 2,
        )

    @staticmethod
    def _scroll_y(lm: np.ndarray) -> float:
        return float(lm[INDEX_TIP][1] + lm[MIDDLE_TIP][1]) / 2
