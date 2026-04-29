"""Financial-balance tool — accounting-firm monthly aggregates (SSK01)."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..http.xml import set_text
from ..models import (
    ErrorResponse,
    FinancialBalanceMergeInput,
    MergeResult,
)
from ._runtime import get_client, mcp, saldeo_call, summarize_merge


@mcp.tool
@saldeo_call
def merge_financial_balance(
    company_program_id: str,
    balance: FinancialBalanceMergeInput,
) -> MergeResult | ErrorResponse:
    """Set the monthly financial balance (income, cost, VAT) for a company (SSK01).

    Used by accounting firms to record the closing aggregates for a given
    (year, month) folder. Single record per call — Saldeo answers with
    ``MERGED`` when the folder already had a balance, ``CREATED`` when it
    didn't.

    Optional ``<ATTACHMENTS>`` are part of the spec but not yet wrapped;
    that's a follow-up once the attachment helper lands.
    """
    xml = _build_financial_balance_merge_xml(balance)
    root = get_client().post_command(
        "/api/xml/1.15/financial_balance/merge",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=1)


def _build_financial_balance_merge_xml(balance: FinancialBalanceMergeInput) -> str:
    # Element order matches financial_balance_merge_request.xsd:
    # <ROOT><FOLDER><YEAR/><MONTH/></FOLDER>
    #       <FINANCIAL_BALANCE><INCOME_MONTH/><COST_MONTH/><VAT/></FINANCIAL_BALANCE>
    # </ROOT>
    root = ET.Element("ROOT")
    folder = ET.SubElement(root, "FOLDER")
    set_text(folder, "YEAR", balance.year)
    set_text(folder, "MONTH", balance.month)

    fb = ET.SubElement(root, "FINANCIAL_BALANCE")
    set_text(fb, "INCOME_MONTH", balance.income_month)
    set_text(fb, "COST_MONTH", balance.cost_month)
    if balance.vat is not None:
        vat = ET.SubElement(fb, "VAT")
        set_text(vat, "VALUE", balance.vat.value)
        set_text(vat, "VALUE_TO_SHIFT", balance.vat.value_to_shift)
    return ET.tostring(root, encoding="unicode")
