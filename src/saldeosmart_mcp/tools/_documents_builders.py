"""XML request-body builders for the document tools.

Split out of ``tools.documents`` so the public tool module stays focused
on the ``@mcp.tool`` registrations. None of these helpers carry MCP
state — they take Pydantic input models, emit XML strings, and that's
all. Keep them out of the public ``__init__`` re-exports; tests can
import directly when needed.

Element order in every builder matches the corresponding XSD or sample
payload mirrored under ``.temp/api-html-mirror/``; the cited spec path
is in the function-level comment.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from xml.etree import ElementTree as ET

from ..http.attachments import PreparedAttachment
from ..http.xml import set_text
from ..models import (
    DocumentAddInput,
    DocumentAddRecognizeInput,
    DocumentCorrectInput,
    DocumentDimensionInput,
    DocumentImportInput,
    DocumentImportLineItemInput,
    DocumentImportNoVATInput,
    DocumentImportVATInput,
    DocumentSyncInput,
    DocumentUpdateInput,
    RecognizeOptionInput,
)
from ._builders import append_id_group


def build_search_xml(
    *,
    document_id: int | None,
    number: str | None,
    nip: str | None,
    guid: str | None,
) -> str:
    """Build the BY_FIELDS document/search payload using ElementTree.

    Avoids hand-rolled escaping: ElementTree escapes special characters
    (`<`, `>`, `&`) in element text automatically.

    Saldeo names the element ``SEARCH_POLICY`` (not ``POLICY``); using the
    wrong tag returns ``4401 No SEARCH_POLICY found in file``.
    """
    root = ET.Element("ROOT")
    ET.SubElement(root, "SEARCH_POLICY").text = "BY_FIELDS"
    fields = ET.SubElement(root, "FIELDS")
    if document_id is not None:
        ET.SubElement(fields, "DOCUMENT_ID").text = str(document_id)
    if number:
        ET.SubElement(fields, "NUMBER").text = number
    if nip:
        ET.SubElement(fields, "NIP").text = nip
    if guid:
        ET.SubElement(fields, "GUID").text = guid
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def build_document_id_groups_xml(
    *,
    contracts: list[int] | None,
    invoices_cost: list[int] | None,
    invoices_internal: list[int] | None,
    invoices_material: list[int] | None,
    invoices_sale: list[int] | None,
    orders: list[int] | None,
    writings: list[int] | None,
    other_documents: list[int] | None,
) -> str:
    root = ET.Element("ROOT")
    append_id_group(root, "CONTRACTS", "CONTRACT", contracts)
    append_id_group(root, "INVOICES_COST", "INVOICE_COST", invoices_cost)
    append_id_group(root, "INVOICES_INTERNAL", "INVOICE_INTERNAL", invoices_internal)
    append_id_group(root, "INVOICES_MATERIAL", "INVOICE_MATERIAL", invoices_material)
    append_id_group(root, "INVOICES_SALE", "INVOICE_SALE", invoices_sale)
    append_id_group(root, "ORDERS", "ORDER", orders)
    append_id_group(root, "WRITINGS", "WRITING", writings)
    append_id_group(root, "OTHER_DOCUMENTS", "OTHER_DOCUMENT", other_documents)
    return ET.tostring(root, encoding="unicode")


def build_ocr_id_list_xml(ocr_origin_ids: list[int]) -> str:
    """Body for document.list_recognized.

    Shape: ``<ROOT><OCR_ID_LIST><OCR_ORIGIN_ID/>...</OCR_ID_LIST></ROOT>``.
    """
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "OCR_ID_LIST")
    for ocr_id in ocr_origin_ids:
        ET.SubElement(container, "OCR_ORIGIN_ID").text = str(ocr_id)
    return ET.tostring(root, encoding="unicode")


def build_document_update_xml(documents: list[DocumentUpdateInput]) -> str:
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "DOCUMENTS")
    for d in documents:
        item = ET.SubElement(container, "DOCUMENT")
        set_text(item, "DOCUMENT_ID", d.document_id)
        set_text(item, "NUMBER", d.number)
        set_text(item, "ISSUE_DATE", d.issue_date)
        set_text(item, "SALE_DATE", d.sale_date)
        set_text(item, "PAYMENT_DATE", d.payment_date)
        if d.contractor_program_id is not None:
            contractor = ET.SubElement(item, "CONTRACTOR")
            set_text(contractor, "CONTRACTOR_PROGRAM_ID", d.contractor_program_id)
        set_text(item, "BANK_ACCOUNT", d.bank_account)
        set_text(item, "SELF_LEARNING", d.self_learning)
    return ET.tostring(root, encoding="unicode")


def build_document_delete_xml(document_ids: list[int]) -> str:
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "DOCUMENT_DELETE_IDS")
    for doc_id in document_ids:
        ET.SubElement(container, "DOCUMENT_DELETE_ID").text = str(doc_id)
    return ET.tostring(root, encoding="unicode")


def build_recognize_xml(documents: list[RecognizeOptionInput]) -> str:
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "DOCUMENTS")
    for d in documents:
        item = ET.SubElement(container, "DOCUMENT")
        set_text(item, "DOCUMENT_ID", d.document_id)
        set_text(item, "SPLIT_MODE", d.split_mode)
        set_text(item, "NO_ROTATE", d.no_rotate)
        set_text(item, "OVERWRITE_DATA", d.overwrite_data)
    return ET.tostring(root, encoding="unicode")


def build_document_sync_xml(syncs: list[DocumentSyncInput]) -> str:
    # Element order matters — Saldeo's document.sync XSD declares
    # <xs:sequence>, which strict parsers enforce. Mirror the spec at
    # .temp/api-html-mirror/1_13/documentsync/document_sync_request.xsd.
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "DOCUMENT_SYNCS")
    for s in syncs:
        item = ET.SubElement(container, "DOCUMENT_SYNC")
        set_text(item, "SALDEO_ID", s.saldeo_id)
        set_text(item, "CONTRACTOR_PROGRAM_ID", s.contractor_program_id)
        set_text(item, "DOCUMENT_NUMBER", s.document_number)
        set_text(item, "GUID", s.guid)
        set_text(item, "DESCRIPTION", s.description)
        set_text(item, "NUMBERING_TYPE", s.numbering_type)
        set_text(item, "ACCOUNT_DOCUMENT_NUMBER", s.account_document_number)
        set_text(item, "DOCUMENT_STATUS", s.document_status)
        set_text(item, "ISSUE_DATE", s.issue_date)
        set_text(item, "SALDEO_GUID", s.saldeo_guid)
    return ET.tostring(root, encoding="unicode")


def build_document_add_xml(
    documents: list[DocumentAddInput],
    prepared: list[PreparedAttachment],
) -> str:
    # Element order matches document_add_request.xml:
    # YEAR, MONTH, ATTMNT, ATTMNT_NAME (optional but always emitted —
    # the helper resolves a name from the file basename when the caller
    # didn't supply one).
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "DOCUMENTS")
    for doc, att in zip(documents, prepared, strict=True):
        item = ET.SubElement(container, "DOCUMENT")
        set_text(item, "YEAR", doc.year)
        set_text(item, "MONTH", doc.month)
        set_text(item, "ATTMNT", att.key)
        set_text(item, "ATTMNT_NAME", att.name)
    return ET.tostring(root, encoding="unicode")


def build_document_add_recognize_xml(document: DocumentAddRecognizeInput) -> str:
    # XSD-style sequence for the AE01 single-document recognize body. The
    # binary file is delivered separately as the attmnt_1 form field — there
    # is no <ATTMNT> element in this request shape.
    root = ET.Element("ROOT")
    item = ET.SubElement(root, "DOCUMENT")
    set_text(item, "VAT_NUMBER", document.vat_number)
    set_text(item, "DOCUMENT_TYPE", document.document_type)
    set_text(item, "SPLIT_MODE", document.split_mode)
    set_text(item, "NO_ROTATE", document.no_rotate)
    return ET.tostring(root, encoding="unicode")


def build_document_correct_xml(documents: list[DocumentCorrectInput]) -> str:
    # Element order matches document_correct_request.xml: DOCUMENT_ID, NUMBER,
    # ISSUE_DATE, SALE_DATE, PAYMENT_DATE, CONTRACTOR, BANK_ACCOUNT,
    # SELF_LEARNING.
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "DOCUMENTS")
    for d in documents:
        item = ET.SubElement(container, "DOCUMENT")
        set_text(item, "DOCUMENT_ID", d.document_id)
        set_text(item, "NUMBER", d.number)
        set_text(item, "ISSUE_DATE", d.issue_date)
        set_text(item, "SALE_DATE", d.sale_date)
        set_text(item, "PAYMENT_DATE", d.payment_date)
        if d.contractor is not None:
            contractor = ET.SubElement(item, "CONTRACTOR")
            set_text(contractor, "SHORT_NAME", d.contractor.short_name)
            set_text(contractor, "FULL_NAME", d.contractor.full_name)
            set_text(contractor, "VAT_NUMBER", d.contractor.vat_number)
            set_text(contractor, "STREET", d.contractor.street)
            set_text(contractor, "CITY", d.contractor.city)
            set_text(contractor, "POSTCODE", d.contractor.postcode)
        set_text(item, "BANK_ACCOUNT", d.bank_account)
        set_text(item, "SELF_LEARNING", d.self_learning)
    return ET.tostring(root, encoding="unicode")


def build_document_dimension_xml(items: list[DocumentDimensionInput]) -> str:
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "DOCUMENT_DIMENSIONS")
    for d in items:
        item = ET.SubElement(container, "DOCUMENT_DIMENSION")
        set_text(item, "DOCUMENT_ID", d.document_id)
        dims = ET.SubElement(item, "DIMENSIONS")
        for dv in d.dimensions:
            dv_el = ET.SubElement(dims, "DIMENSION")
            set_text(dv_el, "CODE", dv.code)
            set_text(dv_el, "VALUE", dv.value)
    return ET.tostring(root, encoding="unicode")


def build_document_import_xml(
    documents: list[DocumentImportInput],
    prepared: list[PreparedAttachment],
) -> str:
    # Element order matches document_import_request.xsd. Each <DOCUMENT>
    # consumes 1 + len(doc.attachments) entries from `prepared`: the source
    # file first, then each supporting attachment.
    expected = sum(1 + len(doc.attachments) for doc in documents)
    if len(prepared) != expected:
        raise ValueError(
            f"prepared attachment count mismatch: got {len(prepared)}, expected {expected}"
        )
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "DOCUMENTS")
    cursor = 0
    for doc in documents:
        cursor = _append_document_import(container, doc, prepared, cursor)
    return ET.tostring(root, encoding="unicode")


def _append_document_import(
    parent: ET.Element,
    doc: DocumentImportInput,
    prepared: list[PreparedAttachment],
    cursor: int,
) -> int:
    item = ET.SubElement(parent, "DOCUMENT")
    source = prepared[cursor]
    cursor += 1

    set_text(item, "ATTMNT", source.key)
    set_text(item, "ATTMNT_NAME", source.name)
    set_text(item, "YEAR", doc.year)
    set_text(item, "MONTH", doc.month)

    type_el = ET.SubElement(item, "DOCUMENT_TYPE")
    if doc.document_type.id is not None:
        set_text(type_el, "ID", doc.document_type.id)
    else:
        set_text(type_el, "SHORT_NAME", doc.document_type.short_name)
        set_text(type_el, "MODEL_TYPE", doc.document_type.model_type)

    set_text(item, "ARCHIVAL_NUMBER", doc.archival_number)
    set_text(item, "RECEIVE_DATE", doc.receive_date)
    set_text(item, "CATEGORY", doc.category)
    set_text(item, "DESCRIPTION", doc.description)
    set_text(item, "REGISTRY", doc.registry)
    set_text(item, "NUMBER", doc.number)
    set_text(item, "ISSUE_DATE", doc.issue_date)
    set_text(item, "SALE_DATE", doc.sale_date)
    set_text(item, "PAYMENT_DATE", doc.payment_date)
    set_text(item, "PAYMENT_TYPE", doc.payment_type)
    set_text(item, "IS_CORRECTIVE", doc.is_corrective)
    set_text(item, "CORR_INV_NUM", doc.corr_inv_num)
    set_text(item, "CORR_INV_DATE", doc.corr_inv_date)
    set_text(item, "IS_CASH_BASIS", doc.is_cash_basis)
    set_text(item, "IS_MPP", doc.is_mpp)
    set_text(item, "CONTRACTOR_ID", doc.contractor_id)
    set_text(item, "CONTRACTOR_AREA", doc.contractor_area)
    set_text(item, "PAYER_CONTRACTOR_ID", doc.payer_contractor_id)
    set_text(item, "COUNTRY_CODE_VAT_NUMBER", doc.country_code_vat_number)
    set_text(item, "BANK_ACCOUNT", doc.bank_account)
    if doc.currency is not None:
        currency = ET.SubElement(item, "CURRENCY")
        set_text(currency, "CURRENCY_ISO4217", doc.currency.iso4217)
        set_text(currency, "CURRENCY_DATE", doc.currency.date)
        set_text(currency, "CURRENCY_RATE", doc.currency.rate)
    if doc.dimensions:
        _append_dimensions(item, doc.dimensions)
    if doc.vat_document is not None:
        _append_vat_document(item, doc.vat_document)
    elif doc.no_vat_document is not None:
        _append_no_vat_document(item, doc.no_vat_document)
    if doc.document_items:
        _append_document_items(item, doc.document_items)
    if doc.payments:
        payments = ET.SubElement(item, "PAYMENTS")
        for p in doc.payments:
            entry = ET.SubElement(payments, "PAYMENT")
            set_text(entry, "DATE", p.date)
            set_text(entry, "AMOUNT", p.amount)
    if doc.attachments:
        atts = ET.SubElement(item, "ATTACHMENTS")
        for att in doc.attachments:
            ref = prepared[cursor]
            cursor += 1
            entry = ET.SubElement(atts, "ATTACHMENT")
            set_text(entry, "ATTMNT", ref.key)
            set_text(entry, "ATTMNT_NAME", ref.name)
            set_text(entry, "DESCRIPTION", att.description)
    return cursor


def _append_dimensions(
    parent: ET.Element,
    dimensions: Sequence[Any],
) -> None:
    """Append <DIMENSIONS><DIMENSION><NAME/><VALUE/></DIMENSION>...</DIMENSIONS>."""
    block = ET.SubElement(parent, "DIMENSIONS")
    for dim in dimensions:
        dim_el = ET.SubElement(block, "DIMENSION")
        set_text(dim_el, "NAME", dim.name)
        set_text(dim_el, "VALUE", dim.value)


def _append_vat_document(parent: ET.Element, vat_doc: DocumentImportVATInput) -> None:
    block = ET.SubElement(parent, "VAT_DOCUMENT")
    if vat_doc.vat_registries:
        registries = ET.SubElement(block, "VAT_REGISTRIES")
        for reg in vat_doc.vat_registries:
            reg_el = ET.SubElement(registries, "VAT_REGISTRY")
            set_text(reg_el, "RATE", reg.rate)
            set_text(reg_el, "NETTO", reg.netto)
            set_text(reg_el, "VAT", reg.vat)
    if vat_doc.items:
        items = ET.SubElement(block, "ITEMS")
        for it in vat_doc.items:
            it_el = ET.SubElement(items, "ITEM")
            set_text(it_el, "RATE", it.rate)
            set_text(it_el, "NETTO", it.netto)
            set_text(it_el, "VAT", it.vat)
            set_text(it_el, "CATEGORY", it.category)
            set_text(it_el, "DESCRIPTION", it.description)
            if it.dimensions:
                _append_dimensions(it_el, it.dimensions)


def _append_no_vat_document(parent: ET.Element, no_vat_doc: DocumentImportNoVATInput) -> None:
    block = ET.SubElement(parent, "NO_VAT_DOCUMENT")
    set_text(block, "TOTAL_VALUE", no_vat_doc.total_value)
    if no_vat_doc.items:
        items = ET.SubElement(block, "ITEMS")
        for it in no_vat_doc.items:
            it_el = ET.SubElement(items, "ITEM")
            set_text(it_el, "VALUE", it.value)
            set_text(it_el, "CATEGORY", it.category)
            set_text(it_el, "DESCRIPTION", it.description)
            if it.dimensions:
                _append_dimensions(it_el, it.dimensions)


def _append_document_items(parent: ET.Element, items: list[DocumentImportLineItemInput]) -> None:
    block = ET.SubElement(parent, "DOCUMENT_ITEMS")
    for it in items:
        it_el = ET.SubElement(block, "DOCUMENT_ITEM")
        set_text(it_el, "CODE", it.code)
        set_text(it_el, "NAME", it.name)
        set_text(it_el, "AMOUNT", it.amount)
        set_text(it_el, "UNIT", it.unit)
        set_text(it_el, "RATE", it.rate)
        set_text(it_el, "UNIT_VALUE", it.unit_value)
        set_text(it_el, "NETTO", it.netto)
        set_text(it_el, "VAT", it.vat)
        set_text(it_el, "GROSS", it.gross)
        set_text(it_el, "CATEGORY", it.category)
        if it.dimension is not None:
            dim_block = ET.SubElement(it_el, "DIMENSIONS")
            dim_el = ET.SubElement(dim_block, "DIMENSION")
            set_text(dim_el, "NAME", it.dimension.name)
            set_text(dim_el, "VALUE", it.dimension.value)
