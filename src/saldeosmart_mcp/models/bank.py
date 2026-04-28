"""Bank statement resource models.

Saldeo's bank-statement responses include rich nested data — matched
contractors, dimensions, settled invoices. These models surface the
headline fields; reach for the lower-level client for raw XML when needed.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from ..http.xml import el_bool, el_int, el_text


class BankOperation(BaseModel):
    """One transaction inside a bank statement.

    Kept deliberately shallow — Saldeo nests dimensions, settlements, and
    matched contractors in here. Surface the headline fields; callers who need
    the raw XML can hit the client directly.
    """

    account_number: str | None = None
    operation_type: str | None = None
    operation_date: str | None = None
    accounting_date: str | None = None
    description: str | None = None
    value: str | None = None
    debit_credit: str | None = None
    currency: str | None = None
    is_approved: bool = False
    is_refund: bool = False

    @classmethod
    def from_xml(cls, el: ET.Element) -> BankOperation:
        return cls(
            account_number=el_text(el, "BANK_OPERATION_ACCOUNT_NUMBER"),
            operation_type=el_text(el, "BANK_OPERATION_TYPE"),
            operation_date=el_text(el, "OPERATION_DATE"),
            accounting_date=el_text(el, "ACCOUNTING_DATE"),
            description=el_text(el, "OPERATION_DESCRIPTION"),
            value=el_text(el, "VALUE"),
            debit_credit=el_text(el, "DEBIT_CREDIT"),
            currency=el_text(el, "CURRENCY_ISO4217"),
            is_approved=el_bool(el, "IS_APPROVED"),
            is_refund=el_bool(el, "IS_REFUND"),
        )


class BankStatement(BaseModel):
    folder_year: int | None = None
    folder_month: int | None = None
    account_number: str | None = None
    currency: str | None = None
    period_from: str | None = None
    period_to: str | None = None
    status: str | None = None
    status_date: str | None = None
    filename: str | None = None
    source_url: str | None = None
    operations: list[BankOperation] = Field(default_factory=list)

    @classmethod
    def from_xml(cls, el: ET.Element) -> BankStatement:
        folder = el.find("FOLDER")
        ops_el = el.find("BANK_OPERATIONS")
        operations = (
            [BankOperation.from_xml(o) for o in ops_el.findall("BANK_OPERATION")]
            if ops_el is not None
            else []
        )
        return cls(
            folder_year=el_int(folder, "YEAR") if folder is not None else None,
            folder_month=el_int(folder, "MONTH") if folder is not None else None,
            account_number=el_text(el, "BANK_STATEMENT_ACCOUNT_NUMBER"),
            currency=el_text(el, "CURRENCY_ISO4217"),
            period_from=el_text(el, "BANK_STATEMENT_PERIOD_FROM"),
            period_to=el_text(el, "BANK_STATEMENT_PERIOD_TO"),
            status=el_text(el, "STATUS"),
            status_date=el_text(el, "STATUS_DATE"),
            filename=el_text(el, "BANK_STATEMENT_FILENAME"),
            source_url=el_text(el, "SOURCE"),
            operations=operations,
        )


class BankStatementList(BaseModel):
    statements: list[BankStatement]
    count: int
