"""Time each stage of the real pipeline. The mouse is never moved (dry-run backend).

Run: python scripts/benchmark.py --frames 2000 --warmup 100 --note "hand moving, lamp on"
Results are software pipeline times only, not end-to-end latency.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime
from importlib import metadata
from pathlib import Path

import numpy as np

from gesture_mouse.app import GestureMouseApp, OpenCvDisplay
from gesture_mouse.camera import Camera
from gesture_mouse.config import load_config
from gesture_mouse.errors import GestureMouseError
from gesture_mouse.gesture_recognizer import HandObservation
from gesture_mouse.hand_tracker import HandTracker
from gesture_mouse.metrics import Recorder
from gesture_mouse.mouse_controller import DryRunBackend, MouseController

OUT_DIR = Path(__file__).resolve().parent.parent / "output" / "benchmarks"
PACKAGES = ("mediapipe", "opencv-contrib-python", "numpy", "pyautogui", "gesture-mouse")


class NoDisplay:
    def show(self, frame: np.ndarray) -> None:
        pass

    def poll_key(self) -> int:
        return -1

    def is_open(self) -> bool:
        return True

    def close(self) -> None:
        pass


class CountingTracker:
    """Wraps the tracker to count frames with a hand."""

    def __init__(self, tracker: HandTracker) -> None:
        self.tracker = tracker
        self.hand_frames = 0

    def start(self) -> None:
        self.tracker.start()

    def detect(self, frame: np.ndarray, timestamp_ms: int) -> HandObservation | None:
        obs = self.tracker.detect(frame, timestamp_ms)
        self.hand_frames += obs is not None
        return obs

    def close(self) -> None:
        self.tracker.close()


def versions() -> dict[str, str]:
    out = {}
    for name in PACKAGES:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = "not installed"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Time each stage of the real pipeline.")
    parser.add_argument("--frames", type=int, default=2000)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--no-show", action="store_true", help="do not open the preview window")
    parser.add_argument("--note", default="", help="conditions: hand or no hand, light, power")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
        tracker = CountingTracker(HandTracker(cfg.tracker))
    except GestureMouseError as exc:
        print(exc, file=sys.stderr)
        return 2

    camera = Camera(cfg.camera)
    display = None
    mouse = MouseController(DryRunBackend(), cfg.cursor)
    try:
        camera.open()
        tracker.start()
        display = NoDisplay() if args.no_show else OpenCvDisplay("Benchmark (dry run)")
        app = GestureMouseApp(cfg, camera, tracker, mouse, display, dry_run=True)
        for _ in range(args.warmup):
            app.step()
        app.metrics = Recorder()
        failed_before = camera.failed_reads
        tracker.hand_frames = 0
        start = time.perf_counter()
        for _ in range(args.frames):
            app.step()
            if not app.running:
                break
        elapsed = time.perf_counter() - start
        frames = len(app.metrics.samples["total"])
        failed = camera.failed_reads - failed_before
        hand_frames = tracker.hand_frames
    except GestureMouseError as exc:
        print(exc, file=sys.stderr)
        return 3
    finally:
        mouse.release_all()
        tracker.close()
        camera.release()
        if display is not None:
            display.close()

    stages = {
        stage: {k: round(v, 3) for k, v in summary.items()}
        for stage, summary in app.metrics.summary().items()
    }
    result = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "note": args.note,
        "measure": "software pipeline time per frame, in ms (not end-to-end latency)",
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": sys.version.split()[0],
            "packages": versions(),
        },
        "camera": {"backend": cfg.camera.backend, "reported": camera.reported},
        "frames": frames,
        "warmup": args.warmup,
        "frames_with_hand": hand_frames,
        "elapsed_s": round(elapsed, 3),
        "achieved_fps": round(frames / elapsed, 2) if elapsed > 0 else 0.0,
        "failed_reads": failed,
        "failed_read_pct": round(100 * failed / (frames + failed), 3) if frames else 0.0,
        "stages_ms": stages,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = args.output or OUT_DIR / f"run-{datetime.now():%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"{frames} frames in {elapsed:.1f} s = {result['achieved_fps']} FPS")
    print(f"frames with a hand: {hand_frames}; failed reads: {failed}")
    print(f"{'stage':<11}{'median':>9}{'p95':>9}{'max':>9}  (ms)")
    for stage, s in stages.items():
        print(f"{stage:<11}{s['median']:>9.2f}{s['p95']:>9.2f}{s['max']:>9.2f}")
    print(f"Saved {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
