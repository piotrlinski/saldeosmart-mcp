"""Financial-balance tool — accounting-firm monthly aggregates (SSK01)."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..http.attachments import PreparedAttachment, prepare_attachments
from ..http.xml import set_text
from ..models import ErrorResponse, FinancialBalanceMergeInput, MergeResult
from . import endpoints
from ._builders import append_close_attachments
from ._runtime import mcp, merge_call, saldeo_call


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

    Optional ``attachments`` carry source-of-truth files (the source
    spreadsheet, a scanned report, etc.). Each attachment is read at tool
    invocation time and uploaded as a separate ``attmnt_N`` form field.
    """
    prepared, form = prepare_attachments([a.attachment for a in balance.attachments])
    xml = _build_financial_balance_merge_xml(balance, prepared)
    return merge_call(
        endpoints.FINANCIAL_BALANCE_MERGE,
        xml,
        total=1,
        query={"company_program_id": company_program_id},
        extra_form=form,
    )


def _build_financial_balance_merge_xml(
    balance: FinancialBalanceMergeInput,
    prepared: list[PreparedAttachment],
) -> str:
    # Element order matches financial_balance_merge_request.xsd:
    # <ROOT><FOLDER><YEAR/><MONTH/></FOLDER>
    #       <FINANCIAL_BALANCE><INCOME_MONTH/><COST_MONTH/><VAT/>
    #                          <ATTACHMENTS/></FINANCIAL_BALANCE>
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
    if balance.attachments:
        append_close_attachments(fb, balance.attachments, prepared)
    return ET.tostring(root, encoding="unicode")
