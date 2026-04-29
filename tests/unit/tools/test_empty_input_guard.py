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
from saldeosmart_mcp.tools.companies import synchronize_companies
from saldeosmart_mcp.tools.contractors import merge_contractors
from saldeosmart_mcp.tools.dimensions import merge_dimensions
from saldeosmart_mcp.tools.documents import (
    add_documents,
    delete_documents,
    merge_document_dimensions,
    recognize_documents,
    sync_documents,
    update_documents,
)
from saldeosmart_mcp.tools.personnel import add_employees, add_personnel_documents


@pytest.mark.parametrize(
    "tool,list_kwarg,extra_kwargs,needs_company_program_id",
    [
        (update_documents, "documents", {}, True),
        (delete_documents, "document_ids", {}, True),
        (recognize_documents, "documents", {}, True),
        (sync_documents, "syncs", {}, True),
        (merge_document_dimensions, "documents", {}, True),
        (merge_categories, "categories", {}, True),
        (merge_payment_methods, "payment_methods", {}, True),
        (merge_registers, "registers", {}, True),
        (merge_descriptions, "descriptions", {}, True),
        (merge_articles, "articles", {}, True),
        (merge_fees, "fees", {"year": 2026, "month": 1}, True),
        (merge_contractors, "contractors", {}, True),
        (merge_dimensions, "dimensions", {}, True),
        (synchronize_companies, "companies", {}, False),
        (add_employees, "employees", {}, True),
        (add_documents, "documents", {}, True),
        (add_personnel_documents, "documents", {}, True),
    ],
)
def test_empty_list_returns_empty_input_error(
    tool: Callable[..., Any],
    list_kwarg: str,
    extra_kwargs: dict[str, Any],
    needs_company_program_id: bool,
) -> None:
    kwargs: dict[str, Any] = {list_kwarg: [], **extra_kwargs}
    if needs_company_program_id:
        kwargs["company_program_id"] = "test-company"
    result = tool(**kwargs)
    assert isinstance(result, ErrorResponse)
    assert result.error == "EMPTY_INPUT"
