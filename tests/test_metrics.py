from __future__ import annotations

import math

import pytest

from gesture_mouse.metrics import FpsCounter, Recorder, summarize


def test_u_met_01_summary_of_known_values() -> None:
    s = summarize(range(1, 101))
    assert s == {"median": 50.5, "p95": 95, "max": 100, "count": 100}
    assert summarize([3.0])["p95"] == 3.0
    assert summarize([4, 1, 3])["median"] == 3


def test_empty_summary() -> None:
    s = summarize([])
    assert s["count"] == 0 and math.isnan(s["median"])


def test_u_met_02_timer_records_durations() -> None:
    ticks = iter([1.000, 1.004, 2.000, 2.010])
    rec = Recorder(clock=lambda: next(ticks))
    with rec.time("inference"):
        pass
    with rec.time("inference"):
        pass
    assert list(rec.samples["inference"]) == pytest.approx([4.0, 10.0])
    assert rec.summary()["inference"]["max"] == pytest.approx(10.0)


def test_recorder_bounds_memory() -> None:
    rec = Recorder(max_samples=3)
    for i in range(10):
        rec.add("total", float(i))
    assert list(rec.samples["total"]) == [7.0, 8.0, 9.0]


def test_fps_counter() -> None:
    fps = FpsCounter(window=5)
    assert fps.tick(0.0) == 0.0
    for i in range(1, 10):
        value = fps.tick(i / 30)
    assert value == pytest.approx(30.0)
