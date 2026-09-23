"""Command-line entry point: python -m gesture_mouse"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from functools import partial
from pathlib import Path

from gesture_mouse import __version__
from gesture_mouse.app import EXIT_CONFIG, run_app
from gesture_mouse.config import AppConfig, Overrides, load_config
from gesture_mouse.errors import ConfigError
from gesture_mouse.logging_setup import configure_logging
from gesture_mouse.mouse_controller import MouseBackend, PyAutoGuiBackend
from gesture_mouse.serial_backend import open_serial_backend

log = logging.getLogger("gesture_mouse")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gesture-mouse",
        description="Control the mouse with one hand in front of the webcam.",
    )
    parser.add_argument("--config", type=Path, help="TOML file with settings to change")
    parser.add_argument("--camera", type=int, help="camera index (default 0)")
    parser.add_argument(
        "--dry-run", action="store_true", help="show gestures but never move the mouse"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="how much to log (default INFO)",
    )
    parser.add_argument(
        "--max-frames", type=int, help="stop after this many frames (for profiling and tests)"
    )
    parser.add_argument(
        "--serial",
        metavar="PORT",
        help="send actions to a serial device instead of the real mouse, "
        "for example rfc2217://localhost:4000 (Wokwi) or COM5",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def overrides_from_args(args: argparse.Namespace) -> Overrides:
    overrides: Overrides = {}
    if args.camera is not None:
        overrides.setdefault("camera", {})["index"] = args.camera
    if args.log_level is not None:
        overrides.setdefault("logging", {})["level"] = args.log_level
    return overrides


def load_from_args(args: argparse.Namespace) -> AppConfig:
    return load_config(args.config, overrides_from_args(args))


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cfg = load_from_args(args)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return EXIT_CONFIG
    configure_logging(cfg.logging.level, cfg.logging.file)
    log.info("Gesture Mouse %s starting", __version__)
    if args.max_frames is not None and args.max_frames <= 0:
        print("--max-frames must be greater than 0", file=sys.stderr)
        return EXIT_CONFIG
    if args.serial and args.dry_run:
        print("--serial and --dry-run cannot be used together", file=sys.stderr)
        return EXIT_CONFIG
    backend: Callable[[], MouseBackend] = PyAutoGuiBackend
    if args.serial:
        backend = partial(open_serial_backend, args.serial)
    return run_app(cfg, dry_run=args.dry_run, backend_factory=backend, max_frames=args.max_frames)


if __name__ == "__main__":
    raise SystemExit(main())
