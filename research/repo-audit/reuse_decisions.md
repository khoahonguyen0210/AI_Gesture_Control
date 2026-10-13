# Reuse Decisions

Three open-source projects were studied before writing any code. This file records what was taken from each of them. The answer is nothing: no code was copied, so no credit or license notice is required.

The labels used below:

- **Reuse**: copy it as it is.
- **Adapt**: copy it and change it.
- **Reference Only**: read it for ideas, but do not copy it.
- **Reimplement Independently**: write a new version from the official guide.
- **Reject**: do not use it.

The studied commits are mediapipe-samples `9cabe32b`, kinivi `0e737bb8`, and Virtual-Mouse `495b2933`.

| Component | Decision | What was checked | Why |
|---|---|---|---|
| Hand landmarker options and video-mode timestamps (mediapipe-samples, `examples/hand_landmarker/python/hand_landmarker.ipynb`) | Reimplement Independently | Read the notebook. It uses `HandLandmarkerOptions(num_hands=2)` and `detect(image)` on a still image. The option names were checked against the installed mediapipe 1.1.0 | The official guide is the better source, and the notebook only handles still images. `hand_tracker.py` was written from the guide. The API can change over time |
| Model download (official URL) | Use through a script, never commit | `scripts/fetch_model.py` downloaded it. The size and hash are in the license audit | The redistribution terms of the model are unverified, so it stays out of the repository |
| Landmark normalization for classifier input (kinivi, `app.py`, `pre_process_landmark`) | Reference Only | Read the function names and the README | The project uses simple distance ratios, not a classifier |
| TFLite classifiers, CSV data, and notebooks (kinivi, `model/`) | Reject | Listed 8 model and data files | Nobody says where the data came from. They also need TensorFlow, and rule-based gestures do not need them |
| FPS helper (kinivi, `utils/cvfpscalc.py`) | Reimplement Independently | Read the file list | It is trivial, and `metrics.py` needs percentiles anyway |
| List of settings (Virtual-Mouse, `src/config.py`) | Reference Only | Read the file | Used as a checklist of settings only. The author's values are not tuned for this project |
| Dead zone and mapping region (Virtual-Mouse, `src/main.py`) | Reimplement Independently | Read the code | Rewritten as plain, tested functions in `geometry.py` (`apply_dead_zone` and `map_to_screen`) |
| Click, drag, and scroll behavior (Virtual-Mouse) | Reject | Read the README's gesture table | It conflicts with this project's gestures |
| `pag.FAILSAFE = False` (Virtual-Mouse, `src/main.py`, line 43) | Reject | Read line 43 | It removes the emergency stop, which this project must keep |
| `xrandr` multi-monitor code (Virtual-Mouse, `src/main.py`, lines 24 to 30) | Reject | Read the code. It uses `subprocess` | It works only on Linux and runs an external program. Several monitors are not supported yet, and the app must not start other programs |
| Two input libraries, `pyautogui` and `pynput` (Virtual-Mouse) | Reject | Read the imports | One input library is enough |

**Result:** no component is copied or adapted, so no third-party notice file is needed.

**Check before the hand tracker was written:** the planned approach (the MediaPipe Tasks API, video mode, `detect_for_video`, and one hand) was confirmed. mediapipe 1.1.0 has no `mediapipe.solutions`, so the older API used by kinivi and Virtual-Mouse is not even available in this project's environment.
