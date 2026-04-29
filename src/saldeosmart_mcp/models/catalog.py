"""Catalog inputs — categories, registers, payment methods, dimensions, articles, fees.

These are the static reference data Saldeo uses to classify documents.
None of these endpoints have a useful read counterpart in this server today,
so the file holds only ``*Input`` models for the corresponding ``*.merge``
write endpoints.
"""

from __future__ import annotations

from datetime import date as _date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CategoryInput(BaseModel):
    """One category for ``category.merge`` (SS09)."""

    name: str
    category_program_id: str | None = None
    description: str | None = None


class PaymentMethodInput(BaseModel):
    """One payment method for ``payment_method.merge`` (SS11)."""

    name: str
    payment_method_program_id: str | None = None
    payment_method_id: int | None = None


class RegisterInput(BaseModel):
    """One register for ``register.merge`` (SS10)."""

    name: str
    register_program_id: str | None = None
    register_id: int | None = None


class DescriptionInput(BaseModel):
    """One description for ``description.merge`` (SS14)."""

    value: str
    program_id: str | None = None


class DimensionValueInput(BaseModel):
    """One value option for an ENUM-type dimension."""

    code: str
    description: str | None = None


class DimensionInput(BaseModel):
    """One dimension for ``dimension.merge`` (SS12).

    ``type`` controls how the dimension is rendered: ENUM uses the ``values``
    list as a fixed enumeration; NUM/LONG_NUM/DATE accept free-form values.
    """

    code: str
    name: str
    type: Literal["ENUM", "NUM", "LONG_NUM", "DATE"]
    values: list[DimensionValueInput] = Field(default_factory=list, max_length=1000)


class ForeignCodeInput(BaseModel):
    contractor_short_name: str | None = None
    code: str


class ArticleInput(BaseModel):
    """One article for ``article.merge`` (SS21)."""

    name: str
    article_program_id: str | None = None
    code: str | None = None
    unit: str | None = None
    pkwiu: str | None = None
    for_documents: bool | None = None
    for_invoices: bool | None = None
    foreign_codes: list[ForeignCodeInput] = Field(default_factory=list, max_length=200)


class FeeInput(BaseModel):
    """One fee row for ``fee.merge`` (SSK04). Always nested under a folder."""

    type: str
    value: str
    maturity: str  # ISO date YYYY-MM-DD
    program_id: str | None = None
    description: str | None = None

    @field_validator("maturity")
    @classmethod
    def _validate_iso_date(cls, v: str) -> str:
        try:
            _date.fromisoformat(v)
        except ValueError as e:
            raise ValueError(
                f"maturity must be ISO date YYYY-MM-DD, got {v!r}"
            ) from e
        return v
