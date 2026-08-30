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
| 2026-10-09 | Camera backend `auto` means DirectShow on Windows and the OpenCV default elsewhere | Measured on this laptop: DirectShow opened camera 0 in about 1.9-2.4 s; MSMF and the OpenCV default took about 7-15 s (test log, Phase 3) | Keep the OpenCV default | Set `camera.backend = "msmf"` or change `backend_api` |
| 2026-10-09 | `Camera.read()` pauses 10 ms between failed reads | A dead device returns at once; the pause keeps the retry from spinning while still ending within a fraction of a second | No pause | Set `READ_RETRY_S = 0` |
| 2026-10-09 | No camera reopen after `CameraLostError`; release the button and exit with code 3 | ERR-4 allows either. A clean exit is simpler and easy to test | One reopen attempt | Add a retry in `run_app` with a test |
| 2026-10-09 | Loop watchdog releases any held button after more than `lost_hand_grace_frames` frames without a hand | Second guard beside the recognizer (Execution Handbook Phase 6) | Recognizer only | Remove `_watchdog` |
| 2026-10-09 | The PyAutoGUI failsafe ends the app with exit code 0 and the message "Emergency stop" | It is a deliberate user action, not a failure | Exit 6 | Change `run_app` |
| 2026-10-09 | CI uses `actions/checkout@v7` and `actions/setup-python@v7` | Latest major tags on 2026-10-09 (`git ls-remote`); both v7 tags date from July 2026 | v6 | Change the tags in `ci.yml` |
| 2026-10-09 | CI does not swap to headless OpenCV on Linux | mediapipe requires `opencv-contrib-python`, so removing it breaks `pip check`; the tests never import `cv2` (checked by blocking it) | Handbook swap step | Add the step back |
| 2026-10-09 | CI workflow has read-only `contents` permission and no secrets | Least privilege | Default permissions | Remove the `permissions` block |
| 2026-10-09 | Config errors from the file, the command line, and range checks are reported in one `ConfigError` | Users can fix every problem at once (U-CFG-09) | Stop at the first problem | â€” |

## Change requests

| Date | Change | Reason | Affected |
|---|---|---|---|
| 2026-10-09 | Add `README.md` | Owner request. Overrides the handbook rule "do not create README.md". | README, Definition of Done item 8 |
| 2026-10-09 | Keep the handbooks out of Git | Owner request (`project-context/` is ignored) | Handbook commit step in Phase 0 |
| 2026-10-09 | Replace `opencv-python` with `opencv-contrib-python` | See Decisions | `pyproject.toml`, CI |

## Integrations

| Date | Component | Result |
|---|---|---|
| 2026-10-09 | Phase R review of all three reference repositories | No component was approved for Reuse or Adapt. Nothing was integrated. |
