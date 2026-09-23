from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from typing import Any

import pytest

from fakes import World
from gesture_mouse.__main__ import main
from gesture_mouse.app import (
    EXIT_CAMERA,
    EXIT_INPUT,
    EXIT_INTERRUPT,
    EXIT_MODEL,
    EXIT_OK,
    EXIT_UNEXPECTED,
    run_app,
)
from gesture_mouse.config import AppConfig, TrackerConfig
from gesture_mouse.errors import CameraLostError, CameraOpenError, InputControlError
from gesture_mouse.hand_tracker import HandTracker
from helpers import make_hand

PINCH = make_hand("pinch_left")
POINT = make_hand("point")
MOVING = [make_hand("point", offset=(0.01 * i, 0.0)) for i in range(40)]


Q = ord("q")


def test_i_app_01_normal_run_shuts_down_in_order() -> None:
    world = World([PINCH] * 30, keys={25: Q})
    assert world.run() == EXIT_OK
    assert world.events[:2] == ["camera.open", "tracker.start"]
    assert world.shutdown_events() == [
        ("mouse_up", "left"),
        "tracker.close",
        "camera.release",
        "display.close",
    ]


def test_i_app_02_tracker_crash_still_releases_everything() -> None:
    world = World([PINCH] * 30, fail_at={"detect": (20, RuntimeError("model broke"))})
    assert world.run() == EXIT_UNEXPECTED
    assert world.shutdown_events()[0] == ("mouse_up", "left")
    assert {"tracker.close", "camera.release", "display.close"} <= set(world.events)


def test_i_app_03_camera_lost_mid_drag_releases_button_first() -> None:
    world = World([PINCH] * 30, fail_at={"read": (20, CameraLostError("gone"))})
    assert world.run() == EXIT_CAMERA
    assert ("mouse_down", "left") in world.events
    assert world.shutdown_events()[0] == ("mouse_up", "left")


def test_i_app_04_pause_during_drag_ends_drag() -> None:
    world = World([PINCH] * 40, keys={20: ord("p"), 35: Q})
    assert world.run() == EXIT_OK
    downs = world.events.index(("mouse_down", "left"))
    ups = [i for i, e in enumerate(world.events) if e == ("mouse_up", "left")]
    assert len(ups) == 1 and ups[0] > downs
    assert world.events.index("tracker.close") > ups[0]


def test_i_app_05_dry_run_never_creates_the_real_backend() -> None:
    world = World([POINT] * 10 + [PINCH] * 20, keys={29: Q})
    assert world.run(dry_run=True) == EXIT_OK
    assert not world.backend_made
    assert not [e for e in world.events if isinstance(e, tuple)]


@pytest.mark.parametrize("key", [Q, 27])
def test_i_app_06_quit_keys_stop_the_loop(key: int) -> None:
    world = World([None] * 10, keys={3: key})
    assert world.run() == EXIT_OK
    assert world.frame == 3


def test_closing_the_window_stops_the_loop() -> None:
    world = World([None])
    original = world.display

    def display(title: str) -> Any:
        d = original(title)
        world.window_open = False
        return d

    world.display = display  # type: ignore[method-assign]
    assert world.run() == EXIT_OK
    assert world.frame == 1


def test_i_app_07_exit_codes_for_startup_failures(tmp_path: Any) -> None:
    world = World([], fail_at={"open": (0, CameraOpenError("no camera"))})
    assert world.run() == EXIT_CAMERA
    assert "tracker.start" not in world.events

    cfg = AppConfig(tracker=TrackerConfig(model_path=str(tmp_path / "missing.task")))
    assert run_app(cfg, camera_factory=World([]).camera, tracker_factory=HandTracker) == EXIT_MODEL

    assert main(["--config", str(tmp_path / "nope.toml")]) == 2


def test_failsafe_is_an_emergency_stop_with_clean_exit() -> None:
    world = World(MOVING, fail_at={"move": (5, InputControlError("failsafe"))})
    assert world.run() == EXIT_OK
    assert "camera.release" in world.events


def test_other_input_errors_exit_6() -> None:
    world = World(MOVING, fail_at={"move": (5, RuntimeError("no display"))})
    assert world.run() == EXIT_INPUT


def test_ctrl_c_exits_130_and_cleans_up() -> None:
    world = World([PINCH] * 30, fail_at={"read": (20, KeyboardInterrupt())})
    assert world.run() == EXIT_INTERRUPT
    assert world.shutdown_events()[0] == ("mouse_up", "left")


def test_missing_package_message(caplog: pytest.LogCaptureFixture) -> None:
    def broken_display(title: str) -> Any:
        raise ImportError("No module named 'cv2'", name="cv2")

    world = World([None])
    world.display = broken_display  # type: ignore[method-assign]
    assert world.run() == EXIT_UNEXPECTED
    assert "Missing package cv2" in caplog.text


def test_shutdown_continues_after_a_failing_step(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World([None], keys={1: Q})
    original: Callable[[TrackerConfig], Any] = world.tracker

    def tracker(cfg: TrackerConfig) -> Any:
        t = original(cfg)

        def broken_close() -> None:
            raise RuntimeError("close failed")

        t.close = broken_close
        return t

    world.tracker = tracker  # type: ignore[method-assign]
    assert world.run() == EXIT_OK
    assert "camera.release" in world.events and "display.close" in world.events


def test_start_paused_sends_nothing() -> None:
    from dataclasses import replace

    cfg = AppConfig()
    cfg = replace(cfg, control=replace(cfg.control, start_paused=True))
    world = World([POINT] * 10, keys={9: Q})
    assert world.run(cfg) == EXIT_OK
    assert not [e for e in world.events if isinstance(e, tuple)]


def test_importing_the_app_loads_no_hardware_library() -> None:
    code = (
        "import sys, gesture_mouse.app, gesture_mouse.__main__;"
        "print([m for m in ('cv2','mediapipe','pyautogui','serial') if m in sys.modules])"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"


def test_max_frames_stops_the_loop() -> None:
    world = World([POINT] * 20)
    assert world.run(max_frames=7) == EXIT_OK
    assert world.frame == 7


def test_max_frames_must_be_positive(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--max-frames", "0"]) == 2
    assert "--max-frames" in capsys.readouterr().err


def test_serial_and_dry_run_cannot_be_combined(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--serial", "COM99", "--dry-run"]) == 2
    assert "--serial and --dry-run" in capsys.readouterr().err
