"""Webcam capture with a first-frame timeout, failure counting, and safe release."""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Callable
from types import TracebackType
from typing import Any

import numpy as np

from gesture_mouse.config import CameraConfig
from gesture_mouse.errors import CameraLostError, CameraOpenError, ConfigError

log = logging.getLogger(__name__)

CaptureFactory = Callable[[int, int | None], Any]

# OpenCV property IDs: CAP_PROP_FRAME_WIDTH, CAP_PROP_FRAME_HEIGHT, CAP_PROP_FPS.
PROPS = {"width": 3, "height": 4, "fps": 5}
BACKEND_NAMES = {"auto": None, "dshow": "CAP_DSHOW", "msmf": "CAP_MSMF"}
READ_RETRY_S = 0.01


def now_ms() -> int:
    return int(time.perf_counter() * 1000)


def opencv_capture(index: int, api: int | None) -> Any:
    import cv2

    return cv2.VideoCapture(index) if api is None else cv2.VideoCapture(index, api)


def backend_api(name: str, platform: str = sys.platform) -> int | None:
    """Map a backend name to an OpenCV API constant. None means OpenCV's default.

    "auto" picks DirectShow on Windows, which opened the camera fastest in our tests.
    """
    if name not in BACKEND_NAMES:
        raise ConfigError(f"unknown camera backend {name!r}")
    if name == "auto" and platform == "win32":
        name = "dshow"
    attr = BACKEND_NAMES[name]
    if attr is None:
        return None
    import cv2

    return int(getattr(cv2, attr))


def _good(ok: bool, frame: Any) -> bool:
    return bool(ok) and frame is not None and getattr(frame, "size", 0) > 0


class Camera:
    def __init__(
        self,
        cfg: CameraConfig,
        capture_factory: CaptureFactory | None = None,
        clock_ms: Callable[[], int] = now_ms,
    ) -> None:
        self.cfg = cfg
        self._factory = capture_factory or opencv_capture
        self._clock = clock_ms
        self._cap: Any = None
        self._first_frame: np.ndarray | None = None
        self._failures = 0
        self._last_ts = -1
        self.reported: dict[str, float] = {}
        self.open_ms: int | None = None

    def open(self) -> None:
        """Open the device and wait for a first frame. Raises CameraOpenError."""
        cfg = self.cfg
        api = backend_api(cfg.backend)
        start = self._clock()
        cap = self._factory(cfg.index, api)
        if cap is None or not cap.isOpened():
            self._release_cap(cap)
            raise CameraOpenError(
                f"Could not open camera {cfg.index}. Close other apps that may be using it, "
                "try another index with --camera (python scripts/list_cameras.py lists them), "
                "and check that camera access is allowed in the system privacy settings."
            )
        self._cap = cap
        for key, value in (("width", cfg.width), ("height", cfg.height), ("fps", cfg.fps)):
            cap.set(PROPS[key], value)
        self.reported = {key: float(cap.get(prop)) for key, prop in PROPS.items()}

        frame = self._wait_first_frame(start)
        if frame is None:
            self.release()
            raise CameraOpenError(
                f"Camera {cfg.index} opened but sent no frame within {cfg.open_timeout_ms} ms. "
                "Another application may be using the camera, or camera access may be "
                "turned off in the system privacy settings."
            )
        self._first_frame = frame
        self.open_ms = self._clock() - start
        log.info(
            "Camera %d opened in %d ms (backend %s); driver reports %gx%g at %g fps",
            cfg.index,
            self.open_ms,
            cfg.backend,
            self.reported["width"],
            self.reported["height"],
            self.reported["fps"],
        )

    def _wait_first_frame(self, start: int) -> np.ndarray | None:
        while True:
            ok, frame = self._cap.read()
            if _good(ok, frame):
                return np.asarray(frame)
            if self._clock() - start >= self.cfg.open_timeout_ms:
                return None
            time.sleep(READ_RETRY_S)

    def read(self) -> tuple[np.ndarray, int]:
        """Return (BGR frame, timestamp ms). Raises CameraLostError after too many failures."""
        if self._cap is None:
            raise CameraLostError("The camera is not open.")
        if self._first_frame is not None:
            frame, self._first_frame = self._first_frame, None
            return frame, self._stamp()
        while True:
            ok, frame = self._cap.read()
            if _good(ok, frame):
                self._failures = 0
                return np.asarray(frame), self._stamp()
            self._failures += 1
            log.debug("Camera read failed (%d in a row)", self._failures)
            if self._failures >= self.cfg.max_consecutive_failures:
                raise CameraLostError(
                    f"Camera {self.cfg.index} stopped sending frames "
                    f"({self._failures} failed reads in a row)."
                )
            time.sleep(READ_RETRY_S)

    def _stamp(self) -> int:
        ts = max(self._clock(), self._last_ts + 1)
        self._last_ts = ts
        return ts

    def release(self) -> None:
        """Free the device. Safe to call any number of times."""
        cap, self._cap = self._cap, None
        self._first_frame = None
        self._release_cap(cap)

    @staticmethod
    def _release_cap(cap: Any) -> None:
        if cap is None:
            return
        try:
            cap.release()
        except Exception:
            log.exception("Error while releasing the camera")

    def __enter__(self) -> Camera:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()
