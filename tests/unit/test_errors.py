"""Tests for the SaldeoError → ErrorResponse mapping.

The ``saldeo_call`` decorator wraps a tool body and converts a raised
``SaldeoError`` into the public ``ErrorResponse``; the shape is part of the
public contract so each branch (with/without http_status, with/without
per-item details) is exercised here.
"""

from __future__ import annotations

from saldeosmart_mcp.errors import ErrorResponse, ItemError, SaldeoError
from saldeosmart_mcp.tools._runtime import saldeo_call


def _wrap(error: SaldeoError) -> ErrorResponse:
    @saldeo_call
    def _raises() -> None:
        raise error

    result = _raises()
    assert isinstance(result, ErrorResponse)
    return result


def test_error_response_minimal() -> None:
    assert _wrap(SaldeoError(code="4302", message="User is locked")) == ErrorResponse(
        error="4302", message="User is locked"
    )


def test_error_response_includes_http_status_when_present() -> None:
    resp = _wrap(SaldeoError(code="4001", message="Invalid signature", http_status=403))
    assert resp.http_status == 403


def test_error_response_includes_per_item_details() -> None:
    resp = _wrap(
        SaldeoError(
            code="VALIDATION",
            message="some items failed",
            details=[
                ItemError(
                    status="NOT_VALID",
                    path="DOCUMENT_ID",
                    message="must be unique",
                    item_id="1",
                ),
                ItemError(status="ERROR", path="", message="not found", item_id="2"),
            ],
        )
    )
    assert resp.details == [
        ItemError(status="NOT_VALID", path="DOCUMENT_ID", message="must be unique", item_id="1"),
        ItemError(status="ERROR", path="", message="not found", item_id="2"),
    ]


def test_error_response_omits_optional_fields_when_absent() -> None:
    resp = _wrap(SaldeoError(code="X", message="y"))
    assert resp.http_status is None
    assert resp.details == []
