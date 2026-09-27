"""Build and test the C protocol code and the C++ differential tests on this computer.

Run: python firmware/build.py --test [--sanitize]
     python firmware/build.py --fuzz 120
On Windows, uses MSVC first (MinGW has no sanitizers); elsewhere gcc or clang. Warnings are errors.
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
FUZZ = ROOT / "fuzz"
OUT = ROOT / "build"
LIBRARY = [SRC / "protocol.c", SRC / "device.c"]
PROGRAMS = {
    "test_protocol": TEST / "test_protocol.c",
    "device_sim": TEST / "device_sim.c",
    "differential_test": FUZZ / "differential_test.cpp",
}
TESTS = ("test_protocol", "differential_test")
VSWHERE = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
C_PAIRS = {"gcc": "g++", "clang": "clang++", "cc": "c++"}


@dataclass
class Compiler:
    name: str
    cc: str
    cxx: str | None
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


def find_msvc() -> Compiler | None:
    env = msvc_env()
    cl = shutil.which("cl", path=env.get("PATH") or env.get("Path")) if env else None
    return Compiler("msvc", cl, cl, env, msvc=True) if env and cl else None


def find_compiler() -> Compiler | None:
    if sys.platform == "win32":
        msvc = find_msvc()
        if msvc:
            return msvc
    for name, cxx_name in C_PAIRS.items():
        cc = shutil.which(name)
        if cc:
            return Compiler(name, cc, shutil.which(cxx_name), dict(os.environ), msvc=False)
    return None


def exe(name: str) -> Path:
    return OUT / (name + (".exe" if sys.platform == "win32" else ""))


def sanitizer_flags(compiler: Compiler) -> list[str]:
    if compiler.msvc:
        return ["/fsanitize=address", "/Zi"]
    return ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-g"]


def _run(cmd: list[str], compiler: Compiler, what: str) -> None:
    result = subprocess.run(cmd, env=compiler.env, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Build of {what} failed:\n{result.stdout}{result.stderr}")


def _build_msvc(compiler: Compiler, name: str, main: Path, flags: list[str]) -> Path:
    target = exe(name)
    base = [compiler.cc, "/nologo", "/W4", "/WX", "/O2", f"/I{SRC}", *flags]
    objects = []
    for source in LIBRARY:
        obj = OUT / f"{name}-{source.stem}.obj"
        _run(
            [*base, "/std:c11", "/c", str(source), f"/Fo{obj}", f"/Fd{OUT / name}.pdb"],
            compiler,
            name,
        )
        objects.append(str(obj))
    std = ["/std:c++17", "/EHsc"] if main.suffix == ".cpp" else ["/std:c11"]
    cmd = [*base, *std, str(main), *objects, f"/Fe{target}", f"/Fo{OUT}{os.sep}"]
    _run([*cmd, f"/Fd{OUT / name}.pdb"], compiler, name)
    return target


def _build_gnu(compiler: Compiler, name: str, main: Path, flags: list[str]) -> Path:
    target = exe(name)
    warn = ["-Wall", "-Wextra", "-Wpedantic", "-Werror", "-Wconversion", "-O2", f"-I{SRC}"]
    objects = []
    for source in LIBRARY:
        obj = OUT / f"{name}-{source.stem}.o"
        _run(
            [compiler.cc, "-std=c11", *warn, *flags, "-c", str(source), "-o", str(obj)],
            compiler,
            name,
        )
        objects.append(str(obj))
    if main.suffix == ".cpp":
        if compiler.cxx is None:
            raise RuntimeError(f"No C++ compiler found next to {compiler.name}.")
        cmd = [compiler.cxx, "-std=c++17", *warn, *flags, str(main), *objects, "-o", str(target)]
    else:
        cmd = [compiler.cc, "-std=c11", *warn, *flags, str(main), *objects, "-o", str(target)]
    _run(cmd, compiler, name)
    return target


def build_one(compiler: Compiler, name: str, main: Path, flags: list[str]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    if compiler.msvc:
        return _build_msvc(compiler, name, main, flags)
    return _build_gnu(compiler, name, main, flags)


def build(compiler: Compiler, sanitize: bool = False) -> dict[str, Path]:
    flags = sanitizer_flags(compiler) if sanitize else []
    return {name: build_one(compiler, name, main, flags) for name, main in PROGRAMS.items()}


def fuzz(compiler: Compiler, seconds: int) -> int:
    """Coverage-guided fuzzing with libFuzzer (MSVC or Clang; GCC has no libFuzzer)."""
    if compiler.msvc:
        flags = ["/fsanitize=fuzzer", "/fsanitize=address", "/Zi"]
    elif "clang" in compiler.name:
        flags = ["-fsanitize=fuzzer,address,undefined", "-g"]
    else:
        print("libFuzzer needs MSVC or Clang.", file=sys.stderr)
        return 1
    target = build_one(compiler, "fuzz_parser", FUZZ / "fuzz_parser.cpp", flags)
    corpus = OUT / "fuzz_corpus"
    corpus.mkdir(exist_ok=True)
    run = [
        str(target),
        str(corpus),
        f"-max_total_time={seconds}",
        "-max_len=256",
        "-print_final_stats=1",
    ]
    return subprocess.run(run, env=compiler.env, cwd=OUT, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and test the C and C++ protocol code.")
    parser.add_argument("--test", action="store_true", help="run the C and C++ tests")
    parser.add_argument("--sanitize", action="store_true", help="build with sanitizers")
    parser.add_argument("--fuzz", type=int, metavar="SECONDS", help="run libFuzzer for SECONDS")
    args = parser.parse_args()

    compiler = find_compiler()
    if compiler is None:
        print("No C compiler found (gcc, clang, or MSVC).", file=sys.stderr)
        return 1
    print(f"Compiler: {compiler.name} ({compiler.cc})")
    try:
        if args.fuzz:
            return fuzz(compiler, args.fuzz)
        built = build(compiler, args.sanitize)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    print("Built:", ", ".join(p.name for p in built.values()))
    if args.test:
        for name in TESTS:
            code = subprocess.run([str(built[name])], env=compiler.env, check=False).returncode
            if code != 0:
                return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
