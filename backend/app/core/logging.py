"""Logging configuration for the application.

Provides `setup_logging()` and `get_logger()`. Production/staging emit
structured JSON logs (one JSON object per line) for ingestion by log
aggregators; development emits human-readable colored text. Both
formats carry `request_id` and, where applicable, `duration_ms`.
"""

import json
import logging
import sys
import traceback
from datetime import datetime, timezone

from app.config import get_settings

_LOGGER_NAME = "kora"

_TEXT_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | "
    "request_id=%(request_id)s | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_LEVEL_COLORS = {
    logging.DEBUG: "\033[36m",
    logging.INFO: "\033[32m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[41m",
}
_RESET_COLOR = "\033[0m"

_RESERVED_RECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "taskName",
}


class _RequestIdFilter(logging.Filter):
    """Guarantee every log record carries a `request_id` attribute."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


class _ColoredFormatter(logging.Formatter):
    """Human-readable colored formatter, used in development only."""

    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelno, "")
        message = super().format(record)
        return f"{color}{message}{_RESET_COLOR}" if color else message


class _JsonFormatter(logging.Formatter):
    """Structured JSON formatter, one object per line.

    Includes standard fields (timestamp, level, logger name, message,
    request_id) plus any extra attributes attached via `extra=...`
    (e.g. `duration_ms`), and a full traceback when logging an
    exception.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }

        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_ATTRS and key not in payload:
                try:
                    json.dumps(value)
                except TypeError:
                    value = str(value)
                payload[key] = value

        if record.exc_info:
            payload["exception"] = "".join(
                traceback.format_exception(*record.exc_info)
            )

        return json.dumps(payload, default=str)


def setup_logging() -> None:
    """Configure application-wide logging.

    Development: colored, human-readable text on stdout.
    Staging/production: structured JSON on stdout, one object per line.
    Idempotent — repeated calls do not attach duplicate handlers.
    """
    settings = get_settings()
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(settings.LOG_LEVEL)
    logger.propagate = False

    if logger.handlers:
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(settings.LOG_LEVEL)
    handler.addFilter(_RequestIdFilter())

    if settings.APP_ENV == "development":
        formatter: logging.Formatter = _ColoredFormatter(
            fmt=_TEXT_FORMAT, datefmt=_DATE_FORMAT
        )
    else:
        formatter = _JsonFormatter()

    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the shared application logger."""
    return logging.getLogger(_LOGGER_NAME).getChild(name)