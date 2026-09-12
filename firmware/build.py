"""Build and test the C protocol code on this computer.

Run: python firmware/build.py --test [--sanitize]
Uses gcc or clang when found, otherwise MSVC from Visual Studio. Warnings are errors.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
TEST = ROOT / "test"
OUT = ROOT / "build"
LIBRARY = [SRC / "protocol.c", SRC / "device.c"]
PROGRAMS = {"test_protocol": TEST / "test_protocol.c", "device_sim": TEST / "device_sim.c"}
VSWHERE = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")


@dataclass
class Compiler:
    name: str
    path: str
    env: dict[str, str]
    msvc: bool


def msvc_env() -> dict[str, str] | None:
    """Environment from vcvars64.bat, read once so cl.exe can be called directly."""
    if sys.platform != "win32" or not VSWHERE.exists():
        return None
    query = [str(VSWHERE), "-latest", "-products", "*", "-property", "installationPath"]
    query += ["-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64"]
    found = subprocess.run(query, capture_output=True, text=True, check=False).stdout.strip()
    vcvars = Path(found) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
    if not found or not vcvars.exists():
        return None
    dump = subprocess.run(
        ["cmd.exe", "/d", "/c", "call", str(vcvars), ">nul", "&&", "set"],
        capture_output=True,
        text=True,
        check=False,
    )
    env = dict(line.split("=", 1) for line in dump.stdout.splitlines() if "=" in line)
    return env if "INCLUDE" in env else None


def find_compiler() -> Compiler | None:
    for name in ("gcc", "clang", "cc"):
        path = shutil.which(name)
        if path:
            return Compiler(name, path, dict(os.environ), msvc=False)
    env = msvc_env()
    if env:
        path = shutil.which("cl", path=env.get("PATH") or env.get("Path"))
        if path:
            return Compiler("msvc", path, env, msvc=True)
    return None


def exe(name: str) -> Path:
    return OUT / (name + (".exe" if sys.platform == "win32" else ""))


def sanitizer_flags(compiler: Compiler) -> list[str]:
    if compiler.msvc:
        return ["/fsanitize=address", "/Zi"]
    return ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-g"]


def build(compiler: Compiler, sanitize: bool = False) -> dict[str, Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    built = {}
    for name, main_file in PROGRAMS.items():
        sources = [str(p) for p in (*LIBRARY, main_file)]
        target = exe(name)
        if compiler.msvc:
            cmd = [compiler.path, "/nologo", "/std:c11", "/W4", "/WX", "/O2", f"/I{SRC}"]
            cmd += sanitizer_flags(compiler) if sanitize else []
            cmd += [*sources, f"/Fe{target}", f"/Fo{OUT}{os.sep}", f"/Fd{OUT / name}.pdb"]
        else:
            cmd = [compiler.path, "-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-Werror"]
            cmd += ["-Wconversion", "-O2", f"-I{SRC}"]
            cmd += sanitizer_flags(compiler) if sanitize else []
            cmd += [*sources, "-o", str(target)]
        result = subprocess.run(cmd, env=compiler.env, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Build of {name} failed:\n{result.stdout}{result.stderr}")
        built[name] = target
    return built


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and test the C protocol code.")
    parser.add_argument("--test", action="store_true", help="run the C tests after building")
    parser.add_argument("--sanitize", action="store_true", help="build with sanitizers")
    args = parser.parse_args()

    compiler = find_compiler()
    if compiler is None:
        print("No C compiler found (gcc, clang, or MSVC).", file=sys.stderr)
        return 1
    print(f"Compiler: {compiler.name} ({compiler.path})")
    try:
        built = build(compiler, args.sanitize)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    print("Built:", ", ".join(p.name for p in built.values()))
    if args.test:
        run = subprocess.run([str(built["test_protocol"])], env=compiler.env, check=False)
        return run.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
