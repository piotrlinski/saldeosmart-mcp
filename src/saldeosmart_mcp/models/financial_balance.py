"""Financial balance model — accounting-firm monthly aggregates."""

from __future__ import annotations

from pydantic import BaseModel


class FinancialBalanceVATInput(BaseModel):
    """``<VAT>`` block inside a FinancialBalanceMergeInput."""

    value: str
    value_to_shift: str | None = None


class FinancialBalanceMergeInput(BaseModel):
    """One ``financial_balance.merge`` request body (SSK01).

    A single (year, month) folder receives at most one balance record,
    optionally with income / cost / VAT amounts. ``ATTACHMENTS`` is part
    of the spec but not yet wrapped — that's a follow-up once the generic
    attachment helper lands.
    """

    year: int
    month: int
    income_month: str | None = None
    cost_month: str | None = None
    vat: FinancialBalanceVATInput | None = None
