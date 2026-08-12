"""List webcams that OpenCV can open. Run: python scripts/list_cameras.py [--backend dshow]"""

from __future__ import annotations

import argparse
import dataclasses

from gesture_mouse.camera import Camera
from gesture_mouse.config import CAMERA_BACKENDS, CameraConfig
from gesture_mouse.errors import CameraOpenError

MAX_INDEX = 4
TIMEOUT_MS = 2000


def main() -> int:
    parser = argparse.ArgumentParser(description="List webcams that OpenCV can open.")
    parser.add_argument("--backend", choices=CAMERA_BACKENDS, default="auto")
    args = parser.parse_args()

    for index in range(MAX_INDEX + 1):
        cfg = dataclasses.replace(
            CameraConfig(), index=index, backend=args.backend, open_timeout_ms=TIMEOUT_MS
        )
        cam = Camera(cfg)
        try:
            cam.open()
            size = f"{cam.reported['width']:g}x{cam.reported['height']:g}"
            print(f"Camera {index}: works, {size}, opened in {cam.open_ms} ms")
        except CameraOpenError as exc:
            print(f"Camera {index}: {str(exc).split('. ')[0]}")
        finally:
            cam.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
