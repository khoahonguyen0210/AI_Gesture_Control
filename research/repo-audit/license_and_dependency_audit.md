# License and Dependency Audit

## Project dependencies

Resolved on 2026-10-09 with Python 3.12.10 on Windows 11. `pip check` reported "No broken requirements found." Exact versions of every installed package are in `requirements.lock.txt`. Licenses come from the installed package metadata.

| Package | Version | License | Role |
|---|---|---|---|
| mediapipe | 1.1.0 | Apache-2.0 | Hand landmark model runtime |
| opencv-contrib-python | 5.0.0.93 | Apache-2.0 | Camera, drawing, preview window |
| numpy | 2.5.3 | BSD-3-Clause and others (0BSD, MIT, Zlib, CC0-1.0) | Landmark math |
| pyautogui | 0.9.54 | BSD | Mouse control |
| pytest | 9.1.1 | MIT | Tests (dev) |
| pytest-cov | 7.1.0 | MIT | Coverage (dev) |
| ruff | 0.17.0 | MIT | Lint and format (dev) |
| mypy | 2.4.0 | MIT | Type checks (dev) |
| build | 1.6.1 | MIT | Builds the sdist and wheel (dev, Extension D) |
| pyproject_hooks | 1.3.3 | MIT | Needed by `build` |
| pyserial | 3.5 | BSD-3-Clause | Serial ports and `rfc2217://` for `--serial` (optional extra `serial`, and dev) |

Notes:

- mediapipe 1.1.0 requires `opencv-contrib-python`, `matplotlib`, `sounddevice`, `absl-py`, `flatbuffers`, and `certifi`. The project does not import the last four itself.
- mediapipe 1.1.0 exposes only `Image`, `ImageFormat`, and `tasks` at the top level. The legacy `mediapipe.solutions` API is not present, which matches the plan to use the Tasks API.
- numpy 2.5.3 requires Python 3.12 or newer, so the project requires Python 3.12 or 3.13.

## Wokwi demo tools and libraries

Added on 2026-10-10. None of these are copied into the repository. PlatformIO downloads them when the firmware is built, and the firmware binary is not committed.

| Item | Version | License | Role |
|---|---|---|---|
| PlatformIO Core | 6.2.0 | Apache-2.0 | Builds the firmware (installed in its own environment, not a project dependency) |
| Espressif 32 platform | 6.9.0 | Apache-2.0 | PlatformIO board support |
| Arduino-ESP32 | 2.0.17 | LGPL-2.1-or-later | Arduino core for the ESP32 |
| Adafruit SSD1306 | 2.5.17 | BSD | OLED driver |
| Adafruit GFX Library | 1.12.6 | BSD | Text and shapes on the OLED |
| Adafruit BusIO | 1.17.4 | MIT | Needed by the Adafruit libraries |
| Wokwi for VS Code | Owner's install | Free license for open-source projects; commercial use needs a paid plan | Runs the simulated ESP32 |

Notes:

- Arduino-ESP32 is LGPL. The firmware is built only for the simulator and is not shipped, so no binary is distributed.
- The Wokwi license needs a free Wokwi account and lasts 30 days. The app sends the simulator only mouse action frames, over localhost.

## Hand landmark model

| Item | Value |
|---|---|
| Source | `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task` |
| Fetched by | `python scripts/fetch_model.py` on 2026-10-09 |
| Size | 7,819,105 bytes |
| SHA-256 | `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1` |
| Redistribution terms | Not stated in the guides that were read. Unverified. |
| Decision | Downloaded at setup time; never committed (`models/` and `*.task` are ignored). |

## Reference repositories

Cloned with `git clone --depth 1` into `research/reference_repos/` (ignored by Git) on 2026-10-09. Nothing from them is copied into this project.

### google-ai-edge/mediapipe-samples (`9cabe32b`)

1. **License:** Apache-2.0, from the root `LICENSE`. It starts with "Copyright 2022 The TensorFlow Authors. All rights reserved." followed by the standard Apache 2.0 text.
2. **NOTICE file:** none at the root, and no license or notice file inside `examples/hand_landmarker/`.
3. **Assets:** the notebook downloads the model and a sample image (`woman_hands.jpg`) at run time; neither is stored in the repository.
4. **Attribution duties if code were copied:** a copy of the license, kept notices, and marked changes.
5. **Dependencies:** the notebook runs `pip install -q mediapipe`.
6. **Network use in scripts:** the notebook cells call `pip install` and `wget` twice (model and sample image).
7. **Compatibility:** the API names used in the notebook exist in mediapipe 1.1.0. The notebook itself was not run.
8. **Tests:** no tests for the Python example. Android examples elsewhere in the repository contain unit tests, which do not apply here.

### kinivi/hand-gesture-recognition-mediapipe (`0e737bb8`)

1. **License:** Apache-2.0, from `LICENSE`. Standard text, with no project-specific copyright line.
2. **Assets:** 8 model and data files under `model/` (`.tflite`, `.hdf5`, `.csv`). Their data origin is not stated. Not copied.
3. **Attribution duties if code were copied:** as for Apache-2.0 above, crediting Kazuhito Takahashi and Nikita Kiselov as the README does.
4. **Dependencies (README):** mediapipe 0.8.1, OpenCV 3.4.2 or later, TensorFlow 2.3.0 or later.
5. **Network use in scripts:** none found in `app.py`.
6. **Compatibility:** incompatible (error recorded). On Python 3.12, `pip install --dry-run "mediapipe==0.8.1" "opencv-python>=3.4.2" "tensorflow>=2.3.0"` failed with "No matching distribution found for mediapipe==0.8.1"; the oldest version offered is 0.10.13. An older interpreter was not available, and the attempt was time-boxed, so it was not tried further.
7. **Tests:** none (`git ls-files | grep -i test` printed nothing).

### Rounak7721/Virtual-Mouse (`495b2933`)

1. **License:** MIT, from `LICENSE`, "Copyright (c) 2026 Rounak Sonavane".
2. **Assets:** three images under `assets/`. Not copied.
3. **Attribution duties if code were copied:** keep the copyright and permission notice.
4. **Dependencies (`requirements.txt`):** opencv-python 4.13.0.92, mediapipe 0.10.14, numpy 2.4.4, pyautogui 0.9.54, pynput 1.8.2 (header says Python 3.12.3).
5. **Network use in scripts:** none. It runs `xrandr` through `subprocess` (Linux only).
6. **Compatibility:** see the run attempt in `repository_comparison.md`.
7. **Tests:** none (`git ls-files | grep -i test` printed nothing).

### Open questions

- The redistribution terms of `hand_landmarker.task` are still unverified. The model card was not reviewed. The model stays out of the repository.
