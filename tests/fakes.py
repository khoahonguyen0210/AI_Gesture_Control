"""Scripted fakes for app-level tests. They share one event list."""

from __future__ import annotations

from typing import Any

import numpy as np

from gesture_mouse.app import run_app
from gesture_mouse.config import AppConfig, CameraConfig, TrackerConfig
from gesture_mouse.gesture_recognizer import HandObservation

FRAME = np.zeros((48, 64, 3), dtype=np.uint8)
MAX_FRAMES = 500


class World:
    """Scripted fakes that share one event list."""

    def __init__(
        self,
        hands: list[HandObservation | None],
        keys: dict[int, int] | None = None,
        fail_at: dict[str, tuple[int, BaseException]] | None = None,
    ) -> None:
        self.hands = hands
        self.keys = keys or {}
        self.fail_at = fail_at or {}
        self.events: list[Any] = []
        self.frame = 0
        self.window_open = True
        self.backend_made = False

    def _maybe_fail(self, where: str) -> None:
        if where in self.fail_at and self.fail_at[where][0] == self.frame:
            raise self.fail_at[where][1]

    def camera(self, cfg: CameraConfig) -> Any:
        world = self

        class Cam:
            def open(self) -> None:
                world._maybe_fail("open")
                world.events.append("camera.open")

            def read(self) -> tuple[np.ndarray, int]:
                world.frame += 1
                assert world.frame < MAX_FRAMES, "test loop did not stop"
                world._maybe_fail("read")
                return FRAME.copy(), world.frame * 33

            def release(self) -> None:
                world.events.append("camera.release")

        return Cam()

    def tracker(self, cfg: TrackerConfig) -> Any:
        world = self

        class Tracker:
            def start(self) -> None:
                world.events.append("tracker.start")

            def detect(self, frame: np.ndarray, ts: int) -> HandObservation | None:
                world._maybe_fail("detect")
                i = min(world.frame - 1, len(world.hands) - 1)
                return world.hands[i] if world.hands else None

            def close(self) -> None:
                world.events.append("tracker.close")

        return Tracker()

    def backend(self) -> Any:
        world = self
        world.backend_made = True

        class Backend:
            def size(self) -> tuple[int, int]:
                return (1000, 800)

            def move_to(self, x: int, y: int) -> None:
                world._maybe_fail("move")
                world.events.append(("move_to", x, y))

            def click(self, button: str) -> None:
                world.events.append(("click", button))

            def mouse_down(self, button: str) -> None:
                world.events.append(("mouse_down", button))

            def mouse_up(self, button: str) -> None:
                world.events.append(("mouse_up", button))

            def scroll(self, amount: int) -> None:
                world.events.append(("scroll", amount))

        return Backend()

    def display(self, title: str) -> Any:
        world = self

        class Display:
            def show(self, frame: np.ndarray) -> None:
                pass

            def poll_key(self) -> int:
                return world.keys.get(world.frame, -1)

            def is_open(self) -> bool:
                return world.window_open

            def close(self) -> None:
                world.events.append("display.close")

        return Display()

    def run(
        self, cfg: AppConfig | None = None, dry_run: bool = False, max_frames: int | None = None
    ) -> int:
        return run_app(
            cfg or AppConfig(),
            dry_run,
            camera_factory=self.camera,
            tracker_factory=self.tracker,
            backend_factory=self.backend,
            display_factory=self.display,
            draw=lambda *args: None,
            max_frames=max_frames,
            mirror=lambda frame: np.ascontiguousarray(frame[:, ::-1]),
        )

    def shutdown_events(self) -> list[Any]:
        names = ("mouse_up", "tracker.close", "camera.release", "display.close")
        return [e for e in self.events if (e[0] if isinstance(e, tuple) else e) in names]
