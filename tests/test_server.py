"""
Tests for server-side concerns: log setup and the SaldeoError → MCP payload
shape. The MCP tool functions themselves hit the network, so we test their
plumbing rather than the tools end-to-end.
"""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from saldeosmart_mcp.client import ItemError, SaldeoError
from saldeosmart_mcp.server import _build_search_xml, _error_payload, _setup_logging


@pytest.fixture
def isolated_root_logger():
    """
    `_setup_logging` mutates the global root logger. Snapshot and restore so
    tests don't bleed handlers/levels into each other.
    """
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    root.handlers.clear()
    yield root
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()
    for h in saved_handlers:
        root.addHandler(h)
    root.setLevel(saved_level)


@pytest.fixture
def clean_env(monkeypatch):
    """Remove any SALDEO_LOG_* env vars so we exercise defaults predictably."""
    for var in ("SALDEO_LOG_DIR", "SALDEO_LOG_LEVEL", "SALDEO_LOG_RETENTION_DAYS"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


# ---- _setup_logging --------------------------------------------------------------


def test_setup_logging_writes_to_configured_dir(tmp_path, isolated_root_logger, clean_env):
    """Custom SALDEO_LOG_DIR must override the default ~/.saldeosmart/logs."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))

    log_file = _setup_logging()

    assert log_file == tmp_path / "saldeosmart.log"
    assert log_file.parent.exists()


def test_setup_logging_routes_client_and_server_loggers(tmp_path, isolated_root_logger, clean_env):
    """Records from both `saldeosmart_mcp.client` and `.server` must land in the file."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))
    log_file = _setup_logging()

    logging.getLogger("saldeosmart_mcp.client").warning("hello from client")
    logging.getLogger("saldeosmart_mcp.server").warning("hello from server")
    for h in logging.getLogger().handlers:
        h.flush()

    contents = log_file.read_text(encoding="utf-8")
    assert "hello from client" in contents
    assert "hello from server" in contents
    assert "saldeosmart_mcp.client" in contents
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


# ---- _error_payload --------------------------------------------------------------


def test_error_payload_minimal():
    e = SaldeoError(code="4302", message="User is locked")
    assert _error_payload(e) == {"error": "4302", "message": "User is locked"}


def test_error_payload_includes_http_status_when_present():
    e = SaldeoError(code="4001", message="Invalid signature", http_status=403)
    payload = _error_payload(e)
    assert payload["http_status"] == 403


def test_error_payload_includes_per_item_details():
    e = SaldeoError(
        code="VALIDATION",
        message="some items failed",
        details=[
            ItemError(status="NOT_VALID", path="DOCUMENT_ID",
                      message="must be unique", item_id="1"),
            ItemError(status="ERROR", path="", message="not found", item_id="2"),
        ],
    )
    payload = _error_payload(e)
    assert len(payload["details"]) == 2
    assert payload["details"][0]["path"] == "DOCUMENT_ID"
    assert payload["details"][1]["item_id"] == "2"


def test_error_payload_omits_optional_fields_when_absent():
    e = SaldeoError(code="X", message="y")
    payload = _error_payload(e)
    assert "http_status" not in payload
    assert "details" not in payload


# ---- _build_search_xml -----------------------------------------------------------


def test_build_search_xml_uses_search_policy_tag():
    """Saldeo expects <SEARCH_POLICY>, not <POLICY>. Wrong tag returns
    `4401 No SEARCH_POLICY found in file` from the live API."""
    xml = _build_search_xml(document_id=123, number=None, nip=None, guid=None)
    root = ET.fromstring(xml)
    assert root.find("SEARCH_POLICY") is not None
    assert root.find("SEARCH_POLICY").text == "BY_FIELDS"
    assert root.find("POLICY") is None  # avoid silently regressing


def test_build_search_xml_only_includes_provided_fields():
    xml = _build_search_xml(document_id=None, number="FV/1/2024", nip=None, guid=None)
    root = ET.fromstring(xml)
    fields = root.find("FIELDS")
    assert fields is not None
    assert fields.find("NUMBER").text == "FV/1/2024"
    assert fields.find("DOCUMENT_ID") is None
    assert fields.find("NIP") is None
    assert fields.find("GUID") is None


def test_build_search_xml_escapes_special_characters():
    """ElementTree must escape angle brackets, ampersands, etc. in field values."""
    xml = _build_search_xml(
        document_id=None, number="A&B<X>", nip=None, guid=None
    )
    # If escaping failed, fromstring would raise.
    root = ET.fromstring(xml)
    assert root.find("FIELDS/NUMBER").text == "A&B<X>"
