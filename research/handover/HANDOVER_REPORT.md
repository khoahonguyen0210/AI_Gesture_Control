# Handover Report

Date: 2026-10-09, updated 2026-10-10. Every claim here points to an entry in `test_log.md` or to a file in `research/repo-audit/`. Anything that was not run is marked "Not run".

## 1. Summary

Gesture Mouse is a local Python desktop app that lets one hand in front of a laptop webcam move the mouse, click, right-click, drag, and scroll. It finds 21 hand landmarks with MediaPipe's pretrained hand model and turns them into mouse actions with rule-based geometry (no trained gesture classifier). All automated tests and static checks pass, the camera and model work on the target laptop, and the tests that need a person at the webcam are listed below for the owner to run.

## 2. Environment

| Item | Value |
|---|---|
| Machine | Lenovo ThinkPad X1 Yoga (21CEX50400), i7-1260P, 16 GB RAM |
| OS | Windows 11 Pro 10.0.26200, display scaled to 150% |
| Python | 3.12.10, 64-bit |
| Runtime packages | mediapipe 1.1.0, opencv-contrib-python 5.0.0.93, numpy 2.5.3, pyautogui 0.9.54 |
| Dev packages | pytest 9.1.1, pytest-cov 7.1.0, ruff 0.17.0, mypy 2.4.0, build 1.6.1, pyserial 3.5 |
| Optional packages | pyserial 3.5 (`.[serial]`, for `--serial`) |
| Firmware tools | PlatformIO 6.2.0 in its own environment; Wokwi for VS Code |
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

`python -m pytest -q -m hardware` runs the two tests that use the real camera and model. `python scripts/check_all.py --all` runs every automated check, the camera tests, and the firmware build, then prints a summary.

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
| AC-09 | Unit tests cover mapping, classification, state changes, click debouncing | Met | 176 tests; geometry 100%, recognizer 99%, mouse controller 94% line coverage |
| AC-10 | Handover documents setup, launch, tests, limits, and results | Met | This report |

## 5. Test results

Last full run: see the Wokwi demo entries in `test_log.md` (176 passed, 2 hardware tests deselected, 0 failed). `check_all.py --all` passed 8 of 8 checks, including the 2 hardware tests and the firmware build.

**Manual tests run by the agent:** M-01, M-02 (camera opens, releases, reopens), M-03 (wrong camera index gives a clear error and exit code 3), M-24 partly (dry run with the real camera, model, and window; no hand shown).

**Wokwi checks run by the owner:** W-01 to W-04 (2026-10-10). The owner reported that the app connects and every gesture shows on the board.

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
| W-01 | Start the Wokwi simulator (`firmware/wokwi/wokwi.toml`) and wait 5 s | `DEMO` on the screen; the `bad` and `wd` counts rise during the demo |
| W-02 | `python -m gesture_mouse --serial rfc2217://localhost:4000`, try every gesture | `LIVE`; the OLED and LEDs react as in the README table |
| W-03 | Press `p` during a drag, then `q` | `PAUSED` and the green LED off; after quitting, the demo starts again 5 s later |
| W-04 | Stop the simulator, run the W-02 command | Clear error; exit code 6 |
| W-05 | `python scripts/serial_check.py rfc2217://localhost:4000` with the tab visible | 300 of 300 frames answered; note the reply times |
| EVAL-1 | Record labeled sessions with `python scripts/record_landmarks.py`, then run `scripts/evaluate_gestures.py` | Tables in `output/evaluation/` |

## 6. Performance results

Software pipeline latency, measured on the machine above on 2026-10-09 (plugged in, Balanced power plan, evening room light, 640x480, no hand in view, preview window off). These are not end-to-end latency figures.

| Median ms | run-01 DirectShow | run-02 MSMF | run-03 MSMF + OpenCV mirror (current code) |
|---|---|---|---|
| capture | 48.34 | 8.53 | 10.69 |
| preprocess | 3.73 | 3.08 | 0.25 |
| inference | 46.20 | 37.94 | 44.54 |
| total | 100.27 | 56.21 | 58.24 |
| achieved FPS | 9.8 | 19.47 | 16.41 |

Each run was 2000 frames with 0 failed reads. The DirectShow camera path delivered only 9.9 frames/s, so the app now uses MSMF (30 frames/s). Inference speed varied between runs; run-02 and run-03 differ mainly there. Camera open time is now about 3-4 s. Details, hypotheses, and the profile are in `test_log.md` (Extension E). The run with a hand in view was not collected.

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
| pyserial (optional) | 3.5 | BSD-3-Clause |
| pytest, pytest-cov, ruff, mypy | see section 2 | MIT |

The Wokwi demo's build tools and libraries are listed in `research/repo-audit/license_and_dependency_audit.md`. None are copied into the repository.

Open question: the redistribution terms of `hand_landmarker.task` are not stated in the guides that were read. The model is downloaded at setup and never committed.

## 10. Skill-to-evidence matrix

| Skill area | Status | Evidence | Limit |
|---|---|---|---|
| Python software engineering | Tested | Package, `pyproject.toml`; pytest, ruff, mypy pass | One mid-size app |
| Computer vision and hand landmarks | Implemented | `hand_tracker.py`; real model runs on real frames | Landmark quality on a real hand not checked (M-04); pretrained model, none trained |
| Gesture interpretation | Tested (automated) | `geometry.py`, `gesture_recognizer.py`; unit tests | Rule-based; no real-hand evaluation yet |
| Real-time frame processing | Tested | Benchmark runs 01-03 | Software pipeline time only; one machine; no hand |
| Camera integration | Tested | Fake-capture tests; M-01 to M-03 | Built-in webcam through OpenCV only |
| Operating-system input | Tested (fakes only) | Mouse controller tests; DPI check | Real mouse not driven yet (M-05 to M-09) |
| State management and safety | Tested | State-machine, watchdog, shutdown, failsafe tests | No formal safety analysis |
| Unit and integration testing | Tested | 176 tests | Hardware behavior only in manual tests |
| Debugging and resource management | Tested | Shutdown-order tests; repeated camera open | No long soak test |
| Performance measurement and engineering | Tested | `metrics.py`, `benchmark.py`, runs 01-03, cProfile, three tested hypotheses | One machine; no hand in view |
| Dependency and license management | Tested | `pip check`, audit files, lock file | Not legal advice; model terms unverified |
| Git and automated checks | Implemented | Git history; `ci.yml`; CI steps pass locally | GitHub Actions has not run (not pushed) |
| Privacy and security | Tested | Search of code and history (test log, Phase 8) | No external audit |
| Packaging and release | Tested | `python -m build`; wheel tested in a new environment; `release.yml` | Release workflow not run (no tag, not pushed) |
| C (device-side protocol code) | Tested (laptop only) | `firmware/src/`; C tests under MSVC with ASan and under clang with UBSan | No microcontroller; no RTOS or driver work |
| C++ | Tested (laptop only) | `firmware/fuzz/`: reference parser, differential test, libFuzzer target; MSVC and Clang builds | Testing role only; not part of the running app |
| Serial protocol design and safe parsing | Tested (laptop only) | Protocol, parser, `SerialBackend`, 1,000,000-byte random-input test, loopback with `device_sim`; `--serial` with pyserial (COM ports and RFC 2217) and a fake-device test suite | Simulated link; watchdog tested with simulated time only |
| Embedded simulation (ESP32) | Implemented | `firmware/wokwi/`: Arduino sketch, OLED and LEDs, demo mode; builds with 0 warnings locally and in CI | Simulator only; the run with the app connected is an owner check (W-01 to W-05) |
| ML training and evaluation | Not started | Gate not met (no real-hand evaluation yet) | — |
| Containerized ML workflow | Not started | Depends on ML training | — |
| Terraform and cloud | Not applicable | Omitted by decision | — |
| Firmware and electronics | Partly (simulated) | The Wokwi ESP32 sketch runs the project's C code | No real board, circuit, or USB HID |

## 11. Known limitations and open items

- Extensions done: D (packaging), E (profiling), A1 (serial protocol and C code, tested on the laptop only), C++ differential fuzzing (owner request), and a Wokwi ESP32 demo with the `--serial` option (owner request, simulator only). B and C wait for the evaluation gate. Appendix A (real board) is not started because it needs a purchase.

- The manual webcam and real-mouse tests in section 5 have not been run.
- About 16-19 FPS on this laptop in evening light without a hand; the model takes most of each frame.
- Gesture thresholds are uncalibrated starting values.
- The preview window must have focus for `p`, `q`, and Esc. Ctrl+C and the screen-corner failsafe work without focus.
- One primary monitor is the supported target. Other platforms, Wayland, and multi-monitor setups are untested.
- Gestures need one hand and fine finger control, so they do not suit everyone. Keep the keyboard and trackpad as a fallback.
- Tracking can vary with lighting, distance, and skin tone; no claim of general accuracy is made.
- The model's redistribution terms are unverified.

## 12. Suggested next steps

Run the owner checklist, record a few labeled sessions, tune `pinch_on` and `pinch_off` from them (`evaluate_gestures.py --summarize`), and then evaluate on separate sessions.
