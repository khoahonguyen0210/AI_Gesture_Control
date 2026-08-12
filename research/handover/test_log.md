# Test Log

Machine for all entries unless stated: Lenovo ThinkPad X1 Yoga, Windows 11 Pro 10.0.26200, Python 3.12.10 in `.venv`.

## Executed

| Date | Phase | Command or procedure | Result |
|---|---|---|---|
| 2026-10-09 | 0 | `python -m pip install -e ".[dev]"` then `python -m pip check` | Pass. "No broken requirements found." |
| 2026-10-09 | 0 | Import check for cv2, numpy, mediapipe, pyautogui | Pass. 5.0.0, 2.5.3, 1.1.0, 0.9.54 |
| 2026-10-09 | 0 | Tasks API import (`vision.HandLandmarker`, `vision.RunningMode`) | Pass. Gate for Phase 1 met. |
| 2026-10-09 | 0 | `python scripts/fetch_model.py` | Pass. 7,819,105 bytes, SHA-256 recorded in the audit |
| 2026-10-09 | 1 | `python -m pytest -q` | 18 passed |
| 2026-10-09 | 1 | `ruff check .`, `ruff format --check .`, `mypy src` | Pass, after one `ruff format` fix |
| 2026-10-09 | 1 | `python -m gesture_mouse --version` | Printed `gesture-mouse 0.1.0` |
| 2026-10-09 | 1 | `python -m gesture_mouse --config does_not_exist.toml` | Readable error, exit code 2 |
| 2026-10-09 | 2 | `python -m pytest -q` | 91 passed (U-CFG, U-GEO-01..06, U-GR-01..15, U-MC-01..05, extra cases) |
| 2026-10-09 | 2 | `python -m pytest --cov=gesture_mouse --cov-report=term-missing` | geometry 100%, gesture_recognizer 99%, mouse_controller 94% |
| 2026-10-09 | 2 | Import purity check (test `test_recognizer_imports_no_hardware_library`) | Pass. Prints `[]` |
| 2026-10-09 | 2 | `ruff check .`, `ruff format --check .`, `mypy src` | Pass |
| 2026-10-09 | R | Shallow clones of the three references; `rev-parse HEAD` | Pass. Hashes match the dossier |
| 2026-10-09 | R | `git ls-files \| grep -i test` in each reference | kinivi and Virtual-Mouse: none. mediapipe-samples: Android tests only, none for the Python example |
| 2026-10-09 | R | kinivi: `pip install --dry-run "mediapipe==0.8.1" ...` (Python 3.12) | Fail: "No matching distribution found for mediapipe==0.8.1" |
| 2026-10-09 | R | Virtual-Mouse: `pip install -r requirements.txt`, `pip check`, legacy `Hands()` start | Pass. numpy 2.4.4, mediapipe 0.10.14; `cv2` reports 5.0.0 because of the duplicate OpenCV install |
| 2026-10-09 | R | `git check-ignore research/reference_repos research/envs` | Both ignored |
| 2026-10-09 | 3 | `python -m pytest -q` | 102 passed, 1 deselected (hardware). U-CAM-01..08 pass |
| 2026-10-09 | 3 | `python -m pytest -q -m hardware` (real camera opens, reads, releases twice) | 1 passed |
| 2026-10-09 | 3 | M-01: `python scripts/list_cameras.py --backend auto|dshow|msmf` | Pass. Camera 0 works at 640x480 with every backend; indices 1-4 report "Could not open camera" |
| 2026-10-09 | 3 | M-02: six open-read-release cycles in a row in one process | Pass. Each reopen succeeded right after the previous release |
| 2026-10-09 | 3 | Camera open time, camera 0 (three runs each, ms) | auto (OpenCV default, MSMF): 14817, 7510, 8244. dshow: 2380, 1864, 2339. msmf: 7822, 6951, 7205. Driver reports 640x480 at 30 fps |

## Planned

| ID | Procedure | Status |
|---|---|---|
| R-VM | Run Virtual-Mouse with the safety steps in Execution Handbook Section 8.1 and record webcam behavior | Planned (owner to run). Its failsafe is off, so it was not run by the agent. |

## Blockers

None.

## Assumptions

| ID | Date | Assumption | How to confirm |
|---|---|---|---|
| A-1 | 2026-10-09 | The built-in camera is index 0 | Confirmed by `python scripts/list_cameras.py` (Phase 3) |
