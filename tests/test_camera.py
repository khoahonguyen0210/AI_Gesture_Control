from __future__ import annotations

import dataclasses
import sys
import types
from typing import Any

import numpy as np
import pytest

from gesture_mouse.camera import PROPS, Camera, backend_api
from gesture_mouse.config import CameraConfig
from gesture_mouse.errors import CameraLostError, CameraOpenError, ConfigError

FRAME = np.zeros((4, 6, 3), dtype=np.uint8)


@pytest.fixture(autouse=True)
def fake_cv2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "cv2", types.SimpleNamespace(CAP_DSHOW=700, CAP_MSMF=1400))


class FakeCapture:
    def __init__(self, opened: bool = True, reads: list[bool] | None = None) -> None:
        self.opened = opened
        self.reads = list(reads or [])
        self.props: dict[int, float] = {}
        self.release_count = 0

    def isOpened(self) -> bool:  # noqa: N802
        return self.opened

    def set(self, prop: int, value: float) -> bool:
        self.props[prop] = value
        return True

    def get(self, prop: int) -> float:
        return self.props.get(prop, 0.0)

    def read(self) -> tuple[bool, Any]:
        ok = self.reads.pop(0) if self.reads else True
        return (True, FRAME.copy()) if ok else (False, None)

    def release(self) -> None:
        self.release_count += 1


class Clock:
    def __init__(self, step: int = 10) -> None:
        self.t = 0
        self.step = step

    def __call__(self) -> int:
        self.t += self.step
        return self.t


def camera(cap: FakeCapture, **cfg: Any) -> Camera:
    config = dataclasses.replace(CameraConfig(), **cfg)
    return Camera(config, capture_factory=lambda index, api: cap, clock_ms=Clock())


def test_u_cam_01_open_sets_properties_and_gets_first_frame() -> None:
    cap = FakeCapture()
    cam = camera(cap)
    cam.open()
    assert cap.props[PROPS["width"]] == 640
    assert cap.props[PROPS["height"]] == 480
    assert cap.props[PROPS["fps"]] == 30
    assert cam.reported == {"width": 640.0, "height": 480.0, "fps": 30.0}
    frame, ts = cam.read()
    assert frame.shape == FRAME.shape
    assert ts > 0
    cam.release()


def test_u_cam_02_not_opened_raises() -> None:
    cap = FakeCapture(opened=False)
    with pytest.raises(CameraOpenError, match="Could not open camera 0"):
        camera(cap).open()
    assert cap.release_count == 1


def test_u_cam_03_no_frame_within_timeout_raises() -> None:
    cap = FakeCapture(reads=[False] * 1000)
    with pytest.raises(CameraOpenError, match="(?i)another application"):
        camera(cap, open_timeout_ms=100).open()
    assert cap.release_count == 1


def test_u_cam_04_transient_failures_recover() -> None:
    cap = FakeCapture()
    cam = camera(cap, max_consecutive_failures=5)
    cam.open()
    cam.read()
    cap.reads = [False, False, False, True, False, False, False, True]
    cam.read()
    cam.read()


def test_u_cam_05_too_many_failures_raises_camera_lost() -> None:
    cap = FakeCapture()
    cam = camera(cap, max_consecutive_failures=3)
    cam.open()
    cam.read()
    cap.reads = [False] * 3
    with pytest.raises(CameraLostError, match="3 failed reads"):
        cam.read()


def test_u_cam_06_release_is_safe_twice_and_before_open() -> None:
    cap = FakeCapture()
    cam = camera(cap)
    cam.release()
    cam.open()
    cam.release()
    cam.release()
    assert cap.release_count == 1
    with pytest.raises(CameraLostError):
        cam.read()


def test_u_cam_07_context_manager_releases_on_exception() -> None:
    cap = FakeCapture()
    with pytest.raises(RuntimeError), camera(cap):
        raise RuntimeError("boom")
    assert cap.release_count == 1


def test_u_cam_08_timestamps_strictly_increase() -> None:
    cap = FakeCapture()
    cam = Camera(CameraConfig(), capture_factory=lambda i, a: cap, clock_ms=lambda: 1000)
    cam.open()
    stamps = [cam.read()[1] for _ in range(5)]
    assert stamps == sorted(set(stamps))
    assert len(stamps) == 5


def test_capture_factory_gets_index() -> None:
    seen: list[tuple[int, int | None]] = []

    def factory(index: int, api: int | None) -> FakeCapture:
        seen.append((index, api))
        return FakeCapture()

    Camera(CameraConfig(index=2, backend="msmf"), capture_factory=factory).open()
    assert seen == [(2, 1400)]


def test_auto_backend_is_dshow_on_windows_only() -> None:
    assert backend_api("auto", "win32") == 700
    assert backend_api("auto", "linux") is None
    assert backend_api("dshow", "linux") == 700


def test_unknown_backend_rejected() -> None:
    with pytest.raises(ConfigError):
        backend_api("v4l9")


@pytest.mark.hardware
def test_real_camera_opens_and_releases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, "cv2")
    cam = Camera(CameraConfig())
    cam.open()
    frame, _ = cam.read()
    assert frame.ndim == 3
    cam.release()
    cam.release()
