"""Document tools — read, search, and write the cost-document family.

Covers nine MCP tools and their per-tool builders. The 3.0 paginated
endpoints (``getidlist`` / ``listbyid``) return their own typed shapes
(:class:`DocumentIdGroups`); the 2.x endpoints return :class:`DocumentList`.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..http.attachments import PreparedAttachment, prepare_attachments
from ..http.xml import set_text
from ..models import (
    Document,
    DocumentAddInput,
    DocumentDimensionInput,
    DocumentIdGroups,
    DocumentList,
    DocumentPolicy,
    DocumentSyncInput,
    DocumentUpdateInput,
    ErrorResponse,
    MergeResult,
    RecognizeOptionInput,
)
from ._builders import append_id_group, build_folder_xml
from ._runtime import (
    get_client,
    mcp,
    parse_collection,
    saldeo_call,
    summarize_merge,
)

# ---- Reads -----------------------------------------------------------------------


@mcp.tool
@saldeo_call
def list_documents(
    company_program_id: str,
    policy: DocumentPolicy = "LAST_10_DAYS",
) -> DocumentList | ErrorResponse:
    """List recently-added cost documents (invoices, receipts) for a company.

    Use this for a fast "what's new" scan. For lookup by a specific identifier,
    prefer ``search_documents``. For paginated browsing of a single month,
    use ``get_document_id_list`` + ``get_documents_by_id`` (3.0 endpoints).

    Args:
        company_program_id: External program ID of the company. Get one from
            ``list_companies`` if unknown.
        policy: Which documents to return:
            - LAST_10_DAYS — all documents added in the last 10 days (default)
            - LAST_10_DAYS_OCRED — only OCR-processed docs from last 10 days
            - SALDEO — only documents marked for export from SaldeoSMART UI

    Returns:
        DocumentList with each document's IDs, dates, monetary fields,
        contractor, and items. On failure, ErrorResponse — see
        docs/ERROR_CODES.md.
    """
    # Use API version 2.12 — most recent stable with rich document fields.
    root = get_client().get(
        "/api/xml/2.12/document/list",
        query={"company_program_id": company_program_id, "policy": policy},
    )
    documents = parse_collection(root, "DOCUMENTS", "DOCUMENT", Document.from_xml)
    return DocumentList(documents=documents, count=len(documents))


@mcp.tool
@saldeo_call
def search_documents(
    company_program_id: str,
    document_id: int | None = None,
    number: str | None = None,
    nip: str | None = None,
    guid: str | None = None,
) -> DocumentList | ErrorResponse:
    """Find a specific document by ID, document number, contractor NIP, or GUID.

    Use this for precise lookup. For a recent-activity scan, use
    ``list_documents`` instead.

    Args:
        company_program_id: External program ID of the company.
        document_id: Saldeo's internal numeric ID. At least one of
            document_id / number / nip / guid must be set.
        number: The document's printed number (e.g. "FV/1/2024").
        nip: The contractor's VAT number — narrows by counterparty.
        guid: Saldeo's stable per-document UUID.

    Returns:
        DocumentList (typically 0 or 1 document, sometimes more if number
        matches multiple). On failure, ErrorResponse.
    """
    if not any((document_id, number, nip, guid)):
        return ErrorResponse(
            error="MISSING_CRITERIA",
            message="Provide at least one of document_id, number, nip, or guid.",
        )

    xml = _build_search_xml(document_id=document_id, number=number, nip=nip, guid=guid)
    root = get_client().post_command(
        "/api/xml/1.8/document/search",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    documents = parse_collection(root, "DOCUMENTS", "DOCUMENT", Document.from_xml)
    return DocumentList(documents=documents, count=len(documents))


@mcp.tool
@saldeo_call
def get_document_id_list(
    company_program_id: str,
    year: int,
    month: int,
) -> DocumentIdGroups | ErrorResponse:
    """Discover all document IDs in one (year, month) folder, grouped by kind.

    Use this as the first step of paginated browsing — call with a specific
    month, then ``get_documents_by_id`` with the buckets you care about.
    For a "last 10 days" scan, use ``list_documents`` instead.

    Saldeo op: ``document.getidlist`` (3.0).

    Args:
        company_program_id: External program ID of the company.
        year: 4-digit year of the folder.
        month: Month of the folder, 1–12.

    Returns:
        DocumentIdGroups with eight ID buckets (contracts, invoices_cost,
        invoices_internal, invoices_material, invoices_sale, orders,
        writings, other_documents). Empty buckets are present but empty.
    """
    xml = build_folder_xml(year, month)
    root = get_client().post_command(
        "/api/xml/3.0/document/getidlist",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return DocumentIdGroups.from_xml(root)


@mcp.tool
@saldeo_call
def get_documents_by_id(
    company_program_id: str,
    contracts: list[int] | None = None,
    invoices_cost: list[int] | None = None,
    invoices_internal: list[int] | None = None,
    invoices_material: list[int] | None = None,
    invoices_sale: list[int] | None = None,
    orders: list[int] | None = None,
    writings: list[int] | None = None,
    other_documents: list[int] | None = None,
) -> DocumentList | ErrorResponse:
    """Fetch full document records for a set of IDs, grouped by kind.

    Pair with ``get_document_id_list`` (3.0 paginated browsing). Pass only
    the buckets you care about — omit unused ones. Saldeo op:
    ``document.listbyid`` (3.0).

    Args:
        company_program_id: External program ID of the company.
        contracts, invoices_cost, invoices_internal, invoices_material,
        invoices_sale, orders, writings, other_documents:
            Optional lists of document IDs from ``get_document_id_list``.
            Each list defaults to None (omitted from the request).

    Returns:
        DocumentList — flat list of full document records (the per-bucket
        grouping from the request is not preserved in the response).
    """
    xml = _build_document_id_groups_xml(
        contracts=contracts,
        invoices_cost=invoices_cost,
        invoices_internal=invoices_internal,
        invoices_material=invoices_material,
        invoices_sale=invoices_sale,
        orders=orders,
        writings=writings,
        other_documents=other_documents,
    )
    root = get_client().post_command(
        "/api/xml/3.0/document/listbyid",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    documents = parse_collection(root, "DOCUMENTS", "DOCUMENT", Document.from_xml)
    return DocumentList(documents=documents, count=len(documents))


@mcp.tool
@saldeo_call
def list_recognized_documents(
    company_program_id: str,
    ocr_origin_ids: list[int],
) -> DocumentList | ErrorResponse:
    """Fetch the OCR-processed document data for a set of OCR origin IDs (SS08).

    Args:
        company_program_id: External program ID of the company.
        ocr_origin_ids: IDs returned by a prior ``document.recognize`` call.
            Saldeo requires at least one — there's no "list everything" mode.

    Returns the same ``DocumentList`` shape as ``list_documents``. The richer
    nested data (articles, OCR origins, dimensions, KSeF) is dropped to keep
    the response LLM-friendly; reach for the lower-level client if needed.
    """
    if not ocr_origin_ids:
        return ErrorResponse(
            error="MISSING_CRITERIA",
            message="Provide at least one OCR origin ID. Get them from document.recognize.",
        )
    xml = _build_ocr_id_list_xml(ocr_origin_ids)
    root = get_client().post_command(
        "/api/xml/2.18/document/list_recognized",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    documents = parse_collection(root, "DOCUMENTS", "DOCUMENT", Document.from_xml)
    return DocumentList(documents=documents, count=len(documents))


# ---- Writes ----------------------------------------------------------------------


@mcp.tool
@saldeo_call
def add_documents(
    company_program_id: str,
    documents: list[DocumentAddInput],
) -> MergeResult | ErrorResponse:
    """Upload cost documents (PDF, image, etc.) to a (year, month) folder (SS05).

    Each entry pairs a folder with one local file. The file is read at
    invocation time, base64-encoded, and uploaded as the matching
    ``attmnt_N`` form field; ``<ATTMNT>`` in the XML carries the integer
    reference, ``<ATTMNT_NAME>`` carries the display name (defaults to the
    file's basename when not overridden in :class:`Attachment`).
    """
    if not documents:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one document is required.",
        )
    prepared, form = prepare_attachments([d.attachment for d in documents])
    xml = _build_document_add_xml(documents, prepared)
    root = get_client().post_command(
        "/api/xml/1.0/document/add",
        xml_command=xml,
        query={"company_program_id": company_program_id},
        extra_form=form,
    )
    return summarize_merge(root, total=len(documents))


@mcp.tool
@saldeo_call
def update_documents(
    company_program_id: str,
    documents: list[DocumentUpdateInput],
) -> MergeResult | ErrorResponse:
    """Edit existing documents (SS17).

    Only set the fields you want to change — everything left as ``None`` is
    preserved on the server side.
    """
    if not documents:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one document is required.",
        )
    xml = _build_document_update_xml(documents)
    root = get_client().post_command(
        "/api/xml/2.4/document/update",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(documents))


@mcp.tool
@saldeo_call
def delete_documents(
    company_program_id: str,
    document_ids: list[int],
) -> MergeResult | ErrorResponse:
    """Delete documents by Saldeo document_id (SS16).

    ⚠ Destructive. Each ID is removed in Saldeo.
    """
    if not document_ids:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one document_id is required.",
        )
    xml = _build_document_delete_xml(document_ids)
    root = get_client().post_command(
        "/api/xml/1.13/document/delete",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(document_ids))


@mcp.tool
@saldeo_call
def recognize_documents(
    company_program_id: str,
    documents: list[RecognizeOptionInput],
) -> MergeResult | ErrorResponse:
    """Trigger OCR recognition on previously-uploaded documents (SS06).

    Saldeo returns OCR_ORIGIN_IDs you can later pass to
    ``list_recognized_documents`` once the recognition completes.
    """
    if not documents:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one document is required.",
        )
    xml = _build_recognize_xml(documents)
    root = get_client().post_command(
        "/api/xml/1.20/document/recognize",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(documents))


@mcp.tool
@saldeo_call
def sync_documents(
    company_program_id: str,
    syncs: list[DocumentSyncInput],
) -> MergeResult | ErrorResponse:
    """Push accounting numbering / status back to Saldeo (SS13).

    Used by ERP integrations to tell Saldeo "we booked this document under
    register X with number Y" so the Saldeo UI can show the right state.
    Each entry must identify the document either by ``saldeo_id`` or by the
    triple (``contractor_program_id``, ``document_number``, ``issue_date``).
    """
    if not syncs:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one sync entry is required.",
        )
    xml = _build_document_sync_xml(syncs)
    root = get_client().post_command(
        "/api/xml/1.13/document/sync",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(syncs))


@mcp.tool
@saldeo_call
def merge_document_dimensions(
    company_program_id: str,
    documents: list[DocumentDimensionInput],
) -> MergeResult | ErrorResponse:
    """Set dimension values on existing documents (SS20).

    Each entry pins one document and the dimension code/value pairs to set.
    The dimensions referenced must already exist (use ``merge_dimensions``).
    """
    if not documents:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one document is required.",
        )
    xml = _build_document_dimension_xml(documents)
    root = get_client().post_command(
        "/api/xml/1.13/document_dimension/merge",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(documents))


# ---- Builders --------------------------------------------------------------------


def _build_search_xml(
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


def _build_document_id_groups_xml(
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


def _build_ocr_id_list_xml(ocr_origin_ids: list[int]) -> str:
    """Body for document.list_recognized.

    Shape: ``<ROOT><OCR_ID_LIST><OCR_ORIGIN_ID/>...</OCR_ID_LIST></ROOT>``.
    """
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "OCR_ID_LIST")
    for ocr_id in ocr_origin_ids:
        ET.SubElement(container, "OCR_ORIGIN_ID").text = str(ocr_id)
    return ET.tostring(root, encoding="unicode")


def _build_document_update_xml(documents: list[DocumentUpdateInput]) -> str:
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


def _build_document_delete_xml(document_ids: list[int]) -> str:
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "DOCUMENT_DELETE_IDS")
    for doc_id in document_ids:
        ET.SubElement(container, "DOCUMENT_DELETE_ID").text = str(doc_id)
    return ET.tostring(root, encoding="unicode")


def _build_recognize_xml(documents: list[RecognizeOptionInput]) -> str:
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "DOCUMENTS")
    for d in documents:
        item = ET.SubElement(container, "DOCUMENT")
        set_text(item, "DOCUMENT_ID", d.document_id)
        set_text(item, "SPLIT_MODE", d.split_mode)
        set_text(item, "NO_ROTATE", d.no_rotate)
        set_text(item, "OVERWRITE_DATA", d.overwrite_data)
    return ET.tostring(root, encoding="unicode")


def _build_document_sync_xml(syncs: list[DocumentSyncInput]) -> str:
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


def _build_document_add_xml(
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


def _build_document_dimension_xml(items: list[DocumentDimensionInput]) -> str:
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
