"""Error handling tests: one per error condition, plus the check that releases a held button."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from fakes import World
from gesture_mouse import __main__ as cli
from gesture_mouse.app import (
    EXIT_CAMERA,
    EXIT_CONFIG,
    EXIT_MODEL,
    EXIT_OK,
    EXIT_UNEXPECTED,
    GestureMouseApp,
    run_app,
)
from gesture_mouse.camera import Camera
from gesture_mouse.config import AppConfig, CameraConfig, TrackerConfig
from gesture_mouse.errors import CameraLostError
from gesture_mouse.mouse_controller import MouseController
from helpers import make_hand

PINCH = make_hand("pinch_left")


class DeadCapture:
    def __init__(self, opened: bool) -> None:
        self.opened = opened

    def isOpened(self) -> bool:  # noqa: N802
        return self.opened

    def set(self, prop: int, value: float) -> bool:
        return True

    def get(self, prop: int) -> float:
        return 0.0

    def read(self) -> tuple[bool, None]:
        return False, None

    def release(self) -> None:
        pass


def real_camera_with(cap: DeadCapture) -> Any:
    def factory(cfg: CameraConfig) -> Camera:
        cfg = CameraConfig(index=cfg.index, backend="msmf", open_timeout_ms=50)
        return Camera(cfg, capture_factory=lambda index, api: cap)

    return factory


def run_with_camera(world: World, factory: Any) -> int:
    return run_app(
        AppConfig(),
        camera_factory=factory,
        tracker_factory=world.tracker,
        backend_factory=world.backend,
        display_factory=world.display,
        draw=lambda *args: None,
    )


@pytest.fixture(autouse=True)
def fake_cv2(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    monkeypatch.setitem(sys.modules, "cv2", types.SimpleNamespace(CAP_DSHOW=700, CAP_MSMF=1400))


def test_i_err_01_camera_not_found(caplog: pytest.LogCaptureFixture) -> None:
    world = World([])
    assert run_with_camera(world, real_camera_with(DeadCapture(opened=False))) == EXIT_CAMERA
    assert "--camera" in caplog.text
    assert not [e for e in world.events if isinstance(e, tuple)]


def test_i_err_02_camera_busy(caplog: pytest.LogCaptureFixture) -> None:
    world = World([])
    assert run_with_camera(world, real_camera_with(DeadCapture(opened=True))) == EXIT_CAMERA
    assert "another application" in caplog.text.lower()


def test_i_err_03_permission_hint(caplog: pytest.LogCaptureFixture) -> None:
    world = World([])
    run_with_camera(world, real_camera_with(DeadCapture(opened=True)))
    assert "privacy settings" in caplog.text


def test_i_err_04_camera_lost_releases_button_first() -> None:
    world = World([PINCH] * 30, fail_at={"read": (20, CameraLostError("gone"))})
    assert world.run() == EXIT_CAMERA
    assert world.shutdown_events()[0] == ("mouse_up", "left")


def test_i_err_05_missing_model_exits_4_without_mouse(tmp_path: Path) -> None:
    world = World([])
    cfg = AppConfig(tracker=TrackerConfig(model_path=str(tmp_path / "missing.task")))
    from gesture_mouse.hand_tracker import HandTracker

    code = run_app(
        cfg,
        camera_factory=world.camera,
        tracker_factory=HandTracker,
        backend_factory=world.backend,
        display_factory=world.display,
    )
    assert code == EXIT_MODEL
    assert not world.backend_made
    assert "camera.open" not in world.events


def test_i_err_06_missing_package(caplog: pytest.LogCaptureFixture) -> None:
    def no_pyautogui() -> Any:
        raise ImportError("No module named 'pyautogui'", name="pyautogui")

    world = World([])
    code = run_app(
        AppConfig(),
        camera_factory=world.camera,
        tracker_factory=world.tracker,
        backend_factory=no_pyautogui,
        display_factory=world.display,
    )
    assert code == EXIT_UNEXPECTED
    assert "Missing package pyautogui" in caplog.text
    assert "pip install" in caplog.text


def test_i_err_07_invalid_config_never_opens_camera(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    started: list[bool] = []
    monkeypatch.setattr(cli, "run_app", lambda *a, **k: started.append(True) or 0)
    bad = tmp_path / "bad.toml"
    bad.write_text("[gesture]\npinch_off = 0.1\nwiggle = 1\n", encoding="utf-8")
    assert cli.main(["--config", str(bad)]) == EXIT_CONFIG
    err = capsys.readouterr().err
    assert "pinch_off" in err and "wiggle" in err
    assert started == []


def test_i_err_08_unexpected_error_releases_everything() -> None:
    world = World([PINCH] * 30, fail_at={"detect": (20, ValueError("bad frame"))})
    assert world.run() == EXIT_UNEXPECTED
    assert world.shutdown_events() == [
        ("mouse_up", "left"),
        "tracker.close",
        "camera.release",
        "display.close",
    ]


def test_watchdog_releases_button_when_hand_is_gone() -> None:
    world = World([PINCH] * 15 + [None] * 20, keys={34: ord("q")})
    cfg = AppConfig()
    cam = world.camera(cfg.camera)
    tracker = world.tracker(cfg.tracker)
    mouse = MouseController(world.backend(), cfg.cursor)
    app = GestureMouseApp(
        cfg,
        cam,
        tracker,
        mouse,
        world.display(""),
        draw=lambda *a: None,
        mirror=lambda frame: frame[:, ::-1],
    )
    app.run()
    assert ("mouse_down", "left") in world.events
    assert ("mouse_up", "left") in world.events
    assert mouse.held_buttons == set()

    mouse.held_buttons.add("left")
    for _ in range(cfg.gesture.lost_hand_grace_frames + 1):
        app._watchdog(None)
    assert mouse.held_buttons == set()


def test_failsafe_stop_is_not_an_error() -> None:
    from gesture_mouse.errors import InputControlError

    moving = [make_hand("point", offset=(0.01 * i, 0.0)) for i in range(40)]
    world = World(moving, fail_at={"move": (6, InputControlError("failsafe"))})
    assert world.run() == EXIT_OK
