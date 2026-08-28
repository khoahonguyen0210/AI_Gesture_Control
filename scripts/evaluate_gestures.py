"""Evaluate the rule-based recognizer on recorded landmarks (from record_landmarks.py).

Run: python scripts/evaluate_gestures.py --input "output/recordings/*.jsonl"
     python scripts/evaluate_gestures.py --input "output/recordings/*.jsonl" --summarize
Every percentage is printed with its counts. Results hold only for the recorded people and
conditions.
"""

from __future__ import annotations

import argparse
import glob
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

from gesture_mouse.config import AppConfig, load_config
from gesture_mouse.geometry import Intent, classify_pose, intent_for
from gesture_mouse.gesture_recognizer import ActionType, GestureRecognizer, HandObservation

OUT_DIR = Path(__file__).resolve().parent.parent / "output" / "evaluation"
EXPECTED = {
    "point": "point",
    "left_pinch": "left_pinch",
    "right_pinch": "right_pinch",
    "two_finger": "scroll",
    "open_palm": "none",
    "fist": "none",
}
PREDICTED = {
    Intent.POINT: "point",
    Intent.LEFT_PINCH: "left_pinch",
    Intent.RIGHT_PINCH: "right_pinch",
    Intent.SCROLL: "scroll",
    Intent.NONE: "none",
    Intent.UNSURE: "unsure",
}
CLASSES = ("point", "left_pinch", "right_pinch", "scroll", "none")
GAP_MS = 500
MATCH_WINDOW_MS = 500


@dataclass
class Row:
    t_ms: int
    label: str
    landmarks: np.ndarray


@dataclass
class Session:
    name: str
    note: str
    rows: list[Row] = field(default_factory=list)

    @property
    def minutes(self) -> float:
        total = 0
        for a, b in zip(self.rows, self.rows[1:], strict=False):
            if b.t_ms - a.t_ms <= GAP_MS:
                total += b.t_ms - a.t_ms
        return total / 60000


def load_sessions(patterns: list[str]) -> list[Session]:
    paths = sorted({Path(p) for pattern in patterns for p in glob.glob(pattern)})
    sessions = []
    for path in paths:
        session = Session(path.stem, "")
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if "meta" in item:
                session.note = item["meta"].get("note", "")
                continue
            lm = np.asarray(item["landmarks"], dtype=float)
            session.rows.append(Row(int(item["t_ms"]), item["label"], lm))
        session.rows.sort(key=lambda r: r.t_ms)
        sessions.append(session)
    return sessions


def frame_confusion(sessions: list[Session], cfg: AppConfig) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for session in sessions:
        for row in session.rows:
            if row.label not in EXPECTED:
                continue
            intent = intent_for(classify_pose(row.landmarks, cfg.gesture), cfg.gesture)
            counts[(EXPECTED[row.label], PREDICTED[intent])] += 1
    return counts


def precision_recall(counts: Counter[tuple[str, str]]) -> dict[str, dict[str, int]]:
    out = {}
    for c in CLASSES:
        tp = counts[(c, c)]
        predicted = sum(n for (_, p), n in counts.items() if p == c)
        actual = sum(n for (e, _), n in counts.items() if e == c)
        out[c] = {"tp": tp, "predicted": predicted, "actual": actual}
    return out


def segments(rows: list[Row], label: str) -> list[tuple[int, int]]:
    """Start and end times of each unbroken run of frames with this label."""
    found: list[list[int]] = []
    prev: Row | None = None
    for row in rows:
        if row.label == label:
            joined = prev is not None and prev.label == label and row.t_ms - prev.t_ms <= GAP_MS
            if joined:
                found[-1][1] = row.t_ms
            else:
                found.append([row.t_ms, row.t_ms])
        prev = row
    return [(a, b) for a, b in found]


def replay(session: Session, cfg: AppConfig) -> list[tuple[int, str]]:
    """Feed the session through the full recognizer; return (time, 'left'|'right') events."""
    rec = GestureRecognizer(cfg.gesture, cfg.cursor)
    events: list[tuple[int, str]] = []
    prev_t: int | None = None
    for row in session.rows:
        if prev_t is not None and row.t_ms - prev_t > GAP_MS:
            for i in range(cfg.gesture.lost_hand_grace_frames + 1):
                rec.update(None, prev_t + i + 1, True)
        prev_t = row.t_ms
        out = rec.update(HandObservation(row.landmarks), row.t_ms, True)
        for action in out.actions:
            if action.type in (ActionType.LEFT_CLICK, ActionType.DRAG_START):
                events.append((row.t_ms, "left"))
            elif action.type is ActionType.RIGHT_CLICK:
                events.append((row.t_ms, "right"))
    return events


def event_report(sessions: list[Session], cfg: AppConfig) -> dict[str, float]:
    report = {"expected_left": 0, "hit_left": 0, "expected_right": 0, "hit_right": 0}
    report["false_events"] = 0
    minutes = 0.0
    for session in sessions:
        minutes += session.minutes
        segs = {
            "left": segments(session.rows, "left_pinch"),
            "right": segments(session.rows, "right_pinch"),
        }
        hit: set[tuple[str, int]] = set()
        for t, kind in replay(session, cfg):
            match = next(
                (
                    i
                    for i, (a, b) in enumerate(segs[kind])
                    if a <= t <= b + MATCH_WINDOW_MS and (kind, i) not in hit
                ),
                None,
            )
            if match is None:
                report["false_events"] += 1
            else:
                hit.add((kind, match))
        for kind in ("left", "right"):
            report[f"expected_{kind}"] += len(segs[kind])
            report[f"hit_{kind}"] += sum(1 for k, _ in hit if k == kind)
    report["minutes"] = round(minutes, 3)
    report["false_per_minute"] = round(report["false_events"] / minutes, 3) if minutes else 0.0
    return report


def ratio_summary(sessions: list[Session], cfg: AppConfig) -> dict[str, dict[str, list[float]]]:
    by_label: dict[str, dict[str, list[float]]] = {}
    for session in sessions:
        for row in session.rows:
            pose = classify_pose(row.landmarks, cfg.gesture)
            entry = by_label.setdefault(row.label, {"ratio_ti": [], "ratio_tm": []})
            entry["ratio_ti"].append(pose.ratio_ti)
            entry["ratio_tm"].append(pose.ratio_tm)
    return {
        label: {k: [float(np.percentile(v, q)) for q in (5, 50, 95)] for k, v in values.items()}
        for label, values in by_label.items()
    }


def pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:5.1f}% ({part}/{whole})" if whole else "  n/a (0/0)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the rule-based recognizer.")
    parser.add_argument("--input", nargs="+", required=True, help="JSONL files or glob patterns")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--summarize", action="store_true", help="print ratio percentiles")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cfg = load_config(args.config)
    sessions = load_sessions(args.input)
    rows = sum(len(s.rows) for s in sessions)
    if not rows:
        print("No recorded frames found.")
        return 1
    print(f"{len(sessions)} sessions, {rows} frames. Recognizer: rule-based geometry.")
    for s in sessions:
        print(f"  {s.name}: {len(s.rows)} frames, note: {s.note or '-'}")

    if args.summarize:
        print("\nRatio percentiles (5th, 50th, 95th) by label:")
        for label, values in ratio_summary(sessions, cfg).items():
            ti = ", ".join(f"{v:.2f}" for v in values["ratio_ti"])
            tm = ", ".join(f"{v:.2f}" for v in values["ratio_tm"])
            print(f"  {label:<12} thumb-index {ti}   thumb-middle {tm}")
        return 0

    counts = frame_confusion(sessions, cfg)
    columns = (*CLASSES, "unsure")
    print("\nFrame-level confusion (rows: recorded label, columns: rule output)")
    print(" " * 12 + "".join(f"{c:>12}" for c in columns))
    for e in CLASSES:
        print(f"{e:<12}" + "".join(f"{counts[(e, p)]:>12}" for p in columns))
    pr = precision_recall(counts)
    print("\nPer class:")
    for c, v in pr.items():
        print(
            f"  {c:<12} precision {pct(v['tp'], v['predicted'])}   "
            f"recall {pct(v['tp'], v['actual'])}"
        )
    events = event_report(sessions, cfg)
    print("\nEvents (full recognizer replay):")
    print(f"  left pinches recognized  {pct(events['hit_left'], events['expected_left'])}")
    print(f"  right pinches recognized {pct(events['hit_right'], events['expected_right'])}")
    print(
        f"  false clicks: {events['false_events']} in {events['minutes']:.2f} min "
        f"= {events['false_per_minute']} per minute"
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = args.output or OUT_DIR / f"eval-{datetime.now():%Y%m%d-%H%M%S}.json"
    result = {
        "recognizer": "rule-based geometry",
        "sessions": [{"name": s.name, "frames": len(s.rows), "note": s.note} for s in sessions],
        "confusion": [{"label": e, "output": p, "count": n} for (e, p), n in counts.items()],
        "per_class": pr,
        "events": events,
    }
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nSaved {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
