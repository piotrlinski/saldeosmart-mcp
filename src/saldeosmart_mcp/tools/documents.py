"""Document tools — read, search, and write the cost-document family.

Covers nine MCP tools. The 3.0 paginated endpoints (``getidlist`` /
``listbyid``) return their own typed shapes (:class:`DocumentIdGroups`);
the 2.x endpoints return :class:`DocumentList`. The XML request-body
builders live in ``tools._documents_builders`` so this module stays
focused on the ``@mcp.tool`` registrations.
"""

from __future__ import annotations

from ..errors import ERROR_MISSING_CRITERIA, ERROR_TOO_MANY_DOCUMENTS
from ..http.attachments import Attachment, prepare_attachments
from ..models import (
    Document,
    DocumentAddInput,
    DocumentAddRecognizeInput,
    DocumentAddRecognizeResult,
    DocumentCorrectInput,
    DocumentDimensionInput,
    DocumentIdGroups,
    DocumentImportInput,
    DocumentList,
    DocumentPolicy,
    DocumentSyncInput,
    DocumentUpdateInput,
    ErrorResponse,
    MergeResult,
    Month,
    RecognizeOptionInput,
    Year,
)
from . import endpoints
from ._builders import build_folder_xml
from ._documents_builders import (
    build_document_add_recognize_xml,
    build_document_add_xml,
    build_document_correct_xml,
    build_document_delete_xml,
    build_document_dimension_xml,
    build_document_id_groups_xml,
    build_document_import_xml,
    build_document_sync_xml,
    build_document_update_xml,
    build_ocr_id_list_xml,
    build_recognize_xml,
    build_search_xml,
)
from ._runtime import (
    get_client,
    mcp,
    merge_call,
    parse_collection,
    require_nonempty,
    saldeo_call,
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
        endpoints.DOCUMENT_LIST,
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
            error=ERROR_MISSING_CRITERIA,
            message="Provide at least one of document_id, number, nip, or guid.",
        )

    xml = build_search_xml(document_id=document_id, number=number, nip=nip, guid=guid)
    root = get_client().post_command(
        endpoints.DOCUMENT_SEARCH,
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    documents = parse_collection(root, "DOCUMENTS", "DOCUMENT", Document.from_xml)
    return DocumentList(documents=documents, count=len(documents))


@mcp.tool
@saldeo_call
def get_document_id_list(
    company_program_id: str,
    year: Year,
    month: Month,
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
        endpoints.DOCUMENT_GET_ID_LIST,
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
    xml = build_document_id_groups_xml(
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
        endpoints.DOCUMENT_LIST_BY_ID,
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
            error=ERROR_MISSING_CRITERIA,
            message="Provide at least one OCR origin ID. Get them from document.recognize.",
        )
    xml = build_ocr_id_list_xml(ocr_origin_ids)
    root = get_client().post_command(
        endpoints.DOCUMENT_LIST_RECOGNIZED,
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    documents = parse_collection(root, "DOCUMENTS", "DOCUMENT", Document.from_xml)
    return DocumentList(documents=documents, count=len(documents))


# ---- Writes ----------------------------------------------------------------------


@mcp.tool
@saldeo_call
@require_nonempty("documents", message="At least one document is required.")
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
    prepared, form = prepare_attachments([d.attachment for d in documents])
    xml = build_document_add_xml(documents, prepared)
    return merge_call(
        endpoints.DOCUMENT_ADD,
        xml,
        total=len(documents),
        query={"company_program_id": company_program_id},
        extra_form=form,
    )


@mcp.tool
@saldeo_call
def add_recognize_document(
    company_program_id: str,
    document: DocumentAddRecognizeInput,
) -> DocumentAddRecognizeResult | ErrorResponse:
    """Upload a single document and trigger OCR in one round-trip (AE01).

    Saldeo accepts one binary attachment per request. Returns an
    ``ocr_origin_id`` you can later pass to ``list_recognized_documents``
    once recognition completes. Costs OCR credits from the wallet —
    ``status=INSUFFICIENT_FUND`` if the account is out.
    """
    _, form = prepare_attachments([document.attachment])
    xml = build_document_add_recognize_xml(document)
    root = get_client().post_command(
        endpoints.DOCUMENT_ADD_RECOGNIZE,
        xml_command=xml,
        query={"company_program_id": company_program_id},
        extra_form=form,
    )
    return DocumentAddRecognizeResult.from_xml(root)


@mcp.tool
@saldeo_call
@require_nonempty("documents", message="At least one document correction is required.")
def correct_documents(
    company_program_id: str,
    documents: list[DocumentCorrectInput],
) -> MergeResult | ErrorResponse:
    """Overwrite OCR-extracted fields on already-uploaded documents (AE02).

    Each entry pins a document by ``document_id`` and supplies the corrected
    field values. ``self_learning=True`` tells Saldeo's recognizer to remember
    the correction for next time the same vendor's document arrives.
    """
    xml = build_document_correct_xml(documents)
    return merge_call(
        endpoints.DOCUMENT_CORRECT,
        xml,
        total=len(documents),
        query={"company_program_id": company_program_id},
    )


@mcp.tool
@saldeo_call
@require_nonempty("documents", message="At least one document is required.")
def import_documents(
    company_program_id: str,
    documents: list[DocumentImportInput],
) -> MergeResult | ErrorResponse:
    """Bulk-import structured documents with full archival metadata (3.0).

    The richest write endpoint Saldeo exposes — accepts up to 50 documents
    per request, each with the source file, header metadata, optional
    currency override, dimensions, line items, payments, and up to 5
    supporting attachments. Use ``document.add`` instead for a simple
    upload-only flow without the structured fields.

    Per-document attachments (the source file + each supporting
    ``DocumentImportAttachmentInput``) are uploaded as ``attmnt_N`` form
    fields; the XML references each by index.
    """
    if len(documents) > 50:
        return ErrorResponse(
            error=ERROR_TOO_MANY_DOCUMENTS,
            message=(
                f"document.import accepts at most 50 documents per request, got {len(documents)}."
            ),
        )
    all_attachments: list[Attachment] = []
    for doc in documents:
        all_attachments.append(doc.attachment)
        all_attachments.extend(a.attachment for a in doc.attachments)
    prepared, form = prepare_attachments(all_attachments)
    xml = build_document_import_xml(documents, prepared)
    return merge_call(
        endpoints.DOCUMENT_IMPORT,
        xml,
        total=len(documents),
        query={"company_program_id": company_program_id},
        extra_form=form,
    )


@mcp.tool
@saldeo_call
@require_nonempty("documents", message="At least one document is required.")
def update_documents(
    company_program_id: str,
    documents: list[DocumentUpdateInput],
) -> MergeResult | ErrorResponse:
    """Edit existing documents (SS17).

    Only set the fields you want to change — everything left as ``None`` is
    preserved on the server side.
    """
    xml = build_document_update_xml(documents)
    return merge_call(
        endpoints.DOCUMENT_UPDATE,
        xml,
        total=len(documents),
        query={"company_program_id": company_program_id},
    )


@mcp.tool
@saldeo_call
@require_nonempty("document_ids", message="At least one document_id is required.")
def delete_documents(
    company_program_id: str,
    document_ids: list[int],
) -> MergeResult | ErrorResponse:
    """Delete documents by Saldeo document_id (SS16).

    ⚠ Destructive. Each ID is removed in Saldeo.
    """
    xml = build_document_delete_xml(document_ids)
    return merge_call(
        endpoints.DOCUMENT_DELETE,
        xml,
        total=len(document_ids),
        query={"company_program_id": company_program_id},
    )


@mcp.tool
@saldeo_call
@require_nonempty("documents", message="At least one document is required.")
def recognize_documents(
    company_program_id: str,
    documents: list[RecognizeOptionInput],
) -> MergeResult | ErrorResponse:
    """Trigger OCR recognition on previously-uploaded documents (SS06).

    Saldeo returns OCR_ORIGIN_IDs you can later pass to
    ``list_recognized_documents`` once the recognition completes.
    """
    xml = build_recognize_xml(documents)
    return merge_call(
        endpoints.DOCUMENT_RECOGNIZE,
        xml,
        total=len(documents),
        query={"company_program_id": company_program_id},
    )


@mcp.tool
@saldeo_call
@require_nonempty("syncs", message="At least one sync entry is required.")
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
    xml = build_document_sync_xml(syncs)
    return merge_call(
        endpoints.DOCUMENT_SYNC,
        xml,
        total=len(syncs),
        query={"company_program_id": company_program_id},
    )


@mcp.tool
@saldeo_call
@require_nonempty("documents", message="At least one document is required.")
def merge_document_dimensions(
    company_program_id: str,
    documents: list[DocumentDimensionInput],
) -> MergeResult | ErrorResponse:
    """Set dimension values on existing documents (SS20).

    Each entry pins one document and the dimension code/value pairs to set.
    The dimensions referenced must already exist (use ``merge_dimensions``).
    """
    xml = build_document_dimension_xml(documents)
    return merge_call(
        endpoints.DOCUMENT_DIMENSION_MERGE,
        xml,
        total=len(documents),
        query={"company_program_id": company_program_id},
    )
