"""Invoice resource models — sales invoices issued in SaldeoSMART.

The wire shape overlaps with cost ``Document`` enough that the parser is
reused; only the container/leaf names differ.
"""

from __future__ import annotations

from typing import Literal
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from .documents import Document

DiscountType = Literal["PERCENTAGE", "AMOUNT"]
VehicleType = Literal["LAND", "WATER", "AIR"]


class InvoiceList(BaseModel):
    invoices: list[Document]
    count: int


class InvoiceIdGroups(BaseModel):
    """Invoice IDs grouped by kind (SSK07 response)."""

    invoices: list[int] = Field(default_factory=list)
    corrective_invoices: list[int] = Field(default_factory=list)
    pre_invoices: list[int] = Field(default_factory=list)
    corrective_pre_invoices: list[int] = Field(default_factory=list)

    @classmethod
    def from_xml(cls, root: ET.Element) -> InvoiceIdGroups:
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
            invoices=ints("INVOICES", "INVOICE_ID"),
            corrective_invoices=ints("CORRECTIVE_INVOICES", "CORRECTIVE_INVOICE_ID"),
            pre_invoices=ints("PRE_INVOICES", "PRE_INVOICE_ID"),
            corrective_pre_invoices=ints(
                "CORRECTIVE_PRE_INVOICES", "CORRECTIVE_PRE_INVOICE_ID"
            ),
        )


# ---- invoice.add (3.1) -----------------------------------------------------------


class InvoiceAddSaleDateRangeInput(BaseModel):
    """Optional ``<SALE_DATE_FROM>`` + ``<SALE_DATE_TO>`` block for service
    invoices that span a period rather than a single day."""

    from_date: str
    to_date: str


class InvoiceAddBankAccountInput(BaseModel):
    """``<BANK_ACCOUNT>`` block for invoice.add — different from contractor
    bank accounts (only NUMBER is required, BANK / BIC_SWIFT optional)."""

    number: str
    bank: str | None = None
    bic_swift: str | None = None


class InvoiceAddDiscountInput(BaseModel):
    """``<DISCOUNT>`` block on an InvoiceAddItemInput."""

    type: DiscountType
    value: str


class InvoiceAddItemInput(BaseModel):
    """One ``<INVOICE_ITEM>`` row.

    Saldeo accepts up to 10000 items per invoice. ``rate`` strings track the
    XSD's ``VATRateType`` (e.g. ``"23"``, ``"5"``, ``"0"``, ``"ZW"``,
    ``"NP"``); ``procedure_code`` and ``gtu_code`` are optional GTU /
    procedure markings used by Polish tax law.
    """

    name: str
    amount: str
    unit: str
    unit_value: str
    pkwiu: str | None = None
    discount: InvoiceAddDiscountInput | None = None
    rate: str | None = None
    procedure_code: str | None = None
    gtu_code: str | None = None


class InvoiceAddPaymentInput(BaseModel):
    """``<INVOICE_PAYMENTS>`` block — single payment record per the XSD."""

    payment_amount: str
    payment_date: str  # ISO YYYY-MM-DD


class InvoiceAddNewTransportVehicleInput(BaseModel):
    """``<NEW_TRANSPORT_VEHICLE>`` block — only required when the invoice
    documents the intra-EU sale of a new transport vehicle."""

    vehicle_type: VehicleType
    admission_date: str  # ISO YYYY-MM-DD
    usage_metrics: int


class InvoiceAddInput(BaseModel):
    """One ``<INVOICE>`` body for ``invoice.add`` (3.1, SSK06).

    Required fields per the XSD: ``issue_date``, ``according_to_agreement``,
    ``purchaser_contractor_id``, ``currency_iso4217``, ``payment_type``,
    plus at least one ``items`` entry.

    ``sale_date`` and ``sale_date_range`` are mutually exclusive (xs:choice
    in the spec); set whichever applies and leave the other ``None``.
    Likewise the recipient block (``recipient_contractor_id`` +
    ``recipient_role``) is opt-in and required-as-a-pair when present.
    """

    issue_date: str
    according_to_agreement: bool
    purchaser_contractor_id: int
    currency_iso4217: str
    payment_type: str
    items: list[InvoiceAddItemInput] = Field(min_length=1, max_length=10000)
    number: str | None = None
    suffix: str | None = None
    sale_date: str | None = None
    sale_date_range: InvoiceAddSaleDateRangeInput | None = None
    due_date: str | None = None
    no_vat: bool | None = None
    cash_basis: bool | None = None
    profit_margin_type: str | None = None
    exempt_vat_basis: str | None = None
    calculated_from_gross: bool | None = None
    is_mpp: bool | None = None
    send_to_contractor: bool | None = None
    recipient_contractor_id: int | None = None
    recipient_role: str | None = None
    recipient_internal_id: str | None = None
    bank_account: InvoiceAddBankAccountInput | None = None
    currency_date: str | None = None
    issue_person: str | None = None
    issue_to_ksef: bool | None = None
    footer: str | None = None
    payments: list[InvoiceAddPaymentInput] = Field(default_factory=list)
    new_transport_vehicle: InvoiceAddNewTransportVehicleInput | None = None
