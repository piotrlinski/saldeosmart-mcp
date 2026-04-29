"""Invoice tools — sales invoices issued in SaldeoSMART."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..models import (
    Document,
    ErrorResponse,
    InvoiceIdGroups,
    InvoiceList,
)
from ._builders import build_folder_xml
from ._runtime import get_client, mcp, parse_collection, saldeo_call


@mcp.tool
@saldeo_call
def list_invoices(company_program_id: str) -> InvoiceList | ErrorResponse:
    """List sales invoices issued in SaldeoSMART (only those marked for export).

    This is for invoices CREATED in SaldeoSMART (the invoicing module),
    not OCR-processed cost documents — for those use list_documents.
    """
    root = get_client().get(
        "/api/xml/1.20/invoice/list",
        query={"company_program_id": company_program_id, "policy": "SALDEO"},
    )
    # Invoice XML structure overlaps with Document; reuse the parser until
    # invoice-specific fields (KSeF status etc.) are needed.
    invoices = parse_collection(root, "INVOICES", "INVOICE", Document.from_xml)
    return InvoiceList(invoices=invoices, count=len(invoices))


@mcp.tool
@saldeo_call
def get_invoice_id_list(
    company_program_id: str,
    year: int,
    month: int,
) -> InvoiceIdGroups | ErrorResponse:
    """List invoice IDs in one folder, grouped by kind (SSK07).

    Buckets: invoices, corrective_invoices, pre_invoices, corrective_pre_invoices.
    Pair with `get_invoices_by_id` to fetch the records.
    """
    xml = build_folder_xml(year, month)
    root = get_client().post_command(
        "/api/xml/3.0/invoice/getidlist",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return InvoiceIdGroups.from_xml(root)


@mcp.tool
@saldeo_call
def get_invoices_by_id(
    company_program_id: str,
    invoices: list[int] | None = None,
    corrective_invoices: list[int] | None = None,
    pre_invoices: list[int] | None = None,
    corrective_pre_invoices: list[int] | None = None,
) -> InvoiceList | ErrorResponse:
    """Fetch full sales-invoice records for a set of IDs, grouped by kind.

    Pair with ``get_invoice_id_list`` for paginated browsing of one folder.
    Saldeo op: ``invoice.listbyid`` (3.0).

    Args:
        company_program_id: External program ID of the company.
        invoices, corrective_invoices, pre_invoices, corrective_pre_invoices:
            Optional lists of invoice IDs from ``get_invoice_id_list``.
            Pass only the buckets you care about; the rest default to None
            (omitted from the request).

    Returns:
        InvoiceList — flat list of invoice records.
    """
    xml = _build_invoice_id_groups_xml(
        invoices=invoices,
        corrective_invoices=corrective_invoices,
        pre_invoices=pre_invoices,
        corrective_pre_invoices=corrective_pre_invoices,
    )
    root = get_client().post_command(
        "/api/xml/3.0/invoice/listbyid",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    invoices_out = parse_collection(root, "INVOICES", "INVOICE", Document.from_xml)
    return InvoiceList(invoices=invoices_out, count=len(invoices_out))


def _build_invoice_id_groups_xml(
    *,
    invoices: list[int] | None,
    corrective_invoices: list[int] | None,
    pre_invoices: list[int] | None,
    corrective_pre_invoices: list[int] | None,
) -> str:
    from ._builders import append_id_group

    root = ET.Element("ROOT")
    append_id_group(root, "INVOICES", "INVOICE_ID", invoices)
    append_id_group(root, "CORRECTIVE_INVOICES", "CORRECTIVE_INVOICE_ID", corrective_invoices)
    append_id_group(root, "PRE_INVOICES", "PRE_INVOICE_ID", pre_invoices)
    append_id_group(
        root, "CORRECTIVE_PRE_INVOICES", "CORRECTIVE_PRE_INVOICE_ID", corrective_pre_invoices
    )
    return ET.tostring(root, encoding="unicode")
