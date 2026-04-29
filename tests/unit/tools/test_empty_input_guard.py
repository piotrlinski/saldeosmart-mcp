"""Empty-list guards on every write tool.

A passed-through empty list would translate to an empty container element
(``<DOCUMENTS/>`` etc.) and Saldeo's behavior on those is undocumented.
We short-circuit at the tool level with ``EMPTY_INPUT`` so callers get a
deterministic error and no HTTP call is issued.

Each tool is parametrized with the kwarg name of its list argument; the
guard runs before ``get_client()`` is touched, so no network mocking is
needed.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from saldeosmart_mcp.errors import ErrorResponse
from saldeosmart_mcp.tools.catalog import (
    merge_articles,
    merge_categories,
    merge_descriptions,
    merge_fees,
    merge_payment_methods,
    merge_registers,
)
from saldeosmart_mcp.tools.contractors import merge_contractors
from saldeosmart_mcp.tools.dimensions import merge_dimensions
from saldeosmart_mcp.tools.documents import (
    delete_documents,
    merge_document_dimensions,
    recognize_documents,
    sync_documents,
    update_documents,
)


@pytest.mark.parametrize(
    "tool,list_kwarg,extra_kwargs",
    [
        (update_documents, "documents", {}),
        (delete_documents, "document_ids", {}),
        (recognize_documents, "documents", {}),
        (sync_documents, "syncs", {}),
        (merge_document_dimensions, "documents", {}),
        (merge_categories, "categories", {}),
        (merge_payment_methods, "payment_methods", {}),
        (merge_registers, "registers", {}),
        (merge_descriptions, "descriptions", {}),
        (merge_articles, "articles", {}),
        (merge_fees, "fees", {"year": 2026, "month": 1}),
        (merge_contractors, "contractors", {}),
        (merge_dimensions, "dimensions", {}),
    ],
)
def test_empty_list_returns_empty_input_error(
    tool: Callable[..., Any],
    list_kwarg: str,
    extra_kwargs: dict[str, Any],
) -> None:
    result = tool(company_program_id="test-company", **{list_kwarg: []}, **extra_kwargs)
    assert isinstance(result, ErrorResponse)
    assert result.error == "EMPTY_INPUT"
