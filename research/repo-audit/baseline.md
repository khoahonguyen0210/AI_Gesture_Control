# Baseline

This is the state of the machine and the repository on 2026-10-09, before any application code was written.

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
| What was done | Installed Python 3.12.10 (64-bit) with `py install 3.12` |
| Interpreter used by the project | 3.12.10, 64-bit, in `.venv` |

## Files that already existed

| File | What it was | What happened to it |
|---|---|---|
| `LICENSE` | MIT license, copyright 2026 khoahonguyen0210 | Kept. The owner chose MIT. |
| `README.md` | Title only | Kept. The owner asked for a full README at the end. |
| `.gitattributes` | Line-ending normalization | Kept |
| `.gitignore` | GitHub's Python template plus `project-context/` | Rewritten for this project. `project-context/` is still ignored |
| `project-context/` | The private planning documents | Not tracked, by the owner's choice |

There was no source code, no tests, and no virtual environment. The repository had one commit ("Initial commit") on `main`.

## Where the planning documents and the workspace disagreed

1. The planning documents said not to create a `README.md`. The owner asked for one, so the owner's request won. See `integration_log.md`.
2. The planning documents said to commit themselves to Git. The owner keeps them out of Git, so `project-context/` is ignored.
3. The planning documents expected the folder name `project_context/`, but the workspace has `project-context/project_context/`. Both names are ignored.
