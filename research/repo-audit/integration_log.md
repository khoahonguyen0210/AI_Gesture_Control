# Integration Log

## Decisions

| Date | Decision | Reason | Alternatives | How to reverse |
|---|---|---|---|---|
| 2026-10-09 | Use Python 3.12.10 in `.venv` | Recommended version; installed with `py install 3.12` because only 3.14 was present | 3.14 (not supported by the plan) | Recreate `.venv` with another interpreter |
| 2026-10-09 | Declare `opencv-contrib-python` instead of `opencv-python` | mediapipe 1.1.0 requires `opencv-contrib-python`. Installing both puts two copies in the same `cv2` folder, which breaks when their versions differ. | Keep both and pin the same version | Change the dependency name in `pyproject.toml` |
| 2026-10-09 | Require Python 3.12 or newer | numpy 2.5.3, the resolved version, needs 3.12 | Lower numpy bound to keep 3.11 (untested) | Lower `requires-python` and the numpy bound, then test on 3.11 |
| 2026-10-09 | Pytest skips `hardware` tests by default (`-m 'not hardware'` in `addopts`) | The default run must work without a webcam or a real mouse | Pass the marker on every command | Remove it from `addopts` |
| 2026-10-09 | Add `gesture.pinch_min_reach` (starting value 0.80) | In a fist the thumb rests on curled fingers, so the thumb-to-fingertip ratio can fall below `pinch_on`. A finger whose tip is curled toward the wrist cannot start a pinch. This refines the recommended landmark rule; the gesture set is unchanged. | Rely on `pinch_on` only (fist could click) | Set the value to 0 |
| 2026-10-09 | A right-click latch gets the same lost-hand grace period as a pinch | A short tracking drop during a held right pinch must not cause a second right click | Drop the latch at once | Remove `RIGHT_LATCHED` from `HELD_STATES` |
| 2026-10-09 | A pinch and a right-pinch release need `exit_frames` frames | Hysteresis plus debounce on release; one noisy frame does not end a drag | Release on the first frame above `pinch_off` | Set `exit_frames = 1` |
| 2026-10-09 | Pinch hold time counts from the first pinch frame, not the debounced entry | The drag starts when the user expects | Count from the debounced entry | — |
| 2026-10-09 | Cursor anchoring as recommended: the click lands on the last pointer position; a drag moves by the change of the thumb-index midpoint | Bible Section 10, rule 5 | Click at the current index tip | — |
| 2026-10-09 | `PyAutoGuiBackend.mouse_up` turns the failsafe off for the release call only | After the failsafe fires, the cursor is in a corner and a normal `mouseUp` would raise again, leaving the button held | Leave the button held | — |
| 2026-10-09 | (Replaced by the next row) Camera backend `auto` means DirectShow on Windows | Measured on this laptop: DirectShow opened camera 0 in about 1.9-2.4 s; MSMF and the OpenCV default took about 7-15 s (test log, Phase 3) | Keep the OpenCV default | Set `camera.backend = "msmf"` or change `backend_api` |
| 2026-10-09 | `Camera.read()` pauses 10 ms between failed reads | A dead device returns at once; the pause keeps the retry from spinning while still ending within a fraction of a second | No pause | Set `READ_RETRY_S = 0` |
| 2026-10-09 | No camera reopen after `CameraLostError`; release the button and exit with code 3 | ERR-4 allows either. A clean exit is simpler and easy to test | One reopen attempt | Add a retry in `run_app` with a test |
| 2026-10-09 | Loop watchdog releases any held button after more than `lost_hand_grace_frames` frames without a hand | Second guard beside the recognizer (Execution Handbook Phase 6) | Recognizer only | Remove `_watchdog` |
| 2026-10-09 | The PyAutoGUI failsafe ends the app with exit code 0 and the message "Emergency stop" | It is a deliberate user action, not a failure | Exit 6 | Change `run_app` |
| 2026-10-09 | CI uses `actions/checkout@v7` and `actions/setup-python@v7` | Latest major tags on 2026-10-09 (`git ls-remote`); both v7 tags date from July 2026 | v6 | Change the tags in `ci.yml` |
| 2026-10-09 | CI does not swap to headless OpenCV on Linux | mediapipe requires `opencv-contrib-python`, so removing it breaks `pip check`; the tests never import `cv2` (checked by blocking it) | Handbook swap step | Add the step back |
| 2026-10-09 | CI workflow has read-only `contents` permission and no secrets | Least privilege | Default permissions | Remove the `permissions` block |
| 2026-10-09 | Version lives only in `pyproject.toml`; `__version__` reads the installed package metadata | Extension D: one place for the version | Keep two copies | Restore the literal in `__init__.py` |
| 2026-10-09 | Build backend requires `setuptools>=77` | `license = "MIT"` (an SPDX expression) and `license-files` need setuptools 77 or newer | Old `License ::` classifiers | Lower the bound and switch to classifiers |
| 2026-10-09 | `MANIFEST.in` adds test helpers, `config/default.toml`, scripts, and the lock file to the sdist | Without them, the tests inside the sdist fail | Leave the sdist without tests | Delete `MANIFEST.in` |
| 2026-10-09 | Release workflow uses `gh release create` with the built-in `github.token`; it checks that the tag matches the package version | No stored secrets and no third-party release action | A marketplace release action | Edit `release.yml` |
| 2026-10-09 | Camera backend `auto` is OpenCV's default again (MSMF on Windows) | Extension E: DirectShow opens faster but delivers only 9.9 frames/s on this camera; MSMF delivers 30.1. Frame rate matters more than start time | DirectShow | Set `camera.backend = "dshow"` |
| 2026-10-09 | Camera properties are set only when the driver reports a different value | Each `set` took seconds on MSMF (9.1 s in the profile); open time fell to about 3-4 s | Always set | Remove the check in `Camera.open` |
| 2026-10-09 | The first-frame timeout starts after the device opens | A slow open must not use up the time meant for the first frame | Count from before the open | — |
| 2026-10-09 | Mirror with `cv2.flip`; convert colors with `cv2.cvtColor` | Extension E-H2: 0.25 ms instead of about 3 ms per frame. The mirror function is injectable so tests need no OpenCV | NumPy copies | Pass a NumPy mirror |
| 2026-10-09 | New CLI option `--max-frames N` | Extension E: lets a profiling run stop by itself | Stop with a key | Remove the option |
| 2026-10-09 | No C++ or Rust code | Extension E-H4: the profile shows no pure-Python bottleneck | Native module | — |
| 2026-10-09 | Device logic (command handler and watchdog) is in `firmware/src/device.c`, apart from the parser in `protocol.c` | Both are plain C with no hardware calls; the simulator and the tests reuse them | One file | Merge the files |
| 2026-10-09 | The parser drops one byte after a bad CRC or an oversized length, then searches for the next start byte | A real frame that begins inside a bad one is still found (C test `test_frame_inside_bad_frame_is_found`) | Drop the whole bad frame | Change `fail(..., 1)` to the frame size |
| 2026-10-09 | Protocol gap: the spec has no NACK reason for a valid-size payload with an invalid value (button above 1, state above 4). The device answers NACK reason 2 (bad length) and runs nothing | Closest existing reason; no new reason without a protocol version change | Add reason 5 in protocol version 2 | Change request to bump `VER` |
| 2026-10-09 | A frame that is rejected (NACK) does not reset the device watchdog | Only frames that run count as contact | Reset on any CRC-valid frame | Move the reset in `device_handle` |
| 2026-10-09 | `device_sim` reads text lines (`T <ms>`, `X <hex bytes>`) instead of raw bytes | Simulated time can be injected, and Windows text-mode pipes cannot corrupt the bytes | Raw binary stdin | — |
| 2026-10-09 | Watchdog time, byte timeout, and heartbeat interval are required arguments with no built-in default | The plan says to choose them from measurement; tests pass 500, 50, and 100 ms as test values only | Guessed defaults | Measure on a real board (Appendix A, not started) |
| 2026-10-09 | `MouseController.release_all()` also calls the backend's own `release_all()` when it has one | `SerialBackend` must send RELEASE_ALL on every exit path. The recognizer is unchanged | Send RELEASE_ALL only on close | Remove the `getattr` call |
| 2026-10-09 | (Replaced on 2026-10-10 by `--serial`) `SerialBackend` is not connected to the command line | A1 has no real serial port and no `pyserial`; it is used by tests and the loopback | Add a `--serial` option | Change request with a serial library audit |
| 2026-10-09 | CI runs `python firmware/build.py --test --sanitize` (gcc with ASan and UBSan on Linux, MSVC with ASan on Windows) | C tests run on every push | Python tests only | Remove the step |
| 2026-10-09 | Extensions B and C are skipped for now | Their gate (measured weakness of the rules) is not met; no real-hand evaluation exists | Train anyway | Run EVAL-1, then check the gate again |
| 2026-10-10 | The C++ reference parser reads a whole buffer, and its CRC uses a lookup table | Written separately from the C code, so the two can disagree when one has a bug | Share code with the C parser | — |
| 2026-10-10 | `extern "C"` guards in `protocol.h` and `device.h` | Lets C++ include the C headers | — | — |
| 2026-10-10 | MSVC builds C files separately (`/std:c11`) before the C++ file (`/std:c++17`) | MSVC rejects both standard flags in one command | — | — |
| 2026-10-09 | Config errors from the file, the command line, and range checks are reported in one `ConfigError` | Users can fix every problem at once (U-CFG-09) | Stop at the first problem | â€” |
| 2026-10-10 | `--serial PORT` connects `SerialBackend` to the command line through pyserial, an optional extra (`.[serial]`) | Owner request (Wokwi demo). pyserial opens both COM ports and `rfc2217://` URLs. It is imported only when `--serial` is used | Raw sockets for Wokwi only | Remove the option and the extra |
| 2026-10-10 | `SerialLink` reads replies before each write and waits only for HELLO_ACK (2 s) and button ACKs (500 ms) | Keeps the reply buffer small without a reader thread | A background reader thread | Return to write-only |
| 2026-10-10 | STATE values 0 to 7 have names (`enum device_state`), one per recognizer state; the device rejects 8 and above | The old range (0 to 4) had no meaning and could not hold all eight states | Fold the states into five values | Restore the old range check |
| 2026-10-10 | HELLO clears buttons, state, position, and scroll on the device | The host starts its cursor at the screen center on each run, so the device must start from zero too | Reset in the sketch only | Remove the reset |
| 2026-10-10 | `MouseController.end_frame()` and `close()` call the backend's `show_state`, `tick`, and `close` when it has them | Same pattern as `release_all`; other backends need no change | Add the methods to every backend | Remove the calls |
| 2026-10-10 | The Wokwi demo runs in its own parser and device, apart from the live session | Switching between the demo and the app never changes the app's cursor | One shared session | Merge the sessions |
| 2026-10-10 | PlatformIO builds `firmware/src` through a pre-build script (`env.BuildSources`) | Both simpler options failed (see the test log); the shared C files stay in one place | Copy the C files into the sketch folder | Copy the files |

## Change requests

| Date | Change | Reason | Affected |
|---|---|---|---|
| 2026-10-09 | Add `README.md` | Owner request. Overrides the handbook rule "do not create README.md". | README, Definition of Done item 8 |
| 2026-10-09 | Keep the handbooks out of Git | Owner request (`project-context/` is ignored) | Handbook commit step in Phase 0 |
| 2026-10-09 | Replace `opencv-python` with `opencv-contrib-python` | See Decisions | `pyproject.toml`, CI |
| 2026-10-09 | Start the extension plan (D, E, A0, A1; B and C only if their gate is met) before the MVP Definition of Done is fully met | Owner instruction ("just follow it"). This is the owner's written exception to the MVP gate (Extension Plan rule 3). Open MVP items: the manual webcam tests | `extensions/`, `firmware/`, workflows, records |
| 2026-10-10 | Add C++ to the project: an independent C++17 reference parser, a seeded differential test, and a libFuzzer target under `firmware/fuzz/` | Owner request. Profiling showed no slow stage for C++ to speed up (Extension E-H4), so C++ was given a testing job instead: it checks the C parser against the protocol rules | `firmware/fuzz/`, `firmware/build.py`, CI, README |
| 2026-10-09 | Add `build` as a development dependency | Extension D. License MIT (`build` 1.6.1, `pyproject_hooks` 1.3.3) | `pyproject.toml` |
| 2026-10-10 | Add a Wokwi ESP32 demo and the `--serial` option | Owner request. The owner uses a free Wokwi account and license, which the Extension Plan's "no account" rule did not foresee. Nothing is bought, and the app itself stays local | `firmware/wokwi/`, `serial_backend.py`, `__main__.py`, CI, README |

## Integrations

| Date | Component | Result |
|---|---|---|
| 2026-10-09 | Phase R review of all three reference repositories | No component was approved for Reuse or Adapt. Nothing was integrated. |
