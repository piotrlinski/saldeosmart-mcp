"""Financial balance model — accounting-firm monthly aggregates."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .accounting_close import CloseAttachmentInput
from .common import Month, Year


class FinancialBalanceVATInput(BaseModel):
    """``<VAT>`` block inside a FinancialBalanceMergeInput."""

    value: str
    value_to_shift: str | None = None


class FinancialBalanceMergeInput(BaseModel):
    """One ``financial_balance.merge`` request body (SSK01).

    A single (year, month) folder receives at most one balance record,
    optionally with income / cost / VAT amounts. ``attachments`` carries
    the optional ``<ATTACHMENTS>`` branch from the spec — useful for
    attaching the source spreadsheet or scanned report.
    """

    year: Year
    month: Month
    income_month: str | None = None
    cost_month: str | None = None
    vat: FinancialBalanceVATInput | None = None
    attachments: list[CloseAttachmentInput] = Field(default_factory=list, max_length=20)
