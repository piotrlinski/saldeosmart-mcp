"""Tests for `saldeosmart_mcp.logging.setup_logging`.

Covers env-var handling (LOG_DIR, LOG_LEVEL, LOG_RETENTION_DAYS), default
location under $HOME, idempotency across repeated calls, and that records
from both client and server loggers reach the file.
"""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from saldeosmart_mcp.logging import setup_logging as _setup_logging


def test_setup_logging_writes_to_configured_dir(tmp_path, isolated_root_logger, clean_env):
    """Custom SALDEO_LOG_DIR must override the default ~/.saldeosmart/logs."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))

    log_file = _setup_logging()

    assert log_file == tmp_path / "saldeosmart.log"
    assert log_file.parent.exists()


def test_setup_logging_routes_client_and_server_loggers(tmp_path, isolated_root_logger, clean_env):
    """Records from both `saldeosmart_mcp.http.client` and `.server` must land in the file."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))
    log_file = _setup_logging()

    logging.getLogger("saldeosmart_mcp.http.client").warning("hello from client")
    logging.getLogger("saldeosmart_mcp.server").warning("hello from server")
    for h in logging.getLogger().handlers:
        h.flush()

    contents = log_file.read_text(encoding="utf-8")
    assert "hello from client" in contents
    assert "hello from server" in contents
    assert "saldeosmart_mcp.http.client" in contents
    assert "saldeosmart_mcp.server" in contents


def test_setup_logging_default_retention_is_one_week(tmp_path, isolated_root_logger, clean_env):
    """Default SALDEO_LOG_RETENTION_DAYS must be 7 (one week)."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))

    _setup_logging()

    handler = next(
        h for h in logging.getLogger().handlers
        if isinstance(h, TimedRotatingFileHandler)
    )
    assert handler.backupCount == 7
    assert handler.when == "MIDNIGHT"


def test_setup_logging_respects_custom_retention(tmp_path, isolated_root_logger, clean_env):
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))
    clean_env.setenv("SALDEO_LOG_RETENTION_DAYS", "3")

    _setup_logging()

    handler = next(
        h for h in logging.getLogger().handlers
        if isinstance(h, TimedRotatingFileHandler)
    )
    assert handler.backupCount == 3


def test_setup_logging_invalid_retention_falls_back_to_default(
    tmp_path, isolated_root_logger, clean_env
):
    """Garbage in SALDEO_LOG_RETENTION_DAYS shouldn't break startup."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))
    clean_env.setenv("SALDEO_LOG_RETENTION_DAYS", "not-a-number")

    _setup_logging()

    handler = next(
        h for h in logging.getLogger().handlers
        if isinstance(h, TimedRotatingFileHandler)
    )
    assert handler.backupCount == 7


def test_setup_logging_zero_retention_is_clamped_to_one(
    tmp_path, isolated_root_logger, clean_env
):
    """A retention of 0 or negative would disable rotation entirely; clamp to 1."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))
    clean_env.setenv("SALDEO_LOG_RETENTION_DAYS", "0")

    _setup_logging()

    handler = next(
        h for h in logging.getLogger().handlers
        if isinstance(h, TimedRotatingFileHandler)
    )
    assert handler.backupCount >= 1


def test_setup_logging_is_idempotent(tmp_path, isolated_root_logger, clean_env):
    """Calling main() twice (tests, reloads) must not stack file handlers."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))

    _setup_logging()
    _setup_logging()
    _setup_logging()

    file_handlers = [
        h for h in logging.getLogger().handlers
        if isinstance(h, TimedRotatingFileHandler)
    ]
    assert len(file_handlers) == 1


def test_setup_logging_creates_missing_directory(tmp_path, isolated_root_logger, clean_env):
    """First run must create ~/.saldeosmart/logs/ if it doesn't exist."""
    target = tmp_path / "nested" / "does" / "not" / "exist"
    clean_env.setenv("SALDEO_LOG_DIR", str(target))

    log_file = _setup_logging()

    assert target.is_dir()
    assert log_file.parent == target


def test_setup_logging_default_location_is_under_home(
    isolated_root_logger, clean_env, monkeypatch, tmp_path
):
    """Without SALDEO_LOG_DIR, the file lives under $HOME/.saldeosmart/logs."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    log_file = _setup_logging()

    assert log_file == fake_home / ".saldeosmart" / "logs" / "saldeosmart.log"


def test_setup_logging_honors_log_level(tmp_path, isolated_root_logger, clean_env):
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))
    clean_env.setenv("SALDEO_LOG_LEVEL", "DEBUG")

    _setup_logging()

    assert logging.getLogger().level == logging.DEBUG
