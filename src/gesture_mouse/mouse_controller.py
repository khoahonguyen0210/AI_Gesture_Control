"""Turn recognizer actions into mouse events through a swappable backend."""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Protocol

from gesture_mouse.config import CursorConfig
from gesture_mouse.errors import InputControlError
from gesture_mouse.geometry import apply_dead_zone
from gesture_mouse.gesture_recognizer import Action, ActionType, GestureState

log = logging.getLogger(__name__)


class MouseBackend(Protocol):
    def size(self) -> tuple[int, int]: ...
    def move_to(self, x: int, y: int) -> None: ...
    def click(self, button: str) -> None: ...
    def mouse_down(self, button: str) -> None: ...
    def mouse_up(self, button: str) -> None: ...
    def scroll(self, amount: int) -> None: ...


class PyAutoGuiBackend:
    """Real mouse. The PyAutoGUI corner failsafe stays on."""

    def __init__(self) -> None:
        import pyautogui

        self._pg: Any = pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0

    def _call(self, name: str, *args: Any, **kwargs: Any) -> None:
        try:
            getattr(self._pg, name)(*args, **kwargs)
        except self._pg.FailSafeException as exc:
            raise InputControlError("failsafe") from exc

    def size(self) -> tuple[int, int]:
        w, h = self._pg.size()
        return int(w), int(h)

    def move_to(self, x: int, y: int) -> None:
        self._call("moveTo", x, y)

    def click(self, button: str) -> None:
        self._call("click", button=button)

    def mouse_down(self, button: str) -> None:
        self._call("mouseDown", button=button)

    def mouse_up(self, button: str) -> None:
        # Releasing never moves the cursor, so it must work even in a failsafe corner.
        previous = self._pg.FAILSAFE
        self._pg.FAILSAFE = False
        try:
            self._pg.mouseUp(button=button)
        finally:
            self._pg.FAILSAFE = previous

    def scroll(self, amount: int) -> None:
        self._call("scroll", amount)


class DryRunBackend:
    """Records actions without touching the real mouse."""

    def __init__(self, width: int = 1920, height: int = 1080) -> None:
        self._size = (width, height)
        self.counts: Counter[str] = Counter()

    def _note(self, name: str, *args: object) -> None:
        self.counts[name] += 1
        log.debug("dry run: %s %s", name, args)

    def size(self) -> tuple[int, int]:
        return self._size

    def move_to(self, x: int, y: int) -> None:
        self._note("move_to", x, y)

    def click(self, button: str) -> None:
        self._note("click", button)

    def mouse_down(self, button: str) -> None:
        self._note("mouse_down", button)

    def mouse_up(self, button: str) -> None:
        self._note("mouse_up", button)

    def scroll(self, amount: int) -> None:
        self._note("scroll", amount)


class MouseController:
    def __init__(self, backend: MouseBackend, cfg: CursorConfig) -> None:
        self.backend = backend
        self.cfg = cfg
        self.held_buttons: set[str] = set()
        self._last_px: tuple[int, int] | None = None
        self._screen = backend.size()

    def to_pixels(self, x: float, y: float) -> tuple[int, int]:
        """Normalized point to pixels, kept away from the screen edges and failsafe corners."""
        w, h = self._screen
        m = self.cfg.screen_edge_margin_px
        px = round(x * (w - 1))
        py = round(y * (h - 1))
        return min(max(px, m), w - 1 - m), min(max(py, m), h - 1 - m)

    def apply(self, action: Action) -> None:
        try:
            self._apply(action)
        except InputControlError:
            raise
        except Exception as exc:
            raise InputControlError(f"mouse action {action.type.value} failed: {exc}") from exc

    def _apply(self, action: Action) -> None:
        kind = action.type
        if kind in (ActionType.MOVE, ActionType.DRAG_MOVE):
            self._move(action, use_dead_zone=True)
        elif kind is ActionType.LEFT_CLICK:
            self._move(action, use_dead_zone=False)
            self.backend.click("left")
        elif kind is ActionType.RIGHT_CLICK:
            self.backend.click("right")
        elif kind is ActionType.DRAG_START:
            self._move(action, use_dead_zone=False)
            if "left" not in self.held_buttons:
                self.backend.mouse_down("left")
                self.held_buttons.add("left")
        elif kind is ActionType.DRAG_END:
            if "left" in self.held_buttons:
                self.held_buttons.discard("left")
                self.backend.mouse_up("left")
        elif kind is ActionType.SCROLL and action.amount:
            self.backend.scroll(action.amount)

    def _move(self, action: Action, use_dead_zone: bool) -> None:
        if action.x is None or action.y is None:
            return
        target = self.to_pixels(action.x, action.y)
        if use_dead_zone:
            target = apply_dead_zone(self._last_px, target, self.cfg.dead_zone_px)
        if target != self._last_px:
            self.backend.move_to(*target)
            self._last_px = target

    def release_all(self) -> None:
        """Release every held button. Safe to call any number of times."""
        for button in sorted(self.held_buttons):
            self.held_buttons.discard(button)
            try:
                self.backend.mouse_up(button)
            except Exception:
                log.exception("Could not release the %s mouse button", button)
        backend_release = getattr(self.backend, "release_all", None)
        if callable(backend_release):
            try:
                backend_release()
            except Exception:
                log.exception("Could not send release-all to the mouse backend")

    def end_frame(self, state: GestureState) -> None:
        """Once per frame. A backend that supports it shows the state and sends keep-alives."""
        show_state = getattr(self.backend, "show_state", None)
        if callable(show_state):
            show_state(state)
        tick = getattr(self.backend, "tick", None)
        if callable(tick):
            tick()

    def close(self) -> None:
        backend_close = getattr(self.backend, "close", None)
        if callable(backend_close):
            backend_close()
