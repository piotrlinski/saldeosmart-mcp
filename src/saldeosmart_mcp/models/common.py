"""Cross-resource models — types referenced by more than one resource family."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from xml.etree import ElementTree as ET

from pydantic import AfterValidator, BaseModel

from ..http.xml import el_text


def _validate_iso_date(value: str) -> str:
    """Reject strings that are not valid ``YYYY-MM-DD`` dates.

    Saldeo expects ISO calendar dates everywhere it accepts a date string;
    sending ``"2026-13-99"`` results in an opaque server error instead of a
    clean field-level validation error. ``date.fromisoformat`` enforces both
    structure and calendar correctness in one call.
    """
    try:
        date.fromisoformat(value)
    except ValueError as e:
        raise ValueError(f"expected YYYY-MM-DD ISO date, got {value!r}") from e
    return value


IsoDate = Annotated[str, AfterValidator(_validate_iso_date)]
"""ISO ``YYYY-MM-DD`` date as a string.

Use anywhere a Saldeo field is documented as a date — the validator rejects
non-ISO strings with a clean Pydantic error pointing at the offending field.
"""


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
