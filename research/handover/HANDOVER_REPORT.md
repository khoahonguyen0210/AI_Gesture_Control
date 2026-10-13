# Handover Report

Written on 2026-10-09 and updated on 2026-10-10. Every claim in this report points to an entry in [`test_log.md`](test_log.md) or to a file in `research/repo-audit/`. Anything that was not run is marked "Not run".

## 1. Summary

Gesture Mouse is a Python desktop app that runs on your own computer. With one hand in front of a laptop webcam, you can move the mouse, click, right click, drag, and scroll. It finds 21 points on your hand with MediaPipe's pretrained hand model, and it turns those points into mouse actions with simple distance rules. There is no trained gesture model.

All automated tests and code checks pass, and the camera and model work on the target laptop. The tests that need a person in front of the webcam are listed in section 5 for the owner to run.

## 2. Environment

| Item | Value |
|---|---|
| Machine | Lenovo ThinkPad X1 Yoga (21CEX50400), i7-1260P, 16 GB RAM |
| OS | Windows 11 Pro 10.0.26200, display scaled to 150% |
| Python | 3.12.10, 64-bit |
| Packages needed to run | mediapipe 1.1.0, opencv-contrib-python 5.0.0.93, numpy 2.5.3, pyautogui 0.9.54 |
| Packages for development | pytest 9.1.1, pytest-cov 7.1.0, ruff 0.17.0, mypy 2.4.0, build 1.6.1, pyserial 3.5 |
| Optional packages | pyserial 3.5 (`.[serial]`, for `--serial`) |
| Firmware tools | PlatformIO 6.2.0 in its own environment, and Wokwi for VS Code |
| Exact versions | `research/repo-audit/requirements.lock.txt` |

## 3. How to install, start, and test

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

## 4. Goals and whether they are met

| # | Goal | Status | Evidence |
|---|---|---|---|
| 1 | The app starts after the documented setup | Met | Clean-environment run (test log, Final checks) |
| 2 | The webcam opens and is released cleanly | Met | M-01, M-02, and the hardware test (test log, Camera) |
| 3 | A visible hand produces hand points | Not run | M-04 needs a hand in front of the camera |
| 4 | The cursor follows the index fingertip | Not run | M-05. The gesture rules and the mapping pass their unit tests |
| 5 | Left click, right click, drag, and scroll work | Partly met | The unit and integration tests pass. M-06 to M-09 have not been run |
| 6 | A short pinch and a long pinch are told apart, with no repeated clicks | Partly met | The pinch unit tests pass. M-06 and M-07 have not been run |
| 7 | Nothing happens by mistake with no hand, an unclear gesture, no camera, or a failed start | Partly met | The unit tests, the 8 error-handling tests, and M-03 pass. M-11 to M-14 have not been run |
| 8 | Pause, resume, and quit work | Partly met | The app-loop tests for pause and quit pass. M-15 to M-17 have not been run |
| 9 | Unit tests cover the mapping, gesture rules, state changes, and click debouncing | Met | 177 tests. Line coverage: geometry 100%, gesture rules 99%, mouse controller 94% |
| 10 | The handover documents setup, start-up, tests, limits, and results | Met | This report |

## 5. Test results

**Last full run:** 177 passed, 2 hardware tests deselected, 0 failed (see the Wokwi demo entries in `test_log.md`). `check_all.py --all` passed 8 of 8 checks, including the 2 hardware tests and the firmware build.

**Manual tests run automatically:** M-01 and M-02 (the camera opens, is released, and opens again), M-03 (a wrong camera index gives a clear error and exit code 3), and M-24 partly (a dry run with the real camera, model, and window, but no hand shown).

**Wokwi checks run by the owner:** W-01 to W-04 (2026-10-10). The owner reported that the app connects and every gesture shows on the board.

**Owner checklist.** These tests need a person at the laptop. Start each one with the preview window in focus, and keep the trackpad within reach. Moving the cursor into any screen corner stops the app.

| ID | Do this | Expect |
|---|---|---|
| M-04 | Run `python -m gesture_mouse --dry-run` and show one hand | Points are drawn on the hand. Moving the hand right moves the points right |
| M-24 | Same run, and try every gesture | The labels change and the mouse does not move |
| M-05 | Run `python -m gesture_mouse` and point with the index finger | The cursor follows |
| M-06 | Pinch the thumb and index finger briefly | One left click on release |
| M-07 | Hold the pinch, move, then open | A drag, then a release |
| M-08 | Pinch the thumb and middle finger | One right click, and no repeat while held |
| M-09 | Raise the index and middle fingers and move the hand up and down | The page scrolls the same way |
| M-14 | Keep your hands out of view for 30 s | Nothing happens |
| M-22 | Show an open palm, then a fist | Nothing happens |
| M-15, M-16 | Press `p` while pointing, then while dragging | Control stops and the drag ends. `p` resumes |
| M-17 | Quit with `q`, then with Esc | The window closes and the camera light turns off |
| M-18 | Push the real cursor into a screen corner | "Emergency stop" and a clean exit |
| M-19 | Press Ctrl+C in the terminal | A clean exit with code 130 |
| M-11 | Open the Windows Camera app, then start Gesture Mouse | An error that mentions another app, and exit code 3 |
| M-12 | Turn off camera access in the Windows privacy settings, start the app, then turn it back on | An error that mentions the privacy settings, and exit code 3 |
| M-20 | Rename `models/hand_landmarker.task`, start the app, then rename it back | A model error with the download command, and exit code 4 |
| M-21 | Start with a config that has `pinch_off = 0.1` and an unknown key | Both errors are listed, and exit code 2 |
| BENCH-2 | Run `python scripts/benchmark.py --note "hand moving"` while going through the gestures | A JSON file in `output/benchmarks/` |
| W-01 | Start the Wokwi simulator (`firmware/wokwi/wokwi.toml`) and wait 5 s | `DEMO` on the screen. The `bad` and `wd` counts rise during the demo |
| W-02 | Run `python -m gesture_mouse --serial rfc2217://localhost:4000` and try every gesture | `LIVE`. The OLED screen and LEDs react as in the README table |
| W-03 | Press `p` during a drag, then `q` | `PAUSED` and the green LED off. After quitting, the demo starts again 5 s later |
| W-04 | Stop the simulator and run the W-02 command | A clear error and exit code 6 |
| W-05 | Run `python scripts/serial_check.py rfc2217://localhost:4000` with the tab visible | 300 of 300 messages answered. Note the reply times |
| EVAL-1 | Record labeled sessions with `python scripts/record_landmarks.py`, then run `scripts/evaluate_gestures.py` | Tables in `output/evaluation/` |

## 6. Performance results

These are delays of the software pipeline, measured on the machine above on 2026-10-09. The laptop was plugged in, on the Balanced power plan, in evening room light, at 640x480, with no hand in view and the preview window off. They are not the full delay from hand movement to screen.

| Median ms | run-01 DirectShow | run-02 MSMF | run-03 MSMF + OpenCV mirror (current code) |
|---|---|---|---|
| capture | 48.34 | 8.53 | 10.69 |
| preprocess | 3.73 | 3.08 | 0.25 |
| inference | 46.20 | 37.94 | 44.54 |
| total | 100.27 | 56.21 | 58.24 |
| achieved frames per second | 9.8 | 19.47 | 16.41 |

Each run was 2000 frames with 0 failed reads. The DirectShow camera path gave only 9.9 frames per second, so the app now uses MSMF, which gives 30. Inference speed changed between runs, and that is the main difference between run-02 and run-03. Camera open time is now about 3 to 4 s. The details, the ideas that were tested, and the profile are in `test_log.md` (Speed investigation). The run with a hand in view was not done.

## 7. Gesture accuracy

Not measured. It needs labeled recordings of a real hand (EVAL-1). The scripts are ready and were tested on made-up data, which only shows that they run.

## 8. What was learned from the reference projects

- **google-ai-edge/mediapipe-samples** (`9cabe32b`, Apache-2.0): read, but not run, because the Python example is a notebook for still images only. Decision: write our own version. Nothing was copied, so there are no obligations.
- **kinivi/hand-gesture-recognition-mediapipe** (`0e737bb8`, Apache-2.0): read. The install failed on Python 3.12 ("No matching distribution found for mediapipe==0.8.1"). Decision: reference only, and its models and data are rejected. Nothing was copied.
- **Rounak7721/Virtual-Mouse** (`495b2933`, MIT): read and installed in its own environment. It was not run, because it turns off the PyAutoGUI emergency stop. Decision: reference only. Its gesture set, disabled emergency stop, `xrandr` code, and second input library are rejected. Nothing was copied.

Nothing is copied, so the repository needs no third-party notice file.

## 9. Dependencies and licenses

| Package | Version | License |
|---|---|---|
| mediapipe | 1.1.0 | Apache-2.0 |
| opencv-contrib-python | 5.0.0.93 | Apache-2.0 |
| numpy | 2.5.3 | BSD-3-Clause and others |
| pyautogui | 0.9.54 | BSD |
| pyserial (optional) | 3.5 | BSD-3-Clause |
| pytest, pytest-cov, ruff, mypy | see section 2 | MIT |

The tools and libraries for the Wokwi demo are listed in `research/repo-audit/license_and_dependency_audit.md`. None of them are copied into the repository.

Open question: the guides that were read do not say whether `hand_landmarker.task` may be redistributed. The model is downloaded at setup and never committed.

## 10. What each skill area shows

| Skill area | Status | Evidence | Limit |
|---|---|---|---|
| Python software engineering | Tested | The package and `pyproject.toml`. pytest, ruff, and mypy pass | One mid-size app |
| Computer vision and hand tracking | Implemented | `hand_tracker.py`. The real model runs on real frames | The quality of the hand points on a real hand is not checked (M-04). The model is pretrained, and nothing was trained |
| Gesture recognition | Tested (automated) | `geometry.py`, `gesture_recognizer.py`, and their unit tests | Rule-based, with no evaluation on a real hand yet |
| Real-time frame processing | Tested | Benchmark runs 01 to 03 | Software time only, one machine, no hand |
| Camera integration | Tested | Fake-camera tests and M-01 to M-03 | The built-in webcam through OpenCV only |
| Operating-system input | Tested (fakes only) | Mouse controller tests and the display scaling check | The real mouse has not been driven yet (M-05 to M-09) |
| State management and safety | Tested | Tests for the gesture states, the hand-lost check, shutdown, and the emergency stop | No formal safety analysis |
| Unit and integration testing | Tested | 177 tests | Behavior on real hardware is covered only by manual tests |
| Debugging and resource management | Tested | Shutdown-order tests and repeated camera opens | No long-running test |
| Performance measurement | Tested | `metrics.py`, `benchmark.py`, runs 01 to 03, cProfile, and three tested ideas | One machine, no hand in view |
| Dependency and license management | Tested | `pip check`, the audit files, and the lock file | Not legal advice. The model's terms are unverified |
| Git and automated checks | Implemented | Git history and `ci.yml` | At the time of writing, GitHub Actions had not run (not pushed yet) |
| Privacy and security | Tested | Search of the code and history (test log, Final checks) | No outside audit |
| Packaging and release | Tested | `python -m build`, the wheel tested in a new environment, and `release.yml` | The release workflow has not run (no tag, not pushed) |
| C (device-side protocol code) | Tested (laptop only) | `firmware/src/`. C tests under MSVC with ASan and under clang with UBSan | No microcontroller, no RTOS or driver work |
| C++ | Tested (laptop only) | `firmware/fuzz/`: the reference parser, the comparison test, and the libFuzzer target. MSVC and Clang builds | Used only for testing, not part of the running app |
| Serial protocol design and safe parsing | Tested (laptop only) | The protocol, parser, `SerialBackend`, a 1,000,000-byte random-input test, a loopback with `device_sim`, and `--serial` with pyserial (COM ports and RFC 2217) with a fake-device test suite | Simulated link. The silence timeout was tested with simulated time only |
| Embedded simulation (ESP32) | Implemented | `firmware/wokwi/`: Arduino sketch, OLED screen and LEDs, and demo mode. It builds with 0 warnings locally and in CI | Simulator only. The run with the app connected is an owner check (W-01 to W-05) |
| Training and evaluating a model | Not started | The condition is not met (no real-hand evaluation yet) | None |
| Containerized training | Not started | Depends on training a model | None |
| Terraform and cloud | Not applicable | Left out on purpose | None |
| Firmware and electronics | Partly (simulated) | The Wokwi ESP32 sketch runs the project's C code | No real board, circuit, or USB mouse function |

## 11. Known limits and open items

- Done so far: packaging, speed work, the serial protocol and C code (tested on the laptop only), C++ comparison testing (owner request), and a Wokwi ESP32 demo with the `--serial` option (owner request, simulator only). Training a classifier waits for a real-hand evaluation. Running on a real board is not started, because it needs a purchase.
- The manual webcam and real-mouse tests in section 5 have not been run.
- The app runs at about 16 to 19 frames per second on this laptop in evening light with no hand, and the model takes most of each frame.
- The gesture limits are starting values and are not tuned.
- The preview window must be in focus for `p`, `q`, and Esc. Ctrl+C and the screen-corner emergency stop work without focus.
- One main monitor is the supported setup. Other systems, Wayland, and setups with several monitors are untested.
- Gestures need one hand and fine finger control, so they do not suit everyone. Keep the keyboard and trackpad as a fallback.
- Tracking can change with light, distance, and skin tone. No general accuracy is claimed.
- The model's redistribution terms are unverified.

## 12. Suggested next steps

Run the owner checklist, record a few labeled sessions, and tune `pinch_on` and `pinch_off` from them (`evaluate_gestures.py --summarize`). Then evaluate on separate sessions.
