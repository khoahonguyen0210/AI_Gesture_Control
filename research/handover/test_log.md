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
| 2026-10-09 | 6 | `python -m pytest -q` | 139 passed, 2 deselected. I-ERR-01..08 and the watchdog test pass |
| 2026-10-09 | 6 | `ruff check .`, `ruff format --check .`, `mypy src` | Pass |
| 2026-10-09 | 6 | Forbidden-pattern search: `grep -rn -E "shell=True\|os\.system\|subprocess\|eval\(\|exec\(\|requests\|urllib\|socket\|http\.client\|import pickle\|__import__\|importlib\.import_module" src scripts tests` | `src/`: no matches. `urllib` only in `scripts/fetch_model.py` (allowed). `subprocess` only in three tests that run the same interpreter with fixed code, no shell |
| 2026-10-09 | 6 | Display scaling check: `pyautogui.size()` vs Windows screen bounds | Windows is at 150% scaling (1280x800 logical). PyAutoGUI calls `SetProcessDPIAware()` on import and reports 1920x1200 physical pixels, so its coordinates are consistent |
| 2026-10-09 | 7 | `python -m pytest -q` | 145 passed, 2 deselected (adds evaluation-script tests) |
| 2026-10-09 | 7 | `python scripts/evaluate_gestures.py` on a synthetic recording made from the test hands | Script runs and saves JSON. Synthetic data only checks the script; it is not an evaluation result |
| 2026-10-09 | 7 | `python scripts/benchmark.py --frames 2000 --warmup 100 --no-show --output output/benchmarks/run-01-no-hand.json` | See "Benchmark run-01" below |
| 2026-10-09 | 8 | CI steps run locally: `pip check`, `ruff check .`, `ruff format --check .`, `mypy src`, `pytest -q -m "not hardware"` | Pass |
| 2026-10-09 | 8 | Full test suite with `cv2`, `mediapipe`, and `pyautogui` blocked from import | 145 passed, 2 deselected. The suite needs no camera, display, or model |
| 2026-10-09 | 8 | GitHub Actions run | Not run. The project is local only and has not been pushed |
| 2026-10-09 | 8 | Clean environment: new Python 3.12 venv, `pip install -e ".[dev]"`, `pip check`, `fetch_model.py`, `pytest -q`, `ruff check .`, `ruff format --check .`, `mypy src` | All pass. 145 passed, 2 deselected. Installed versions match `requirements.lock.txt` exactly. The model was already present, so the fetch step reused it |
| 2026-10-09 | 8 | Dry-run launch from the clean environment, quitting with Esc after 60 frames | Pass. Exit code 0 |
| 2026-10-09 | 8 | Imports used by `src` and `scripts` | cv2, mediapipe, numpy, pyautogui are all used; no unused dependency |
| 2026-10-09 | 8 | `git ls-files` check for clones, environments, models, output, handbooks | None tracked; all ignored |
| 2026-10-09 | 8 | Search for unfinished-work markers in `src`, `tests`, `scripts`, `config`, `.github` | None |
| 2026-10-09 | 8 | Privacy and security search of tracked files and history: local paths, emails, keys and tokens, image or video writes, network calls | No paths, emails, or keys. No image or video is ever written. Only network call: `scripts/fetch_model.py`. Commit author email will be public if pushed |
| 2026-10-09 | Ext D | `python -m build` | Built `gesture_mouse-0.1.0.tar.gz` and `gesture_mouse-0.1.0-py3-none-any.whl` |
| 2026-10-09 | Ext D | Wheel contents (`zipfile` listing) | 13 package modules plus `licenses/LICENSE` and `licenses/THIRD_PARTY_NOTICES.txt`; no models, data, or records |
| 2026-10-09 | Ext D | sdist contents | First build lacked `tests/helpers.py`, `tests/fakes.py`, `config/default.toml`, and the scripts; fixed with `MANIFEST.in`. Second build: 53 entries including them |
| 2026-10-09 | Ext D | New venv: `pip install dist/*.whl pytest`, `gesture-mouse --version`, `pip check`, `pytest -q` | `gesture-mouse 0.1.0`; package imported from site-packages; no broken requirements; 145 passed, 2 deselected |
| 2026-10-09 | Ext D | Release workflow run | Not run. It runs only on a pushed `v*` tag; no tag was made (needs owner approval) |

### Benchmark run-01 (no hand)

Software pipeline latency measured on the machine in `output/benchmarks/machine.txt` (ThinkPad X1 Yoga, i7-1260P, plugged in, Balanced power plan, evening room light, DirectShow, 640x480) on 2026-10-09. No hand was in view; the preview window was off, so the display stage is near zero. Not end-to-end latency.

| Stage | Median ms | 95th percentile ms | Max ms |
|---|---|---|---|
| capture | 48.34 | 69.51 | 93.18 |
| preprocess (mirror) | 3.73 | 4.60 | 110.52 |
| inference | 46.20 | 62.23 | 1041.68 |
| recognize | 0.01 | 0.02 | 0.06 |
| dispatch | 0.00 | 0.01 | 0.05 |
| draw | 0.46 | 0.71 | 2.40 |
| display | 0.00 | 0.00 | 0.01 |
| total | 100.27 | 120.32 | 1052.34 |

2000 frames in 204.0 s, so 9.8 FPS achieved, against 30 FPS reported by the driver. Failed reads: 0 (0%). Frames with a hand: 0. The capture stage waits for the camera; a likely cause (a hypothesis, not tested) is longer exposure in low light. The run with a hand moving through the gestures still needs the owner.

## Planned

| ID | Procedure | Status |
|---|---|---|
| M-04 | Show one hand: 21 points drawn in the right places after mirroring; no hand gives no points; two hands use only one; hand at the frame edge; lower light | Planned (owner to run) |
| M-24 | `python -m gesture_mouse --dry-run` with a hand: labels and landmarks follow the hand; the mouse does not move | Planned (owner to run) |
| M-05 to M-09 | `python -m gesture_mouse`: point moves the cursor; short pinch clicks once; held pinch drags and releases; thumb-middle pinch right-clicks once; two-finger pose scrolls in the expected direction | Planned (owner to run) |
| M-15, M-16 | Press `p` while pointing and while dragging: control stops, the drag ends; press `p` again to resume | Planned (owner to run) |
| M-10 to M-13 | Camera unavailable (`--camera 9`, done as M-03), camera in use (open the Windows Camera app first), camera permission off, camera lost mid-run | M-10 executed as M-03. M-11 to M-13: Planned (owner to run). M-13 is covered by I-ERR-04 |
| M-18 | Move the physical cursor into a screen corner while running: "Emergency stop" and a clean exit | Planned (owner to run) |
| M-19 | Ctrl+C in the terminal: clean exit with code 130 | Planned (owner to run) |
| M-20 | Rename `models/hand_landmarker.task`, start the app: model error with the fetch command, exit 4; then restore the file | Planned (owner to run). Covered by I-ERR-05 |
| M-21 | Config with `pinch_off = 0.1` and an unknown key: all errors listed, exit 2, camera never opened | Planned (owner to run). Covered by I-ERR-07 |
| M-17 | Quit with `q`, then with Esc: window closes, camera light turns off, no button held | Planned (owner to run) |
| REC-1 | `python scripts/record_landmarks.py --note "..."`: record a few hundred labeled frames | Planned (owner to run) |
| BENCH-2 | `python scripts/benchmark.py --frames 2000 --warmup 100 --note "hand moving through gestures"` | Planned (owner to run) |
| EVAL-1 | Record several labeled sessions, then `python scripts/evaluate_gestures.py --input "output/recordings/*.jsonl"`; keep tuning and reporting sessions apart | Planned (owner to run) |
| R-VM | Run Virtual-Mouse with the safety steps in Execution Handbook Section 8.1 and record webcam behavior | Planned (owner to run). Its failsafe is off, so it was not run by the agent. |

## Blockers

| ID | Date | Description | What is blocked | What continues |
|---|---|---|---|---|
| B-1 | 2026-10-09 | The agent cannot hold a hand in front of the webcam | Manual rows M-04 to M-09, M-11, M-12, M-14 to M-24, BENCH-2, EVAL-1 | Everything automated; owner checklist in `HANDOVER_REPORT.md` |

## Assumptions

| ID | Date | Assumption | How to confirm |
|---|---|---|---|
| A-1 | 2026-10-09 | The built-in camera is index 0 | Confirmed by `python scripts/list_cameras.py` (Phase 3) |

### Extension E: profiling-driven optimization

Same machine as run-01 (`output/benchmarks/machine.txt`), 2026-10-09, evening room light, no hand in view, preview window off. Software pipeline latency, not end-to-end latency.

**Measurements before any change**

| Check | Result |
|---|---|
| Camera only, DirectShow, 300 frames | 9.9 frames/s (median gap 96.5 ms). The pipeline in run-01 (9.8 FPS) was limited by the camera, not the code |
| Camera only, 150 frames each | MSMF 30.1 frames/s; DirectShow 9.9 frames/s |
| DirectShow asked for MJPG or YUY2 | The camera stays in YUY2 at 9.9 frames/s |
| Mirror and color conversion, 640x480, 500 runs | NumPy mirror 1.700 ms vs `cv2.flip` 0.135 ms; NumPy BGR to RGB 1.484 ms vs `cv2.cvtColor` 0.615 ms |

**Hypotheses, written before each change, and results**

| ID | Change | Success criterion | Result |
|---|---|---|---|
| E-H1 | Use MSMF (OpenCV default) instead of DirectShow on Windows | Achieved FPS at least 15 and total median at most 70 ms | Met. run-02: 19.47 FPS, total median 56.21 ms (run-01: 9.8 FPS, 100.27 ms) |
| E-H2 | `cv2.flip` and `cv2.cvtColor` instead of NumPy copies | Mirror stage median at most 1 ms | Met. run-03: 0.25 ms (run-02: 3.08 ms). Total FPS in run-03 was 16.41, because inference was slower in that run (median 44.54 vs 37.94 ms); this is run-to-run variation and is not credited to or blamed on the change |
| E-H3 | Set camera properties only when the driver reports a different value | MSMF open time at most 5 s | Met. 3277, 3968, 2954 ms (before: 6951 to 14817 ms). Camera still 30.2 frames/s at 640x480 |
| E-H4 | Rewrite a stage in C++ or Rust | A pure-Python stage is the bottleneck | Rejected. cProfile of 300 dry-run frames (`python -m cProfile -o output/profile.out -m gesture_mouse --dry-run --max-frames 300`): MediaPipe native inference 16.2 s, camera property setting 9.1 s (startup), camera reads 4.9 s, `waitKey` 1.8 s. Project Python code is not near the top |

| Stage (median ms) | run-01 DirectShow | run-02 MSMF | run-03 MSMF + OpenCV mirror |
|---|---|---|---|
| capture | 48.34 | 8.53 | 10.69 |
| preprocess | 3.73 | 3.08 | 0.25 |
| inference | 46.20 | 37.94 | 44.54 |
| total | 100.27 | 56.21 | 58.24 |
| total, 95th percentile | 120.32 | 88.45 | 96.89 |
| achieved FPS | 9.8 | 19.47 | 16.41 |

Tests after the changes: `python -m pytest -q` 149 passed, 2 deselected; `ruff`, `ruff format --check`, `mypy src` pass; the suite also passes with `cv2`, `mediapipe`, and `pyautogui` blocked.
