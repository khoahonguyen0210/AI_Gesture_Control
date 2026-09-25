from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from gesture_mouse.serial_backend import SerialLink, decode
from test_serial_backend import FakePort, StepClock

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "serial_check.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("serial_check", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["serial_check"] = module
    spec.loader.exec_module(module)
    return module


class DroppingPort(FakePort):
    """Loses the reply to one sequence number."""

    def write(self, data: bytes) -> int:
        if any(f.seq == 47 for f in decode(data)):
            self.sent += data
            return len(data)
        return super().write(data)


def test_measure_counts_replies_and_lost_frames() -> None:
    clock = StepClock()
    link = SerialLink(DroppingPort(), clock, sleep=clock.sleep)
    times, lost = load_script().measure(link, 300, timeout_ms=20)
    assert lost == [47]
    assert len(times) == 299
    assert max(times) == 0
