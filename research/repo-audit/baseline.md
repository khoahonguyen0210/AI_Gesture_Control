# Baseline

Recorded on 2026-10-09, before any application code was written.

## Machine

| Item | Value |
|---|---|
| Laptop | Lenovo ThinkPad X1 Yoga (model 21CEX50400) |
| CPU | 12th Gen Intel Core i7-1260P |
| RAM | 16 GB |
| OS | Windows 11 Pro, version 10.0.26200 |
| Webcam | "Integrated Camera", device status OK (not opened during the baseline) |
| Git | 2.55.0.windows.5 |

## Python

| Check | Result |
|---|---|
| `py -0p` before setup | Only Python 3.14 (64-bit) was installed |
| Action | Installed Python 3.12.10 (64-bit) with `py install 3.12` |
| Project interpreter | 3.12.10, 64-bit, in `.venv` |

## Existing files

| File | Purpose | Action |
|---|---|---|
| `LICENSE` | MIT license, copyright 2026 khoahonguyen0210 | Kept. The owner chose MIT. |
| `README.md` | Title only | Kept. The owner asked for a full README at the end. |
| `.gitattributes` | Line-ending normalization | Kept |
| `.gitignore` | GitHub Python template plus `project-context/` | Rewritten for this project; `project-context/` stays ignored |
| `project-context/` | The four handbooks | Not tracked, by owner decision |

There was no source code, no tests, and no virtual environment. The repository had one commit ("Initial commit") on `main`.

## Conflicts between the handbooks and the workspace

1. The handbooks say "do not create README.md". The owner asked for one. The owner's request wins; see `integration_log.md`.
2. The handbooks say to commit the handbooks. The owner keeps them out of Git (`project-context/` is ignored).
3. The handbooks place them in `project_context/`; the workspace has `project-context/project_context/`. Both names are ignored.
