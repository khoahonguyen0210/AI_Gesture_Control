"""Logging setup. Logs never contain image data."""

from __future__ import annotations

import logging
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(level: str = "INFO", file: str | None = None) -> None:
    """Send logs to the console and, if given, to a file."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if file:
        Path(file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(file, encoding="utf-8"))
    logging.basicConfig(level=level.upper(), format=LOG_FORMAT, handlers=handlers, force=True)
