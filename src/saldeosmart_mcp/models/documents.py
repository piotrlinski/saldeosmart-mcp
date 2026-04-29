"""Document resource models — read responses, ID-list groupings, and write inputs.

The richest resource family in SaldeoSMART. Cost documents (invoices,
receipts) and their ancillary types (line items, dimensions, OCR origins)
all live here. Sales invoices are a separate file (``invoices.py``); some
3.0 endpoints reuse the ``Document`` shape via a parser hook.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Literal
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from ..http.xml import el_bool, el_int, el_text
from .contractors import Contractor

DocumentPolicy = Literal["LAST_10_DAYS", "LAST_10_DAYS_OCRED", "SALDEO"]


def _sum_vat_registries(el: ET.Element, leaf: str) -> str | None:
    """Sum a leaf (NETTO/VAT) across every <VAT_REGISTRY> under <VAT_REGISTRIES>.

    SaldeoSMART breaks invoice/document amounts down per VAT rate rather than
    exposing a single document-level total — so to recover ``value_net`` and
    ``value_vat`` we walk the registries and add them up.
    """
    container = el.find("VAT_REGISTRIES")
    if container is None:
        return None
    total = Decimal("0")
    found = False
    for reg in container.findall("VAT_REGISTRY"):
        raw = el_text(reg, leaf)
        if not raw:
            continue
        try:
            total += Decimal(raw)
        except (InvalidOperation, ValueError):
            continue
        found = True
    return format(total, "f") if found else None


class DocumentItem(BaseModel):
    name: str | None = None
    quantity: str | None = None
    unit_price_net: str | None = None
    value_net: str | None = None
    value_gross: str | None = None
    vat_rate: str | None = None
    category: str | None = None

    @classmethod
    def from_xml(cls, el: ET.Element) -> DocumentItem:
        return cls(
            name=el_text(el, "NAME") or el_text(el, "DESCRIPTION"),
            quantity=el_text(el, "AMOUNT"),
            unit_price_net=el_text(el, "UNIT_VALUE"),
            value_net=el_text(el, "NETTO"),
            value_gross=el_text(el, "GROSS"),
            vat_rate=el_text(el, "RATE"),
            category=el_text(el, "CATEGORY"),
        )


class Document(BaseModel):
    document_id: int | None = None
    guid: str | None = None
    number: str | None = None
    type: str | None = None
    issue_date: str | None = None
    sale_date: str | None = None
    payment_due_date: str | None = None
    value_net: str | None = None
    value_gross: str | None = None
    value_vat: str | None = None
    currency: str | None = None
    is_paid: bool = False
    is_mpp: bool = False
    source_url: str | None = None
    preview_url: str | None = None
    contractor: Contractor | None = None
    items: list[DocumentItem] = Field(default_factory=list)

    @classmethod
    def from_xml(cls, el: ET.Element) -> Document:
        contractor_el = el.find("CONTRACTOR")
        items_el = el.find("DOCUMENT_ITEMS")
        item_tag = "DOCUMENT_ITEM"
        if items_el is None:
            items_el = el.find("ITEMS")
            item_tag = "ITEM"
        items = (
            [DocumentItem.from_xml(i) for i in items_el.findall(item_tag)]
            if items_el is not None
            else []
        )
        return cls(
            document_id=el_int(el, "DOCUMENT_ID") or el_int(el, "INVOICE_ID"),
            guid=el_text(el, "GUID"),
            number=el_text(el, "NUMBER"),
            type=el_text(el, "TYPE"),
            issue_date=el_text(el, "ISSUE_DATE"),
            sale_date=el_text(el, "SALE_DATE"),
            payment_due_date=el_text(el, "PAYMENT_DATE") or el_text(el, "PAYMENT_DUE_DATE"),
            value_net=_sum_vat_registries(el, "NETTO"),
            value_gross=el_text(el, "SUM"),
            value_vat=_sum_vat_registries(el, "VAT"),
            currency=el_text(el, "CURRENCY_ISO4217") or el_text(el, "CURRENCY"),
            is_paid=el_bool(el, "IS_DOCUMENT_PAID"),
            is_mpp=el_bool(el, "IS_MPP"),
            source_url=el_text(el, "SOURCE_URL") or el_text(el, "SOURCE"),
            preview_url=el_text(el, "PREVIEW_URL"),
            contractor=Contractor.from_xml(contractor_el) if contractor_el is not None else None,
            items=items,
        )


class DocumentList(BaseModel):
    documents: list[Document]
    count: int


class DocumentIdGroups(BaseModel):
    """Document IDs grouped by Saldeo's logical buckets (SS22 response).

    Saldeo's 3.0 endpoint returns one container per kind so callers can decide
    which subset to fetch via ``listbyid``. Empty buckets are omitted.
    """

    contracts: list[int] = Field(default_factory=list)
    invoices_cost: list[int] = Field(default_factory=list)
    invoices_internal: list[int] = Field(default_factory=list)
    invoices_material: list[int] = Field(default_factory=list)
    invoices_sale: list[int] = Field(default_factory=list)
    orders: list[int] = Field(default_factory=list)
    writings: list[int] = Field(default_factory=list)
    other_documents: list[int] = Field(default_factory=list)

    @classmethod
    def from_xml(cls, root: ET.Element) -> DocumentIdGroups:
        def ints(container: str, leaf: str) -> list[int]:
            container_el = root.find(container)
            if container_el is None:
                return []
            out: list[int] = []
            for el in container_el.findall(leaf):
                if el.text and el.text.strip().isdigit():
                    out.append(int(el.text.strip()))
            return out

        return cls(
            contracts=ints("CONTRACTS", "CONTRACT"),
            invoices_cost=ints("INVOICES_COST", "INVOICE_COST"),
            invoices_internal=ints("INVOICES_INTERNAL", "INVOICE_INTERNAL"),
            invoices_material=ints("INVOICES_MATERIAL", "INVOICE_MATERIAL"),
            invoices_sale=ints("INVOICES_SALE", "INVOICE_SALE"),
            orders=ints("ORDERS", "ORDER"),
            writings=ints("WRITINGS", "WRITING"),
            other_documents=ints("OTHER_DOCUMENTS", "OTHER_DOCUMENT"),
        )


# ---- Write inputs ----------------------------------------------------------------


class DocumentUpdateInput(BaseModel):
    """One document edit for ``document.update`` (SS17).

    ``document_id`` is required (Saldeo's primary key). Only fields you
    actually want to change need to be set; unspecified fields are left alone.
    """

    document_id: int
    number: str | None = None
    issue_date: str | None = None
    sale_date: str | None = None
    payment_date: str | None = None
    contractor_program_id: str | None = None
    bank_account: str | None = None
    self_learning: bool | None = None


class DocumentSyncInput(BaseModel):
    """One document mapping for ``document.sync`` (SS13).

    Reports the accounting-side number/status back to Saldeo for a document.
    Either ``saldeo_id`` or (``contractor_program_id`` + ``document_number`` +
    ``issue_date``) must identify the document.

    ``saldeo_id`` is ``str`` (not ``int`` like ``document_id`` elsewhere)
    because the document.sync XSD declares ``<SALDEO_ID>`` as ``xs:string``.
    """

    saldeo_id: str | None = None
    saldeo_guid: str | None = None
    contractor_program_id: str | None = None
    document_number: str | None = None
    issue_date: str | None = None
    guid: str | None = None
    description: str | None = None
    numbering_type: str | None = None
    account_document_number: str | None = None
    document_status: Literal["BUFFER", "INTRODUCED", "BOOKED"] | None = None


class DocumentDimensionValueInput(BaseModel):
    code: str
    value: str | None = None


class DocumentDimensionInput(BaseModel):
    """One ``DOCUMENT_DIMENSION`` row for ``document_dimension.merge`` (SS20)."""

    document_id: int
    dimensions: list[DocumentDimensionValueInput] = Field(min_length=1, max_length=200)


class RecognizeOptionInput(BaseModel):
    """One document for ``document.recognize`` (SS06)."""

    document_id: int
    split_mode: Literal[
        "NO_SPLIT",
        "SPLIT_ONE_SIDED",
        "SPLIT_TWO_SIDED",
        "AUTO_ONE_SIDED",
        "AUTO_TWO_SIDED",
    ] | None = None
    no_rotate: bool | None = None
    overwrite_data: bool | None = None
