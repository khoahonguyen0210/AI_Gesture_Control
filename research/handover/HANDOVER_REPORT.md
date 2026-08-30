# Handover Report

Date: 2026-10-09. Every claim here points to an entry in `test_log.md` or to a file in `research/repo-audit/`. Anything that was not run is marked "Not run".

## 1. Summary

Gesture Mouse is a local Python desktop app that lets one hand in front of a laptop webcam move the mouse, click, right-click, drag, and scroll. It finds 21 hand landmarks with MediaPipe's pretrained hand model and turns them into mouse actions with rule-based geometry (no trained gesture classifier). All automated tests and static checks pass, the camera and model work on the target laptop, and the tests that need a person at the webcam are listed below for the owner to run.

## 2. Environment

| Item | Value |
|---|---|
| Machine | Lenovo ThinkPad X1 Yoga (21CEX50400), i7-1260P, 16 GB RAM |
| OS | Windows 11 Pro 10.0.26200, display scaled to 150% |
| Python | 3.12.10, 64-bit |
| Runtime packages | mediapipe 1.1.0, opencv-contrib-python 5.0.0.93, numpy 2.5.3, pyautogui 0.9.54 |
| Dev packages | pytest 9.1.1, pytest-cov 7.1.0, ruff 0.17.0, mypy 2.4.0 |
| Exact versions | `requirements.lock.txt` |

## 3. How to install, launch, and test

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/fetch_model.py
python -m pytest -q
ruff check .
ruff format --check .
mypy src
python -m gesture_mouse --dry-run
python -m gesture_mouse
```

`python -m pytest -q -m hardware` runs the two tests that use the real camera and model.

## 4. Acceptance criteria

| ID | Criterion | Status | Evidence |
|---|---|---|---|
| AC-01 | App starts after the documented setup | Met | Clean-environment run (test log, Phase 8) |
| AC-02 | Webcam opens and releases cleanly | Met | M-01, M-02, hardware test (test log, Phase 3) |
| AC-03 | A visible hand produces landmarks | Not run | M-04 needs a hand in front of the camera |
| AC-04 | Cursor follows the index tip | Not run | M-05; recognizer and mapping pass unit tests |
| AC-05 | Left click, right click, drag, scroll work | Partly met | Unit and integration tests pass; M-06 to M-09 not run |
| AC-06 | Brief and held pinch are told apart; no repeated clicks | Partly met | U-GR-04 to U-GR-08 pass; M-06, M-07 not run |
| AC-07 | No unintended action with no hand, an uncertain gesture, no camera, or a failed start | Partly met | U-GR-01, U-GR-07, U-GR-15, I-ERR-01 to 08, M-03 pass; M-11 to M-14 not run |
| AC-08 | Pause, resume, and exit work | Partly met | I-APP-04, I-APP-06 pass; M-15 to M-17 not run |
| AC-09 | Unit tests cover mapping, classification, state changes, click debouncing | Met | 145 tests; geometry 100%, recognizer 99%, mouse controller 94% line coverage |
| AC-10 | Handover documents setup, launch, tests, limits, and results | Met | This report |

## 5. Test results

Last full run: see the Phase 8 clean-environment entry in `test_log.md` (145 passed, 2 hardware tests deselected, 0 failed). The hardware tests passed separately (2 passed).

**Manual tests run by the agent:** M-01, M-02 (camera opens, releases, reopens), M-03 (wrong camera index gives a clear error and exit code 3), M-24 partly (dry run with the real camera, model, and window; no hand shown).

**Owner checklist.** These need a person at the laptop. Start each one with the preview window in focus, and keep the trackpad within reach. Moving the cursor into any screen corner stops the app.

| ID | Do this | Expect |
|---|---|---|
| M-04 | `python -m gesture_mouse --dry-run`, show one hand | Points drawn on the hand; moving right moves them right |
| M-24 | Same run; try every gesture | Labels change; the mouse does not move |
| M-05 | `python -m gesture_mouse`, point with the index finger | The cursor follows |
| M-06 | Pinch thumb and index briefly | One left click on release |
| M-07 | Hold the pinch, move, then open | Drag, then release |
| M-08 | Pinch thumb and middle finger | One right click, no repeat while held |
| M-09 | Index and middle up, move the hand up and down | The page scrolls the same way |
| M-14 | Keep hands out of view for 30 s | Nothing happens |
| M-22 | Show an open palm, then a fist | Nothing happens |
| M-15, M-16 | Press `p` while pointing, then while dragging | Control stops; the drag ends; `p` resumes |
| M-17 | Quit with `q`, then with Esc | Window closes; camera light turns off |
| M-18 | Push the real cursor into a screen corner | "Emergency stop", clean exit |
| M-19 | Ctrl+C in the terminal | Clean exit, code 130 |
| M-11 | Open the Windows Camera app, then start Gesture Mouse | Error that mentions another app; exit code 3 |
| M-12 | Turn off camera access in Windows privacy settings, start the app, then turn it back on | Error that mentions privacy settings; exit code 3 |
| M-20 | Rename `models/hand_landmarker.task`, start, then rename it back | Model error with the fetch command; exit code 4 |
| M-21 | Start with a config that has `pinch_off = 0.1` and an unknown key | Both errors listed; exit code 2 |
| BENCH-2 | `python scripts/benchmark.py --note "hand moving"` while moving through the gestures | JSON in `output/benchmarks/` |
| EVAL-1 | Record labeled sessions with `python scripts/record_landmarks.py`, then run `scripts/evaluate_gestures.py` | Tables in `output/evaluation/` |

## 6. Performance results

Software pipeline latency, measured on the machine above on 2026-10-09 (plugged in, Balanced power plan, evening room light, DirectShow, 640x480, no hand in view, preview window off). These are not end-to-end latency figures.

| Stage | Median ms | 95th percentile ms | Max ms |
|---|---|---|---|
| capture | 48.34 | 69.51 | 93.18 |
| inference | 46.20 | 62.23 | 1041.68 |
| total | 100.27 | 120.32 | 1052.34 |

2000 frames in 204.0 s: 9.8 FPS achieved, against 30 FPS reported by the driver; 0 failed reads. The full table is in `test_log.md`. The run with a hand in view was not collected.

Camera open time on this laptop (three runs each): DirectShow 1864 to 2380 ms; MSMF 6951 to 7822 ms; OpenCV default 7510 to 14817 ms. So the app uses DirectShow by default on Windows.

## 7. Recognition evaluation

Not collected. It needs labeled recordings of a real hand (EVAL-1). The scripts are ready and tested on synthetic data, which only shows that they run.

## 8. Reference repository outcomes

- **google-ai-edge/mediapipe-samples** (`9cabe32b`, Apache-2.0): inspected; not run (the Python example is an image-only notebook). Decision: Reimplement Independently. Nothing copied, so no obligations.
- **kinivi/hand-gesture-recognition-mediapipe** (`0e737bb8`, Apache-2.0): inspected; install failed on Python 3.12 ("No matching distribution found for mediapipe==0.8.1"). Decision: Reference Only; its models and data are rejected. Nothing copied.
- **Rounak7721/Virtual-Mouse** (`495b2933`, MIT): inspected; installed in its own environment; not run, because it turns off the PyAutoGUI failsafe. Decision: Reference Only; its gesture set, disabled failsafe, `xrandr` code, and second input library are rejected. Nothing copied.

`THIRD_PARTY_NOTICES.txt` says "None at this time."

## 9. Dependencies and licenses

| Package | Version | License |
|---|---|---|
| mediapipe | 1.1.0 | Apache-2.0 |
| opencv-contrib-python | 5.0.0.93 | Apache-2.0 |
| numpy | 2.5.3 | BSD-3-Clause and others |
| pyautogui | 0.9.54 | BSD |
| pytest, pytest-cov, ruff, mypy | see section 2 | MIT |

Open question: the redistribution terms of `hand_landmarker.task` are not stated in the guides that were read. The model is downloaded at setup and never committed.

## 10. Skill-to-evidence matrix

| Skill area | Status | Evidence | Limit |
|---|---|---|---|
| Python software engineering | Tested | Package, `pyproject.toml`; pytest, ruff, mypy pass | One mid-size app |
| Computer vision and hand landmarks | Implemented | `hand_tracker.py`; real model runs on real frames | Landmark quality on a real hand not checked (M-04); pretrained model, none trained |
| Gesture interpretation | Tested (automated) | `geometry.py`, `gesture_recognizer.py`; unit tests | Rule-based; no real-hand evaluation yet |
| Real-time frame processing | Tested | Benchmark run-01 | Software pipeline time only; one machine; no hand |
| Camera integration | Tested | Fake-capture tests; M-01 to M-03 | Built-in webcam through OpenCV only |
| Operating-system input | Tested (fakes only) | Mouse controller tests; DPI check | Real mouse not driven yet (M-05 to M-09) |
| State management and safety | Tested | State-machine, watchdog, shutdown, failsafe tests | No formal safety analysis |
| Unit and integration testing | Tested | 145 tests | Hardware behavior only in manual tests |
| Debugging and resource management | Tested | Shutdown-order tests; repeated camera open | No long soak test |
| Performance measurement | Tested | `metrics.py`, `benchmark.py`, run-01 | One machine, one condition |
| Dependency and license management | Tested | `pip check`, audit files, lock file | Not legal advice; model terms unverified |
| Git and automated checks | Implemented | Git history; `ci.yml`; CI steps pass locally | GitHub Actions has not run (not pushed) |
| Privacy and security | Tested | Search of code and history (test log, Phase 8) | No external audit |
| Terraform and cloud | Not applicable | Omitted by decision | — |
| Firmware and electronics | Not applicable | Out of scope | — |

## 11. Known limitations and open items

- The manual webcam and real-mouse tests in section 5 have not been run.
- About 10 FPS on this laptop in evening light; the camera wait and the model take most of the time.
- Gesture thresholds are uncalibrated starting values.
- The preview window must have focus for `p`, `q`, and Esc. Ctrl+C and the screen-corner failsafe work without focus.
- One primary monitor is the supported target. Other platforms, Wayland, and multi-monitor setups are untested.
- Gestures need one hand and fine finger control, so they do not suit everyone. Keep the keyboard and trackpad as a fallback.
- Tracking can vary with lighting, distance, and skin tone; no claim of general accuracy is made.
- The model's redistribution terms are unverified.

## 12. Suggested next steps

Run the owner checklist, record a few labeled sessions, tune `pinch_on` and `pinch_off` from them (`evaluate_gestures.py --summarize`), and then evaluate on separate sessions.
