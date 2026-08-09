"""Typed configuration: defaults, TOML loading, overrides, and validation.

All numeric defaults are uncalibrated starting values.
"""

from __future__ import annotations

import dataclasses
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gesture_mouse.errors import ConfigError

CAMERA_BACKENDS = ("auto", "dshow", "msmf")
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
SPECIAL_KEYS = ("Esc",)


@dataclass(frozen=True)
class CameraConfig:
    index: int = 0
    backend: str = "auto"
    width: int = 640
    height: int = 480
    fps: int = 30
    open_timeout_ms: int = 3000
    max_consecutive_failures: int = 30


@dataclass(frozen=True)
class TrackerConfig:
    model_path: str = "models/hand_landmarker.task"
    min_hand_detection_confidence: float = 0.5
    min_hand_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5


@dataclass(frozen=True)
class GestureConfig:
    pinch_on: float = 0.30
    pinch_off: float = 0.45
    finger_extended_margin: float = 1.10
    pinch_min_reach: float = 0.80
    enter_frames: int = 3
    exit_frames: int = 2
    drag_hold_ms: int = 350
    click_cooldown_ms: int = 250
    lost_hand_grace_frames: int = 5
    scroll_gain: float = 40.0
    scroll_dead_zone: float = 0.01
    scroll_max_step: int = 5


@dataclass(frozen=True)
class CursorConfig:
    margin: float = 0.15
    smoothing_alpha: float = 0.35
    dead_zone_px: int = 3
    screen_edge_margin_px: int = 2


@dataclass(frozen=True)
class UiConfig:
    window_title: str = "Gesture Mouse"
    show_debug_values: bool = False


@dataclass(frozen=True)
class ControlConfig:
    start_paused: bool = False
    pause_key: str = "p"
    quit_keys: tuple[str, ...] = ("q", "Esc")


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    file: str | None = None


@dataclass(frozen=True)
class AppConfig:
    camera: CameraConfig = field(default_factory=CameraConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    gesture: GestureConfig = field(default_factory=GestureConfig)
    cursor: CursorConfig = field(default_factory=CursorConfig)
    ui: UiConfig = field(default_factory=UiConfig)
    control: ControlConfig = field(default_factory=ControlConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


Overrides = dict[str, dict[str, Any]]

_INVALID = object()


def load_config(path: Path | None = None, overrides: Overrides | None = None) -> AppConfig:
    """Build the config from defaults, then the TOML file, then overrides."""
    problems: list[str] = []
    cfg = AppConfig()
    if path is not None:
        cfg = _merge(cfg, _read_toml(path), problems, source=str(path))
    if overrides:
        cfg = _merge(cfg, overrides, problems, source="command line")
    try:
        validate(cfg)
    except ConfigError as exc:
        problems.extend(exc.problems)
    if problems:
        raise ConfigError(problems)
    return cfg


def validate(cfg: AppConfig) -> None:
    """Check value ranges and relations. Raises one ConfigError listing every problem."""
    p: list[str] = []
    c, t, g, cur, ctl = cfg.camera, cfg.tracker, cfg.gesture, cfg.cursor, cfg.control

    if c.index < 0:
        p.append("camera.index must be 0 or greater")
    if c.backend not in CAMERA_BACKENDS:
        p.append(f"camera.backend must be one of {', '.join(CAMERA_BACKENDS)}")
    for name in ("width", "height", "fps", "open_timeout_ms", "max_consecutive_failures"):
        if getattr(c, name) <= 0:
            p.append(f"camera.{name} must be greater than 0")

    if not t.model_path:
        p.append("tracker.model_path must not be empty")
    for name in (
        "min_hand_detection_confidence",
        "min_hand_presence_confidence",
        "min_tracking_confidence",
    ):
        if not 0.0 <= getattr(t, name) <= 1.0:
            p.append(f"tracker.{name} must be between 0 and 1")

    for name in ("pinch_on", "pinch_off"):
        if not 0.0 < getattr(g, name) < 1.0:
            p.append(f"gesture.{name} must be between 0 and 1")
    if g.pinch_off <= g.pinch_on:
        p.append("gesture.pinch_off must be greater than gesture.pinch_on")
    if g.finger_extended_margin <= 0:
        p.append("gesture.finger_extended_margin must be greater than 0")
    if g.pinch_min_reach <= 0:
        p.append("gesture.pinch_min_reach must be greater than 0")
    for name in (
        "enter_frames",
        "exit_frames",
        "drag_hold_ms",
        "click_cooldown_ms",
        "lost_hand_grace_frames",
        "scroll_max_step",
    ):
        if getattr(g, name) <= 0:
            p.append(f"gesture.{name} must be greater than 0")
    if g.scroll_gain <= 0:
        p.append("gesture.scroll_gain must be greater than 0")
    if g.scroll_dead_zone < 0:
        p.append("gesture.scroll_dead_zone must be 0 or greater")

    if not 0.0 <= cur.margin < 0.5:
        p.append("cursor.margin must be at least 0 and less than 0.5")
    if not 0.0 < cur.smoothing_alpha <= 1.0:
        p.append("cursor.smoothing_alpha must be greater than 0 and at most 1")
    if cur.dead_zone_px < 0:
        p.append("cursor.dead_zone_px must be 0 or greater")
    if cur.screen_edge_margin_px < 1:
        p.append("cursor.screen_edge_margin_px must be at least 1")

    if not cfg.ui.window_title:
        p.append("ui.window_title must not be empty")

    keys = [ctl.pause_key, *ctl.quit_keys]
    if not ctl.quit_keys:
        p.append("control.quit_keys must not be empty")
    for key in keys:
        if len(key) != 1 and key not in SPECIAL_KEYS:
            p.append(f"control key {key!r} must be one character or 'Esc'")
    if ctl.pause_key in ctl.quit_keys:
        p.append("control.pause_key must differ from control.quit_keys")

    if cfg.logging.level.upper() not in LOG_LEVELS:
        p.append(f"logging.level must be one of {', '.join(LOG_LEVELS)}")

    if p:
        raise ConfigError(p)


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot read config file {path}: {exc}") from exc


def _merge(cfg: AppConfig, data: dict[str, Any], problems: list[str], source: str) -> AppConfig:
    sections: dict[str, Any] = {}
    for section_name, values in data.items():
        if not hasattr(cfg, section_name):
            problems.append(f"unknown section [{section_name}] in {source}")
            continue
        if not isinstance(values, dict):
            problems.append(f"[{section_name}] in {source} must be a table")
            continue
        section = getattr(cfg, section_name)
        known = {f.name: f for f in dataclasses.fields(section)}
        changes: dict[str, Any] = {}
        for key, value in values.items():
            if key not in known:
                problems.append(f"unknown key {section_name}.{key} in {source}")
                continue
            default = getattr(type(section)(), key)
            coerced = _coerce(value, default)
            if coerced is _INVALID:
                problems.append(f"{section_name}.{key} in {source} has the wrong type: {value!r}")
                continue
            changes[key] = coerced
        sections[section_name] = dataclasses.replace(section, **changes)
    return dataclasses.replace(cfg, **sections)


def _coerce(value: Any, default: Any) -> Any:
    if default is None:
        return value if isinstance(value, str) else _INVALID
    if isinstance(default, bool):
        return value if isinstance(value, bool) else _INVALID
    if isinstance(default, int):
        return value if isinstance(value, int) and not isinstance(value, bool) else _INVALID
    if isinstance(default, float):
        ok = isinstance(value, int | float) and not isinstance(value, bool)
        return float(value) if ok else _INVALID
    if isinstance(default, str):
        return value if isinstance(value, str) else _INVALID
    if isinstance(default, tuple):
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            return tuple(value)
        return _INVALID
    return _INVALID
