# Repository Comparison

## Commits

All three hashes match the ones in the research dossier, so the repositories have not changed since the research date.

| Repository | Commit | Date and subject |
|---|---|---|
| google-ai-edge/mediapipe-samples | `9cabe32bfdd0a7457e2cb1d2f29ffcf7dc24195f` | 2026-10-07, "Add Web READMEs" |
| kinivi/hand-gesture-recognition-mediapipe | `0e737bb8c45ea03f6fafb1f5dbfe9246c34a8003` | 2021-01-28, "Notebook translation and other improvements" |
| Rounak7721/Virtual-Mouse | `495b293320fc588bc2bc05a81cbdf1f54fa1e7fd` | 2026-06-21, "docs: add demo video, rebrand to V-Mouse, add .gitignore" |

## Status

| Repository | Inspected | Installed | Run |
|---|---|---|---|
| mediapipe-samples | Yes (README, license, notebook API calls) | Not needed | Not run: the Python example is an image-only notebook |
| kinivi | Yes (README, license, `app.py`, model folder) | Failed: `mediapipe==0.8.1` has no build for Python 3.12 | Not run: could not install |
| Virtual-Mouse | Yes (README, license, `requirements.txt`, `src/`) | Yes, in `research/envs/virtual-mouse` (Python 3.12.10). `pip check` clean. | Not run (see below) |

**Virtual-Mouse install details.** The pinned packages install together on Python 3.12, and `mp.solutions.hands.Hands(max_num_hands=1)` starts with numpy 2.4.4, so the dossier's numpy concern did not appear. However, `cv2.__version__` reports 5.0.0, not the pinned 4.13: mediapipe 0.10.14 also installs `opencv-contrib-python` (latest), which overwrites the `cv2` folder of `opencv-python`. This is the same problem that led this project to declare only `opencv-contrib-python`.

**Why Virtual-Mouse was not run.** It turns off the PyAutoGUI failsafe (`pag.FAILSAFE = False`, line 43) and controls the real mouse. Running it needs the owner at the laptop with the safety steps from Execution Handbook Section 8.1. Webcam rows below are "not observed".

## Webcam behavior (Section 8.7)

| Item | mediapipe-samples | kinivi | Virtual-Mouse |
|---|---|---|---|
| Webcam opened | Not run | Not run | Not observed |
| Landmarks drawn | Not run | Not run | Not observed |
| Gestures tried | Not run | Not run | Not observed |
| No-hand behavior | Not run | Not run | Not observed |
| Camera busy | Not run | Not run | Not observed. From the code: `cam.read()` failure prints a message and continues with no limit or pause (lines 331-334). |
| Shutdown | Not run | `cap.release()` at the end of `main()` (line 180), not in a `finally` | From the code: `cam.release()` runs only after a normal loop exit (line 356); an exception skips it |

## Requirement comparison

S = satisfies, P = partly, N = no, U = unknown. Evidence is from reading code at the commits above.

| Requirement | mediapipe-samples | kinivi | Virtual-Mouse |
|---|---|---|---|
| FR-01 camera index configurable | N (no webcam) | S (`--device`) | S (`CAM_ID`) |
| FR-02 camera wrapper with safe release | N | P (release, no `finally`) | P (release, no `finally`) |
| FR-02a first-frame check and clear error | N | N | P (checks `isOpened`) |
| FR-02c tolerate failed reads with a limit | N | U | N (no limit) |
| FR-02d mirrored frames | N | S | S |
| FR-02e increasing timestamps | P (guide documents it) | N (legacy API) | N (legacy API) |
| FR-04 one hand, 21 landmarks | S (Tasks API) | S (legacy) | S (legacy) |
| FR-04c no legacy API | S | N | N |
| FR-05 to FR-09 MVP gesture table | N | N (no mouse) | P (different gestures) |
| FR-14 recognition separated from hardware | N | P (classifier module) | N |
| FR-14a scale-free ratios | N | P (normalized landmarks) | U |
| FR-15 debounce | N | U | P (wait times) |
| FR-16 release everything on any exit | N | N | N |
| FR-17 failsafe on | N/A | N/A | N (turned off) |

## Conclusion

No repository meets the safety and structure requirements, and none needs to be copied. The project keeps its own implementation, written from the official MediaPipe guide and the Bible. See `reuse_decisions.md`.
