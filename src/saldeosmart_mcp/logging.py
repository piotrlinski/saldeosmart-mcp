"""File-based logging setup for the MCP server.

MCP uses stdio as its transport, so writing log records to stdout would
corrupt the protocol stream. We attach only a daily-rotated file handler;
no stream handler is added.

This module is imported once from ``server.main()`` and is otherwise
side-effect free: importing it does NOT install handlers — only calling
``setup_logging()`` does.
"""

from __future__ import annotations

import logging as _stdlogging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

logger = _stdlogging.getLogger(__name__)


def setup_logging() -> Path:
    """Route every log record from this package to a file with daily rotation.

    Configurable via env vars:
        SALDEO_LOG_DIR             — override the directory
                                     (default ~/.saldeosmart/logs)
        SALDEO_LOG_LEVEL           — root log level (default INFO)
        SALDEO_LOG_RETENTION_DAYS  — how many daily-rotated files to keep
                                     (default 7)

    Idempotent: calling it twice with the same settings does not stack
    handlers. Returns the path to the live log file.
    """
    log_dir = Path(os.environ.get("SALDEO_LOG_DIR") or Path.home() / ".saldeosmart" / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "saldeosmart.log"

    try:
        retention_days = int(os.environ.get("SALDEO_LOG_RETENTION_DAYS", "7"))
    except ValueError:
        retention_days = 7
    retention_days = max(retention_days, 1)

    handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=retention_days,
        encoding="utf-8",
        utc=False,
    )
    handler.setFormatter(
        _stdlogging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )

    root = _stdlogging.getLogger()
    root.setLevel(os.environ.get("SALDEO_LOG_LEVEL", "INFO"))

    # Idempotent: don't stack handlers if main() runs twice (tests, reloads).
    for existing in root.handlers:
        if isinstance(existing, TimedRotatingFileHandler) and getattr(
            existing, "baseFilename", ""
        ) == str(log_file):
            return log_file
    root.addHandler(handler)
    return log_file


# Back-compat alias so callers that import the underscore-prefixed name still work
# during the transition. Treat as private — production callers should use
# `setup_logging` (no underscore).
_setup_logging = setup_logging
