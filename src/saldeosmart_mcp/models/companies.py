"""Company resource models. Used by ``list_companies`` / ``synchronize_companies``."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from ..http.xml import el_int, el_text
from .common import VatNumber


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
        # SaldeoSMART's company.list returns <FULL_NAME>/<SHORT_NAME>,
        # <STREET>, and <POSTCODE> — not the <NAME>/<ADDRESS>/<POSTAL_CODE>
        # this parser used to read. Fallbacks accept either spelling so the
        # model still works if Saldeo ever ships the alternates.
        return cls(
            company_id=el_int(el, "COMPANY_ID"),
            program_id=el_text(el, "COMPANY_PROGRAM_ID"),
            name=el_text(el, "FULL_NAME") or el_text(el, "NAME"),
            short_name=el_text(el, "SHORT_NAME"),
            vat_number=el_text(el, "VAT_NUMBER"),
            regon=el_text(el, "REGON"),
            address=el_text(el, "STREET") or el_text(el, "ADDRESS"),
            city=el_text(el, "CITY"),
            postal_code=el_text(el, "POSTCODE") or el_text(el, "POSTAL_CODE"),
        )


class CompanyList(BaseModel):
    companies: list[Company]
    count: int


class CompanySynchronizeInput(BaseModel):
    """One ``COMPANY`` row for ``company.synchronize`` (SS15).

    Both fields are required by the spec: ``company_id`` is Saldeo's
    internal numeric ID; ``company_program_id`` is your ERP-side identifier
    (must be unique within the accounting firm).
    """

    company_id: int
    company_program_id: str


class CompanyCreateBankAccountInput(BaseModel):
    """One ``<BANK_ACCOUNT>`` row inside a ``CompanyCreateInput``.

    The first account in the list is treated as the primary. ``name`` is
    optional; everything else is required by the spec.
    """

    number: str
    bank_name: str
    bic_number: str
    currency_iso4217: str
    name: str | None = None


class CompanyCreateInput(BaseModel):
    """One ``<COMPANY>`` body for ``company.create`` (SS01).

    Saldeo creates a new client company plus its admin user in one shot.
    Required: ``company_program_id``, ``username``, ``email``, ``short_name``
    (max 8 chars), ``full_name``, ``vat_number``, ``city``, ``postcode``,
    ``street``, plus at least one bank account.

    Bank accounts are unusual: the spec says the section is ``O`` (optional)
    at the wrapper level but warns "if missing Saldeo synthesizes a
    placeholder". Pass real accounts whenever possible; an empty list omits
    the wrapper entirely.
    """

    company_program_id: str
    username: str
    email: str
    short_name: str
    full_name: str
    vat_number: VatNumber
    city: str
    postcode: str
    street: str
    first_name: str | None = None
    last_name: str | None = None
    telephone: str | None = None
    contact_person: str | None = None
    bank_accounts: list[CompanyCreateBankAccountInput] = Field(default_factory=list)
    zus_bank_account: str | None = None
    send_email: bool | None = None
    producer: str | None = None  # METAINF/PRODUCER override
