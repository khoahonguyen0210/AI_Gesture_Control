# License and Dependency Audit

## Project dependencies

Resolved on 2026-10-09 with Python 3.12.10 on Windows 11. `pip check` reported "No broken requirements found." Exact versions of every installed package are in `requirements.lock.txt`. Licenses come from the installed package metadata.

| Package | Version | License | Role |
|---|---|---|---|
| mediapipe | 1.1.0 | Apache-2.0 | Hand landmark model runtime |
| opencv-contrib-python | 5.0.0.93 | Apache-2.0 | Camera, drawing, preview window |
| numpy | 2.5.3 | BSD-3-Clause and others (0BSD, MIT, Zlib, CC0-1.0) | Landmark math |
| pyautogui | 0.9.54 | BSD | Mouse control |
| pytest | 9.1.1 | MIT | Tests (dev) |
| pytest-cov | 7.1.0 | MIT | Coverage (dev) |
| ruff | 0.17.0 | MIT | Lint and format (dev) |
| mypy | 2.4.0 | MIT | Type checks (dev) |

Notes:

- mediapipe 1.1.0 requires `opencv-contrib-python`, `matplotlib`, `sounddevice`, `absl-py`, `flatbuffers`, and `certifi`. The project does not import the last four itself.
- mediapipe 1.1.0 exposes only `Image`, `ImageFormat`, and `tasks` at the top level. The legacy `mediapipe.solutions` API is not present, which matches the plan to use the Tasks API.
- numpy 2.5.3 requires Python 3.12 or newer, so the project requires Python 3.12 or 3.13.

## Hand landmark model

| Item | Value |
|---|---|
| Source | `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task` |
| Fetched by | `python scripts/fetch_model.py` on 2026-10-09 |
| Size | 7,819,105 bytes |
| SHA-256 | `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1` |
| Redistribution terms | Not stated in the guides that were read. Unverified. |
| Decision | Downloaded at setup time; never committed (`models/` and `*.task` are ignored). |
