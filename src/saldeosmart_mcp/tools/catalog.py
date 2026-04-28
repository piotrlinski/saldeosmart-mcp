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
    """Add or update document categories (SS09)."""
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
    """Add or update payment methods (SS11)."""
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
    """Add or update registers (SS10)."""
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
    """Add or update business event descriptions (SS14)."""
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
    """Add or update article catalog (SS21)."""
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
    """Add or update accounting-firm fees for a given month (SSK04).

    ``maturity`` per fee is the due date (YYYY-MM-DD).
    """
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
                set_text(fc_el, "CONTRACTOR_SHORT_NAME", fc.contractor_short_name)
                set_text(fc_el, "CONTRACTOR_PROGRAM_ID", fc.contractor_program_id)
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
