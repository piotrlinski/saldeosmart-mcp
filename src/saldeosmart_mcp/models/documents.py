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

from ..http.attachments import Attachment
from ..http.xml import el_bool, el_int, el_text, parse_int_list
from .common import IsoDate
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
        return cls(
            contracts=parse_int_list(root, "CONTRACTS", "CONTRACT"),
            invoices_cost=parse_int_list(root, "INVOICES_COST", "INVOICE_COST"),
            invoices_internal=parse_int_list(root, "INVOICES_INTERNAL", "INVOICE_INTERNAL"),
            invoices_material=parse_int_list(root, "INVOICES_MATERIAL", "INVOICE_MATERIAL"),
            invoices_sale=parse_int_list(root, "INVOICES_SALE", "INVOICE_SALE"),
            orders=parse_int_list(root, "ORDERS", "ORDER"),
            writings=parse_int_list(root, "WRITINGS", "WRITING"),
            other_documents=parse_int_list(root, "OTHER_DOCUMENTS", "OTHER_DOCUMENT"),
        )


# ---- Write inputs ----------------------------------------------------------------


class DocumentAddInput(BaseModel):
    """One ``<DOCUMENT>`` row for ``document.add`` (SS05).

    Pairs a (year, month) folder with a single binary attachment. The
    attachment is read from disk at tool invocation time; the resolved
    display name is sent as ``<ATTMNT_NAME>``.
    """

    year: int
    month: int
    attachment: Attachment


SplitMode = Literal[
    "NO_SPLIT",
    "SPLIT_ONE_SIDED",
    "SPLIT_TWO_SIDED",
    "AUTO_ONE_SIDED",
    "AUTO_TWO_SIDED",
]


class DocumentAddRecognizeInput(BaseModel):
    """Single document upload + OCR trigger for ``document.add_recognize`` (AE01).

    Saldeo accepts one attachment per request; the file is delivered as the
    ``attmnt_1`` form field and the XML carries only the OCR options.
    """

    attachment: Attachment
    vat_number: str
    split_mode: SplitMode = "NO_SPLIT"
    document_type: Literal["COST", "SALE"] | None = None
    no_rotate: bool | None = None


class DocumentAddRecognizeResult(BaseModel):
    """Result of ``document.add_recognize``.

    ``status`` is one of ``SENT`` (success), ``NOT_VALID``, ``INSUFFICIENT_FUND``,
    ``ERROR``. ``ocr_origin_id`` is the handle for ``list_recognized_documents``
    once Saldeo finishes the OCR pass.

    Monetary values (``cost``, ``remaining_credits``) are returned as the raw
    Saldeo string. Every other monetary field in the package follows the same
    convention — preserve the wire value verbatim and let callers parse to
    ``Decimal`` when they need arithmetic.
    """

    status: str
    status_message: str | None = None
    ocr_origin_id: int | None = None
    cost: str | None = None
    sent_document_count: int | None = None
    sent_page_count: int | None = None
    split_mode: str | None = None
    no_rotate: bool | None = None
    remaining_credits: str | None = None

    @classmethod
    def from_xml(cls, root: ET.Element) -> DocumentAddRecognizeResult:
        doc = root.find("DOCUMENT")
        wallet = root.find("WALLET")
        return cls(
            status=(el_text(doc, "STATUS") if doc is not None else None) or "UNKNOWN",
            status_message=el_text(doc, "STATUS_MESSAGE") if doc is not None else None,
            ocr_origin_id=el_int(doc, "OCR_ORIGIN_ID") if doc is not None else None,
            cost=el_text(doc, "COST") if doc is not None else None,
            sent_document_count=el_int(doc, "SENT_DOCUMENT_COUNT") if doc is not None else None,
            sent_page_count=el_int(doc, "SENT_PAGE_COUNT") if doc is not None else None,
            split_mode=el_text(doc, "SPLIT_MODE") if doc is not None else None,
            no_rotate=el_bool(doc, "NO_ROTATE") if doc is not None else None,
            remaining_credits=el_text(wallet, "REMAINING_CREDITS") if wallet is not None else None,
        )


class DocumentCorrectContractorInput(BaseModel):
    """``<CONTRACTOR>`` block inside a ``DocumentCorrectInput``. All fields
    required by the spec when the block is present."""

    short_name: str
    full_name: str
    vat_number: str
    street: str
    city: str
    postcode: str


class DocumentCorrectInput(BaseModel):
    """One ``<DOCUMENT>`` row for ``document.correct`` (AE02).

    Used to overwrite extracted fields on an OCR'd document — Saldeo's
    ``self_learning`` flag tells the recognizer to remember the correction
    and apply it the next time the same vendor's document arrives.
    """

    document_id: int
    number: str | None = None
    issue_date: IsoDate | None = None
    sale_date: IsoDate | None = None
    payment_date: IsoDate | None = None
    contractor: DocumentCorrectContractorInput | None = None
    bank_account: str | None = None
    self_learning: bool | None = None


# ---- document.import (3.0) -------------------------------------------------------


DocumentModelType = Literal[
    "CONTRACT",
    "INVOICE_COST",
    "INVOICE_INTERNAL",
    "INVOICE_MATERIAL",
    "INVOICE_SALES",
    "ORDER",
    "WRITING",
]


ContractorAreaType = Literal[
    "COUNTRY",
    "EU",
    "EU_3",
    "EU_IMPORT_SERVICES",
    "EU_TAX_PURCHASER",
    "NON_COUNTRY",
    "NON_COUNTRY_NP",
    "NON_EU",
    "NON_EU_TAX_PURCHASER",
    "NON_EU_TRAVEL",
    "NON_EU_VAT_RETURN",
    "NO_VAT",
    "OUTSIDE_EU_IMPORT_SERVICES",
    "PROCEDURE_OSS",
    "REVERSE_CHARGE",
    "REVERSE_CHARGE_SERVICES",
    "TAXPRO_IMPORT_GOODS_ART33A",
    "TAXPRO_IMPORT_SERVICES_ART28B",
    "TAXPRO_IMPORT_SERVICES_NO_ART28B",
    "TAXPRO_NOT_APPLICABLE",
    "TAXPRO_REVERSE_CHARGE_ART27_PAR1_P5",
    "TAXPRO_REVERSE_CHARGE_ART27_PAR1_P7_P8",
]


class DocumentImportTypeInput(BaseModel):
    """``<DOCUMENT_TYPE>`` choice for document.import — by name+model or by ID."""

    short_name: str | None = None
    model_type: DocumentModelType | None = None
    id: int | None = None


class DocumentImportCurrencyInput(BaseModel):
    """``<CURRENCY>`` block on a ``DocumentImportInput``."""

    iso4217: str
    date: IsoDate
    rate: str | None = None


class DocumentImportDimensionInput(BaseModel):
    """``<DIMENSION>`` row inside a DIMENSIONS list (header or per-item)."""

    name: str
    value: str


class DocumentImportVATRegistryInput(BaseModel):
    """One ``<VAT_REGISTRY>`` summary inside ``DocumentImportVATInput``."""

    rate: str
    netto: str
    vat: str


class DocumentImportVATItemInput(BaseModel):
    """One ``<ITEM>`` inside a VAT_DOCUMENT.ITEMS block."""

    rate: str
    netto: str
    vat: str
    category: str | None = None
    description: str | None = None
    dimensions: list[DocumentImportDimensionInput] = Field(default_factory=list)


class DocumentImportVATInput(BaseModel):
    """``<VAT_DOCUMENT>`` block for VAT-bearing imports."""

    vat_registries: list[DocumentImportVATRegistryInput] = Field(default_factory=list)
    items: list[DocumentImportVATItemInput] = Field(default_factory=list)


class DocumentImportNoVATItemInput(BaseModel):
    """One ``<ITEM>`` inside a NO_VAT_DOCUMENT.ITEMS block."""

    value: str
    category: str | None = None
    description: str | None = None
    dimensions: list[DocumentImportDimensionInput] = Field(default_factory=list)


class DocumentImportNoVATInput(BaseModel):
    """``<NO_VAT_DOCUMENT>`` block for non-VAT imports."""

    total_value: str | None = None
    items: list[DocumentImportNoVATItemInput] = Field(default_factory=list)


class DocumentImportLineItemInput(BaseModel):
    """One ``<DOCUMENT_ITEM>`` inside DOCUMENT_ITEMS — product line."""

    code: str | None = None
    name: str | None = None
    amount: str | None = None
    unit: str | None = None
    rate: str | None = None
    unit_value: str | None = None
    netto: str | None = None
    vat: str | None = None
    gross: str | None = None
    category: str | None = None
    dimension: DocumentImportDimensionInput | None = None


class DocumentImportPaymentInput(BaseModel):
    """One ``<PAYMENT>`` inside PAYMENTS — partial-payment record."""

    date: IsoDate
    amount: str


class DocumentImportAttachmentInput(BaseModel):
    """One ``<ATTACHMENT>`` inside a DocumentImportInput.attachments list.

    Distinct from :class:`CloseAttachmentInput` — document.import attachments
    only carry an optional description; no TYPE / NAME / SHORT_DESCRIPTION.
    """

    attachment: Attachment
    description: str | None = None


class DocumentImportInput(BaseModel):
    """One ``<DOCUMENT>`` row for ``document.import`` (3.0).

    Saldeo accepts up to 50 documents per request. The required fields are
    ``year``, ``month``, ``document_type``, plus the ``attachment``
    (delivered as the matching ``attmnt_N`` form field). Up to 5 supporting
    attachments per document via ``attachments``.

    The ``vat_document`` / ``no_vat_document`` pair is mutually exclusive
    per the XSD's ``<xs:choice>``; provide whichever matches the document
    flavor (VAT-bearing invoices vs accounts / no-VAT documents).
    """

    year: int
    month: int
    document_type: DocumentImportTypeInput
    attachment: Attachment
    archival_number: str | None = None
    receive_date: IsoDate | None = None
    category: str | None = None
    description: str | None = None
    registry: str | None = None
    number: str | None = None
    issue_date: IsoDate | None = None
    sale_date: IsoDate | None = None
    payment_date: IsoDate | None = None
    payment_type: str | None = None
    is_corrective: bool | None = None
    corr_inv_num: str | None = None
    corr_inv_date: IsoDate | None = None
    is_cash_basis: bool | None = None
    is_mpp: bool | None = None
    contractor_id: int | None = None
    contractor_area: ContractorAreaType | None = None
    payer_contractor_id: int | None = None
    country_code_vat_number: str | None = None
    bank_account: str | None = None
    currency: DocumentImportCurrencyInput | None = None
    dimensions: list[DocumentImportDimensionInput] = Field(default_factory=list)
    vat_document: DocumentImportVATInput | None = None
    no_vat_document: DocumentImportNoVATInput | None = None
    document_items: list[DocumentImportLineItemInput] = Field(default_factory=list)
    payments: list[DocumentImportPaymentInput] = Field(default_factory=list)
    attachments: list[DocumentImportAttachmentInput] = Field(
        default_factory=list, max_length=5
    )


class DocumentUpdateInput(BaseModel):
    """One document edit for ``document.update`` (SS17).

    ``document_id`` is required (Saldeo's primary key). Only fields you
    actually want to change need to be set; unspecified fields are left alone.
    """

    document_id: int
    number: str | None = None
    issue_date: IsoDate | None = None
    sale_date: IsoDate | None = None
    payment_date: IsoDate | None = None
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
    issue_date: IsoDate | None = None
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
    split_mode: SplitMode | None = None
    no_rotate: bool | None = None
    overwrite_data: bool | None = None
