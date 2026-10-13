# Integration Log

This file records the choices made while building the project, why they were made, and how to undo each one.

## Decisions

| Date | Decision | Reason | Other options | How to undo |
|---|---|---|---|---|
| 2026-10-09 | Use Python 3.12.10 in `.venv` | It is the recommended version. It was installed with `py install 3.12` because only 3.14 was present | 3.14, which the project does not support | Recreate `.venv` with another Python |
| 2026-10-09 | Declare `opencv-contrib-python` instead of `opencv-python` | mediapipe 1.1.0 requires `opencv-contrib-python`. Installing both puts two copies in the same `cv2` folder, which breaks when their versions differ | Keep both and pin the same version | Change the dependency name in `pyproject.toml` |
| 2026-10-09 | Require Python 3.12 or newer | numpy 2.5.3, the version that was installed, needs 3.12 | Lower the numpy limit to keep 3.11 (untested) | Lower `requires-python` and the numpy limit, then test on 3.11 |
| 2026-10-09 | pytest skips `hardware` tests by default (`-m 'not hardware'` in `addopts`) | The default run must work without a webcam or a real mouse | Pass the marker on every command | Remove it from `addopts` |
| 2026-10-09 | Add `gesture.pinch_min_reach` (starting value 0.80) | In a fist, the thumb rests on the curled fingers, so the thumb-to-fingertip ratio can fall below `pinch_on`. A finger whose tip is curled toward the wrist now cannot start a pinch. The set of gestures is unchanged | Use `pinch_on` only, which would let a fist click | Set the value to 0 |
| 2026-10-09 | A right-click hold gets the same grace period for a lost hand as a pinch | A short tracking drop during a held right pinch must not cause a second right click | End the hold at once | Remove `RIGHT_LATCHED` from `HELD_STATES` |
| 2026-10-09 | Ending a pinch or a right pinch takes `exit_frames` frames | The fingers must open for several frames, so one noisy frame does not end a drag | End on the first frame above `pinch_off` | Set `exit_frames = 1` |
| 2026-10-09 | The pinch hold time counts from the first pinch frame, not from the confirmed start | The drag starts when the user expects it | Count from the confirmed start | None |
| 2026-10-09 | The click lands on the last pointer position, and a drag moves by the change of the thumb-index midpoint | Closing the fingers must not move the cursor away from where you pointed | Click at the current index fingertip | None |
| 2026-10-09 | `PyAutoGuiBackend.mouse_up` turns the emergency stop off for the release call only | After the emergency stop fires, the cursor is in a corner, and a normal `mouseUp` would fail again and leave the button held | Leave the button held | None |
| 2026-10-09 | (Replaced by a later row) Camera backend `auto` meant DirectShow on Windows | Measured on this laptop: DirectShow opened camera 0 in about 1.9 to 2.4 s, while MSMF and the OpenCV default took about 7 to 15 s (see the test log) | Keep the OpenCV default | Set `camera.backend = "msmf"` or change `backend_api` |
| 2026-10-09 | `Camera.read()` pauses 10 ms between failed reads | A dead device fails at once. The pause stops the retries from spinning, and the loop still ends within a fraction of a second | No pause | Set `READ_RETRY_S = 0` |
| 2026-10-09 | The app does not reopen the camera after `CameraLostError`. It releases the button and exits with code 3 | Either choice was allowed. A clean exit is simpler and easy to test | Try to reopen once | Add a retry in `run_app` with a test |
| 2026-10-09 | A second check in the main loop releases any held button after more than `lost_hand_grace_frames` frames without a hand | It is a backup for the gesture rules, which already do this | Rely on the gesture rules only | Remove `_watchdog` |
| 2026-10-09 | The PyAutoGUI emergency stop ends the app with exit code 0 and the message "Emergency stop" | It is something the user did on purpose, not a failure | Exit with code 6 | Change `run_app` |
| 2026-10-09 | CI uses `actions/checkout@v7` and `actions/setup-python@v7` | They were the latest major versions on 2026-10-09 (checked with `git ls-remote`). Both v7 tags date from July 2026 | v6 | Change the tags in `ci.yml` |
| 2026-10-09 | CI does not switch to headless OpenCV on Linux | mediapipe requires `opencv-contrib-python`, so removing it breaks `pip check`. The tests never import `cv2` (checked by blocking it) | Add a swap step | Add the step back |
| 2026-10-09 | The CI workflow has read-only `contents` permission and no secrets | It gets only the access it needs | Default permissions | Remove the `permissions` block |
| 2026-10-09 | The version lives only in `pyproject.toml`, and `__version__` reads it from the installed package | One place for the version | Keep two copies | Put the literal back in `__init__.py` |
| 2026-10-09 | The build backend requires `setuptools>=77` | `license = "MIT"` (an SPDX expression) and `license-files` need setuptools 77 or newer | The old `License ::` classifiers | Lower the limit and switch to classifiers |
| 2026-10-09 | (Replaced on 2026-10-10: `MANIFEST.in` was removed) `MANIFEST.in` added the test helpers, `config/default.toml`, the scripts, and the lock file to the source package | Without them, the tests inside the source package fail | Ship the source package without tests | Delete `MANIFEST.in` |
| 2026-10-09 | The release workflow uses `gh release create` with the built-in `github.token`, and checks that the tag matches the package version | No stored secrets and no third-party release action | A release action from the marketplace | Edit `release.yml` |
| 2026-10-09 | Camera backend `auto` is OpenCV's default again (MSMF on Windows) | DirectShow opens faster but gives only 9.9 frames per second on this camera, while MSMF gives 30.1. Frame rate matters more than start time | DirectShow | Set `camera.backend = "dshow"` |
| 2026-10-09 | Camera properties are set only when the driver reports a different value | Each `set` took seconds on MSMF (9.1 s in the profile). Open time fell to about 3 to 4 s | Always set them | Remove the check in `Camera.open` |
| 2026-10-09 | The timeout for the first frame starts after the device opens | A slow open must not use up the time meant for the first frame | Count from before the open | None |
| 2026-10-09 | Mirror with `cv2.flip` and convert colors with `cv2.cvtColor` | 0.25 ms instead of about 3 ms per frame. The mirror function can be swapped out, so tests do not need OpenCV | NumPy copies | Pass a NumPy mirror |
| 2026-10-09 | New command-line option `--max-frames N` | A profiling run can stop by itself | Stop with a key | Remove the option |
| 2026-10-09 | No C++ or Rust code in the app | The profile shows no slow Python stage to speed up | A native module | None |
| 2026-10-09 | The device logic (command handler and silence timeout) is in `firmware/src/device.c`, apart from the parser in `protocol.c` | Both are plain C with no hardware calls, so the simulator and the tests can reuse them | One file | Merge the files |
| 2026-10-09 | After a bad CRC or a length that is too large, the parser drops one byte and searches for the next start byte | A real message that begins inside a bad one is still found (C test `test_frame_inside_bad_frame_is_found`) | Drop the whole bad message | Change `fail(..., 1)` to the message size |
| 2026-10-09 | The protocol has no NACK reason for a payload of the right size with a wrong value (a button above 1, or a state above 4). The device answers NACK reason 2 (bad length) and runs nothing | It is the closest existing reason. A new reason would need a new protocol version | Add reason 5 in protocol version 2 | Make a change request to raise `VER` |
| 2026-10-09 | A rejected message (NACK) does not reset the device's silence timeout | Only messages that actually run count as contact | Reset on any message with a good CRC | Move the reset in `device_handle` |
| 2026-10-09 | `device_sim` reads text lines (`T <ms>` and `X <hex bytes>`) instead of raw bytes | Simulated time can be added, and Windows text-mode pipes cannot damage the bytes | Raw binary input | None |
| 2026-10-09 | The silence timeout, the byte timeout, and the heartbeat interval are required arguments with no built-in default | They should be chosen from measurements. The tests pass 500, 50, and 100 ms as test values only | Guessed defaults | Measure on a real board (not started) |
| 2026-10-09 | `MouseController.release_all()` also calls the backend's own `release_all()` when it has one | `SerialBackend` must send RELEASE_ALL on every exit path. The gesture rules are unchanged | Send RELEASE_ALL only on close | Remove the `getattr` call |
| 2026-10-09 | (Replaced on 2026-10-10 by `--serial`) `SerialBackend` was not connected to the command line | There was no real serial port and no `pyserial` yet. Tests and the loopback used it | Add a `--serial` option | Make a change request with a review of serial libraries |
| 2026-10-09 | CI runs `python firmware/build.py --test --sanitize` (gcc with ASan and UBSan on Linux, MSVC with ASan on Windows) | The C tests run on every push | Run the Python tests only | Remove the step |
| 2026-10-09 | Training a classifier (an optional later step) is skipped for now | It should start only if measurements show the gesture rules are weak, and no real-hand evaluation exists yet | Train anyway | Run the evaluation, then check again |
| 2026-10-10 | The C++ reference parser reads a whole buffer, and its CRC uses a lookup table | It was written separately from the C code, so the two can disagree when one has a bug | Share code with the C parser | None |
| 2026-10-10 | Added `extern "C"` guards in `protocol.h` and `device.h` | C++ can then include the C headers | None | None |
| 2026-10-10 | MSVC builds the C files separately (`/std:c11`) before the C++ file (`/std:c++17`) | MSVC rejects both standard flags in one command | None | None |
| 2026-10-09 | Config errors from the file, the command line, and the range checks are reported together in one `ConfigError` | The user can fix every problem at once | Stop at the first problem | None |
| 2026-10-10 | `--serial PORT` connects `SerialBackend` to the command line through pyserial, an optional extra (`.[serial]`) | Owner request (Wokwi demo). pyserial opens both COM ports and `rfc2217://` addresses. It is imported only when `--serial` is used | Raw sockets for Wokwi only | Remove the option and the extra |
| 2026-10-10 | (Replaced by the next row) `SerialLink` read replies before each write and waited only for HELLO_ACK (2 s) and button ACKs (500 ms) | Keeps the reply buffer small without a reader thread | A background reader thread | Go back to write-only |
| 2026-10-10 | Button ACKs are checked in `tick()`, once per frame, with a 2 s limit. Only HELLO is waited for | The simulator answered in 234 to 1625 ms, and a blocking wait froze the app and stopped it on a slow reply. A missing ACK still means RELEASE_ALL and an error | A longer blocking wait | Wait in `_button` again |
| 2026-10-10 | The Wokwi sketch draws the OLED in a FreeRTOS task on core 0, and the loop on core 1 only handles serial bytes and LEDs | A full OLED update blocks for a long time in the simulator, and replies must not wait for it | Draw less often in the loop | Call `draw` from `loop` |
| 2026-10-10 | STATE values 0 to 7 have names (`enum device_state`), one for each state of the gesture rules. The device rejects 8 and above | The old range (0 to 4) had no clear meaning and could not hold all eight states | Fold the states into five values | Restore the old range check |
| 2026-10-10 | HELLO clears the buttons, state, position, and scroll on the device | The host starts its cursor at the screen center on each run, so the device must start from zero too | Reset in the sketch only | Remove the reset |
| 2026-10-10 | `MouseController.end_frame()` and `close()` call the backend's `show_state`, `tick`, and `close` when it has them | It is the same pattern as `release_all`, and other backends need no change | Add the methods to every backend | Remove the calls |
| 2026-10-10 | The Wokwi demo runs in its own parser and device, apart from the live session | Switching between the demo and the app never changes the app's cursor | One shared session | Merge the sessions |
| 2026-10-10 | PlatformIO builds `firmware/src` through a pre-build script (`env.BuildSources`) | The two simpler options failed (see the test log), and the shared C files stay in one place | Copy the C files into the sketch folder | Copy the files |
| 2026-10-10 | On Windows, `firmware/build.py` tries MSVC before gcc or clang | The GitHub Windows runner has MinGW gcc on its PATH, which has no sanitizer libraries, so the CI build failed with `cannot find -lasan`. MSVC has AddressSanitizer, so Windows keeps its memory checks | Skip the sanitizers on Windows | Restore the old search order |
| 2026-10-10 | Remove `MANIFEST.in` and `THIRD_PARTY_NOTICES.txt`, and move the lock file to `research/repo-audit/` | Owner request, for a tidier repository root. The release workflow tests the built package against the repository's own tests, so the source package does not need them. Nothing is copied, so the notice file only said "None" | Keep the files | Restore them from Git history |

## Change requests

| Date | Change | Reason | What it touched |
|---|---|---|---|
| 2026-10-09 | Add `README.md` | Owner request. It overrides the planning documents' rule "do not create README.md" | README |
| 2026-10-09 | Keep the planning documents out of Git | Owner request (`project-context/` is ignored) | The first setup step |
| 2026-10-09 | Replace `opencv-python` with `opencv-contrib-python` | See Decisions | `pyproject.toml`, CI |
| 2026-10-09 | Start the optional extras (packaging, profiling, and the serial protocol in C) before the main manual webcam tests were done | Owner instruction ("just follow it"). It is the owner's written exception to the rule that the main work must be finished first. The open items are the manual webcam tests | `firmware/`, workflows, records |
| 2026-10-10 | Add C++ to the project: an independent C++17 reference parser, a seeded comparison test, and a libFuzzer target under `firmware/fuzz/` | Owner request. Profiling showed no slow stage for C++ to speed up, so C++ was given a testing job: it checks the C parser against the protocol rules | `firmware/fuzz/`, `firmware/build.py`, CI, README |
| 2026-10-09 | Add `build` as a development dependency | Needed to build the release packages. License MIT (`build` 1.6.1, `pyproject_hooks` 1.3.3) | `pyproject.toml` |
| 2026-10-10 | Add a Wokwi ESP32 demo and the `--serial` option | Owner request. The owner uses a free Wokwi account and license, which the original "no accounts" rule did not foresee. Nothing is bought, and the app itself stays local | `firmware/wokwi/`, `serial_backend.py`, `__main__.py`, CI, README |

## Code taken from other projects

| Date | Component | Result |
|---|---|---|
| 2026-10-09 | Review of all three reference repositories | No component was approved for Reuse or Adapt. Nothing was taken from them |
