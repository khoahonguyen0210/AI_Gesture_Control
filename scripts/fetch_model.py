"""Download the MediaPipe hand landmark model once. Run: python scripts/fetch_model.py"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
DEST = Path(__file__).resolve().parent.parent / "models" / "hand_landmarker.task"


def main() -> int:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists() and DEST.stat().st_size > 0:
        print(f"Model already present: {DEST}")
    else:
        tmp = DEST.with_suffix(".part")
        print(f"Downloading {URL}")
        try:
            urllib.request.urlretrieve(URL, tmp)  # fixed https URL
        except OSError as exc:
            print(f"Download failed: {exc}", file=sys.stderr)
            return 1
        if tmp.stat().st_size == 0:
            tmp.unlink()
            print("Downloaded file is empty.", file=sys.stderr)
            return 1
        tmp.replace(DEST)
    digest = hashlib.sha256(DEST.read_bytes()).hexdigest()
    print(f"Path: {DEST}\nSize: {DEST.stat().st_size} bytes\nSHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
