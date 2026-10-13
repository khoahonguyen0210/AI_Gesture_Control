# Test Log

This file lists every check that was run, with its result, and every check that is still waiting for a person.

All entries come from the same machine unless stated otherwise: Lenovo ThinkPad X1 Yoga, Windows 11 Pro 10.0.26200, Python 3.12.10 in `.venv`.

Manual tests have IDs that start with `M-` (for example M-04). They need a person at the laptop. The same IDs are used in the checklist in [`HANDOVER_REPORT.md`](HANDOVER_REPORT.md).

## Checks that were run

| Date | Step | Command or procedure | Result |
|---|---|---|---|
| 2026-10-09 | Setup | `python -m pip install -e ".[dev]"`, then `python -m pip check` | Pass. "No broken requirements found." |
| 2026-10-09 | Setup | Import check for cv2, numpy, mediapipe, and pyautogui | Pass. Versions 5.0.0, 2.5.3, 1.1.0, and 0.9.54 |
| 2026-10-09 | Setup | Import of the Tasks API (`vision.HandLandmarker`, `vision.RunningMode`) | Pass. This was the condition for starting the app code |
| 2026-10-09 | Setup | `python scripts/fetch_model.py` | Pass. 7,819,105 bytes. The SHA-256 is recorded in the license audit |
| 2026-10-09 | Project skeleton | `python -m pytest -q` | 18 passed |
| 2026-10-09 | Project skeleton | `ruff check .`, `ruff format --check .`, `mypy src` | Pass, after one `ruff format` fix |
| 2026-10-09 | Project skeleton | `python -m gesture_mouse --version` | Printed `gesture-mouse 0.1.0` |
| 2026-10-09 | Project skeleton | `python -m gesture_mouse --config does_not_exist.toml` | A readable error and exit code 2 |
| 2026-10-09 | Gesture rules and mouse | `python -m pytest -q` | 91 passed (settings, geometry, gesture rules, and mouse controller tests, plus extra cases) |
| 2026-10-09 | Gesture rules and mouse | `python -m pytest --cov=gesture_mouse --cov-report=term-missing` | Coverage: geometry 100%, gesture_recognizer 99%, mouse_controller 94% |
| 2026-10-09 | Gesture rules and mouse | Import check (test `test_recognizer_imports_no_hardware_library`) | Pass. Prints `[]` |
| 2026-10-09 | Gesture rules and mouse | `ruff check .`, `ruff format --check .`, `mypy src` | Pass |
| 2026-10-09 | Reference repos | Shallow clones of the three reference repositories, then `rev-parse HEAD` | Pass. The hashes match the earlier research |
| 2026-10-09 | Reference repos | `git ls-files \| grep -i test` in each reference | kinivi and Virtual-Mouse: none. mediapipe-samples: Android tests only, none for the Python example |
| 2026-10-09 | Reference repos | kinivi: `pip install --dry-run "mediapipe==0.8.1" ...` (Python 3.12) | Fail: "No matching distribution found for mediapipe==0.8.1" |
| 2026-10-09 | Reference repos | Virtual-Mouse: `pip install -r requirements.txt`, `pip check`, and a start of the old `Hands()` API | Pass. numpy 2.4.4 and mediapipe 0.10.14. `cv2` reports 5.0.0 because of the duplicate OpenCV install |
| 2026-10-09 | Reference repos | `git check-ignore research/reference_repos research/envs` | Both are ignored |
| 2026-10-09 | Camera | `python -m pytest -q` | 102 passed, 1 deselected (hardware). The 8 camera unit tests pass |
| 2026-10-09 | Camera | `python -m pytest -q -m hardware` (the real camera opens, reads, and is released twice) | 1 passed |
| 2026-10-09 | Camera | M-01: `python scripts/list_cameras.py --backend` with auto, dshow, and msmf | Pass. Camera 0 works at 640x480 with every backend. Indices 1 to 4 report "Could not open camera" |
| 2026-10-09 | Camera | M-02: six open-read-release cycles in a row in one process | Pass. Each reopen worked right after the previous release |
| 2026-10-09 | Camera | Camera open time for camera 0 (three runs each, in ms) | auto (OpenCV default, MSMF): 14817, 7510, 8244. dshow: 2380, 1864, 2339. msmf: 7822, 6951, 7205. The driver reports 640x480 at 30 fps |
| 2026-10-09 | Hand tracker | Check of the installed API: `help(vision.HandLandmarkerOptions)` and `dir(result)` | The names match the plan: `running_mode`, `num_hands`, three confidence options, and the result fields `hand_landmarks`, `hand_world_landmarks`, and `handedness`. Calling `close()` twice is safe |
| 2026-10-09 | Hand tracker | `python -m pytest -q` | 108 passed, 2 deselected. The 5 hand tracker unit tests pass |
| 2026-10-09 | Hand tracker | `python -m pytest -q -m hardware` | 2 passed (the real camera, and the real model on a blank frame) |
| 2026-10-09 | Hand tracker | 90 real camera frames through the real tracker, with no window and nothing saved | Ran without errors. 0 frames with a hand, because no hand was shown |
| 2026-10-09 | Hand tracker | `python scripts/record_landmarks.py --config does_not_exist.toml` | A readable error and exit code 2 |
| 2026-10-09 | App loop | `python -m pytest -q` | 129 passed, 2 deselected. The 7 app-loop tests and 2 metrics tests pass |
| 2026-10-09 | App loop | `ruff check .`, `ruff format --check .`, `mypy src` | Pass |
| 2026-10-09 | App loop | M-03: `python -m gesture_mouse --camera 9 --dry-run` | Pass. "Could not open camera 9. Try another index with --camera ..." and exit code 3 |
| 2026-10-09 | App loop | M-24 (partly): `run_app` in dry-run mode with the real camera, model, and preview window, quitting after 90 frames | Pass. The window opened, ran 90 frames, and exited with code 0. The real mouse backend was never created. No hand was shown, so the gesture labels were not checked |
| 2026-10-09 | Error handling | `python -m pytest -q` | 139 passed, 2 deselected. The 8 error-handling tests and the test for the hand-lost check pass |
| 2026-10-09 | Error handling | `ruff check .`, `ruff format --check .`, `mypy src` | Pass |
| 2026-10-09 | Error handling | Search for risky code patterns: `grep -rn -E "shell=True\|os\.system\|subprocess\|eval\(\|exec\(\|requests\|urllib\|socket\|http\.client\|import pickle\|__import__\|importlib\.import_module" src scripts tests` | `src/`: no matches. `urllib` appears only in `scripts/fetch_model.py`, which is allowed. `subprocess` appears only in three tests that run the same Python with fixed code and no shell |
| 2026-10-09 | Error handling | Display scaling check: `pyautogui.size()` against the Windows screen size | Windows is at 150% scaling (1280x800 logical). PyAutoGUI calls `SetProcessDPIAware()` when it is imported and reports 1920x1200 physical pixels, so its coordinates are consistent |
| 2026-10-09 | Scripts and benchmark | `python -m pytest -q` | 145 passed, 2 deselected (adds the evaluation script tests) |
| 2026-10-09 | Scripts and benchmark | `python scripts/evaluate_gestures.py` on a made-up recording built from the test hands | The script runs and saves JSON. Made-up data only checks that the script runs. It is not an evaluation result |
| 2026-10-09 | Scripts and benchmark | `python scripts/benchmark.py --frames 2000 --warmup 100 --no-show --output output/benchmarks/run-01-no-hand.json` | See "Benchmark run-01" below |
| 2026-10-09 | Final checks | The CI steps, run locally: `pip check`, `ruff check .`, `ruff format --check .`, `mypy src`, and `pytest -q -m "not hardware"` | Pass |
| 2026-10-09 | Final checks | The full test suite, with `cv2`, `mediapipe`, and `pyautogui` blocked from importing | 145 passed, 2 deselected. The tests need no camera, display, or model |
| 2026-10-09 | Final checks | GitHub Actions run | Not run. The project was local only and had not been pushed |
| 2026-10-09 | Final checks | Clean environment: a new Python 3.12 venv, `pip install -e ".[dev]"`, `pip check`, `fetch_model.py`, `pytest -q`, `ruff check .`, `ruff format --check .`, and `mypy src` | All pass. 145 passed, 2 deselected. The installed versions match `requirements.lock.txt` exactly. The model was already there, so the download step reused it |
| 2026-10-09 | Final checks | Dry-run start from the clean environment, quitting with Esc after 60 frames | Pass. Exit code 0 |
| 2026-10-09 | Final checks | Imports used by `src` and `scripts` | cv2, mediapipe, numpy, and pyautogui are all used. No dependency is unused |
| 2026-10-09 | Final checks | `git ls-files` check for clones, environments, models, output, and the planning documents | None are tracked. All are ignored |
| 2026-10-09 | Final checks | Search for unfinished-work markers in `src`, `tests`, `scripts`, `config`, and `.github` | None found |
| 2026-10-09 | Final checks | Privacy and security search of tracked files and history: local paths, emails, keys and tokens, image or video writes, and network calls | No paths, emails, or keys. No image or video is ever written. The only network call is in `scripts/fetch_model.py`. The commit author email will be public if the repository is pushed |
| 2026-10-09 | Packaging | `python -m build` | Built `gesture_mouse-0.1.0.tar.gz` and `gesture_mouse-0.1.0-py3-none-any.whl` |
| 2026-10-09 | Packaging | Contents of the wheel (`zipfile` listing) | 13 package modules plus `licenses/LICENSE` and `licenses/THIRD_PARTY_NOTICES.txt`. No models, data, or recordings |
| 2026-10-09 | Packaging | Contents of the source package | The first build lacked `tests/helpers.py`, `tests/fakes.py`, `config/default.toml`, and the scripts. This was fixed with `MANIFEST.in`. The second build has 53 entries, including them |
| 2026-10-09 | Packaging | New venv: `pip install dist/*.whl pytest`, `gesture-mouse --version`, `pip check`, and `pytest -q` | `gesture-mouse 0.1.0`. The package was imported from site-packages. No broken requirements. 145 passed, 2 deselected |
| 2026-10-09 | Packaging | Release workflow run | Not run. It runs only on a pushed `v*` tag, and no tag was made (the owner must approve it) |

### Benchmark run-01 (no hand)

This measures the delay of the software pipeline on the machine in `output/benchmarks/machine.txt` (ThinkPad X1 Yoga, i7-1260P, plugged in, Balanced power plan, evening room light, DirectShow, 640x480) on 2026-10-09. No hand was in view and the preview window was off, so the display stage is close to zero. This is not the full delay from hand movement to screen.

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

2000 frames took 204.0 s, which is 9.8 frames per second, while the driver reports 30. Failed reads: 0 (0%). Frames with a hand: 0. The capture stage waits for the camera. A likely cause is a longer exposure in low light, but this is a guess that was not tested. The run with a hand moving through the gestures still needs the owner.

## Checks still waiting

| ID | Procedure | Status |
|---|---|---|
| M-04 | Show one hand. The 21 points should be drawn in the right places after mirroring. With no hand there should be no points. With two hands only one should be used. Also try a hand at the edge of the frame and lower light | Waiting for the owner |
| M-24 | Run `python -m gesture_mouse --dry-run` with a hand. The labels and points should follow the hand, and the mouse should not move | Waiting for the owner |
| M-05 to M-09 | Run `python -m gesture_mouse`. Pointing should move the cursor. A short pinch should click once. A held pinch should drag and then release. A thumb-and-middle-finger pinch should right click once. The two-finger pose should scroll in the expected direction | Waiting for the owner |
| M-15, M-16 | Press `p` while pointing and while dragging. Control should stop and the drag should end. Press `p` again to resume | Waiting for the owner |
| M-10 to M-13 | Camera not available (`--camera 9`, done as M-03), camera in use (open the Windows Camera app first), camera permission off, and camera lost during a run | M-10 was done as M-03. M-11 to M-13 are waiting for the owner. M-13 is also covered by an automated test |
| M-18 | Move the real cursor into a screen corner while the app runs. It should print "Emergency stop" and exit cleanly | Waiting for the owner |
| M-19 | Press Ctrl+C in the terminal. The app should exit cleanly with code 130 | Waiting for the owner |
| M-20 | Rename `models/hand_landmarker.task` and start the app. It should show a model error with the download command and exit with code 4. Then rename the file back | Waiting for the owner. Also covered by an automated test |
| M-21 | Use a config with `pinch_off = 0.1` and an unknown key. Both errors should be listed, the exit code should be 2, and the camera should never open | Waiting for the owner. Also covered by an automated test |
| M-17 | Quit with `q`, then with Esc. The window should close, the camera light should turn off, and no button should stay held | Waiting for the owner |
| REC-1 | Run `python scripts/record_landmarks.py --note "..."` and record a few hundred labeled frames | Waiting for the owner |
| BENCH-2 | Run `python scripts/benchmark.py --frames 2000 --warmup 100 --note "hand moving through gestures"` | Waiting for the owner |
| EVAL-1 | Record several labeled sessions, then run `python scripts/evaluate_gestures.py --input "output/recordings/*.jsonl"`. Keep the sessions used for tuning apart from the sessions used for reporting | Waiting for the owner |
| R-VM | Run Virtual-Mouse with safety steps in place and note how the webcam behaves | Waiting for the owner. Its emergency stop is off, so it was not run automatically |

## Blockers

| ID | Date | Description | What is blocked | What can continue |
|---|---|---|---|---|
| B-1 | 2026-10-09 | An automated run cannot hold a hand in front of the webcam | The manual tests M-04 to M-09, M-11, M-12, M-14 to M-24, BENCH-2, and EVAL-1 | Everything automated. The owner's checklist is in `HANDOVER_REPORT.md` |

## Assumptions

| ID | Date | Assumption | How to confirm |
|---|---|---|---|
| A-1 | 2026-10-09 | The built-in camera is index 0 | Confirmed by `python scripts/list_cameras.py` |

## Speed investigation

This used the same machine as run-01 (`output/benchmarks/machine.txt`) on 2026-10-09, in evening room light, with no hand in view and the preview window off. It measures the delay of the software pipeline, not the full delay from hand movement to screen.

**Measurements before any change**

| Check | Result |
|---|---|
| Camera only, DirectShow, 300 frames | 9.9 frames per second (median gap 96.5 ms). The pipeline in run-01 (9.8 frames per second) was limited by the camera, not by the code |
| Camera only, 150 frames each | MSMF 30.1 frames per second. DirectShow 9.9 frames per second |
| DirectShow asked for MJPG or YUY2 | The camera stays in YUY2 at 9.9 frames per second |
| Mirror and color conversion, 640x480, 500 runs | NumPy mirror 1.700 ms against `cv2.flip` 0.135 ms. NumPy BGR to RGB 1.484 ms against `cv2.cvtColor` 0.615 ms |

**Ideas, written down before each change, and the results**

| ID | Change | What counts as success | Result |
|---|---|---|---|
| H1 | Use MSMF (the OpenCV default) instead of DirectShow on Windows | At least 15 frames per second and a median total of at most 70 ms | Met. run-02: 19.47 frames per second and a median total of 56.21 ms (run-01: 9.8 and 100.27 ms) |
| H2 | Use `cv2.flip` and `cv2.cvtColor` instead of NumPy copies | A median mirror stage of at most 1 ms | Met. run-03: 0.25 ms (run-02: 3.08 ms). The total in run-03 was 16.41 frames per second, because inference was slower in that run (median 44.54 ms against 37.94 ms). This is variation between runs, and it is neither credited to nor blamed on the change |
| H3 | Set camera properties only when the driver reports a different value | An MSMF open time of at most 5 s | Met. 3277, 3968, and 2954 ms (before: 6951 to 14817 ms). The camera still gives 30.2 frames per second at 640x480 |
| H4 | Rewrite a stage in C++ or Rust | A stage written in plain Python is the slow part | Rejected. cProfile of 300 dry-run frames (`python -m cProfile -o output/profile.out -m gesture_mouse --dry-run --max-frames 300`): MediaPipe's native inference took 16.2 s, setting camera properties 9.1 s (at startup), camera reads 4.9 s, and `waitKey` 1.8 s. The project's own Python code is not near the top |

| Stage (median ms) | run-01 DirectShow | run-02 MSMF | run-03 MSMF + OpenCV mirror |
|---|---|---|---|
| capture | 48.34 | 8.53 | 10.69 |
| preprocess | 3.73 | 3.08 | 0.25 |
| inference | 46.20 | 37.94 | 44.54 |
| total | 100.27 | 56.21 | 58.24 |
| total, 95th percentile | 120.32 | 88.45 | 96.89 |
| achieved frames per second | 9.8 | 19.47 | 16.41 |

Tests after the changes: `python -m pytest -q` gave 149 passed, 2 deselected. `ruff`, `ruff format --check`, and `mypy src` pass. The suite also passes with `cv2`, `mediapipe`, and `pyautogui` blocked.

## Device protocol and C code (laptop only, no hardware)

| Date | Command or procedure | Result |
|---|---|---|
| 2026-10-09 | Looked for `gcc`, `clang`, `cc`, and `cl` on the PATH, and checked `vswhere` and WSL | None on the PATH. Visual Studio Community 2026 with MSVC 14.51.36231 was found. WSL Ubuntu has no compiler. Nothing was installed or bought |
| 2026-10-09 | `python firmware/build.py --test` (MSVC, `/std:c11 /W4 /WX`) | Built `test_protocol` and `device_sim` with no warnings. 1000065 checks, 0 failed |
| 2026-10-09 | `python firmware/build.py --test --sanitize` (MSVC AddressSanitizer) | 1000065 checks, 0 failed. The program links `clang_rt.asan`. MSVC has no sanitizer for undefined behavior |
| 2026-10-09 | Strict clang build with `zig cc` (the pip package `ziglang`, in a temporary environment and not a project dependency): `-std=c11 -Wall -Wextra -Wpedantic -Werror -Wconversion` | The first try failed because of a signed/unsigned conversion in the CRC loop. It was fixed with 32-bit arithmetic. The second try was clean, with 1000065 checks and 0 failed |
| 2026-10-09 | The same clang build with `-fsanitize=undefined -fno-sanitize-recover=undefined` | 1000065 checks, 0 failed |
| 2026-10-09 | `python -m pytest -q tests/test_serial_backend.py tests/test_protocol_loopback.py` | 14 passed. In the loopback test, every message from the host was acknowledged with its own sequence number. A damaged message got NACK reason 1 and did not run. A device-to-host message type got NACK reason 3. After the host went silent for longer than the timeout, the device printed `WATCHDOG release_all` and ended with no button held |
| 2026-10-09 | CRC check value for the ASCII text `123456789` | `0x29B1` in both C and Python |
| 2026-10-09 | `git diff main -- src/gesture_mouse/gesture_recognizer.py` | Empty. The gesture rules were not changed |
| 2026-10-09 | `python -m pytest -q`, `ruff check .`, `ruff format --check .`, and `mypy src` | 163 passed, 2 deselected. All pass |

Limits: no microcontroller, no physical serial port, and no real link were used. The silence timeout was tested with simulated time only.

## C++ comparison testing (owner request)

| Date | Command or procedure | Result |
|---|---|---|
| 2026-10-10 | `python firmware/build.py --test` (MSVC, C++17, `/W4 /WX`) | `test_protocol`: 1000065 checks, 0 failed. `differential_test`: 202004 streams, 0 differences |
| 2026-10-10 | A bug was planted on purpose: after a bad CRC, the C parser dropped a whole message instead of one byte. Then it was restored with `git checkout` | `differential_test`: 26448 differences. `test_protocol`: 3 failed. After restoring: 0 and 0 |
| 2026-10-10 | Strict Clang (`zig c++ -std=c++17 -Wall -Wextra -Wpedantic -Werror -Wconversion -fsanitize=undefined`) | It builds. 202004 streams, 0 differences. The warnings that appeared came from zig's own C++ library build, not from project files |
| 2026-10-10 | `python firmware/build.py --fuzz 120` (MSVC libFuzzer with AddressSanitizer) | 533065 inputs in 121 s, about 4405 per second, 467 new coverage units, and no crash or difference. Exit code 0 |

## Wokwi demo (owner request)

| Date | Command or procedure | Result |
|---|---|---|
| 2026-10-10 | The owner activated the free Wokwi for VS Code license | The extension `wokwi.wokwi-vscode` was installed |
| 2026-10-10 | Installed PlatformIO 6.2.0 with pip in `research/envs/platformio` (ignored by Git) | Downloaded the Espressif 32 platform 6.9.0, Arduino-ESP32 2.0.17, and the Adafruit SSD1306, GFX, and BusIO libraries |
| 2026-10-10 | First builds | `symlink://../src` failed (no library manifest). `build_src_filter` with `../src` failed (the source folders clashed). This was fixed with a pre-build script that calls `env.BuildSources` on `firmware/src` |
| 2026-10-10 | `pio run -d firmware/wokwi` (`-Wall -Wextra`) | Success, 0 warnings. RAM 6.8% (22,152 of 327,680 bytes). Flash 23.1% (302,389 of 1,310,720 bytes) |
| 2026-10-10 | `python firmware/build.py --test --sanitize` | 1000068 checks, 0 failed (this adds the HELLO reset and STATE range checks). 202004 streams, 0 differences |
| 2026-10-10 | `python -m pytest -q` | 176 passed, 2 deselected. The new tests use a fake serial device for the handshake, button ACKs, NACKs, timeouts, state messages, and closing the port |
| 2026-10-10 | `python -m gesture_mouse --serial rfc2217://localhost:4000` with no simulator running | A clear error ("actively refused") and exit code 6. The camera was not opened and the real mouse was not used |
| 2026-10-10 | `python scripts/check_all.py --all` | 8 of 8 checks passed, including the camera tests and the firmware build |
| 2026-10-10 | Owner run 1: `python -m gesture_mouse --serial rfc2217://localhost:4000` | It connected and ran for about 3 minutes, then stopped with "no ACK for left button down (seq 212)". No NACK was logged |
| 2026-10-10 | Checked whether the lost ACK contained a `0xFF` byte (the Telnet escape byte in RFC 2217) | No. The ACK for seq 212 is `a5 01 30 d4 01 d4 28 96`. Only the ACKs for seq 47, 215, and 255 contain `0xFF` |
| 2026-10-10 | New `scripts/serial_check.py`, run against the simulator | 4 of 5 answered, with a median of 367 ms and a maximum of 860 ms. A later run of 25 got all answers, between 234 and 1625 ms, and was faster while the tab was visible. With the tab hidden, there was no HELLO_ACK at all |
| 2026-10-10 | Owner run 2 (a blocking wait of 500 ms) | It stopped after 30 s with "no ACK for right button down (seq 192)" |
| 2026-10-10 | Cause | The simulator slows down or pauses when its tab is hidden or covered, and the app waited at most 500 ms for each button ACK. pyserial already sets `TCP_NODELAY` |
| 2026-10-10 | Fixes: ACKs are checked once per frame without waiting (a 2 s limit, then RELEASE_ALL and stop). The OLED is drawn in its own FreeRTOS task on core 0 every 100 ms, so serial replies never wait for the screen | 177 passed, 2 deselected. The firmware builds with 0 warnings (RAM 6.8%, flash 23.1%) |
| 2026-10-10 | GitHub Actions, Windows job (first push) | Failed. `build.py` chose MinGW gcc, and the linker could not find `-lasan` and `-lubsan`. This was fixed by trying MSVC first on Windows. It was checked locally with a stand-in `gcc` on the PATH: MSVC was chosen, and `build.py --test --sanitize` passed (1000068 checks, 202004 streams, 0 differences) |
| 2026-10-10 | After removing `MANIFEST.in` and `THIRD_PARTY_NOTICES.txt`: `python -m build` and `check_all.py` | The source package and the wheel were built. The wheel holds `licenses/LICENSE`. 6 of 6 checks passed |
| 2026-10-10 | Owner run 3, with the fixes and the simulator restarted on the new firmware | The owner reported that the app connects and every gesture shows on the board. No reply times were recorded |

Limits: the ESP32 runs only in the simulator. No real board or physical serial port was used.

## Training a classifier (not started)

This optional step should start only if recorded numbers show a weakness in the gesture rules. No real-hand evaluation exists yet (EVAL-1 is waiting), so the condition is not met. Anything that builds on a trained classifier waits for the same reason.
