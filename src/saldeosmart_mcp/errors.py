"""Errors and structured error payloads.

Two flavours of error live here:

- ``SaldeoError`` (Python exception) — what the HTTP layer raises when
  Saldeo returned a structured ERROR envelope, an HTTP failure with no
  body, or a parse error.
- ``ErrorResponse`` / ``ItemErrorPayload`` / ``MergeResult`` (Pydantic
  models) — what gets serialized over MCP back to the calling client, so
  the LLM on the other side receives something with a stable JSON Schema.

``ItemError`` (dataclass) is the in-process representation that bridges
between the two: the per-item walker produces them, then they're converted
to ``ItemErrorPayload`` at the MCP boundary.

``iter_item_errors`` is the per-item walker — Saldeo answers ``STATUS=OK``
at the envelope level even when individual items fail, so callers that
mutate state need to inspect each item.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field


@dataclass
class ItemError:
    """A per-item validation/operation error nested inside a successful RESPONSE.

    SaldeoSMART batch endpoints (e.g. document/update, document/import,
    employee/add, personnel/document/add) report results per item and include
    detailed errors when an individual item fails. This wraps both shapes:

    - validation errors:   <ERRORS><ERROR><PATH/><MESSAGE/></ERROR></ERRORS>
    - operational errors:  <UPDATE_STATUS>ERROR</UPDATE_STATUS><ERROR_MESSAGE/>

    `path` is empty ("") for operational errors that don't point at a field.
    """

    status: str
    path: str
    message: str
    item_id: str | None = None


class SaldeoError(Exception):
    """Raised when SaldeoSMART API returns an error response.

    Covers both:
    - top-level errors: <RESPONSE><STATUS>ERROR</STATUS>
                        <ERROR_CODE/><ERROR_MESSAGE/></RESPONSE>
    - HTTP transport errors (non-2xx, network, parse failures), encoded with
      synthetic codes like HTTP_500, NETWORK_ERROR, PARSE_ERROR.

    `details` carries per-field validation errors when present (rare for
    top-level errors, common for per-item errors via :func:`iter_item_errors`).
    """

    def __init__(
        self,
        code: str,
        message: str,
        raw_xml: str | None = None,
        http_status: int | None = None,
        details: list[ItemError] | None = None,
    ):
        self.code = code
        self.message = message
        self.raw_xml = raw_xml
        self.http_status = http_status
        self.details = details or []
        super().__init__(f"[{code}] {message}")


class ItemErrorPayload(BaseModel):
    """Per-item error nested inside a structured SaldeoError response."""

    status: str
    path: str
    message: str
    item_id: str | None = None

    @classmethod
    def from_dataclass(cls, e: ItemError) -> ItemErrorPayload:
        return cls(status=e.status, path=e.path, message=e.message, item_id=e.item_id)


class ErrorResponse(BaseModel):
    """Uniform error shape returned to MCP clients on SaldeoSMART failures."""

    error: str
    message: str
    http_status: int | None = None
    details: list[ItemErrorPayload] = Field(default_factory=list)


class MergeResult(BaseModel):
    """Outcome of a Saldeo merge/update/delete batch.

    Saldeo answers ``STATUS=OK`` at the envelope level even when individual
    items fail; ``successful`` and ``errors`` summarize what actually got
    through. ``operation`` echoes the Saldeo operation name (from METAINF)
    so callers can verify the right endpoint was hit.
    """

    operation: str | None = None
    total: int
    successful: int
    errors: list[ItemErrorPayload] = Field(default_factory=list)


# Per-item status fields used across batch endpoints. Field name varies:
#   document/update      → UPDATE_STATUS, values UPDATED|NOT_VALID|ERROR
#   document/import      → STATUS,        values VALID|NOT_VALID
#   personnel/document/* → STATUS,        values CREATED|CONFLICT|NOT_VALID
#   employee/add         → STATUS,        values CREATED|CONFLICT|NOT_VALID
# Anything not in the "happy" set is treated as a failure.
_ITEM_STATUS_TAGS = ("UPDATE_STATUS", "STATUS")
_ITEM_OK_VALUES = frozenset({"UPDATED", "VALID", "CREATED", "OK"})

# Element tags used to identify the item itself (for surfacing context in errors).
_ITEM_ID_TAGS = (
    "DOCUMENT_ID",
    "INVOICE_ID",
    "CONTRACTOR_ID",
    "EMPLOYEE_ID",
    "PERSONNEL_DOCUMENT_ID",
    "ASSURANCE_PROGRAM_ID",
)


def _local_el_text(parent: ET.Element, tag: str) -> str | None:
    """Local mini-helper so this module stays free of cross-package imports.

    Mirrors `saldeosmart_mcp.http.xml.el_text` for the narrow case where the
    iter_item_errors walker needs to read child text. Kept private so the
    public XML helpers live in one place.
    """
    child = parent.find(tag)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def iter_item_errors(root: ET.Element) -> list[ItemError]:
    """Walk a successful (STATUS=OK) RESPONSE and collect per-item failures.

    SaldeoSMART batch endpoints return STATUS=OK at the top level even when
    individual items fail. Callers that mutate state (document/update,
    document/import, contractor/merge, employee/add, …) should run this and
    decide whether to surface those errors as warnings or treat them as fatal.

    Returns an empty list if everything succeeded.
    """
    errors: list[ItemError] = []
    # Walk only container > row level: <RESPONSE><DOCUMENTS><DOCUMENT>...,
    # <RESPONSE><PERSONNEL_DOCUMENTS><PERSONNEL_DOCUMENT>..., etc. Using
    # root.iter() would descend into per-item bodies and mistake a nested
    # <STATUS> (e.g. inside <DOCUMENT_ITEMS>/<ITEM>) for a row-level result.
    for container in root:
        for item in container:
            status_value: str | None = None
            for tag in _ITEM_STATUS_TAGS:
                child = item.find(tag)
                if child is not None and child.text:
                    status_value = child.text.strip().upper()
                    break
            if status_value is None or status_value in _ITEM_OK_VALUES:
                continue

            item_id = next(
                (_local_el_text(item, t) for t in _ITEM_ID_TAGS if item.find(t) is not None),
                None,
            )

            # Validation errors: nested <ERRORS><ERROR><PATH/><MESSAGE/></ERROR></ERRORS>
            nested = item.find("ERRORS")
            added = False
            if nested is not None:
                for err in nested.findall("ERROR"):
                    errors.append(
                        ItemError(
                            status=status_value,
                            path=(_local_el_text(err, "PATH") or "").strip(),
                            message=(_local_el_text(err, "MESSAGE") or "").strip(),
                            item_id=item_id,
                        )
                    )
                    added = True

            # Operational errors: sibling <ERROR_MESSAGE/> or <STATUS_MESSAGE/>
            if not added:
                msg = (_local_el_text(item, "ERROR_MESSAGE") or "").strip() or (
                    _local_el_text(item, "STATUS_MESSAGE") or ""
                ).strip()
                errors.append(
                    ItemError(
                        status=status_value,
                        path="",
                        message=msg or f"item failed with status {status_value}",
                        item_id=item_id,
                    )
                )
    return errors
