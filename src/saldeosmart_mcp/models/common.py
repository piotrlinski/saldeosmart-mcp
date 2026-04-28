"""Cross-resource models — types referenced by more than one resource family."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from pydantic import BaseModel

from ..http.xml import el_text


class BankAccount(BaseModel):
    """A bank account as it appears nested inside contractor / company XML."""

    name: str | None = None
    number: str | None = None

    @classmethod
    def from_xml(cls, el: ET.Element) -> BankAccount:
        return cls(name=el_text(el, "NAME"), number=el_text(el, "NUMBER"))


class BankAccountInput(BaseModel):
    """Bank account payload accepted by ``contractor.merge``.

    ``number`` is required; ``name`` is the account's friendly label.
    """

    name: str | None = None
    number: str
