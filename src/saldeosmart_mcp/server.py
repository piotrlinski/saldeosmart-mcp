"""
SaldeoSMART MCP server — read-only access to documents, invoices, contractors.

Exposes Claude-friendly tools that wrap the XML/MD5/gzip ugliness of the
SaldeoSMART API behind clean Python signatures returning plain dicts.

Configuration via environment variables:
    SALDEO_USERNAME   — your SaldeoSMART login
    SALDEO_API_TOKEN  — API token from Settings → API
    SALDEO_BASE_URL   — optional, defaults to https://saldeo.brainshare.pl
                        (use https://saldeo-test.brainshare.pl for sandbox)

Run locally:
    python -m saldeosmart_mcp.server

Connect from Claude Desktop — see README.md for claude_desktop_config.json snippet.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from xml.etree import ElementTree as ET

from fastmcp import FastMCP

from .client import SaldeoClient, SaldeoConfig, SaldeoError, el_int, el_text

logger = logging.getLogger(__name__)

mcp = FastMCP("SaldeoSMART")


def _client() -> SaldeoClient:
    """Build a client from env vars. Raises a clear error if creds are missing."""
    username = os.environ.get("SALDEO_USERNAME")
    token = os.environ.get("SALDEO_API_TOKEN")
    if not username or not token:
        raise RuntimeError(
            "Missing SaldeoSMART credentials. Set SALDEO_USERNAME and "
            "SALDEO_API_TOKEN environment variables (the token is generated "
            "in SaldeoSMART under Settings → API)."
        )
    base_url = os.environ.get("SALDEO_BASE_URL") or "https://saldeo.brainshare.pl"
    return SaldeoClient(SaldeoConfig(username=username, api_token=token,
                                     base_url=base_url))


# ---- Parsers ---------------------------------------------------------------------

def _parse_company(el: ET.Element) -> dict[str, Any]:
    return {
        "company_id": el_int(el, "COMPANY_ID"),
        "program_id": el_text(el, "COMPANY_PROGRAM_ID"),
        "name": el_text(el, "NAME"),
        "short_name": el_text(el, "SHORT_NAME"),
        "vat_number": el_text(el, "VAT_NUMBER"),
        "regon": el_text(el, "REGON"),
        "address": el_text(el, "ADDRESS"),
        "city": el_text(el, "CITY"),
        "postal_code": el_text(el, "POSTAL_CODE"),
    }


def _parse_contractor(el: ET.Element) -> dict[str, Any]:
    return {
        "contractor_id": el_int(el, "CONTRACTOR_ID"),
        "program_id": el_text(el, "CONTRACTOR_PROGRAM_ID"),
        "short_name": el_text(el, "SHORT_NAME"),
        "full_name": el_text(el, "FULL_NAME"),
        "vat_number": el_text(el, "VAT_NUMBER"),
        "address": el_text(el, "ADDRESS"),
        "city": el_text(el, "CITY"),
        "postal_code": el_text(el, "POSTAL_CODE"),
        "inactive": el_text(el, "INACTIVE") == "true",
    }


def _parse_document(el: ET.Element) -> dict[str, Any]:
    """Parse a DOCUMENT element. Keeps it flat for easy LLM consumption."""
    contractor_el = el.find("CONTRACTOR")
    contractor = _parse_contractor(contractor_el) if contractor_el is not None else None

    items: list[dict[str, Any]] = []
    items_el = el.find("DOCUMENT_ITEMS")
    if items_el is not None:
        for item in items_el.findall("DOCUMENT_ITEM"):
            items.append({
                "name": el_text(item, "NAME"),
                "quantity": el_text(item, "QUANTITY"),
                "unit_price_net": el_text(item, "UNIT_PRICE_NET"),
                "value_net": el_text(item, "VALUE_NET"),
                "value_gross": el_text(item, "VALUE_GROSS"),
                "vat_rate": el_text(item, "VAT_RATE"),
                "category": el_text(item, "CATEGORY"),
            })

    return {
        "document_id": el_int(el, "DOCUMENT_ID"),
        "guid": el_text(el, "GUID"),
        "number": el_text(el, "NUMBER"),
        "type": el_text(el, "TYPE"),
        "issue_date": el_text(el, "ISSUE_DATE"),
        "sale_date": el_text(el, "SALE_DATE"),
        "payment_due_date": el_text(el, "PAYMENT_DUE_DATE"),
        "value_net": el_text(el, "VALUE_NET"),
        "value_gross": el_text(el, "VALUE_GROSS"),
        "value_vat": el_text(el, "VALUE_VAT"),
        "currency": el_text(el, "CURRENCY"),
        "is_paid": el_text(el, "IS_DOCUMENT_PAID") == "true",
        "is_mpp": el_text(el, "IS_MPP") == "true",
        "source_url": el_text(el, "SOURCE_URL"),
        "preview_url": el_text(el, "PREVIEW_URL"),
        "contractor": contractor,
        "items": items,
    }


# ---- Tools -----------------------------------------------------------------------

@mcp.tool
def list_companies(company_program_id: str | None = None) -> dict[str, Any]:
    """
    List companies (firms) available in SaldeoSMART.

    Args:
        company_program_id: Optional. Filter by external program ID
            (e.g. an ERP-side identifier). If omitted, returns all companies.

    Returns:
        {"companies": [...]} where each entry has company_id, program_id,
        name, short_name, vat_number, regon, address, city, postal_code.
    """
    query = {"company_program_id": company_program_id} if company_program_id else {}
    with _client() as c:
        try:
            root = c.get("/api/xml/1.0/company/list", query=query)
        except SaldeoError as e:
            return {"error": e.code, "message": e.message}

    companies_el = root.find("COMPANIES")
    companies = (
        [_parse_company(el) for el in companies_el.findall("COMPANY")]
        if companies_el is not None else []
    )
    return {"companies": companies, "count": len(companies)}


@mcp.tool
def list_contractors(company_program_id: str) -> dict[str, Any]:
    """
    List contractors (suppliers and customers) for a specific company.

    Args:
        company_program_id: External program ID of the company. Required.
            Get one from list_companies first if you don't know it.

    Returns:
        {"contractors": [...]} with contractor_id, program_id, name,
        vat_number, address, etc.
    """
    with _client() as c:
        try:
            root = c.get("/api/xml/1.23/contractor/list",
                         query={"company_program_id": company_program_id})
        except SaldeoError as e:
            return {"error": e.code, "message": e.message}

    contractors_el = root.find("CONTRACTORS")
    contractors = (
        [_parse_contractor(el) for el in contractors_el.findall("CONTRACTOR")]
        if contractors_el is not None else []
    )
    return {"contractors": contractors, "count": len(contractors)}


@mcp.tool
def list_documents(
    company_program_id: str,
    policy: str = "LAST_10_DAYS",
) -> dict[str, Any]:
    """
    List documents (invoices, receipts) for a company.

    Args:
        company_program_id: External program ID of the company.
        policy: Which documents to return. One of:
            - "LAST_10_DAYS" — all documents added in the last 10 days (default)
            - "LAST_10_DAYS_OCRED" — only OCR-processed docs from last 10 days
            - "SALDEO" — only documents marked for export from SaldeoSMART UI

    Returns:
        {"documents": [...]} with full document details including line items,
        contractor info, amounts, dates, and links to PDF/JPG previews.
    """
    if policy not in ("LAST_10_DAYS", "LAST_10_DAYS_OCRED", "SALDEO"):
        return {
            "error": "INVALID_POLICY",
            "message": f"policy must be LAST_10_DAYS, LAST_10_DAYS_OCRED, or SALDEO; got {policy!r}",
        }

    with _client() as c:
        try:
            # Use API version 2.12 — most recent stable with rich document fields
            root = c.get("/api/xml/2.12/document/list",
                         query={"company_program_id": company_program_id,
                                "policy": policy})
        except SaldeoError as e:
            return {"error": e.code, "message": e.message}

    docs_el = root.find("DOCUMENTS")
    documents = (
        [_parse_document(el) for el in docs_el.findall("DOCUMENT")]
        if docs_el is not None else []
    )
    return {"documents": documents, "count": len(documents)}


@mcp.tool
def search_documents(
    company_program_id: str,
    document_id: int | None = None,
    number: str | None = None,
    nip: str | None = None,
    guid: str | None = None,
) -> dict[str, Any]:
    """
    Search for specific documents by ID, document number, contractor NIP, or GUID.

    Pass at least one of document_id / number / nip / guid. Combining number+nip
    narrows down a single invoice from a known supplier.

    Args:
        company_program_id: External program ID of the company.
        document_id: Internal SaldeoSMART document ID.
        number: Document number as printed on the invoice.
        nip: Contractor's tax ID.
        guid: Document GUID.

    Returns:
        {"documents": [...]} with full details for matched documents.
    """
    if not any((document_id, number, nip, guid)):
        return {
            "error": "MISSING_CRITERIA",
            "message": "Provide at least one of document_id, number, nip, or guid.",
        }

    # Build BY_FIELDS search request XML per spec v1.8
    fields_xml = ""
    if document_id is not None:
        fields_xml += f"<DOCUMENT_ID>{document_id}</DOCUMENT_ID>"
    if number:
        fields_xml += f"<NUMBER>{_xml_escape(number)}</NUMBER>"
    if nip:
        fields_xml += f"<NIP>{_xml_escape(nip)}</NIP>"
    if guid:
        fields_xml += f"<GUID>{_xml_escape(guid)}</GUID>"

    xml = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<ROOT>"
        "<POLICY>BY_FIELDS</POLICY>"
        f"<FIELDS>{fields_xml}</FIELDS>"
        "</ROOT>"
    )

    with _client() as c:
        try:
            root = c.post_command(
                "/api/xml/1.8/document/search",
                xml_command=xml,
                query={"company_program_id": company_program_id},
            )
        except SaldeoError as e:
            return {"error": e.code, "message": e.message}

    docs_el = root.find("DOCUMENTS")
    documents = (
        [_parse_document(el) for el in docs_el.findall("DOCUMENT")]
        if docs_el is not None else []
    )
    return {"documents": documents, "count": len(documents)}


@mcp.tool
def list_invoices(company_program_id: str) -> dict[str, Any]:
    """
    List sales invoices issued in SaldeoSMART (only those marked for export).

    This is for invoices CREATED in SaldeoSMART (the invoicing module),
    not OCR-processed cost documents — for those use list_documents.

    Args:
        company_program_id: External program ID of the company.

    Returns:
        {"invoices": [...]} with invoice details including KSeF status if applicable.
    """
    with _client() as c:
        try:
            root = c.get("/api/xml/1.20/invoice/list",
                         query={"company_program_id": company_program_id,
                                "policy": "SALDEO"})
        except SaldeoError as e:
            return {"error": e.code, "message": e.message}

    invoices_el = root.find("INVOICES")
    invoices: list[dict[str, Any]] = []
    if invoices_el is not None:
        for inv in invoices_el.findall("INVOICE"):
            # Reuse document parser since structure is similar
            invoices.append(_parse_document(inv))
    return {"invoices": invoices, "count": len(invoices)}


# ---- Helpers ---------------------------------------------------------------------

def _xml_escape(s: str) -> str:
    """Minimal XML-escape for text-only nodes."""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("SALDEO_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    mcp.run()  # stdio transport — what Claude Desktop expects


if __name__ == "__main__":
    main()
