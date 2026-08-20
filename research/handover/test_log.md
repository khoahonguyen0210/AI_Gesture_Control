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
| 2026-10-09 | 3 | M-01: `python scripts/list_cameras.py --backend` with auto, dshow, msmf | Pass. Camera 0 works at 640x480 with every backend; indices 1-4 report "Could not open camera" |
| 2026-10-09 | 3 | M-02: six open-read-release cycles in a row in one process | Pass. Each reopen succeeded right after the previous release |
| 2026-10-09 | 3 | Camera open time, camera 0 (three runs each, ms) | auto (OpenCV default, MSMF): 14817, 7510, 8244. dshow: 2380, 1864, 2339. msmf: 7822, 6951, 7205. Driver reports 640x480 at 30 fps |
| 2026-10-09 | 4 | Installed API check: `help(vision.HandLandmarkerOptions)`, `dir(result)` | Names match the handbook: `running_mode`, `num_hands`, three confidence options; result fields `hand_landmarks`, `hand_world_landmarks`, `handedness`. `close()` twice is safe |
| 2026-10-09 | 4 | `python -m pytest -q` | 108 passed, 2 deselected. U-HT-01..05 pass |
| 2026-10-09 | 4 | `python -m pytest -q -m hardware` | 2 passed (real camera; real model on a blank frame) |
| 2026-10-09 | 4 | 90 real camera frames through the real tracker, no window, nothing saved | Ran without errors. 0 frames with a hand (no hand was shown) |
| 2026-10-09 | 4 | `python scripts/record_landmarks.py --config does_not_exist.toml` | Readable error, exit code 2 |
| 2026-10-09 | 5 | `python -m pytest -q` | 129 passed, 2 deselected. I-APP-01..07 and U-MET-01..02 pass |
| 2026-10-09 | 5 | `ruff check .`, `ruff format --check .`, `mypy src` | Pass |
| 2026-10-09 | 5 | M-03: `python -m gesture_mouse --camera 9 --dry-run` | Pass. "Could not open camera 9. Try another index with --camera ..."; exit code 3 |
| 2026-10-09 | 5 | M-24 (partial): `run_app` in dry-run with the real camera, model, and preview window, quitting after 90 frames | Pass. Window opened, ran 90 frames, exit code 0, real mouse backend never created. No hand was shown, so gesture labels were not checked |

## Planned

| ID | Procedure | Status |
|---|---|---|
| M-04 | Show one hand: 21 points drawn in the right places after mirroring; no hand gives no points; two hands use only one; hand at the frame edge; lower light | Planned (owner to run) |
| M-24 | `python -m gesture_mouse --dry-run` with a hand: labels and landmarks follow the hand; the mouse does not move | Planned (owner to run) |
| M-05 to M-09 | `python -m gesture_mouse`: point moves the cursor; short pinch clicks once; held pinch drags and releases; thumb-middle pinch right-clicks once; two-finger pose scrolls in the expected direction | Planned (owner to run) |
| M-15, M-16 | Press `p` while pointing and while dragging: control stops, the drag ends; press `p` again to resume | Planned (owner to run) |
| M-17 | Quit with `q`, then with Esc: window closes, camera light turns off, no button held | Planned (owner to run) |
| REC-1 | `python scripts/record_landmarks.py --note "..."`: record a few hundred labeled frames | Planned (owner to run) |
| R-VM | Run Virtual-Mouse with the safety steps in Execution Handbook Section 8.1 and record webcam behavior | Planned (owner to run). Its failsafe is off, so it was not run by the agent. |

## Blockers

None.

## Assumptions

| ID | Date | Assumption | How to confirm |
|---|---|---|---|
| A-1 | 2026-10-09 | The built-in camera is index 0 | Confirmed by `python scripts/list_cameras.py` (Phase 3) |
