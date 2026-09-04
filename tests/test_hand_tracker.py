from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from gesture_mouse.config import TrackerConfig
from gesture_mouse.errors import ModelNotFoundError
from gesture_mouse.hand_tracker import HandTracker, observation_from_result


def fake_result(hands: int = 1, with_handedness: bool = True) -> SimpleNamespace:
    points = [SimpleNamespace(x=i / 21, y=1 - i / 21, z=0.01 * i) for i in range(21)]
    category = SimpleNamespace(category_name="Right", score=0.93)
    return SimpleNamespace(
        hand_landmarks=[points] * hands,
        handedness=[[category]] * hands if with_handedness else [],
    )


def tracker_with_file(tmp_path: Path) -> HandTracker:
    model = tmp_path / "hand.task"
    model.write_bytes(b"not a real model")
    return HandTracker(TrackerConfig(model_path=str(model)))


def test_u_ht_01_missing_model_raises_without_mediapipe(tmp_path: Path) -> None:
    code = (
        "import sys\n"
        "from gesture_mouse.config import TrackerConfig\n"
        "from gesture_mouse.hand_tracker import HandTracker\n"
        "from gesture_mouse.errors import ModelNotFoundError\n"
        "try:\n"
        f"    HandTracker(TrackerConfig(model_path={str(tmp_path / 'none.task')!r}))\n"
        "except ModelNotFoundError as exc:\n"
        "    print('fetch_model.py' in str(exc), 'mediapipe' in sys.modules)\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "True False"


def test_u_ht_02_empty_model_rejected(tmp_path: Path) -> None:
    model = tmp_path / "empty.task"
    model.touch()
    with pytest.raises(ModelNotFoundError, match="empty"):
        HandTracker(TrackerConfig(model_path=str(model)))


def test_u_ht_03_result_conversion() -> None:
    obs = observation_from_result(fake_result())
    assert obs is not None
    assert obs.landmarks.shape == (21, 3)
    assert obs.landmarks[1][0] == pytest.approx(1 / 21)
    assert obs.handedness == "Right"
    assert obs.score == pytest.approx(0.93)
    assert observation_from_result(fake_result(hands=0)) is None
    assert observation_from_result(SimpleNamespace()) is None
    no_side = observation_from_result(fake_result(with_handedness=False))
    assert no_side is not None and no_side.handedness is None


def test_u_ht_04_timestamps_forced_to_increase(tmp_path: Path) -> None:
    tracker = tracker_with_file(tmp_path)
    stamps = [tracker.next_timestamp(t) for t in (10, 10, 5, 50, 50)]
    assert stamps == [10, 11, 12, 50, 51]


def test_u_ht_05_close_twice_is_safe(tmp_path: Path) -> None:
    tracker = tracker_with_file(tmp_path)
    tracker.close()
    closed: list[int] = []
    tracker._landmarker = SimpleNamespace(close=lambda: closed.append(1))
    tracker.close()
    tracker.close()
    assert closed == [1]


def test_relative_model_path_resolves_against_project(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from gesture_mouse import hand_tracker

    root = tmp_path / "project"
    (root / "models").mkdir(parents=True)
    (root / "models" / "m.task").write_bytes(b"x")
    monkeypatch.setattr(hand_tracker, "PROJECT_ROOT", root)
    monkeypatch.chdir(tmp_path)
    assert hand_tracker.resolve_model_path("models/m.task") == root / "models" / "m.task"
    assert hand_tracker.resolve_model_path("models/none.task") == Path("models/none.task")


@pytest.mark.hardware
def test_real_model_runs_on_a_blank_frame() -> None:
    tracker = HandTracker(TrackerConfig())
    try:
        assert tracker.detect(np.zeros((480, 640, 3), np.uint8), 1) is None
    finally:
        tracker.close()
