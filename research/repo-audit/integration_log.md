# Integration Log

## Decisions

| Date | Decision | Reason | Alternatives | How to reverse |
|---|---|---|---|---|
| 2026-10-09 | Use Python 3.12.10 in `.venv` | Recommended version; installed with `py install 3.12` because only 3.14 was present | 3.14 (not supported by the plan) | Recreate `.venv` with another interpreter |
| 2026-10-09 | Declare `opencv-contrib-python` instead of `opencv-python` | mediapipe 1.1.0 requires `opencv-contrib-python`. Installing both puts two copies in the same `cv2` folder, which breaks when their versions differ. | Keep both and pin the same version | Change the dependency name in `pyproject.toml` |
| 2026-10-09 | Require Python 3.12 or newer | numpy 2.5.3, the resolved version, needs 3.12 | Lower numpy bound to keep 3.11 (untested) | Lower `requires-python` and the numpy bound, then test on 3.11 |
| 2026-10-09 | Pytest skips `hardware` tests by default (`-m 'not hardware'` in `addopts`) | The default run must work without a webcam or a real mouse | Pass the marker on every command | Remove it from `addopts` |
| 2026-10-09 | Config errors from the file, the command line, and range checks are reported in one `ConfigError` | Users can fix every problem at once (U-CFG-09) | Stop at the first problem | — |

## Change requests

| Date | Change | Reason | Affected |
|---|---|---|---|
| 2026-10-09 | Add `README.md` | Owner request. Overrides the handbook rule "do not create README.md". | README, Definition of Done item 8 |
| 2026-10-09 | Keep the handbooks out of Git | Owner request (`project-context/` is ignored) | Handbook commit step in Phase 0 |
| 2026-10-09 | Replace `opencv-python` with `opencv-contrib-python` | See Decisions | `pyproject.toml`, CI |
