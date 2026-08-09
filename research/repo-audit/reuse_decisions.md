# Reuse Decisions

Labels: Reuse, Adapt, Reference Only, Reimplement Independently, Reject. Commits: mediapipe-samples `9cabe32b`, kinivi `0e737bb8`, Virtual-Mouse `495b2933`.

| Component | Decision | Evidence | License rationale | Integration change | Attribution | Risks | Reason |
|---|---|---|---|---|---|---|---|
| HandLandmarker options and VIDEO-mode timestamps (mediapipe-samples `examples/hand_landmarker/python/hand_landmarker.ipynb`) | Reimplement Independently | Read the notebook: it uses `HandLandmarkerOptions(num_hands=2)` and `detect(image)` on a still image (IMAGE mode). Option names checked against the installed mediapipe 1.1.0 in Phase 4. | Apache-2.0, but nothing is copied | `hand_tracker.py` written from the official guide | None needed | API changes over time | The guide is the authority; the notebook is image-only |
| Model download (official URL) | Use via script, not committed | `scripts/fetch_model.py` downloaded it (size and hash in the license audit) | Model terms unverified | None | None | Redistribution terms unknown | Keep it out of the repository |
| Landmark normalization for classifier input (kinivi `app.py`, `pre_process_landmark`) | Reference Only | Read function names and README | Apache-2.0 | None | None | — | The MVP uses rule-based ratios, not classifier input |
| TFLite classifiers, CSV data, notebooks (kinivi `model/`) | Reject | Listed 8 model and data files | Data origin not stated | None | None | TensorFlow cost; unknown data provenance | Not needed for rule-based gestures |
| FPS helper (kinivi `utils/cvfpscalc.py`) | Reimplement Independently | Read the file list | Apache-2.0 | `metrics.py` | None | — | Trivial; `metrics.py` needs percentiles anyway |
| Config parameter list (Virtual-Mouse `src/config.py`) | Reference Only | Read the file | MIT | None | None | Author's values are not tuned for this project | Used as a checklist of settings only |
| Dead zone and mapping region (Virtual-Mouse `src/main.py`) | Reimplement Independently | Read the code | MIT | `geometry.py` (`apply_dead_zone`, `map_to_screen`) | None | — | The Bible requires pure, tested functions |
| Click, drag, and scroll semantics (Virtual-Mouse) | Reject | README gesture table | MIT | None | None | — | Conflicts with the MVP gesture table |
| `pag.FAILSAFE = False` (Virtual-Mouse `src/main.py` line 43) | Reject | Read line 43 | MIT | None | None | Removes the emergency stop | Violates FR-17 |
| `xrandr` multi-monitor code (Virtual-Mouse `src/main.py` lines 24-30) | Reject | Read the code; uses `subprocess` | MIT | None | None | Linux only; runs an external program | Multi-monitor is not in the MVP; the project forbids `subprocess` in the app |
| Two input libraries, `pyautogui` + `pynput` (Virtual-Mouse) | Reject | Read the imports | MIT | None | None | Extra dependency | One input library is enough |

**Result:** no component is copied or adapted. `THIRD_PARTY_NOTICES.txt` stays at "None at this time."

**Phase 4 gate:** the dossier's hand-landmarker approach (Tasks API, VIDEO mode, `detect_for_video`, one hand) is confirmed. mediapipe 1.1.0 has no `mediapipe.solutions`, so the legacy API used by kinivi and Virtual-Mouse is not even available in the project environment.
