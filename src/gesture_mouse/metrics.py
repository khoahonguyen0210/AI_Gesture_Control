"""Stage timers, rolling FPS, and percentile summaries."""

from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Callable, Iterable
from types import TracebackType

STAGES = ("capture", "preprocess", "inference", "recognize", "dispatch", "draw", "display")


def summarize(samples: Iterable[float]) -> dict[str, float]:
    """Median, 95th percentile (nearest rank), maximum, and count."""
    data = sorted(samples)
    n = len(data)
    if n == 0:
        return {"median": math.nan, "p95": math.nan, "max": math.nan, "count": 0}
    mid = n // 2
    median = data[mid] if n % 2 else (data[mid - 1] + data[mid]) / 2
    p95 = data[max(0, math.ceil(0.95 * n) - 1)]
    return {"median": median, "p95": p95, "max": data[-1], "count": n}


class StageTimer:
    """Context manager that adds the elapsed milliseconds to a recorder stage."""

    def __init__(self, recorder: Recorder, stage: str) -> None:
        self.recorder = recorder
        self.stage = stage
        self._start = 0.0

    def __enter__(self) -> StageTimer:
        self._start = self.recorder.clock()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.recorder.add(self.stage, (self.recorder.clock() - self._start) * 1000.0)


class Recorder:
    """Keeps per-stage durations in ms. Set max_samples to bound memory in long runs."""

    def __init__(
        self,
        max_samples: int | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.clock = clock
        self.samples: dict[str, deque[float]] = {
            s: deque(maxlen=max_samples) for s in (*STAGES, "total")
        }

    def time(self, stage: str) -> StageTimer:
        return StageTimer(self, stage)

    def add(self, stage: str, ms: float) -> None:
        self.samples[stage].append(ms)

    def summary(self) -> dict[str, dict[str, float]]:
        return {stage: summarize(values) for stage, values in self.samples.items()}


class FpsCounter:
    """Frames per second over the last `window` frames."""

    def __init__(self, window: int = 30) -> None:
        self._times: deque[float] = deque(maxlen=window)

    def tick(self, t_s: float) -> float:
        self._times.append(t_s)
        if len(self._times) < 2:
            return 0.0
        span = self._times[-1] - self._times[0]
        return (len(self._times) - 1) / span if span > 0 else 0.0
