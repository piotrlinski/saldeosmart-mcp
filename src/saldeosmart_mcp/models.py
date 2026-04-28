"""
Pydantic models for SaldeoSMART MCP responses.

Each domain model carries a `from_xml` classmethod that knows how to read its
own XML representation. Tool functions in `server.py` stay thin: hit the API,
hand the root element to a model, return a typed response.

FastMCP picks up these types and publishes a JSON Schema to Claude — the LLM
sees field names, types, and descriptions instead of opaque dicts.
"""

from __future__ import annotations

from typing import Literal
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from .client import ItemError, el_bool, el_int, el_text

DocumentPolicy = Literal["LAST_10_DAYS", "LAST_10_DAYS_OCRED", "SALDEO"]


class Company(BaseModel):
    company_id: int | None = None
    program_id: str | None = None
    name: str | None = None
    short_name: str | None = None
    vat_number: str | None = None
    regon: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None

    @classmethod
    def from_xml(cls, el: ET.Element) -> Company:
        return cls(
            company_id=el_int(el, "COMPANY_ID"),
            program_id=el_text(el, "COMPANY_PROGRAM_ID"),
            name=el_text(el, "NAME"),
            short_name=el_text(el, "SHORT_NAME"),
            vat_number=el_text(el, "VAT_NUMBER"),
            regon=el_text(el, "REGON"),
            address=el_text(el, "ADDRESS"),
            city=el_text(el, "CITY"),
            postal_code=el_text(el, "POSTAL_CODE"),
        )


class Contractor(BaseModel):
    contractor_id: int | None = None
    program_id: str | None = None
    short_name: str | None = None
    full_name: str | None = None
    vat_number: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    inactive: bool = False

    @classmethod
    def from_xml(cls, el: ET.Element) -> Contractor:
        return cls(
            contractor_id=el_int(el, "CONTRACTOR_ID"),
            program_id=el_text(el, "CONTRACTOR_PROGRAM_ID"),
            short_name=el_text(el, "SHORT_NAME"),
            full_name=el_text(el, "FULL_NAME"),
            vat_number=el_text(el, "VAT_NUMBER"),
            address=el_text(el, "ADDRESS"),
            city=el_text(el, "CITY"),
            postal_code=el_text(el, "POSTAL_CODE"),
            inactive=el_bool(el, "INACTIVE"),
        )


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
            name=el_text(el, "NAME"),
            quantity=el_text(el, "QUANTITY"),
            unit_price_net=el_text(el, "UNIT_PRICE_NET"),
            value_net=el_text(el, "VALUE_NET"),
            value_gross=el_text(el, "VALUE_GROSS"),
            vat_rate=el_text(el, "VAT_RATE"),
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
        items = (
            [DocumentItem.from_xml(i) for i in items_el.findall("DOCUMENT_ITEM")]
            if items_el is not None
            else []
        )
        return cls(
            document_id=el_int(el, "DOCUMENT_ID"),
            guid=el_text(el, "GUID"),
            number=el_text(el, "NUMBER"),
            type=el_text(el, "TYPE"),
            issue_date=el_text(el, "ISSUE_DATE"),
            sale_date=el_text(el, "SALE_DATE"),
            payment_due_date=el_text(el, "PAYMENT_DUE_DATE"),
            value_net=el_text(el, "VALUE_NET"),
            value_gross=el_text(el, "VALUE_GROSS"),
            value_vat=el_text(el, "VALUE_VAT"),
            currency=el_text(el, "CURRENCY"),
            is_paid=el_bool(el, "IS_DOCUMENT_PAID"),
            is_mpp=el_bool(el, "IS_MPP"),
            source_url=el_text(el, "SOURCE_URL"),
            preview_url=el_text(el, "PREVIEW_URL"),
            contractor=Contractor.from_xml(contractor_el) if contractor_el is not None else None,
            items=items,
        )


class CompanyList(BaseModel):
    companies: list[Company]
    count: int


class ContractorList(BaseModel):
    contractors: list[Contractor]
    count: int


class DocumentList(BaseModel):
    documents: list[Document]
    count: int


class InvoiceList(BaseModel):
    invoices: list[Document]
    count: int


class ItemErrorPayload(BaseModel):
    """Per-item error nested inside a structured SaldeoError response."""

    status: str
    path: str
    message: str
    item_id: str | None = None

    @classmethod
    def from_dataclass(cls, e: ItemError) -> ItemErrorPayload:
        return cls(status=e.status, path=e.path, message=e.message, item_id=e.item_id)


class ErrorResponse(BaseModel):
    """Uniform error shape returned to MCP clients on SaldeoSMART failures."""

    error: str
    message: str
    http_status: int | None = None
    details: list[ItemErrorPayload] = Field(default_factory=list)
