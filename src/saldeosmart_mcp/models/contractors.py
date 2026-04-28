"""Contractor resource models — read response and merge input."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from ..http.xml import el_bool, el_int, el_text
from .common import BankAccountInput


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
        # SaldeoSMART emits <STREET>/<POSTCODE> (not <ADDRESS>/<POSTAL_CODE>),
        # and embedded contractors inside <DOCUMENT>/<INVOICE> use <NIP> rather
        # than <VAT_NUMBER>. Fallbacks accept either spelling.
        return cls(
            contractor_id=el_int(el, "CONTRACTOR_ID"),
            program_id=el_text(el, "CONTRACTOR_PROGRAM_ID"),
            short_name=el_text(el, "SHORT_NAME"),
            full_name=el_text(el, "FULL_NAME"),
            vat_number=el_text(el, "VAT_NUMBER") or el_text(el, "NIP"),
            address=el_text(el, "STREET") or el_text(el, "ADDRESS"),
            city=el_text(el, "CITY"),
            postal_code=el_text(el, "POSTCODE") or el_text(el, "POSTAL_CODE"),
            inactive=el_bool(el, "INACTIVE"),
        )


class ContractorList(BaseModel):
    contractors: list[Contractor]
    count: int


class ContractorInput(BaseModel):
    """One contractor for ``contractor.merge``. Spec: SS02."""

    short_name: str
    full_name: str
    contractor_program_id: str | None = None
    contractor_id: int | None = None
    supplier: bool | None = None
    customer: bool | None = None
    vat_number: str | None = None
    city: str | None = None
    postcode: str | None = None
    street: str | None = None
    country_iso3166a2: str | None = None
    telephone: str | None = None
    contact_person: str | None = None
    description: str | None = None
    payment_days: int | None = None
    bank_accounts: list[BankAccountInput] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
