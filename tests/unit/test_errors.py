"""Tests for the SaldeoError → MCP error-payload shape.

`error_payload` is what tools return to the MCP boundary on failure; the
shape is part of the public contract so each branch (with/without
http_status, with/without per-item details) is exercised here.
"""

from __future__ import annotations

from saldeosmart_mcp.errors import ItemError, SaldeoError
from saldeosmart_mcp.tools._runtime import _error_payload


def test_error_payload_minimal() -> None:
    e = SaldeoError(code="4302", message="User is locked")
    assert _error_payload(e) == {"error": "4302", "message": "User is locked"}


def test_error_payload_includes_http_status_when_present() -> None:
    e = SaldeoError(code="4001", message="Invalid signature", http_status=403)
    payload = _error_payload(e)
    assert payload["http_status"] == 403


def test_error_payload_includes_per_item_details() -> None:
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


def test_error_payload_omits_optional_fields_when_absent() -> None:
    e = SaldeoError(code="X", message="y")
    payload = _error_payload(e)
    assert "http_status" not in payload
    assert "details" not in payload
