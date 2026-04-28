"""
SaldeoSMART MCP server — read-only access to documents, invoices, contractors.

Exposes Claude-friendly tools that wrap the XML/MD5/gzip ugliness of the
SaldeoSMART API behind clean Python signatures returning Pydantic models.

Configuration via environment variables (loaded by :class:`SaldeoConfig`):
    SALDEO_USERNAME   — your SaldeoSMART login
    SALDEO_API_TOKEN  — API token from Settings → API
    SALDEO_BASE_URL   — optional, defaults to https://saldeo.brainshare.pl
                        (use https://saldeo-test.brainshare.pl for sandbox)
    SALDEO_TIMEOUT    — optional request timeout in seconds (default 30)

Run locally:
    python -m saldeosmart_mcp.server

Connect from Claude Desktop — see README.md for claude_desktop_config.json snippet.
"""

from __future__ import annotations

import functools
import logging
import os
from collections.abc import Callable
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, TypeVar
from xml.etree import ElementTree as ET

from fastmcp import FastMCP
from pydantic import ValidationError

from .client import SaldeoClient, SaldeoConfig, SaldeoError
from .models import (
    BankStatement,
    BankStatementList,
    Company,
    CompanyList,
    Contractor,
    ContractorList,
    Document,
    DocumentIdGroups,
    DocumentList,
    DocumentPolicy,
    Employee,
    EmployeeList,
    ErrorResponse,
    InvoiceIdGroups,
    InvoiceList,
    ItemErrorPayload,
    PersonnelDocument,
    PersonnelDocumentList,
)

logger = logging.getLogger(__name__)

mcp = FastMCP("SaldeoSMART")

_T = TypeVar("_T")


# ---- Client lifecycle -----------------------------------------------------------

_SHARED_CLIENT: SaldeoClient | None = None


def _client() -> SaldeoClient:
    """Return the process-wide SaldeoClient, initialising it on first use.

    A single client lets httpx pool connections across tool calls and matches
    the spec's "no concurrent requests" rule.
    """
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None:
        try:
            # BaseSettings loads username/api_token from SALDEO_* env vars.
            config = SaldeoConfig()  # type: ignore[call-arg]
        except ValidationError as e:
            missing = ", ".join(f"SALDEO_{str(err['loc'][0]).upper()}" for err in e.errors())
            raise RuntimeError(
                f"Missing SaldeoSMART credentials ({missing}). The token is generated "
                f"in SaldeoSMART under Settings → API."
            ) from e
        _SHARED_CLIENT = SaldeoClient(config)
    return _SHARED_CLIENT


def _reset_client_for_tests() -> None:
    """Drop the cached client. Tests use this to swap configs between runs."""
    global _SHARED_CLIENT
    if _SHARED_CLIENT is not None:
        _SHARED_CLIENT.close()
        _SHARED_CLIENT = None


# ---- Tool plumbing --------------------------------------------------------------


def _saldeo_call(fn: Callable[..., _T]) -> Callable[..., _T | ErrorResponse]:
    """Decorator: turn a SaldeoError raised inside a tool into ErrorResponse.

    Tool bodies stay focused on the happy path; the error envelope is uniform.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            return fn(*args, **kwargs)
        except SaldeoError as e:
            return _error_response(e)

    return wrapper


def _parse_collection(
    root: ET.Element,
    container_tag: str,
    item_tag: str,
    parser: Callable[[ET.Element], _T],
) -> list[_T]:
    """Find <container_tag>/<item_tag>* and parse each child with `parser`."""
    container = root.find(container_tag)
    if container is None:
        return []
    return [parser(el) for el in container.findall(item_tag)]


def _error_response(e: SaldeoError) -> ErrorResponse:
    return ErrorResponse(
        error=e.code,
        message=e.message,
        http_status=e.http_status,
        details=[ItemErrorPayload.from_dataclass(d) for d in e.details],
    )


# Backwards-compat shim: legacy tests import `_error_payload` and expect a plain dict.
def _error_payload(e: SaldeoError) -> dict[str, Any]:
    """Render SaldeoError as a JSON-friendly dict for the MCP boundary."""
    payload: dict[str, Any] = {"error": e.code, "message": e.message}
    if e.http_status is not None:
        payload["http_status"] = e.http_status
    if e.details:
        payload["details"] = [
            {"status": d.status, "path": d.path, "message": d.message, "item_id": d.item_id}
            for d in e.details
        ]
    return payload


# ---- Tools ---------------------------------------------------------------------


@mcp.tool
@_saldeo_call
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
    root = _client().get("/api/xml/1.0/company/list", query=query)
    companies = _parse_collection(root, "COMPANIES", "COMPANY", Company.from_xml)
    return CompanyList(companies=companies, count=len(companies))


@mcp.tool
@_saldeo_call
def list_contractors(company_program_id: str) -> ContractorList | ErrorResponse:
    """List contractors (suppliers and customers) for a specific company.

    Args:
        company_program_id: External program ID of the company. Required.
            Get one from list_companies first if you don't know it.
    """
    root = _client().get(
        "/api/xml/1.23/contractor/list",
        query={"company_program_id": company_program_id},
    )
    contractors = _parse_collection(root, "CONTRACTORS", "CONTRACTOR", Contractor.from_xml)
    return ContractorList(contractors=contractors, count=len(contractors))


@mcp.tool
@_saldeo_call
def list_documents(
    company_program_id: str,
    policy: DocumentPolicy = "LAST_10_DAYS",
) -> DocumentList | ErrorResponse:
    """List documents (invoices, receipts) for a company.

    Args:
        company_program_id: External program ID of the company.
        policy: Which documents to return:
            - LAST_10_DAYS — all documents added in the last 10 days (default)
            - LAST_10_DAYS_OCRED — only OCR-processed docs from last 10 days
            - SALDEO — only documents marked for export from SaldeoSMART UI
    """
    # Use API version 2.12 — most recent stable with rich document fields.
    root = _client().get(
        "/api/xml/2.12/document/list",
        query={"company_program_id": company_program_id, "policy": policy},
    )
    documents = _parse_collection(root, "DOCUMENTS", "DOCUMENT", Document.from_xml)
    return DocumentList(documents=documents, count=len(documents))


@mcp.tool
@_saldeo_call
def search_documents(
    company_program_id: str,
    document_id: int | None = None,
    number: str | None = None,
    nip: str | None = None,
    guid: str | None = None,
) -> DocumentList | ErrorResponse:
    """Search for specific documents by ID, document number, contractor NIP, or GUID.

    Pass at least one of document_id / number / nip / guid. Combining number+nip
    narrows down a single invoice from a known supplier.
    """
    if not any((document_id, number, nip, guid)):
        return ErrorResponse(
            error="MISSING_CRITERIA",
            message="Provide at least one of document_id, number, nip, or guid.",
        )

    xml = _build_search_xml(document_id=document_id, number=number, nip=nip, guid=guid)
    root = _client().post_command(
        "/api/xml/1.8/document/search",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    documents = _parse_collection(root, "DOCUMENTS", "DOCUMENT", Document.from_xml)
    return DocumentList(documents=documents, count=len(documents))


@mcp.tool
@_saldeo_call
def list_invoices(company_program_id: str) -> InvoiceList | ErrorResponse:
    """List sales invoices issued in SaldeoSMART (only those marked for export).

    This is for invoices CREATED in SaldeoSMART (the invoicing module),
    not OCR-processed cost documents — for those use list_documents.
    """
    root = _client().get(
        "/api/xml/1.20/invoice/list",
        query={"company_program_id": company_program_id, "policy": "SALDEO"},
    )
    # Invoice XML structure overlaps with Document; reuse the parser until
    # invoice-specific fields (KSeF status etc.) are needed.
    invoices = _parse_collection(root, "INVOICES", "INVOICE", Document.from_xml)
    return InvoiceList(invoices=invoices, count=len(invoices))


@mcp.tool
@_saldeo_call
def list_bank_statements(company_program_id: str) -> BankStatementList | ErrorResponse:
    """List bank statements (with operations, dimensions, settlements).

    Args:
        company_program_id: External program ID of the company.

    Returns:
        BankStatementList with one entry per statement and a flat list of
        bank operations under each statement (account number, amount, type,
        debit/credit, currency, etc.). Saldeo returns rich nested data
        (matched contractors, dimensions, settled invoices) — only the
        headline fields are surfaced; raw XML access is via the lower-level
        client if you need everything.
    """
    root = _client().get(
        "/api/xml/2.18/bank_statement/list",
        query={"company_program_id": company_program_id},
    )
    statements = _parse_collection(
        root, "BANK_STATEMENTS", "BANK_STATEMENT", BankStatement.from_xml
    )
    return BankStatementList(statements=statements, count=len(statements))


@mcp.tool
@_saldeo_call
def list_employees(company_program_id: str) -> EmployeeList | ErrorResponse:
    """List employees registered in SaldeoSMART Personnel for a company.

    Requires the SaldeoSMART Personnel module to be active on the account.
    Returns headline fields (id, name, PESEL, NIP, email, address, hire date,
    inactive flag); contracts and full payroll detail are not surfaced here.
    """
    root = _client().get(
        "/api/xml/2.20/employee/list",
        query={"company_program_id": company_program_id},
    )
    employees = _parse_collection(root, "EMPLOYEES", "EMPLOYEE", Employee.from_xml)
    return EmployeeList(employees=employees, count=len(employees))


@mcp.tool
@_saldeo_call
def list_personnel_documents(
    company_program_id: str,
    employee_id: int | None = None,
    year: int | None = None,
    month: int | None = None,
    only_remaining: bool = False,
) -> PersonnelDocumentList | ErrorResponse:
    """List personnel documents (HR files: contracts, declarations, etc.).

    Args:
        company_program_id: External program ID of the company.
        employee_id: Optional. Restrict to one employee.
        year, month: Optional folder filter (e.g. year=2024, month=3).
        only_remaining: If True, list documents not yet sent to the accounting
            program. Mutually exclusive with `employee_id`.

    Saldeo's spec requires exactly one of {ALL_PERSONNEL_DOCUMENTS,
    ALL_REMAINING_DOCUMENTS, EMPLOYEE_ID}; this wrapper picks the right one
    based on which arguments you set.
    """
    xml = _build_personnel_list_xml(
        employee_id=employee_id,
        year=year,
        month=month,
        only_remaining=only_remaining,
    )
    root = _client().post_command(
        "/api/xml/2.20/personnel_document/list",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    docs = _parse_collection(
        root, "PERSONNEL_DOCUMENTS", "PERSONNEL_DOCUMENT", PersonnelDocument.from_xml
    )
    return PersonnelDocumentList(personnel_documents=docs, count=len(docs))


@mcp.tool
@_saldeo_call
def get_document_id_list(
    company_program_id: str,
    year: int,
    month: int,
) -> DocumentIdGroups | ErrorResponse:
    """List document IDs in one folder, grouped by kind (SS22).

    A 3.0 endpoint. Use this first to discover IDs, then `get_documents_by_id`
    to fetch full document details. Saldeo splits results into eight buckets
    (contracts, cost invoices, sale invoices, internal/material invoices,
    orders, writings, other). Empty buckets come back empty.
    """
    xml = _build_folder_xml(year, month)
    root = _client().post_command(
        "/api/xml/3.0/document/getidlist",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return DocumentIdGroups.from_xml(root)


@mcp.tool
@_saldeo_call
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
    """Fetch documents by ID, grouped by kind (SS23).

    Pass IDs in the buckets returned by `get_document_id_list`. Empty buckets
    can be omitted. Returns a flat ``DocumentList`` of whatever the server
    sent back (Saldeo returns the full document records, not just the IDs).
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
    root = _client().post_command(
        "/api/xml/3.0/document/listbyid",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    documents = _parse_collection(root, "DOCUMENTS", "DOCUMENT", Document.from_xml)
    return DocumentList(documents=documents, count=len(documents))


@mcp.tool
@_saldeo_call
def get_invoice_id_list(
    company_program_id: str,
    year: int,
    month: int,
) -> InvoiceIdGroups | ErrorResponse:
    """List invoice IDs in one folder, grouped by kind (SSK07).

    Buckets: invoices, corrective_invoices, pre_invoices, corrective_pre_invoices.
    Pair with `get_invoices_by_id` to fetch the records.
    """
    xml = _build_folder_xml(year, month)
    root = _client().post_command(
        "/api/xml/3.0/invoice/getidlist",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return InvoiceIdGroups.from_xml(root)


@mcp.tool
@_saldeo_call
def get_invoices_by_id(
    company_program_id: str,
    invoices: list[int] | None = None,
    corrective_invoices: list[int] | None = None,
    pre_invoices: list[int] | None = None,
    corrective_pre_invoices: list[int] | None = None,
) -> InvoiceList | ErrorResponse:
    """Fetch invoices by ID, grouped by kind (SSK08)."""
    xml = _build_invoice_id_groups_xml(
        invoices=invoices,
        corrective_invoices=corrective_invoices,
        pre_invoices=pre_invoices,
        corrective_pre_invoices=corrective_pre_invoices,
    )
    root = _client().post_command(
        "/api/xml/3.0/invoice/listbyid",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    invoices_out = _parse_collection(root, "INVOICES", "INVOICE", Document.from_xml)
    return InvoiceList(invoices=invoices_out, count=len(invoices_out))


@mcp.tool
@_saldeo_call
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
    the response Claude-friendly; reach for the lower-level client if needed.
    """
    if not ocr_origin_ids:
        return ErrorResponse(
            error="MISSING_CRITERIA",
            message="Provide at least one OCR origin ID. Get them from document.recognize.",
        )
    xml = _build_ocr_id_list_xml(ocr_origin_ids)
    root = _client().post_command(
        "/api/xml/2.18/document/list_recognized",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    documents = _parse_collection(root, "DOCUMENTS", "DOCUMENT", Document.from_xml)
    return DocumentList(documents=documents, count=len(documents))


# ---- Search XML builder ---------------------------------------------------------


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


def _build_folder_xml(year: int, month: int) -> str:
    """Body for the 3.0 *.getidlist operations: <ROOT><FOLDER><YEAR/><MONTH/></FOLDER></ROOT>."""
    root = ET.Element("ROOT")
    folder = ET.SubElement(root, "FOLDER")
    ET.SubElement(folder, "YEAR").text = str(year)
    ET.SubElement(folder, "MONTH").text = str(month)
    return ET.tostring(root, encoding="unicode")


def _append_id_group(root: ET.Element, container_tag: str, item_tag: str,
                     ids: list[int] | None) -> None:
    """Append <CONTAINER><ITEM>id</ITEM>...</CONTAINER> if `ids` is non-empty."""
    if not ids:
        return
    container = ET.SubElement(root, container_tag)
    for value in ids:
        ET.SubElement(container, item_tag).text = str(value)


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
    _append_id_group(root, "CONTRACTS", "CONTRACT", contracts)
    _append_id_group(root, "INVOICES_COST", "INVOICE_COST", invoices_cost)
    _append_id_group(root, "INVOICES_INTERNAL", "INVOICE_INTERNAL", invoices_internal)
    _append_id_group(root, "INVOICES_MATERIAL", "INVOICE_MATERIAL", invoices_material)
    _append_id_group(root, "INVOICES_SALE", "INVOICE_SALE", invoices_sale)
    _append_id_group(root, "ORDERS", "ORDER", orders)
    _append_id_group(root, "WRITINGS", "WRITING", writings)
    _append_id_group(root, "OTHER_DOCUMENTS", "OTHER_DOCUMENT", other_documents)
    return ET.tostring(root, encoding="unicode")


def _build_invoice_id_groups_xml(
    *,
    invoices: list[int] | None,
    corrective_invoices: list[int] | None,
    pre_invoices: list[int] | None,
    corrective_pre_invoices: list[int] | None,
) -> str:
    root = ET.Element("ROOT")
    _append_id_group(root, "INVOICES", "INVOICE_ID", invoices)
    _append_id_group(root, "CORRECTIVE_INVOICES", "CORRECTIVE_INVOICE_ID", corrective_invoices)
    _append_id_group(root, "PRE_INVOICES", "PRE_INVOICE_ID", pre_invoices)
    _append_id_group(
        root, "CORRECTIVE_PRE_INVOICES", "CORRECTIVE_PRE_INVOICE_ID", corrective_pre_invoices
    )
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


def _build_personnel_list_xml(
    *,
    employee_id: int | None,
    year: int | None,
    month: int | None,
    only_remaining: bool,
) -> str:
    """Body for personnel_document.list. Spec: exactly one of
    {ALL_PERSONNEL_DOCUMENTS, ALL_REMAINING_DOCUMENTS, EMPLOYEE_ID}."""
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "PERSONNEL_DOCUMENT")
    if employee_id is not None:
        ET.SubElement(container, "EMPLOYEE_ID").text = str(employee_id)
    elif only_remaining:
        ET.SubElement(container, "ALL_REMAINING_DOCUMENTS").text = "true"
    else:
        ET.SubElement(container, "ALL_PERSONNEL_DOCUMENTS").text = "true"
    if year is not None:
        ET.SubElement(container, "YEAR").text = str(year)
    if month is not None:
        ET.SubElement(container, "MONTH").text = str(month)
    return ET.tostring(root, encoding="unicode")


# ---- Logging & entrypoint -------------------------------------------------------


def _setup_logging() -> Path:
    """Route every log record from this package to a file under
    ``~/.saldeosmart/logs/`` with daily rotation and one-week retention.

    Critical for MCP: stdio is the transport, so writing to stdout would corrupt
    the protocol. We attach only a file handler (no stream handler).

    Configurable via env vars:
        SALDEO_LOG_DIR             — override the directory (default ~/.saldeosmart/logs)
        SALDEO_LOG_LEVEL           — root log level (default INFO)
        SALDEO_LOG_RETENTION_DAYS  — how many daily-rotated files to keep (default 7)
    """
    log_dir = Path(os.environ.get("SALDEO_LOG_DIR") or Path.home() / ".saldeosmart" / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "saldeosmart.log"

    try:
        retention_days = int(os.environ.get("SALDEO_LOG_RETENTION_DAYS", "7"))
    except ValueError:
        retention_days = 7
    retention_days = max(retention_days, 1)

    handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=retention_days,
        encoding="utf-8",
        utc=False,
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(os.environ.get("SALDEO_LOG_LEVEL", "INFO"))

    # Idempotent: don't stack handlers if main() runs twice (tests, reloads).
    for existing in root.handlers:
        if isinstance(existing, TimedRotatingFileHandler) and getattr(
            existing, "baseFilename", ""
        ) == str(log_file):
            return log_file
    root.addHandler(handler)
    return log_file


def main() -> None:
    log_file = _setup_logging()
    logger.info("SaldeoSMART MCP server starting; logs at %s", log_file)
    try:
        mcp.run()  # stdio transport — what Claude Desktop expects
    finally:
        _reset_client_for_tests()


if __name__ == "__main__":
    main()
