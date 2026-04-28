"""Bank statement tools — read-only listing.

Saldeo's bank statements are produced by uploading a statement PDF and
running their OCR — there's no write counterpart in this server today.
The Bank Statement module is a separate Saldeo entitlement; calls return
``6001 — User does not have access`` if the account doesn't have it.
"""

from __future__ import annotations

from ..models import BankStatement, BankStatementList, ErrorResponse
from ._runtime import get_client, mcp, parse_collection, saldeo_call


@mcp.tool
@saldeo_call
def list_bank_statements(company_program_id: str) -> BankStatementList | ErrorResponse:
    """List bank statements (with operations, dimensions, settlements).

    Args:
        company_program_id: External program ID of the company.

    Returns:
        BankStatementList with one entry per statement and a flat list of
        bank operations under each statement (account number, amount, type,
        debit/credit, currency, etc.). Saldeo returns rich nested data
        (matched contractors, dimensions, settled invoices) — only the
        headline fields are surfaced; raw XML access is via the lower-level
        client if you need everything.
    """
    root = get_client().get(
        "/api/xml/2.18/bank_statement/list",
        query={"company_program_id": company_program_id},
    )
    statements = parse_collection(
        root, "BANK_STATEMENTS", "BANK_STATEMENT", BankStatement.from_xml
    )
    return BankStatementList(statements=statements, count=len(statements))
