"""MCP tool registry — one submodule per Saldeo resource family.

**Importing this package has a side effect**: every tool submodule is
imported eagerly, which is what registers the ``@mcp.tool`` decorators
against the shared FastMCP instance. ``server.main()`` does
``import saldeosmart_mcp.tools`` exactly once before calling ``mcp.run()``;
that's enough to make every tool visible to MCP clients.

Tool functions are also re-exported here so callers can do
``from saldeosmart_mcp.tools import list_documents`` without having to
remember which file each tool lives in. The mcp instance and helpers
live in ``_runtime``.
"""

from __future__ import annotations

# Importing each submodule registers its @mcp.tool functions against the shared
# FastMCP instance. The submodules each `from ._runtime import mcp`, so
# `_runtime` is fully initialized before the first tool body runs regardless of
# the order in this file (isort puts `from .` before `from ._runtime`).
from . import (
    accounting_close,
    bank,
    catalog,
    companies,
    contractors,
    dimensions,
    documents,
    financial_balance,
    invoices,
    personnel,
)
from ._runtime import (
    close_client,
    error_response,
    get_client,
    mcp,
    parse_collection,
    saldeo_call,
    summarize_merge,
)
from .accounting_close import merge_declarations, renew_assurances
from .bank import list_bank_statements
from .catalog import (
    merge_articles,
    merge_categories,
    merge_descriptions,
    merge_fees,
    merge_payment_methods,
    merge_registers,
)
from .companies import list_companies, synchronize_companies
from .contractors import list_contractors, merge_contractors
from .dimensions import merge_dimensions
from .documents import (
    add_documents,
    add_recognize_document,
    correct_documents,
    delete_documents,
    get_document_id_list,
    get_documents_by_id,
    list_documents,
    list_recognized_documents,
    merge_document_dimensions,
    recognize_documents,
    search_documents,
    sync_documents,
    update_documents,
)
from .financial_balance import merge_financial_balance
from .invoices import (
    get_invoice_id_list,
    get_invoices_by_id,
    list_invoices,
)
from .personnel import (
    add_employees,
    add_personnel_documents,
    list_employees,
    list_personnel_documents,
)

__all__ = [
    # Reads
    "list_bank_statements",
    "list_companies",
    "list_contractors",
    "list_documents",
    "list_employees",
    "list_invoices",
    "list_personnel_documents",
    "list_recognized_documents",
    "search_documents",
    "get_document_id_list",
    "get_documents_by_id",
    "get_invoice_id_list",
    "get_invoices_by_id",
    # Writes
    "add_documents",
    "add_employees",
    "add_personnel_documents",
    "add_recognize_document",
    "correct_documents",
    "delete_documents",
    "merge_articles",
    "merge_categories",
    "merge_contractors",
    "merge_descriptions",
    "merge_declarations",
    "merge_dimensions",
    "merge_document_dimensions",
    "merge_fees",
    "merge_financial_balance",
    "merge_payment_methods",
    "merge_registers",
    "recognize_documents",
    "renew_assurances",
    "sync_documents",
    "synchronize_companies",
    "update_documents",
    # Runtime helpers
    "close_client",
    "error_response",
    "get_client",
    "mcp",
    "parse_collection",
    "saldeo_call",
    "summarize_merge",
    # Submodule references (so static analyzers see them as used)
    "accounting_close",
    "bank",
    "catalog",
    "companies",
    "contractors",
    "dimensions",
    "documents",
    "financial_balance",
    "invoices",
    "personnel",
]
