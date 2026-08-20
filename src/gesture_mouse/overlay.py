"""Draw landmarks and status text on the preview frame."""

from __future__ import annotations

import numpy as np

from gesture_mouse.gesture_recognizer import HandObservation, RecognizerOutput

HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),
)  # fmt: skip

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (60, 200, 60)
ORANGE = (0, 140, 255)
RED = (40, 40, 220)
FONT_SCALE = 0.6


def to_pixels(landmarks: np.ndarray, width: int, height: int) -> list[tuple[int, int]]:
    return [(int(x * width), int(y * height)) for x, y in landmarks[:, :2]]


def draw_landmarks(frame: np.ndarray, landmarks: np.ndarray) -> None:
    import cv2

    h, w = frame.shape[:2]
    pts = to_pixels(landmarks, w, h)
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], WHITE, 2, cv2.LINE_AA)
    for p in pts:
        cv2.circle(frame, p, 4, GREEN, -1, cv2.LINE_AA)


def draw_text(
    frame: np.ndarray,
    text: str,
    org: tuple[int, int],
    color: tuple[int, int, int] = WHITE,
    scale: float = FONT_SCALE,
) -> None:
    """Text with a dark outline so it stays readable on any background."""
    import cv2

    font = cv2.FONT_HERSHEY_SIMPLEX
    thick = max(1, round(scale * 2))
    cv2.putText(frame, text, org, font, scale, BLACK, thick + 3, cv2.LINE_AA)
    cv2.putText(frame, text, org, font, scale, color, thick, cv2.LINE_AA)


def draw_overlay(
    frame: np.ndarray,
    obs: HandObservation | None,
    out: RecognizerOutput,
    fps: float,
    enabled: bool,
    dry_run: bool,
    show_debug: bool,
    help_text: str,
) -> None:
    """Draw everything the preview shows. Call it after the tracker has used the frame."""
    h, w = frame.shape[:2]
    if obs is not None:
        draw_landmarks(frame, obs.landmarks)
    draw_text(frame, out.label, (10, 40), WHITE, scale=1.1)
    status, color = ("ENABLED", GREEN) if enabled else ("PAUSED", ORANGE)
    draw_text(frame, status, (10, 75), color)
    draw_text(frame, f"{fps:4.1f} FPS", (w - 120, 30))
    if dry_run:
        draw_text(frame, "DRY RUN: mouse is not moved", (10, 105), ORANGE)
    if show_debug and out.debug:
        values = "  ".join(f"{k} {v:.2f}" for k, v in sorted(out.debug.items()))
        draw_text(frame, values, (10, h - 40), scale=0.5)
    draw_text(frame, help_text, (10, h - 12), scale=0.5)
