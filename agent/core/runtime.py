"""Invocation-scoped runtime limits shared across service entry paths."""

from contextvars import ContextVar, Token
from collections.abc import Callable
import math
import time

CALLER_DEADLINE_HEADER = "x-grc-caller-deadline-unix-ms"
CALLER_COMPLETION_RESERVE_SECONDS = 30.0

_model_deadline: ContextVar[float | None] = ContextVar("model_deadline", default=None)


def deadline_from_unix_ms(
    value: str | int | float | None,
    *,
    monotonic_clock: Callable[[], float] = time.monotonic,
    wall_clock: Callable[[], float] = time.time,
) -> float | None:
    """Convert a cross-process caller deadline into a local model deadline."""
    if value is None:
        return None
    try:
        deadline_seconds = float(value) / 1000.0
    except (TypeError, ValueError):
        return None
    if not math.isfinite(deadline_seconds):
        return None

    remaining = deadline_seconds - wall_clock() - CALLER_COMPLETION_RESERVE_SECONDS
    return monotonic_clock() + max(0.0, remaining)


def earliest_deadline(*deadlines: float | None) -> float | None:
    """Return the tightest available runtime limit."""
    available = [deadline for deadline in deadlines if deadline is not None]
    return min(available) if available else None


def get_model_deadline() -> float | None:
    """Return the current invocation's absolute monotonic model deadline."""
    return _model_deadline.get()


def set_model_deadline(deadline: float | None) -> Token:
    """Set the model deadline for the current invocation context."""
    return _model_deadline.set(deadline)


def reset_model_deadline(token: Token) -> None:
    """Restore the previous invocation context."""
    _model_deadline.reset(token)
