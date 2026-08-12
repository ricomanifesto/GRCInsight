"""Invocation-scoped runtime limits shared by Lambda entry paths."""

from contextvars import ContextVar, Token

_model_deadline: ContextVar[float | None] = ContextVar("model_deadline", default=None)


def get_model_deadline() -> float | None:
    """Return the current Lambda invocation's absolute model deadline."""
    return _model_deadline.get()


def set_model_deadline(deadline: float | None) -> Token:
    """Set the model deadline for the current invocation context."""
    return _model_deadline.set(deadline)


def reset_model_deadline(token: Token) -> None:
    """Restore the previous invocation context."""
    _model_deadline.reset(token)
