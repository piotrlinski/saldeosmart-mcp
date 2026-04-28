"""Company resource models. Used by ``list_companies``."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from pydantic import BaseModel

from ..http.xml import el_int, el_text


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


class CompanyList(BaseModel):
    companies: list[Company]
    count: int
