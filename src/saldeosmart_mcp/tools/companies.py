"""Company tools — discovery of the available companies on the account."""

from __future__ import annotations

from ..models import Company, CompanyList, ErrorResponse
from ._runtime import get_client, mcp, parse_collection, saldeo_call


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
