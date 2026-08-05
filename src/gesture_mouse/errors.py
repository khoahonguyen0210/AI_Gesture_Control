"""Project exception types. Each carries a message a user can act on."""

from __future__ import annotations


class GestureMouseError(Exception):
    """Base class for all project errors."""


class ConfigError(GestureMouseError):
    """The configuration is missing, unreadable, or invalid."""

    def __init__(self, problems: list[str] | str) -> None:
        self.problems = [problems] if isinstance(problems, str) else list(problems)
        lines = "\n".join(f"  - {p}" for p in self.problems)
        super().__init__(f"Invalid configuration:\n{lines}")


class CameraOpenError(GestureMouseError):
    """The camera could not be opened or gave no frame."""


class CameraLostError(GestureMouseError):
    """The camera stopped giving frames during a run."""


class ModelNotFoundError(GestureMouseError):
    """The hand landmark model file is missing or empty."""


class InputControlError(GestureMouseError):
    """The mouse could not be controlled, or the failsafe was triggered."""
