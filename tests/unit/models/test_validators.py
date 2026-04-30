"""Tests for the validated string aliases in :mod:`saldeosmart_mcp.models.common`.

These guard the boundary contract:

- ``IsoDate`` rejects malformed / out-of-range calendar dates.
- ``Nip`` / ``Pesel`` reject the wrong digit count and tolerate
  copy-paste decorations (spaces, dashes).
- ``VatNumber`` accepts EU country prefix + 8-15 digits.
- ``Year`` / ``Month`` enforce the small-integer range LLM clients
  routinely get wrong (off-by-millennium years, month=0/13).
- All validators raise Pydantic ``ValidationError`` (not raw ``ValueError``)
  so callers can rely on a uniform error shape.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from saldeosmart_mcp.models.common import IsoDate, Month, Nip, Pesel, VatNumber, Year


class _IsoModel(BaseModel):
    d: IsoDate


class _NipModel(BaseModel):
    n: Nip


class _PeselModel(BaseModel):
    p: Pesel


class _VatModel(BaseModel):
    v: VatNumber


class _PeriodModel(BaseModel):
    year: Year
    month: Month


# ---- IsoDate ---------------------------------------------------------------------


def test_iso_date_accepts_canonical_form() -> None:
    assert _IsoModel(d="2026-04-30").d == "2026-04-30"


@pytest.mark.parametrize(
    "bad",
    ["", "2026-13-01", "2026-02-30", "2026/04/30", "30-04-2026", "not a date"],
)
def test_iso_date_rejects_invalid(bad: str) -> None:
    with pytest.raises(ValidationError, match="ISO date"):
        _IsoModel(d=bad)


# ---- Nip / Pesel -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1234567890", "1234567890"),
        ("123-456-78-90", "1234567890"),
        ("123 456 78 90", "1234567890"),
    ],
)
def test_nip_strips_separators(raw: str, expected: str) -> None:
    assert _NipModel(n=raw).n == expected


@pytest.mark.parametrize("bad", ["", "123", "12345678901", "abcdefghij"])
def test_nip_rejects_wrong_shape(bad: str) -> None:
    with pytest.raises(ValidationError, match="10-digit NIP"):
        _NipModel(n=bad)


def test_pesel_accepts_11_digits() -> None:
    assert _PeselModel(p="01234567890").p == "01234567890"


@pytest.mark.parametrize("bad", ["", "12345", "012345678901", "letters here!"])
def test_pesel_rejects_wrong_shape(bad: str) -> None:
    with pytest.raises(ValidationError, match="11-digit PESEL"):
        _PeselModel(p=bad)


# ---- VatNumber -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("PL1234567890", "PL1234567890"),
        ("pl 123-456-78-90", "PL1234567890"),
        ("DE123456789", "DE123456789"),
        ("1234567890", "1234567890"),  # bare 10-digit Polish NIP, no prefix
    ],
)
def test_vat_number_accepts_eu_and_bare_forms(raw: str, expected: str) -> None:
    assert _VatModel(v=raw).v == expected


@pytest.mark.parametrize("bad", ["", "AB", "PL123", "PLABCDEFGH", "1234567"])
def test_vat_number_rejects_garbage(bad: str) -> None:
    with pytest.raises(ValidationError, match="VAT number"):
        _VatModel(v=bad)


# ---- Year / Month ----------------------------------------------------------------


@pytest.mark.parametrize("year", [1999, 2100, 0, -1, 99999])
def test_year_rejects_out_of_range(year: int) -> None:
    with pytest.raises(ValidationError):
        _PeriodModel(year=year, month=1)


@pytest.mark.parametrize("month", [0, 13, -1, 100])
def test_month_rejects_out_of_range(month: int) -> None:
    with pytest.raises(ValidationError):
        _PeriodModel(year=2026, month=month)


def test_year_month_accept_boundary_values() -> None:
    a = _PeriodModel(year=2000, month=1)
    b = _PeriodModel(year=2099, month=12)
    assert (a.year, a.month) == (2000, 1)
    assert (b.year, b.month) == (2099, 12)
