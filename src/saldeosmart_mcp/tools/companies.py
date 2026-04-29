"""Company tools — discovery + ERP-side identifier synchronization."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..http.xml import set_text
from ..models import (
    Company,
    CompanyList,
    CompanySynchronizeInput,
    ErrorResponse,
    MergeResult,
)
from ._runtime import get_client, mcp, parse_collection, saldeo_call, summarize_merge


@mcp.tool
@saldeo_call
def list_companies(company_program_id: str | None = None) -> CompanyList | ErrorResponse:
    """List companies (firms) available in SaldeoSMART.

    Args:
        company_program_id: Optional. Filter by external program ID
            (e.g. an ERP-side identifier). If omitted, returns all companies.

    Returns:
        CompanyList with each entry's company_id, program_id, name, short_name,
        vat_number, regon, address, city, postal_code. On Saldeo errors,
        an ErrorResponse with code, message, and optional per-item details.
    """
    query = {"company_program_id": company_program_id} if company_program_id else {}
    root = get_client().get("/api/xml/1.0/company/list", query=query)
    companies = parse_collection(root, "COMPANIES", "COMPANY", Company.from_xml)
    return CompanyList(companies=companies, count=len(companies))


@mcp.tool
@saldeo_call
def synchronize_companies(
    companies: list[CompanySynchronizeInput],
) -> MergeResult | ErrorResponse:
    """Pin Saldeo company IDs to your ERP's program IDs (SS15).

    Establishes the mapping that every other tool relies on (every other
    endpoint expects ``company_program_id``). Each row sets one
    ``COMPANY_PROGRAM_ID`` for the matching ``COMPANY_ID`` — Saldeo answers
    per-item with ``MERGED`` / ``NOT_VALID`` / ``CONFLICT``.
    """
    if not companies:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one company mapping is required.",
        )
    xml = _build_company_synchronize_xml(companies)
    root = get_client().post_command("/api/xml/1.0/company/synchronize", xml_command=xml)
    return summarize_merge(root, total=len(companies))


def _build_company_synchronize_xml(companies: list[CompanySynchronizeInput]) -> str:
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "COMPANIES")
    for c in companies:
        item = ET.SubElement(container, "COMPANY")
        set_text(item, "COMPANY_ID", c.company_id)
        set_text(item, "COMPANY_PROGRAM_ID", c.company_program_id)
    return ET.tostring(root, encoding="unicode")
