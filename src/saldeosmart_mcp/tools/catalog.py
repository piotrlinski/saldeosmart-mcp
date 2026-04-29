"""Catalog tools — categories, payment methods, registers, descriptions, articles, fees.

These are the static reference data Saldeo uses to classify documents.
All six operations are write-only (``*.merge``); no read counterpart in
the API today.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..http.xml import set_text
from ..models import (
    ArticleInput,
    CategoryInput,
    DescriptionInput,
    ErrorResponse,
    FeeInput,
    MergeResult,
    PaymentMethodInput,
    RegisterInput,
)
from ._builders import build_simple_merge_xml
from ._runtime import get_client, mcp, saldeo_call, summarize_merge


@mcp.tool
@saldeo_call
def merge_categories(
    company_program_id: str,
    categories: list[CategoryInput],
) -> MergeResult | ErrorResponse:
    """Create or update document categories for a company.

    Categories classify cost documents (e.g. "Office supplies", "Fuel").
    Each item is matched on ``category_program_id`` (your ERP-side ID); set
    it to update an existing category, omit it to create a new one. Saldeo
    op: ``category.merge`` (SS09).

    Args:
        company_program_id: External program ID of the company.
        categories: One CategoryInput per category. ``name`` is required.

    Returns:
        MergeResult — total + per-item successes/errors. On envelope-level
        failure, ErrorResponse (see docs/ERROR_CODES.md).
    """
    if not categories:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one category is required.",
        )
    xml = build_simple_merge_xml(
        container_tag="CATEGORIES",
        item_tag="CATEGORY",
        items=categories,
        field_specs=[
            ("category_program_id", "CATEGORY_PROGRAM_ID"),
            ("name", "NAME"),
            ("description", "DESCRIPTION"),
        ],
    )
    root = get_client().post_command(
        "/api/xml/1.0/category/merge",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(categories))


@mcp.tool
@saldeo_call
def merge_payment_methods(
    company_program_id: str,
    payment_methods: list[PaymentMethodInput],
) -> MergeResult | ErrorResponse:
    """Create or update payment methods (e.g. "cash", "transfer", "card").

    Each item is matched on ``payment_method_program_id`` or
    ``payment_method_id`` for update; without either, a new method is
    created. Saldeo op: ``payment_method.merge`` (SS11).

    Args:
        company_program_id: External program ID of the company.
        payment_methods: One PaymentMethodInput per method. ``name`` is required.

    Returns:
        MergeResult on success, ErrorResponse on failure.
    """
    if not payment_methods:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one payment method is required.",
        )
    xml = build_simple_merge_xml(
        container_tag="PAYMENT_METHODS",
        item_tag="PAYMENT_METHOD",
        items=payment_methods,
        field_specs=[
            ("payment_method_program_id", "PAYMENT_METHOD_PROGRAM_ID"),
            ("payment_method_id", "PAYMENT_METHOD_ID"),
            ("name", "NAME"),
        ],
    )
    root = get_client().post_command(
        "/api/xml/1.0/payment_method/merge",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(payment_methods))


@mcp.tool
@saldeo_call
def merge_registers(
    company_program_id: str,
    registers: list[RegisterInput],
) -> MergeResult | ErrorResponse:
    """Create or update accounting registers (sales/purchase ledgers).

    A register groups documents that get posted together (e.g. "VAT-S" for
    sales). Match on ``register_program_id`` or ``register_id`` to update.
    Saldeo op: ``register.merge`` (SS10).

    Args:
        company_program_id: External program ID of the company.
        registers: One RegisterInput per register. ``name`` is required.

    Returns:
        MergeResult on success, ErrorResponse on failure.
    """
    if not registers:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one register is required.",
        )
    xml = build_simple_merge_xml(
        container_tag="REGISTERS",
        item_tag="REGISTER",
        items=registers,
        field_specs=[
            ("register_program_id", "REGISTER_PROGRAM_ID"),
            ("register_id", "REGISTER_ID"),
            ("name", "NAME"),
        ],
    )
    root = get_client().post_command(
        "/api/xml/1.0/register/merge",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(registers))


@mcp.tool
@saldeo_call
def merge_descriptions(
    company_program_id: str,
    descriptions: list[DescriptionInput],
) -> MergeResult | ErrorResponse:
    """Create or update reusable business-event descriptions.

    Pre-canned descriptions that bookkeepers attach to documents (e.g.
    "goods purchase", "service fee"). Saldeo op: ``description.merge`` (SS14).

    Args:
        company_program_id: External program ID of the company.
        descriptions: One DescriptionInput per row. ``value`` is required.

    Returns:
        MergeResult on success, ErrorResponse on failure.
    """
    if not descriptions:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one description is required.",
        )
    xml = build_simple_merge_xml(
        container_tag="DESCRIPTIONS",
        item_tag="DESCRIPTION",
        items=descriptions,
        field_specs=[
            ("program_id", "PROGRAM_ID"),
            ("value", "VALUE"),
        ],
    )
    root = get_client().post_command(
        "/api/xml/1.13/description/merge",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(descriptions))


@mcp.tool
@saldeo_call
def merge_articles(
    company_program_id: str,
    articles: list[ArticleInput],
) -> MergeResult | ErrorResponse:
    """Create or update the article (product/service) catalog.

    Articles are line-item products keyed by ``code``. Optional
    ``foreign_codes`` map a contractor's external code (per-supplier SKU)
    to your internal ``code``. Saldeo op: ``article.merge`` (SS21).

    Args:
        company_program_id: External program ID of the company.
        articles: One ArticleInput per article. ``name`` is required.
            Set ``for_documents`` to expose in cost-document line items;
            ``for_invoices`` to expose in sales-invoice line items.

    Returns:
        MergeResult on success, ErrorResponse on failure.
    """
    if not articles:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one article is required.",
        )
    xml = _build_article_merge_xml(articles)
    root = get_client().post_command(
        "/api/xml/1.14/article/merge",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(articles))


@mcp.tool
@saldeo_call
def merge_fees(
    company_program_id: str,
    year: int,
    month: int,
    fees: list[FeeInput],
) -> MergeResult | ErrorResponse:
    """Create or update the accounting-firm fee schedule for one month.

    Used by accounting offices to bill their clients (e.g. monthly retainer,
    extra-document fees). All fees are nested under one ``<FOLDER>`` of
    (year, month). Saldeo op: ``fee.merge`` (SSK04).

    Args:
        company_program_id: External program ID of the company being billed.
        year: 4-digit year of the billing folder (e.g. 2024).
        month: Month of the billing folder, 1–12.
        fees: One FeeInput per fee row. ``type``, ``value``, and
            ``maturity`` (ISO YYYY-MM-DD due date) are required; ``maturity``
            is validated client-side.

    Returns:
        MergeResult on success, ErrorResponse on failure.
    """
    if not fees:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one fee is required.",
        )
    xml = _build_fee_merge_xml(year=year, month=month, fees=fees)
    root = get_client().post_command(
        "/api/xml/1.13/fee/merge",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(fees))


# ---- Builders --------------------------------------------------------------------


def _build_article_merge_xml(articles: list[ArticleInput]) -> str:
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "ARTICLES")
    for a in articles:
        item = ET.SubElement(container, "ARTICLE")
        set_text(item, "ARTICLE_PROGRAM_ID", a.article_program_id)
        set_text(item, "CODE", a.code)
        set_text(item, "NAME", a.name)
        set_text(item, "UNIT", a.unit)
        set_text(item, "PKWIU", a.pkwiu)
        set_text(item, "FOR_DOCUMENTS", a.for_documents)
        set_text(item, "FOR_INVOICES", a.for_invoices)
        if a.foreign_codes:
            codes = ET.SubElement(item, "FOREIGN_CODES")
            for fc in a.foreign_codes:
                fc_el = ET.SubElement(codes, "FOREIGN_CODE")
                # Spec (.temp/api-html-mirror/1_14/article/article_merge_request.xml)
                # only defines CONTRACTOR_SHORT_NAME and CODE inside FOREIGN_CODE.
                set_text(fc_el, "CONTRACTOR_SHORT_NAME", fc.contractor_short_name)
                set_text(fc_el, "CODE", fc.code)
    return ET.tostring(root, encoding="unicode")


def _build_fee_merge_xml(*, year: int, month: int, fees: list[FeeInput]) -> str:
    root = ET.Element("ROOT")
    folder = ET.SubElement(root, "FOLDER")
    set_text(folder, "YEAR", year)
    set_text(folder, "MONTH", month)
    container = ET.SubElement(root, "FEES")
    for fee in fees:
        item = ET.SubElement(container, "FEE")
        set_text(item, "PROGRAM_ID", fee.program_id)
        set_text(item, "TYPE", fee.type)
        set_text(item, "VALUE", fee.value)
        set_text(item, "MATURITY", fee.maturity)
        set_text(item, "DESCRIPTION", fee.description)
    return ET.tostring(root, encoding="unicode")
