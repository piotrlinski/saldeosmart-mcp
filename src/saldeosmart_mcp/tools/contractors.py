"""Contractor tools — list and merge."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..http.xml import set_text
from ..models import (
    Contractor,
    ContractorInput,
    ContractorList,
    ErrorResponse,
    MergeResult,
)
from ._runtime import (
    get_client,
    mcp,
    parse_collection,
    saldeo_call,
    summarize_merge,
)


@mcp.tool
@saldeo_call
def list_contractors(company_program_id: str) -> ContractorList | ErrorResponse:
    """List contractors (suppliers and customers) for a specific company.

    Args:
        company_program_id: External program ID of the company. Required.
            Get one from list_companies first if you don't know it.
    """
    root = get_client().get(
        "/api/xml/1.23/contractor/list",
        query={"company_program_id": company_program_id},
    )
    contractors = parse_collection(root, "CONTRACTORS", "CONTRACTOR", Contractor.from_xml)
    return ContractorList(contractors=contractors, count=len(contractors))


@mcp.tool
@saldeo_call
def merge_contractors(
    company_program_id: str,
    contractors: list[ContractorInput],
) -> MergeResult | ErrorResponse:
    """Add or update contractors (suppliers/customers) in bulk (SS02).

    Each entry must include short_name and full_name. ``contractor_program_id``
    is your ERP-side ID; ``contractor_id`` is Saldeo's; either can identify
    an existing contractor for update. Without one, a new contractor is
    created. Saldeo returns per-item statuses — fields that failed validation
    surface in the ``errors`` list.
    """
    xml = _build_contractor_merge_xml(contractors)
    root = get_client().post_command(
        "/api/xml/1.23/contractor/merge",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(contractors))


def _build_contractor_merge_xml(contractors: list[ContractorInput]) -> str:
    """Hand-rolled builder for contractor.merge (1.23) — has nested
    BANK_ACCOUNTS and EMAILS lists."""
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "CONTRACTORS")
    for c in contractors:
        item = ET.SubElement(container, "CONTRACTOR")
        set_text(item, "CONTRACTOR_PROGRAM_ID", c.contractor_program_id)
        set_text(item, "CONTRACTOR_ID", c.contractor_id)
        set_text(item, "SHORT_NAME", c.short_name)
        set_text(item, "FULL_NAME", c.full_name)
        set_text(item, "SUPPLIER", c.supplier)
        set_text(item, "CUSTOMER", c.customer)
        set_text(item, "VAT_NUMBER", c.vat_number)
        set_text(item, "CITY", c.city)
        set_text(item, "POSTCODE", c.postcode)
        set_text(item, "STREET", c.street)
        set_text(item, "COUNTRY_ISO3166A2", c.country_iso3166a2)
        set_text(item, "TELEPHONE", c.telephone)
        set_text(item, "CONTACT_PERSON", c.contact_person)
        set_text(item, "DESCRIPTION", c.description)
        set_text(item, "PAYMENT_DAYS", c.payment_days)
        if c.bank_accounts:
            accounts = ET.SubElement(item, "BANK_ACCOUNTS")
            for acc in c.bank_accounts:
                acc_el = ET.SubElement(accounts, "BANK_ACCOUNT")
                set_text(acc_el, "NAME", acc.name)
                set_text(acc_el, "NUMBER", acc.number)
        if c.emails:
            emails = ET.SubElement(item, "EMAILS")
            for addr in c.emails:
                set_text(emails, "EMAIL", addr)
    return ET.tostring(root, encoding="unicode")
