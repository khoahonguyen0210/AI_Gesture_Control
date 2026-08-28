from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from gesture_mouse.config import AppConfig
from helpers import make_landmarks

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "evaluate_gestures.py"
PLAN = [
    ("point", "point", 10),
    ("left_pinch", "pinch_left", 4),
    ("point", "point", 8),
    ("right_pinch", "pinch_right", 10),
    ("other", "open", 5),
    ("open_palm", "open", 10),
    ("fist", "fist", 10),
    ("two_finger", "two_finger", 10),
]


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("evaluate_gestures", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["evaluate_gestures"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ev() -> ModuleType:
    return load_script()


def write_session(path: Path, plan: list[tuple[str, str, int]]) -> None:
    lines = [json.dumps({"meta": {"note": "synthetic"}})]
    t = 0
    for label, pose, n in plan:
        for _ in range(n):
            t += 33
            lm = make_landmarks(pose).tolist()
            lines.append(json.dumps({"t_ms": t, "label": label, "landmarks": lm}))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_confusion_is_diagonal_for_clean_poses(ev: ModuleType, tmp_path: Path) -> None:
    write_session(tmp_path / "a.jsonl", PLAN)
    sessions = ev.load_sessions([str(tmp_path / "*.jsonl")])
    assert sessions[0].note == "synthetic"
    counts = ev.frame_confusion(sessions, AppConfig())
    assert counts[("point", "point")] == 18
    assert counts[("none", "none")] == 20
    assert counts[("scroll", "scroll")] == 10
    assert sum(n for (e, p), n in counts.items() if e != p) == 0
    pr = ev.precision_recall(counts)
    assert pr["left_pinch"] == {"tp": 4, "predicted": 4, "actual": 4}


def test_event_report_counts_hits_and_false_clicks(ev: ModuleType, tmp_path: Path) -> None:
    write_session(tmp_path / "a.jsonl", PLAN)
    report = ev.event_report(ev.load_sessions([str(tmp_path / "a.jsonl")]), AppConfig())
    assert report["expected_left"] == 1 and report["hit_left"] == 1
    assert report["expected_right"] == 1 and report["hit_right"] == 1
    assert report["false_events"] == 0
    assert report["minutes"] > 0


def test_pinch_recorded_under_a_negative_label_is_a_false_click(
    ev: ModuleType, tmp_path: Path
) -> None:
    write_session(tmp_path / "b.jsonl", [("point", "point", 5), ("fist", "pinch_left", 4)] * 2)
    report = ev.event_report(ev.load_sessions([str(tmp_path / "b.jsonl")]), AppConfig())
    assert report["expected_left"] == 0
    assert report["false_events"] >= 1


def test_segments_split_on_label_change_and_gap(ev: ModuleType) -> None:
    rows = [ev.Row(t, label, None) for t, label in [(0, "a"), (30, "a"), (60, "b"), (90, "a")]]
    rows.append(ev.Row(2000, "a", None))
    assert ev.segments(rows, "a") == [(0, 30), (90, 90), (2000, 2000)]


def test_ratio_summary(ev: ModuleType, tmp_path: Path) -> None:
    write_session(tmp_path / "a.jsonl", PLAN)
    summary = ev.ratio_summary(ev.load_sessions([str(tmp_path / "a.jsonl")]), AppConfig())
    assert summary["left_pinch"]["ratio_ti"][1] == pytest.approx(0.05)


def test_pct_shows_counts(ev: ModuleType) -> None:
    assert ev.pct(1, 4) == " 25.0% (1/4)"
    assert "0/0" in ev.pct(0, 0)
