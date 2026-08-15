"""Record labeled hand landmarks (never images) for tuning and evaluation.

Run: python scripts/record_landmarks.py --note "desk lamp, 50 cm, right hand"
Keys: 1-6 or 0 choose the label, space starts or stops recording, q or Esc quits.
Each recorded frame with a hand becomes one JSON line in output/recordings/.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import cv2

from gesture_mouse.camera import Camera
from gesture_mouse.config import load_config
from gesture_mouse.errors import GestureMouseError
from gesture_mouse.hand_tracker import HandTracker
from gesture_mouse.overlay import RED, WHITE, draw_landmarks, draw_text

LABELS = {
    "0": "other",
    "1": "point",
    "2": "left_pinch",
    "3": "right_pinch",
    "4": "two_finger",
    "5": "open_palm",
    "6": "fist",
}
OUT_DIR = Path(__file__).resolve().parent.parent / "output" / "recordings"
WINDOW = "Record landmarks"


def main() -> int:
    parser = argparse.ArgumentParser(description="Record labeled hand landmarks.")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--camera", type=int)
    parser.add_argument("--note", default="", help="conditions: light, distance, which hand")
    args = parser.parse_args()

    overrides = {"camera": {"index": args.camera}} if args.camera is not None else {}
    try:
        cfg = load_config(args.config, overrides)
        tracker = HandTracker(cfg.tracker)
    except GestureMouseError as exc:
        print(exc, file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    label_key, recording, saved = "0", False, 0
    cam = Camera(cfg.camera)
    try:
        cam.open()
        with path.open("w", encoding="utf-8") as out:
            meta = {"labels": LABELS, "note": args.note, "camera": cfg.camera.index}
            out.write(json.dumps({"meta": meta}) + "\n")
            while True:
                frame, t_ms = cam.read()
                frame = cv2.flip(frame, 1)
                obs = tracker.detect(frame, t_ms)
                if obs is not None:
                    draw_landmarks(frame, obs.landmarks)
                    if recording:
                        row = {
                            "t_ms": t_ms,
                            "label": LABELS[label_key],
                            "landmarks": [[round(v, 5) for v in p] for p in obs.landmarks],
                        }
                        out.write(json.dumps(row) + "\n")
                        saved += 1
                status = f"REC {saved}" if recording else f"stopped ({saved} saved)"
                draw_text(frame, f"label: {LABELS[label_key]}", (10, 30))
                draw_text(frame, status, (10, 60), RED if recording else WHITE)
                draw_text(frame, "1-6/0 label, space record, q quit", (10, 470), scale=0.5)
                cv2.imshow(WINDOW, frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == ord(" "):
                    recording = not recording
                elif chr(key) in LABELS:
                    label_key = chr(key)
    except GestureMouseError as exc:
        print(exc, file=sys.stderr)
        return 3
    finally:
        tracker.close()
        cam.release()
        cv2.destroyAllWindows()
    print(f"Saved {saved} frames to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
