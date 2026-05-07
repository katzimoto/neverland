from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

from shared.correlation import get_correlation_id


class JsonFormatter(logging.Formatter):
    """Format log records as JSON with a correlation ID."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", get_correlation_id()),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


def configure_json_logging(level: int = logging.INFO) -> None:
    """Configure root logging for services that do not need custom handlers."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)


def log_extra(extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return logging extra values with a correlation ID."""
    values = dict(extra or {})
    values.setdefault("correlation_id", get_correlation_id())
    return values
