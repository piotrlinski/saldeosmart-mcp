"""Cross-resource models — types referenced by more than one resource family.

Read-vs-write date typing — important to know:

- **Write** inputs use :data:`IsoDate`, which validates the ``YYYY-MM-DD``
  shape at the boundary so a typo like ``"2026-13-99"`` fails fast with a
  clean Pydantic error instead of a 4xx from Saldeo.
- **Read** models keep ``str | None`` because the source is the Saldeo XML
  response itself; we trust it (it's already been through Saldeo's own
  validation) and a stricter type would mean a single bad row could blow
  up an entire list response.

The asymmetry is deliberate. Don't paper over it by stuffing ``IsoDate``
into a read model — that turns a bad cell into a parser crash.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated
from xml.etree import ElementTree as ET

from pydantic import AfterValidator, BaseModel, Field

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


_SEPARATOR_RE = re.compile(r"[\s\-]+")


def _strip_separators(value: str) -> str:
    """Remove whitespace and dashes (common in copy-pasted IDs)."""
    return _SEPARATOR_RE.sub("", value)


def _validate_nip(value: str) -> str:
    """Reject NIPs that aren't 10 digits (after stripping spaces and dashes).

    Polish NIP is always 10 digits. We strip common copy-paste decorations
    (``"123-456-78-90"``, ``"123 456 78 90"``) and require exactly 10
    digits. Checksum validation is intentionally NOT enforced — Saldeo's
    own validator runs server-side, and over-strict client checks reject
    legitimate edge cases (test environments, historical rows).
    """
    cleaned = _strip_separators(value)
    if not (len(cleaned) == 10 and cleaned.isdigit()):
        raise ValueError(f"expected 10-digit NIP, got {value!r}")
    return cleaned


def _validate_pesel(value: str) -> str:
    """Reject PESELs that aren't 11 digits (after stripping whitespace)."""
    cleaned = _strip_separators(value)
    if not (len(cleaned) == 11 and cleaned.isdigit()):
        raise ValueError(f"expected 11-digit PESEL, got {value!r}")
    return cleaned


_VAT_RE = re.compile(r"^[A-Z]{0,2}\d{8,15}$")


def _validate_vat_number(value: str) -> str:
    """Reject VAT numbers that don't look like an EU/non-EU tax ID.

    Accepts: optional 2-letter country prefix (uppercase) followed by 8–15
    digits. Strips spaces and dashes first. The wide range covers Polish
    NIPs (10 digits, no prefix or ``PL`` prefix), German USt-IdNr
    (``DE`` + 9), French TVA (``FR`` + 11), etc. Anything else is rejected
    so a typo doesn't silently end up as a contractor identifier.
    """
    cleaned = _strip_separators(value).upper()
    if not _VAT_RE.match(cleaned):
        raise ValueError(
            f"expected VAT number in format [CC]NNNNNNNNNN (8-15 digits, "
            f"optional 2-letter country prefix), got {value!r}"
        )
    return cleaned


Nip = Annotated[str, AfterValidator(_validate_nip)]
"""10-digit Polish tax ID. Strips spaces and dashes; no checksum check."""

Pesel = Annotated[str, AfterValidator(_validate_pesel)]
"""11-digit Polish national ID. Strips spaces; no checksum check."""

VatNumber = Annotated[str, AfterValidator(_validate_vat_number)]
"""EU-style VAT number: optional 2-letter country prefix + 8-15 digits."""


Year = Annotated[int, Field(ge=2000, le=2099)]
"""4-digit year for a (year, month) folder. Catches LLM off-by-millennium typos."""

Month = Annotated[int, Field(ge=1, le=12)]
"""Calendar month, 1-12."""


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
