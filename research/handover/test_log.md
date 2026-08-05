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

## Planned

Manual webcam and mouse rows from the test matrix are added here as their phases arrive.

## Blockers

None.

## Assumptions

| ID | Date | Assumption | How to confirm |
|---|---|---|---|
| A-1 | 2026-10-09 | The built-in camera is index 0 | `python scripts/list_cameras.py` (Phase 3) |
