"""Company tools — discovery + ERP-side identifier synchronization."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..http.xml import set_text
from ..models import (
    Company,
    CompanyCreateInput,
    CompanyList,
    CompanySynchronizeInput,
    ErrorResponse,
    MergeResult,
)
from . import endpoints
from ._runtime import get_client, mcp, merge_call, parse_collection, require_nonempty, saldeo_call


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
    root = get_client().get(endpoints.COMPANY_LIST, query=query)
    companies = parse_collection(root, "COMPANIES", "COMPANY", Company.from_xml)
    return CompanyList(companies=companies, count=len(companies))


@mcp.tool
@saldeo_call
@require_nonempty("companies", message="At least one company mapping is required.")
def synchronize_companies(
    companies: list[CompanySynchronizeInput],
) -> MergeResult | ErrorResponse:
    """Pin Saldeo company IDs to your ERP's program IDs (SS15).

    Establishes the mapping that every other tool relies on (every other
    endpoint expects ``company_program_id``). Each row sets one
    ``COMPANY_PROGRAM_ID`` for the matching ``COMPANY_ID`` — Saldeo answers
    per-item with ``MERGED`` / ``NOT_VALID`` / ``CONFLICT``.
    """
    xml = _build_company_synchronize_xml(companies)
    return merge_call(endpoints.COMPANY_SYNCHRONIZE, xml, total=len(companies))


def _build_company_synchronize_xml(companies: list[CompanySynchronizeInput]) -> str:
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "COMPANIES")
    for c in companies:
        item = ET.SubElement(container, "COMPANY")
        set_text(item, "COMPANY_ID", c.company_id)
        set_text(item, "COMPANY_PROGRAM_ID", c.company_program_id)
    return ET.tostring(root, encoding="unicode")


@mcp.tool
@saldeo_call
@require_nonempty("companies", message="At least one company is required.")
def create_companies(
    companies: list[CompanyCreateInput],
) -> MergeResult | ErrorResponse:
    """Create new client companies (and their admin users) in one shot (SS01).

    Each entry creates a new Saldeo company plus the admin login that owns
    it. The ``send_email`` flag controls whether Saldeo emails the welcome
    message to the admin (default: skip). Saldeo answers per-company with
    ``CREATED`` or ``MERGED`` (when the COMPANY_PROGRAM_ID already exists)
    plus the resolved Saldeo COMPANY_ID and the generated PASSWORD.

    Many required fields and irreversible side effects — usually low value
    for an interactive MCP session, but exposed here for completeness.
    """
    xml = _build_company_create_xml(companies)
    return merge_call(endpoints.COMPANY_CREATE, xml, total=len(companies))


def _build_company_create_xml(companies: list[CompanyCreateInput]) -> str:
    # Element order matches company_create_request.xml. METAINF/PRODUCER is
    # written when any of the input rows set ``producer`` — Saldeo allows a
    # single METAINF block at the top of the request, not per-company.
    root = ET.Element("ROOT")
    producer = next((c.producer for c in companies if c.producer), None)
    if producer:
        metainf = ET.SubElement(root, "METAINF")
        set_text(metainf, "PRODUCER", producer)
    container = ET.SubElement(root, "COMPANIES")
    for c in companies:
        item = ET.SubElement(container, "COMPANY")
        set_text(item, "COMPANY_PROGRAM_ID", c.company_program_id)
        set_text(item, "USERNAME", c.username)
        set_text(item, "FIRST_NAME", c.first_name)
        set_text(item, "LAST_NAME", c.last_name)
        set_text(item, "EMAIL", c.email)
        set_text(item, "SHORT_NAME", c.short_name)
        set_text(item, "FULL_NAME", c.full_name)
        set_text(item, "VAT_NUMBER", c.vat_number)
        set_text(item, "CITY", c.city)
        set_text(item, "POSTCODE", c.postcode)
        set_text(item, "STREET", c.street)
        set_text(item, "TELEPHONE", c.telephone)
        set_text(item, "CONTACT_PERSON", c.contact_person)
        if c.bank_accounts:
            accounts = ET.SubElement(item, "BANK_ACCOUNTS")
            for ba in c.bank_accounts:
                ba_el = ET.SubElement(accounts, "BANK_ACCOUNT")
                set_text(ba_el, "NAME", ba.name)
                set_text(ba_el, "NUMBER", ba.number)
                set_text(ba_el, "BANK_NAME", ba.bank_name)
                set_text(ba_el, "BIC_NUMBER", ba.bic_number)
                set_text(ba_el, "CURRENCY_ISO4217", ba.currency_iso4217)
        set_text(item, "ZUS_BANK_ACCOUNT", c.zus_bank_account)
        set_text(item, "SEND_EMAIL", c.send_email)
    return ET.tostring(root, encoding="unicode")
