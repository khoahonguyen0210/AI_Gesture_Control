"""Run every automated check, in CI order. Run: python scripts/check_all.py [--all]"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_PIO = ROOT / "research" / "envs" / "platformio" / "Scripts" / "pio.exe"


def find_pio() -> str | None:
    found = shutil.which("pio")
    if found:
        return found
    return str(LOCAL_PIO) if LOCAL_PIO.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run every automated check, in CI order.")
    parser.add_argument("--hardware", action="store_true", help="also run the real-camera tests")
    parser.add_argument("--firmware", action="store_true", help="also build the Wokwi firmware")
    parser.add_argument("--all", action="store_true", help="same as --hardware --firmware")
    args = parser.parse_args()

    py = sys.executable
    steps: list[tuple[str, list[str] | None]] = [
        ("pip check", [py, "-m", "pip", "check"]),
        ("ruff lint", [py, "-m", "ruff", "check", "."]),
        ("ruff format", [py, "-m", "ruff", "format", "--check", "."]),
        ("mypy", [py, "-m", "mypy", "src"]),
        ("C and C++ tests", [py, "firmware/build.py", "--test", "--sanitize"]),
        ("Python tests", [py, "-m", "pytest", "-q", "-m", "not hardware"]),
    ]
    if args.hardware or args.all:
        steps.append(("camera tests", [py, "-m", "pytest", "-q", "-m", "hardware"]))
    if args.firmware or args.all:
        pio = find_pio()
        steps.append(("Wokwi firmware", [pio, "run", "-d", "firmware/wokwi"] if pio else None))

    results = []
    for name, cmd in steps:
        print(f"\n=== {name}", flush=True)
        if cmd is None:
            print("PlatformIO not found. Install it with: python -m pip install platformio")
            results.append((name, False, 0.0))
            continue
        start = time.perf_counter()
        ok = subprocess.run(cmd, cwd=ROOT).returncode == 0
        results.append((name, ok, time.perf_counter() - start))

    print("\n=== Summary")
    for name, ok, seconds in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<16} {seconds:6.1f} s")
    failed = [name for name, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
