"""JSON round-trip and Pydantic constraint tests for the public model surface.

The MCP boundary serializes every tool result to JSON; if a model field is
renamed or its type changes incompatibly, downstream clients break silently
unless we exercise the dump/parse round-trip here. We also pin a couple of
field-level constraints (``max_length`` on attachment lists) so a future
edit can't quietly remove them.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from saldeosmart_mcp.errors import ErrorResponse, ItemError, MergeResult
from saldeosmart_mcp.models import (
    Attachment,
    Document,
    DocumentImportAttachmentInput,
    DocumentImportInput,
    DocumentImportTypeInput,
    DocumentItem,
    DocumentList,
)


def test_document_list_round_trips_through_json() -> None:
    """Serializing a DocumentList to JSON and parsing it back must be lossless."""
    original = DocumentList(
        documents=[
            Document(
                document_id=42,
                number="FV/1/2024",
                value_net="100.00",
                value_gross="123.00",
                value_vat="23.00",
                items=[DocumentItem(name="Widget", value_net="100.00")],
            )
        ],
        count=1,
    )
    parsed = DocumentList.model_validate_json(original.model_dump_json())
    assert parsed == original


def test_error_response_round_trips_with_item_errors() -> None:
    """ErrorResponse with nested ItemError list is the most common failure shape."""
    original = ErrorResponse(
        error="EMPTY_INPUT",
        message="At least one document is required.",
        http_status=None,
        details=[ItemError(status="NOT_VALID", path="DOCUMENT_ID", message="missing")],
    )
    parsed = ErrorResponse.model_validate_json(original.model_dump_json())
    assert parsed == original


def test_merge_result_round_trips() -> None:
    original = MergeResult(operation="document.update", total=3, successful=2)
    parsed = MergeResult.model_validate_json(original.model_dump_json())
    assert parsed == original


# ---- Field constraint enforcement ------------------------------------------------


def test_document_import_input_caps_attachments_at_5() -> None:
    """Spec: at most 5 supporting attachments per imported document."""
    too_many = [
        DocumentImportAttachmentInput(attachment=Attachment(path="/dev/null")) for _ in range(6)
    ]
    with pytest.raises(ValidationError, match="at most 5"):
        DocumentImportInput(
            attachment=Attachment(path="/dev/null"),
            year=2026,
            month=1,
            document_type=DocumentImportTypeInput(short_name="VAT", model_type="INVOICE_COST"),
            attachments=too_many,
        )


def test_document_import_input_accepts_5_attachments() -> None:
    """Boundary: 5 is allowed, 6 is not (see test above)."""
    five = [
        DocumentImportAttachmentInput(attachment=Attachment(path="/dev/null")) for _ in range(5)
    ]
    doc = DocumentImportInput(
        attachment=Attachment(path="/dev/null"),
        year=2026,
        month=1,
        document_type=DocumentImportTypeInput(short_name="VAT", model_type="INVOICE_COST"),
        attachments=five,
    )
    assert len(doc.attachments) == 5
