"""Python host talks to the C device code (device_sim) through a pipe. No hardware is used."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from gesture_mouse.config import CursorConfig
from gesture_mouse.gesture_recognizer import Action, ActionType
from gesture_mouse.mouse_controller import MouseController
from gesture_mouse.serial_backend import MsgType, SerialBackend, decode, encode

BUILD_SCRIPT = Path(__file__).resolve().parent.parent / "firmware" / "build.py"
WATCHDOG_MS = 500
BYTE_TIMEOUT_MS = 50
HEARTBEAT_MS = 100
A = ActionType


def load_build() -> ModuleType:
    spec = importlib.util.spec_from_file_location("firmware_build", BUILD_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["firmware_build"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def device_sim() -> tuple[Path, dict[str, str]]:
    build = load_build()
    compiler = build.find_compiler()
    if compiler is None:
        pytest.skip("no C compiler found")
    return build.build(compiler)["device_sim"], compiler.env


class SimLink:
    """Writes frames as device_sim input lines, stamped with the simulated time."""

    def __init__(self) -> None:
        self.t = 0
        self.lines: list[str] = []

    def clock(self) -> int:
        return self.t

    def write(self, data: bytes) -> int:
        self.lines.append(f"T {self.t}")
        self.lines.append("X " + data.hex(" "))
        return len(data)

    def raw(self, data: bytes) -> None:
        self.write(data)

    def advance(self, ms: int) -> None:
        self.t += ms
        self.lines.append(f"T {self.t}")


def run_sim(sim: tuple[Path, dict[str, str]], link: SimLink) -> list[str]:
    exe, env = sim
    result = subprocess.run(
        [str(exe), str(WATCHDOG_MS), str(BYTE_TIMEOUT_MS)],
        input="\n".join(link.lines) + "\n",
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=True,
    )
    return result.stdout.splitlines()


def replies(lines: list[str]) -> list[Any]:
    data = b"".join(bytes.fromhex(line[6:]) for line in lines if line.startswith("REPLY"))
    return decode(data)


def events(lines: list[str]) -> list[str]:
    return [line for line in lines if not line.startswith("REPLY")]


def test_gesture_session_round_trip(device_sim: tuple[Path, dict[str, str]]) -> None:
    link = SimLink()
    backend = SerialBackend(link, HEARTBEAT_MS, link.clock, size=(1000, 800))
    mc = MouseController(backend, CursorConfig())
    backend.hello()
    steps = [
        Action(A.MOVE, 0.6, 0.5),
        Action(A.LEFT_CLICK, 0.6, 0.5),
        Action(A.DRAG_START, 0.6, 0.5),
        Action(A.DRAG_MOVE, 0.4, 0.25),
        Action(A.DRAG_END),
        Action(A.RIGHT_CLICK),
        Action(A.SCROLL, amount=-3),
    ]
    for action in steps:
        link.advance(30)
        mc.apply(action)
        backend.tick()
    mc.release_all()

    lines = run_sim(device_sim, link)
    assert events(lines) == [
        "HELLO v1",
        "MOVE 99 0",
        "BUTTON left down",
        "BUTTON left up",
        "BUTTON left down",
        "MOVE -199 -200",
        "BUTTON left up",
        "BUTTON right down",
        "BUTTON right up",
        "SCROLL -3",
        "RELEASE_ALL buttons=0",
        "END buttons=0 state=0 x=-100 y=-200 scroll=-3",
    ]
    got = replies(lines)
    assert got[0].type == MsgType.HELLO_ACK and got[0].payload[0] == 1
    assert all(f.type == MsgType.ACK and f.payload[0] == f.seq for f in got[1:])
    assert [f.seq for f in got] == list(range(len(got)))


def test_watchdog_releases_button_when_host_goes_silent(
    device_sim: tuple[Path, dict[str, str]],
) -> None:
    link = SimLink()
    backend = SerialBackend(link, HEARTBEAT_MS, link.clock)
    backend.mouse_down("left")
    for _ in range(5):
        link.advance(HEARTBEAT_MS)
        backend.tick()
    link.advance(WATCHDOG_MS + 1)

    lines = events(run_sim(device_sim, link))
    assert lines[0] == "BUTTON left down"
    assert lines.count("HEARTBEAT") == 5
    assert lines[-2] == f"WATCHDOG release_all at {link.t} ms"
    assert lines[-1].startswith("END buttons=0")


def test_bad_bytes_get_nack_and_do_not_run(device_sim: tuple[Path, dict[str, str]]) -> None:
    link = SimLink()
    corrupted = bytearray(encode(MsgType.BUTTON, 9, b"\x00\x01"))
    corrupted[-1] ^= 0xFF
    link.raw(b"\x00\x13\x37")
    link.raw(bytes(corrupted))
    link.raw(encode(MsgType.ACK, 10, b"\x0a"))
    link.raw(encode(MsgType.HEARTBEAT, 11))

    lines = run_sim(device_sim, link)
    assert "BUTTON left down" not in lines
    assert "BAD_FRAME seq=9 reason=1" in lines
    assert "REJECTED seq=10 type=0x30" in lines
    assert "HEARTBEAT" in lines
    nacks = [f for f in replies(lines) if f.type == MsgType.NACK]
    assert [(f.payload[0], f.payload[1]) for f in nacks] == [(9, 1), (10, 3)]
    assert lines[-1].startswith("END buttons=0")
