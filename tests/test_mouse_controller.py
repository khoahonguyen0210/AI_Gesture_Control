from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from gesture_mouse.config import CursorConfig
from gesture_mouse.errors import InputControlError
from gesture_mouse.gesture_recognizer import Action, ActionType, GestureState
from gesture_mouse.mouse_controller import DryRunBackend, MouseController, PyAutoGuiBackend

A = ActionType


class RecordingBackend:
    def __init__(self, width: int = 1000, height: int = 800) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self._size = (width, height)
        self.fail_on: str | None = None

    def size(self) -> tuple[int, int]:
        return self._size

    def _rec(self, *call: Any) -> None:
        if call[0] == self.fail_on:
            raise RuntimeError("backend broke")
        self.calls.append(call)

    def move_to(self, x: int, y: int) -> None:
        self._rec("move_to", x, y)

    def click(self, button: str) -> None:
        self._rec("click", button)

    def mouse_down(self, button: str) -> None:
        self._rec("mouse_down", button)

    def mouse_up(self, button: str) -> None:
        self._rec("mouse_up", button)

    def scroll(self, amount: int) -> None:
        self._rec("scroll", amount)


def controller() -> tuple[MouseController, RecordingBackend]:
    backend = RecordingBackend()
    return MouseController(backend, CursorConfig()), backend


def test_u_mc_01_release_all_is_idempotent() -> None:
    mc, backend = controller()
    mc.apply(Action(A.DRAG_START, 0.5, 0.5))
    mc.release_all()
    mc.release_all()
    assert backend.calls.count(("mouse_up", "left")) == 1
    assert mc.held_buttons == set()


def test_release_all_with_nothing_held_does_nothing() -> None:
    mc, backend = controller()
    mc.release_all()
    assert backend.calls == []


def test_u_mc_02_dry_run_never_loads_pyautogui(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pyautogui", None)
    backend = DryRunBackend()
    mc = MouseController(backend, CursorConfig())
    for kind in A:
        mc.apply(Action(kind, 0.3, 0.3, amount=1))
    mc.release_all()
    assert backend.counts["mouse_down"] == 1
    assert backend.counts["mouse_up"] == 1


@pytest.mark.parametrize(("x", "y"), [(0, 0), (1, 1), (0, 1), (1, 0), (-5, 9)])
def test_u_mc_03_never_maps_to_a_corner(x: float, y: float) -> None:
    mc, _ = controller()
    px, py = mc.to_pixels(x, y)
    assert 2 <= px <= 1000 - 3
    assert 2 <= py <= 800 - 3


def test_center_maps_to_center() -> None:
    mc, _ = controller()
    assert mc.to_pixels(0.5, 0.5) == (500, 400)


def make_fake_pyautogui() -> types.SimpleNamespace:
    class FailSafeException(Exception):
        pass

    fake = types.SimpleNamespace(FAILSAFE=False, PAUSE=0.1, FailSafeException=FailSafeException)
    fake.released = []

    def corner_check() -> None:
        if fake.FAILSAFE:
            raise FailSafeException("corner")

    def move_to(x: int, y: int) -> None:
        corner_check()

    def mouse_up(button: str) -> None:
        corner_check()
        fake.released.append(button)

    fake.moveTo = move_to
    fake.mouseUp = mouse_up
    fake.size = lambda: (1920, 1080)
    return fake


def test_u_mc_04_failsafe_becomes_input_control_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = make_fake_pyautogui()
    monkeypatch.setitem(sys.modules, "pyautogui", fake)
    backend = PyAutoGuiBackend()
    assert fake.FAILSAFE is True
    assert fake.PAUSE == 0
    with pytest.raises(InputControlError, match="failsafe"):
        backend.move_to(0, 0)


def test_release_works_inside_the_failsafe_corner(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = make_fake_pyautogui()
    monkeypatch.setitem(sys.modules, "pyautogui", fake)
    backend = PyAutoGuiBackend()
    backend.mouse_up("left")
    assert fake.released == ["left"]
    assert fake.FAILSAFE is True


def test_u_mc_05_button_state_follows_drag() -> None:
    mc, backend = controller()
    mc.apply(Action(A.DRAG_END))
    assert backend.calls == []
    mc.apply(Action(A.DRAG_START, 0.5, 0.5))
    mc.apply(Action(A.DRAG_START, 0.5, 0.5))
    assert mc.held_buttons == {"left"}
    assert backend.calls.count(("mouse_down", "left")) == 1
    mc.apply(Action(A.DRAG_MOVE, 0.6, 0.5))
    mc.apply(Action(A.DRAG_END))
    assert mc.held_buttons == set()
    assert backend.calls[-1] == ("mouse_up", "left")


def test_click_moves_to_anchor_first() -> None:
    mc, backend = controller()
    mc.apply(Action(A.LEFT_CLICK, 0.5, 0.5))
    assert backend.calls == [("move_to", 500, 400), ("click", "left")]


def test_dead_zone_skips_tiny_moves() -> None:
    mc, backend = controller()
    mc.apply(Action(A.MOVE, 0.5, 0.5))
    mc.apply(Action(A.MOVE, 0.501, 0.501))
    assert backend.calls == [("move_to", 500, 400)]


def test_scroll_and_right_click() -> None:
    mc, backend = controller()
    mc.apply(Action(A.SCROLL, amount=3))
    mc.apply(Action(A.SCROLL, amount=0))
    mc.apply(Action(A.RIGHT_CLICK))
    assert backend.calls == [("scroll", 3), ("click", "right")]


def test_backend_error_becomes_input_control_error() -> None:
    mc, backend = controller()
    backend.fail_on = "click"
    with pytest.raises(InputControlError, match="right_click"):
        mc.apply(Action(A.RIGHT_CLICK))


def test_release_all_survives_backend_error() -> None:
    mc, backend = controller()
    mc.apply(Action(A.DRAG_START, 0.5, 0.5))
    backend.fail_on = "mouse_up"
    mc.release_all()
    assert mc.held_buttons == set()


class DeviceBackend(RecordingBackend):
    def show_state(self, state: GestureState) -> None:
        self._rec("show_state", state)

    def tick(self) -> None:
        self._rec("tick")

    def close(self) -> None:
        self._rec("close")


def test_end_frame_and_close_use_optional_backend_hooks() -> None:
    backend = DeviceBackend()
    mc = MouseController(backend, CursorConfig())
    mc.end_frame(GestureState.POINTING)
    mc.close()
    assert backend.calls == [("show_state", GestureState.POINTING), ("tick",), ("close",)]


def test_end_frame_and_close_skip_missing_hooks() -> None:
    mc, backend = controller()
    mc.end_frame(GestureState.IDLE)
    mc.close()
    assert backend.calls == []
