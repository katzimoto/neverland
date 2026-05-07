from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str:
    """Return the current correlation ID, creating one when absent."""
    current = _correlation_id.get()
    if current is None:
        current = str(uuid4())
        _correlation_id.set(current)
    return current


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set and return the current correlation ID."""
    value = correlation_id or str(uuid4())
    _correlation_id.set(value)
    return value


def clear_correlation_id() -> None:
    """Clear the correlation ID for the current context."""
    _correlation_id.set(None)
