"""Main loop: startup order, per-frame pipeline, keys, and guaranteed shutdown."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, Protocol

import numpy as np

from gesture_mouse.camera import Camera
from gesture_mouse.config import AppConfig, CameraConfig, TrackerConfig
from gesture_mouse.errors import (
    CameraLostError,
    CameraOpenError,
    ConfigError,
    InputControlError,
    ModelNotFoundError,
)
from gesture_mouse.gesture_recognizer import GestureRecognizer, HandObservation
from gesture_mouse.hand_tracker import HandTracker
from gesture_mouse.metrics import FpsCounter, Recorder
from gesture_mouse.mouse_controller import (
    DryRunBackend,
    MouseBackend,
    MouseController,
    PyAutoGuiBackend,
)
from gesture_mouse.overlay import draw_overlay

log = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_CAMERA = 3
EXIT_MODEL = 4
EXIT_UNEXPECTED = 5
EXIT_INPUT = 6
EXIT_INTERRUPT = 130

HELP_TEXT = "p: pause   q or Esc: quit   cursor in a screen corner: emergency stop"
METRIC_SAMPLES = 1000


class CameraLike(Protocol):
    def open(self) -> None: ...
    def read(self) -> tuple[np.ndarray, int]: ...
    def release(self) -> None: ...


class TrackerLike(Protocol):
    def start(self) -> None: ...
    def detect(self, frame_bgr: np.ndarray, timestamp_ms: int) -> HandObservation | None: ...
    def close(self) -> None: ...


class Display(Protocol):
    def show(self, frame: np.ndarray) -> None: ...
    def poll_key(self) -> int: ...
    def is_open(self) -> bool: ...
    def close(self) -> None: ...


class OpenCvDisplay:
    def __init__(self, title: str) -> None:
        import cv2

        self._cv2: Any = cv2
        self.title = title
        cv2.namedWindow(title, cv2.WINDOW_AUTOSIZE)

    def show(self, frame: np.ndarray) -> None:
        self._cv2.imshow(self.title, frame)

    def poll_key(self) -> int:
        key = int(self._cv2.waitKey(1))
        return -1 if key < 0 else key & 0xFF

    def is_open(self) -> bool:
        return bool(self._cv2.getWindowProperty(self.title, self._cv2.WND_PROP_VISIBLE) >= 1)

    def close(self) -> None:
        self._cv2.destroyAllWindows()


def key_code(name: str) -> int:
    return 27 if name == "Esc" else ord(name)


class GestureMouseApp:
    def __init__(
        self,
        cfg: AppConfig,
        camera: CameraLike,
        tracker: TrackerLike,
        mouse: MouseController,
        display: Display,
        dry_run: bool = False,
        draw: Callable[..., None] = draw_overlay,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.cfg = cfg
        self.camera = camera
        self.tracker = tracker
        self.mouse = mouse
        self.display = display
        self.dry_run = dry_run
        self.draw = draw
        self.clock = clock
        self.recognizer = GestureRecognizer(cfg.gesture, cfg.cursor)
        self.metrics = Recorder(METRIC_SAMPLES, clock)
        self.fps = FpsCounter()
        self.enabled = not cfg.control.start_paused
        self.running = True
        self.frames = 0
        self._frames_without_hand = 0
        self._pause_code = key_code(cfg.control.pause_key)
        self._quit_codes = {key_code(k) for k in cfg.control.quit_keys}

    def run(self) -> None:
        while self.running:
            self.step()

    def step(self) -> None:
        m = self.metrics
        start = self.clock()
        with m.time("capture"):
            frame, t_ms = self.camera.read()
        with m.time("preprocess"):
            frame = np.ascontiguousarray(frame[:, ::-1])
        with m.time("inference"):
            obs = self.tracker.detect(frame, t_ms)
        with m.time("recognize"):
            out = self.recognizer.update(obs, t_ms, self.enabled)
        with m.time("dispatch"):
            for action in out.actions:
                self.mouse.apply(action)
            self._watchdog(obs)
        fps = self.fps.tick(self.clock())
        with m.time("draw"):
            self.draw(
                frame,
                obs,
                out,
                fps,
                self.enabled,
                self.dry_run,
                self.cfg.ui.show_debug_values,
                HELP_TEXT,
            )
        with m.time("display"):
            self.display.show(frame)
            key = self.display.poll_key()
        m.add("total", (self.clock() - start) * 1000.0)
        self.frames += 1
        self.handle_key(key)
        if self.running and not self.display.is_open():
            log.info("Preview window closed")
            self.running = False

    def _watchdog(self, obs: HandObservation | None) -> None:
        """Second guard, beside the recognizer: never hold a button with no hand in view."""
        self._frames_without_hand = 0 if obs is not None else self._frames_without_hand + 1
        grace = self.cfg.gesture.lost_hand_grace_frames
        if self.mouse.held_buttons and self._frames_without_hand > grace:
            log.warning("No hand for %d frames with a button held; releasing it", grace)
            self.mouse.release_all()

    def handle_key(self, key: int) -> None:
        if key in self._quit_codes:
            self.running = False
        elif key == self._pause_code:
            self.enabled = not self.enabled
            if not self.enabled:
                self.mouse.release_all()
            log.info("Control %s", "enabled" if self.enabled else "paused")


def run_app(
    cfg: AppConfig,
    dry_run: bool = False,
    camera_factory: Callable[[CameraConfig], CameraLike] = Camera,
    tracker_factory: Callable[[TrackerConfig], TrackerLike] = HandTracker,
    backend_factory: Callable[[], MouseBackend] = PyAutoGuiBackend,
    display_factory: Callable[[str], Display] = OpenCvDisplay,
    draw: Callable[..., None] = draw_overlay,
) -> int:
    """Start everything in the required order, run the loop, and always shut down."""
    tracker: TrackerLike | None = None
    mouse: MouseController | None = None
    camera: CameraLike | None = None
    display: Display | None = None
    try:
        tracker = tracker_factory(cfg.tracker)
        backend = DryRunBackend() if dry_run else backend_factory()
        mouse = MouseController(backend, cfg.cursor)
        camera = camera_factory(cfg.camera)
        camera.open()
        tracker.start()
        display = display_factory(cfg.ui.window_title)
        app = GestureMouseApp(cfg, camera, tracker, mouse, display, dry_run, draw)
        log.info("Running%s. %s", " in dry-run mode" if dry_run else "", HELP_TEXT)
        app.run()
        log.info("Stopped after %d frames", app.frames)
        return EXIT_OK
    except ConfigError as exc:
        log.error("%s", exc)
        return EXIT_CONFIG
    except (CameraOpenError, CameraLostError) as exc:
        log.error("%s", exc)
        return EXIT_CAMERA
    except ModelNotFoundError as exc:
        log.error("%s", exc)
        return EXIT_MODEL
    except InputControlError as exc:
        if str(exc) == "failsafe":
            log.warning("Emergency stop: the cursor reached a screen corner.")
            return EXIT_OK
        log.error("Mouse control failed: %s", exc)
        return EXIT_INPUT
    except KeyboardInterrupt:
        log.info("Stopped with Ctrl+C")
        return EXIT_INTERRUPT
    except ImportError as exc:
        log.error(
            "Missing package %s. Install the project with: python -m pip install -e .",
            exc.name or exc,
        )
        return EXIT_UNEXPECTED
    except Exception:
        log.exception("Unexpected error")
        return EXIT_UNEXPECTED
    finally:
        shutdown(mouse, tracker, camera, display)


def shutdown(
    mouse: MouseController | None,
    tracker: TrackerLike | None,
    camera: CameraLike | None,
    display: Display | None,
) -> None:
    """Release the mouse first, then the tracker, camera, and window. One failure skips nothing."""
    steps: list[tuple[str, Callable[[], None] | None]] = [
        ("release mouse buttons", mouse.release_all if mouse else None),
        ("close tracker", tracker.close if tracker else None),
        ("release camera", camera.release if camera else None),
        ("close window", display.close if display else None),
    ]
    for name, step in steps:
        if step is None:
            continue
        try:
            step()
        except Exception:
            log.exception("Could not %s", name)
