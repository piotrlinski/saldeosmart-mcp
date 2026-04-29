"""Invoice tools — sales invoices issued in SaldeoSMART."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..http.xml import set_text
from ..models import (
    Document,
    ErrorResponse,
    InvoiceAddInput,
    InvoiceIdGroups,
    InvoiceList,
    MergeResult,
)
from ._builders import build_folder_xml
from ._runtime import get_client, mcp, parse_collection, saldeo_call, summarize_merge


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


@mcp.tool
@saldeo_call
def add_invoice(
    company_program_id: str,
    invoice: InvoiceAddInput,
) -> MergeResult | ErrorResponse:
    """Issue a new sales invoice in SaldeoSMART (3.1, SSK06).

    Creates one invoice with up to 10000 line items, optional payments, and
    optional new-transport-vehicle metadata. Saldeo answers per-record with
    ``CREATED`` (success) or ``NOT_VALID`` / ``ERROR``. No file attachments —
    SaldeoSMART generates the printable PDF on its side from the structured
    invoice data.
    """
    xml = _build_invoice_add_xml(invoice)
    root = get_client().post_command(
        "/api/xml/3.1/invoice/add",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=1)


def _build_invoice_add_xml(invoice: InvoiceAddInput) -> str:
    # Element order matches invoice_add_request.xsd. NUMBER + SUFFIX (when
    # present) lead the body, then the date block, the flags, the recipient
    # block, the bank/currency/footer fields, the items, and the optional
    # payments and new-transport-vehicle blocks.
    root = ET.Element("ROOT")
    item = ET.SubElement(root, "INVOICE")
    set_text(item, "NUMBER", invoice.number)
    set_text(item, "SUFFIX", invoice.suffix)
    set_text(item, "ISSUE_DATE", invoice.issue_date)
    if invoice.sale_date_range is not None:
        set_text(item, "SALE_DATE_FROM", invoice.sale_date_range.from_date)
        set_text(item, "SALE_DATE_TO", invoice.sale_date_range.to_date)
    else:
        set_text(item, "SALE_DATE", invoice.sale_date)
    set_text(item, "DUE_DATE", invoice.due_date)
    set_text(item, "ACCORDING_TO_AGREEMENT", invoice.according_to_agreement)
    set_text(item, "NO_VAT", invoice.no_vat)
    set_text(item, "CASH_BASIS", invoice.cash_basis)
    set_text(item, "PROFIT_MARGIN_TYPE", invoice.profit_margin_type)
    set_text(item, "EXEMPT_VAT_BASIS", invoice.exempt_vat_basis)
    set_text(item, "CALCULATED_FROM_GROSS", invoice.calculated_from_gross)
    set_text(item, "IS_MPP", invoice.is_mpp)
    set_text(item, "PURCHASER_CONTRACTOR_ID", invoice.purchaser_contractor_id)
    set_text(item, "SEND_TO_CONTRACTOR", invoice.send_to_contractor)
    if invoice.recipient_contractor_id is not None:
        set_text(item, "RECIPIENT_CONTRACTOR_ID", invoice.recipient_contractor_id)
        set_text(item, "RECIPIENT_ROLE", invoice.recipient_role)
        set_text(item, "RECIPIENT_INTERNAL_ID", invoice.recipient_internal_id)
    if invoice.bank_account is not None:
        bank = ET.SubElement(item, "BANK_ACCOUNT")
        set_text(bank, "NUMBER", invoice.bank_account.number)
        set_text(bank, "BANK", invoice.bank_account.bank)
        set_text(bank, "BIC_SWIFT", invoice.bank_account.bic_swift)
    set_text(item, "CURRENCY_ISO4217", invoice.currency_iso4217)
    set_text(item, "CURRENCY_DATE", invoice.currency_date)
    set_text(item, "PAYMENT_TYPE", invoice.payment_type)
    set_text(item, "ISSUE_PERSON", invoice.issue_person)
    set_text(item, "ISSUE_TO_KSEF", invoice.issue_to_ksef)
    set_text(item, "FOOTER", invoice.footer)
    items = ET.SubElement(item, "INVOICE_ITEMS")
    for it in invoice.items:
        line = ET.SubElement(items, "INVOICE_ITEM")
        set_text(line, "NAME", it.name)
        set_text(line, "PKWIU", it.pkwiu)
        set_text(line, "AMOUNT", it.amount)
        set_text(line, "UNIT", it.unit)
        set_text(line, "UNIT_VALUE", it.unit_value)
        if it.discount is not None:
            disc = ET.SubElement(line, "DISCOUNT")
            set_text(disc, "DISCOUNT_TYPE", it.discount.type)
            set_text(disc, "DISCOUNT_VALUE", it.discount.value)
        set_text(line, "RATE", it.rate)
        set_text(line, "PROCEDURE_CODE", it.procedure_code)
        set_text(line, "GTU_CODE", it.gtu_code)
    if invoice.payments:
        payments = ET.SubElement(item, "INVOICE_PAYMENTS")
        # XSD shape repeats PAYMENT_AMOUNT + PAYMENT_DATE per entry directly
        # under <INVOICE_PAYMENTS> — there's no inner wrapper.
        for p in invoice.payments:
            set_text(payments, "PAYMENT_AMOUNT", p.payment_amount)
            set_text(payments, "PAYMENT_DATE", p.payment_date)
    if invoice.new_transport_vehicle is not None:
        vehicle = ET.SubElement(item, "NEW_TRANSPORT_VEHICLE")
        set_text(vehicle, "VEHICLE_TYPE", invoice.new_transport_vehicle.vehicle_type)
        set_text(vehicle, "ADMISSION_DATE", invoice.new_transport_vehicle.admission_date)
        set_text(vehicle, "USAGE_METRICS", invoice.new_transport_vehicle.usage_metrics)
    return ET.tostring(root, encoding="unicode")


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
