"""Shared fixtures for the test suite.

Anything reused across the unit/* tree lives here so individual test
files stay focused on their subject.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest


@pytest.fixture
def isolated_root_logger() -> Iterator[logging.Logger]:
    """Snapshot and restore the root logger.

    `setup_logging` mutates the global root logger; without this fixture
    handlers and levels bleed between tests.
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
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Drop SALDEO_LOG_* env vars so logging tests exercise real defaults."""
    for var in ("SALDEO_LOG_DIR", "SALDEO_LOG_LEVEL", "SALDEO_LOG_RETENTION_DAYS"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch
