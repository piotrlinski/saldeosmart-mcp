"""Tests for the SaldeoError → ErrorResponse mapping.

`error_response` is what tools return to the MCP boundary on failure; the
shape is part of the public contract so each branch (with/without
http_status, with/without per-item details) is exercised here.
"""

from __future__ import annotations

from saldeosmart_mcp.errors import ErrorResponse, ItemError, ItemErrorPayload, SaldeoError
from saldeosmart_mcp.tools._runtime import error_response


def test_error_response_minimal() -> None:
    e = SaldeoError(code="4302", message="User is locked")
    assert error_response(e) == ErrorResponse(error="4302", message="User is locked")


def test_error_response_includes_http_status_when_present() -> None:
    e = SaldeoError(code="4001", message="Invalid signature", http_status=403)
    resp = error_response(e)
    assert resp.http_status == 403


def test_error_response_includes_per_item_details() -> None:
    e = SaldeoError(
        code="VALIDATION",
        message="some items failed",
        details=[
            ItemError(status="NOT_VALID", path="DOCUMENT_ID",
                      message="must be unique", item_id="1"),
            ItemError(status="ERROR", path="", message="not found", item_id="2"),
        ],
    )
    resp = error_response(e)
    assert resp.details == [
        ItemErrorPayload(status="NOT_VALID", path="DOCUMENT_ID",
                         message="must be unique", item_id="1"),
        ItemErrorPayload(status="ERROR", path="", message="not found", item_id="2"),
    ]


def test_error_response_omits_optional_fields_when_absent() -> None:
    e = SaldeoError(code="X", message="y")
    resp = error_response(e)
    assert resp.http_status is None
    assert resp.details == []
