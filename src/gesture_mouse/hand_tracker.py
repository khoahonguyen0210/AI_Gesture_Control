"""MediaPipe hand landmark tracking (Tasks API, VIDEO mode, one hand)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

from gesture_mouse.config import TrackerConfig
from gesture_mouse.errors import ModelNotFoundError
from gesture_mouse.gesture_recognizer import HandObservation

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FETCH_COMMAND = "python scripts/fetch_model.py"


def resolve_model_path(path: str) -> Path:
    """Use the path as given if it exists; otherwise try it relative to the project folder."""
    p = Path(path)
    if p.is_absolute() or p.exists():
        return p
    fallback = PROJECT_ROOT / p
    return fallback if fallback.exists() else p


def check_model(path: str) -> Path:
    p = resolve_model_path(path)
    if not p.is_file() or p.stat().st_size == 0:
        raise ModelNotFoundError(
            f"Hand model not found or empty: {p}. Download it with: {FETCH_COMMAND}"
        )
    return p


def observation_from_result(result: Any) -> HandObservation | None:
    """Turn a HandLandmarkerResult into a HandObservation for the first hand, or None."""
    hands = getattr(result, "hand_landmarks", None)
    if not hands:
        return None
    points = np.array([(p.x, p.y, p.z) for p in hands[0]], dtype=float)
    if points.shape != (21, 3):
        return None
    handedness: str | None = None
    score: float | None = None
    categories = getattr(result, "handedness", None)
    if categories and categories[0]:
        handedness = categories[0][0].category_name
        score = float(categories[0][0].score)
    return HandObservation(points, handedness, score)


class HandTracker:
    def __init__(self, cfg: TrackerConfig) -> None:
        self.cfg = cfg
        self.model_path = check_model(cfg.model_path)
        self._landmarker: Any = None
        self._mp: Any = None
        self._cv2: Any = None
        self._last_ts = -1

    def start(self) -> None:
        """Load MediaPipe and the model. Kept apart from __init__ so a missing model fails first."""
        os.environ.setdefault("GLOG_minloglevel", "2")
        import cv2
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision

        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(self.model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=self.cfg.min_hand_detection_confidence,
            min_hand_presence_confidence=self.cfg.min_hand_presence_confidence,
            min_tracking_confidence=self.cfg.min_tracking_confidence,
        )
        self._mp = mp
        self._cv2 = cv2
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        log.info("Hand model loaded from %s", self.model_path)

    def next_timestamp(self, timestamp_ms: int) -> int:
        """MediaPipe needs strictly increasing timestamps."""
        ts = max(int(timestamp_ms), self._last_ts + 1)
        self._last_ts = ts
        return ts

    def detect(self, frame_bgr: np.ndarray, timestamp_ms: int) -> HandObservation | None:
        if self._landmarker is None:
            self.start()
        rgb = self._cv2.cvtColor(frame_bgr, self._cv2.COLOR_BGR2RGB)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, self.next_timestamp(timestamp_ms))
        return observation_from_result(result)

    def close(self) -> None:
        """Free the model. Safe to call any number of times."""
        landmarker, self._landmarker = self._landmarker, None
        if landmarker is not None:
            try:
                landmarker.close()
            except Exception:
                log.exception("Error while closing the hand tracker")
