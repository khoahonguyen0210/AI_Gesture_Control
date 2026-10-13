# Repository Comparison

This file compares the three open-source projects that were studied before writing any code.

## Commits

All three hashes match the ones noted at the start of the research, so the repositories have not changed since then.

| Repository | Commit | Date and subject |
|---|---|---|
| google-ai-edge/mediapipe-samples | `9cabe32bfdd0a7457e2cb1d2f29ffcf7dc24195f` | 2026-10-07, "Add Web READMEs" |
| kinivi/hand-gesture-recognition-mediapipe | `0e737bb8c45ea03f6fafb1f5dbfe9246c34a8003` | 2021-01-28, "Notebook translation and other improvements" |
| Rounak7721/Virtual-Mouse | `495b293320fc588bc2bc05a81cbdf1f54fa1e7fd` | 2026-06-21, "docs: add demo video, rebrand to V-Mouse, add .gitignore" |

## What was done with each one

| Repository | Read | Installed | Run |
|---|---|---|---|
| mediapipe-samples | Yes (README, license, and the API calls in the notebook) | Not needed | No. The Python example is a notebook that only works on still images |
| kinivi | Yes (README, license, `app.py`, and the model folder) | Failed. `mediapipe==0.8.1` has no build for Python 3.12 | No, because it could not be installed |
| Virtual-Mouse | Yes (README, license, `requirements.txt`, and `src/`) | Yes, in `research/envs/virtual-mouse` (Python 3.12.10). `pip check` was clean | No (see below) |

**Virtual-Mouse install details.** The pinned packages install together on Python 3.12, and `mp.solutions.hands.Hands(max_num_hands=1)` starts with numpy 2.4.4, so the expected numpy problem did not appear. However, `cv2.__version__` reports 5.0.0 instead of the pinned 4.13. The reason is that mediapipe 0.10.14 also installs the latest `opencv-contrib-python`, which overwrites the `cv2` folder of `opencv-python`. This is the same problem that led this project to declare only `opencv-contrib-python`.

**Why Virtual-Mouse was not run.** It turns off the PyAutoGUI emergency stop (`pag.FAILSAFE = False`, line 43) and controls the real mouse. Running it safely needs the owner at the laptop. So the webcam rows below say "Not observed".

## Webcam behavior

| Item | mediapipe-samples | kinivi | Virtual-Mouse |
|---|---|---|---|
| Webcam opened | Not run | Not run | Not observed |
| Landmarks drawn | Not run | Not run | Not observed |
| Gestures tried | Not run | Not run | Not observed |
| Behavior with no hand | Not run | Not run | Not observed |
| Camera busy | Not run | Not run | Not observed. From the code: when `cam.read()` fails, it prints a message and carries on, with no limit and no pause (lines 331 to 334) |
| Shutdown | Not run | `cap.release()` at the end of `main()` (line 180), not inside a `finally` block | From the code: `cam.release()` runs only after a normal exit from the loop (line 356), so an error skips it |

## Comparison with what this project needs

Yes means it does this. Partly means it does some of it. No means it does not. Unknown means the code did not show it. All answers come from reading the code at the commits above.

| What this project needs | mediapipe-samples | kinivi | Virtual-Mouse |
|---|---|---|---|
| The camera index can be set | No (no webcam) | Yes (`--device`) | Yes (`CAM_ID`) |
| The camera is always released safely | No | Partly (released, but not in a `finally` block) | Partly (released, but not in a `finally` block) |
| The first frame is checked and a clear error is shown | No | No | Partly (checks `isOpened`) |
| Failed reads are tolerated, up to a limit | No | Unknown | No (no limit) |
| Frames are mirrored | No | Yes | Yes |
| Timestamps always increase | Partly (the guide describes it) | No (old API) | No (old API) |
| One hand with 21 landmarks | Yes (Tasks API) | Yes (old API) | Yes (old API) |
| Avoids the old MediaPipe API | Yes | No | No |
| The same gestures as this project | No | No (no mouse) | Partly (different gestures) |
| Gesture logic is separate from the hardware | No | Partly (a classifier module) | No |
| Gesture measurements do not depend on hand size or distance | No | Partly (normalized landmarks) | Unknown |
| Repeated clicks are prevented | No | Unknown | Partly (wait times) |
| Everything is released on every exit | No | No | No |
| The emergency stop stays on | Not applicable | Not applicable | No (turned off) |

## Conclusion

No repository meets this project's safety and structure needs, and none needs to be copied. The project keeps its own implementation, written from the official MediaPipe guide. See `reuse_decisions.md`.
