"""Logging configuration for the application.

This module provides a single, centralized entry point for configuring
Python's standard `logging` module, plus a `get_logger` helper so every
part of the application shares the same handlers, formatting, and log
level instead of configuring logging ad hoc in each module.
"""

import logging
import sys

from app.config import get_settings

_LOGGER_NAME = "kora"

_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | "
    "request_id=%(request_id)s | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_LEVEL_COLORS = {
    logging.DEBUG: "\033[36m",     # cyan
    logging.INFO: "\033[32m",      # green
    logging.WARNING: "\033[33m",   # yellow
    logging.ERROR: "\033[31m",     # red
    logging.CRITICAL: "\033[41m",  # red background
}
_RESET_COLOR = "\033[0m"


class _RequestIdFilter(logging.Filter):
    """Guarantee every log record carries a `request_id` attribute.

    Log records emitted outside of the request-logging middleware (e.g.
    during application startup) have no `request_id`. This filter fills
    in a default value so the shared formatter never raises a
    `KeyError` when rendering `%(request_id)s`.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach a default `request_id` to the record if missing.

        Args:
            record: The log record being processed.

        Returns:
            Always True, so the record is never filtered out.
        """
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


class _ColoredFormatter(logging.Formatter):
    """Formatter that colors log output by severity level.

    Intended for local development only, where a human reads logs
    directly from a terminal. Production and staging environments use
    the plain `logging.Formatter` instead, since colored output is not
    machine-friendly for log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with ANSI color codes.

        Args:
            record: The log record to format.

        Returns:
            The formatted, colorized log line.
        """
        color = _LEVEL_COLORS.get(record.levelno, "")
        message = super().format(record)
        if not color:
            return message
        return f"{color}{message}{_RESET_COLOR}"


def setup_logging() -> None:
    """Configure application-wide logging.

    Configures a single shared logger (`kora`) with one console handler.
    Development environments get colored output for readability;
    staging and production get plain, structured output suitable for
    log aggregation systems. The log level is read from
    `Settings.LOG_LEVEL`.

    This function is idempotent: calling it more than once will not
    attach duplicate handlers.
    """
    settings = get_settings()
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(settings.LOG_LEVEL)
    logger.propagate = False

    if logger.handlers:
        # Logging has already been configured; avoid duplicate handlers.
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(settings.LOG_LEVEL)
    handler.addFilter(_RequestIdFilter())

    formatter: logging.Formatter
    if settings.APP_ENV == "development":
        formatter = _ColoredFormatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    else:
        formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the shared application logger.

    All loggers returned by this function propagate to the same shared
    `kora` logger configured by `setup_logging`, so they share the same
    handlers, formatting, and log level, guaranteeing consistent log
    output across the entire application.

    Args:
        name: Name of the module or component requesting a logger,
            typically `__name__`.

    Returns:
        A `logging.Logger` instance namespaced under the shared
        application logger.
    """
    return logging.getLogger(_LOGGER_NAME).getChild(name)