"""Structured JSON logger.

Every log entry includes ``session_id``, ``phase``, ``agent``, and ``event``
as required by architecture.md §8.  ``print()`` is banned outside scripts —
use this module instead (rules.md §2).
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any


class _JSONFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge structured extras (session_id, phase, agent, event, …)
        if hasattr(record, "structured"):
            payload.update(record.structured)  # type: ignore[attr-defined]
        if record.exc_info and record.exc_info[1] is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured for structured JSON output to stdout.

    Args:
        name: Logger name, typically ``__name__`` of the calling module.

    Returns:
        A ``logging.Logger`` with JSON formatting on stdout.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_event(
    logger: logging.Logger,
    message: str,
    *,
    session_id: str | None = None,
    phase: str | None = None,
    agent: str | None = None,
    event: str | None = None,
    level: int = logging.INFO,
    **extra: Any,
) -> None:
    """Emit a structured log entry.

    Args:
        logger: The logger instance.
        message: Human-readable summary.
        session_id: Current session UUID.
        phase: Pipeline phase name (e.g. ``"phase1"``).
        agent: Agent name (e.g. ``"agent1"``).
        event: Event type (e.g. ``"started"``, ``"completed"``, ``"failed"``).
        level: Log level (default ``INFO``).
        **extra: Additional key-value pairs to include.
    """
    structured: dict[str, Any] = {}
    if session_id is not None:
        structured["session_id"] = session_id
    if phase is not None:
        structured["phase"] = phase
    if agent is not None:
        structured["agent"] = agent
    if event is not None:
        structured["event"] = event
    structured.update(extra)

    record = logger.makeRecord(
        name=logger.name,
        level=level,
        fn="",
        lno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    record.structured = structured  # type: ignore[attr-defined]
    logger.handle(record)
