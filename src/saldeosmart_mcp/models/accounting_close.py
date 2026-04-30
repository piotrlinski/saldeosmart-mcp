"""Accounting-firm close models — declarations and assurances.

Both endpoints (SSK02 ``declaration.merge``, SSK03 ``assurance.renew``) share
the same skeleton: a (year, month) folder, a list of items, each item with
optional metadata + an optional list of attachments. The detail blocks
differ — declarations carry tax periods, assurances carry ZUS reports
discriminated by ``TYPE``.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from ..http.attachments import Attachment
from .common import IsoDate

# ---- Shared pieces ---------------------------------------------------------------


CloseAttachmentType = Literal["DECLARATION", "REPORT"]
PeriodType = Literal["MONTH", "QUARTER", "YEAR"]


class CloseAttachmentInput(BaseModel):
    """One ``<ATTACHMENT>`` entry inside a tax / assurance ATTACHMENTS list.

    Pairs an Attachment (path → base64) with the metadata Saldeo wants in
    the XML: type, display name, optional description fields.
    """

    type: CloseAttachmentType
    name: str
    attachment: Attachment
    description: str | None = None
    short_description: str | None = None


# ---- declaration.merge (SSK02) ---------------------------------------------------


class TaxDetailsInput(BaseModel):
    """``<TAX_DETAILS>`` block inside a ``DeclarationTaxInput``."""

    type: str
    period: str
    period_type: PeriodType
    deadline: IsoDate
    tax_value: str
    correction_no: str | None = None
    description: str | None = None


class DeclarationTaxInput(BaseModel):
    """One ``<TAX>`` row inside ``DeclarationMergeInput.taxes``."""

    declaration_program_id: str
    tax_details: TaxDetailsInput | None = None
    attachments: list[CloseAttachmentInput] = Field(default_factory=list, max_length=20)


class DeclarationMergeInput(BaseModel):
    """One ``declaration.merge`` request body (SSK02).

    Folders are 1:1 with calendar months. Provide every tax declaration
    entry that should be created or updated in the folder; Saldeo answers
    per-tax with ``MERGED`` (existed) or ``CREATED`` (new).
    """

    year: int
    month: int
    taxes: list[DeclarationTaxInput] = Field(default_factory=list, max_length=50)


# ---- assurance.renew (SSK03) -----------------------------------------------------


PersonIdType = Literal["PES", "NIP", "DOW", "PAS"]


class AssuranceEmployeesDetailsInput(BaseModel):
    """``<ASSURANCE_DETAILS>`` for ``TYPE=EMPLOYEES`` — ZUS-51 to ZUS-54 totals."""

    type: Literal["EMPLOYEES"] = "EMPLOYEES"
    period: str
    deadline: IsoDate
    zus_51: str | None = None
    zus_52: str | None = None
    zus_53: str | None = None
    zus_54: str | None = None


class AssurancePersonalDetailsInput(BaseModel):
    """``<ASSURANCE_DETAILS>`` for ``TYPE=PERSONAL`` — single employee."""

    type: Literal["PERSONAL"] = "PERSONAL"
    last_name: str
    first_name: str
    person_id_type: PersonIdType
    person_id: str
    period: str
    deadline: IsoDate
    person_code: str | None = None
    zus_51: str | None = None
    zus_52: str | None = None
    zus_53: str | None = None
    zus_54: str | None = None


class AssuranceCompanyDetailsInput(BaseModel):
    """``<ASSURANCE_DETAILS>`` for ``TYPE=COMPANY`` — owner contributions."""

    type: Literal["COMPANY"] = "COMPANY"
    period: str
    deadline: IsoDate
    zus_contribution: str | None = None
    zus_excess_payment: str | None = None
    zus_description: str | None = None


class AssurancePartnerDetailsInput(BaseModel):
    """``<ASSURANCE_DETAILS>`` for ``TYPE=PARTNER`` — single partner."""

    type: Literal["PARTNER"] = "PARTNER"
    last_name: str
    first_name: str
    person_id_type: PersonIdType
    person_id: str
    period: str
    deadline: IsoDate
    person_code: str | None = None
    zus_contribution: str | None = None
    zus_underpayment: str | None = None
    zus_description: str | None = None


AssuranceDetailsInput = Annotated[
    AssuranceEmployeesDetailsInput
    | AssurancePersonalDetailsInput
    | AssuranceCompanyDetailsInput
    | AssurancePartnerDetailsInput,
    Field(discriminator="type"),
]


class AssuranceItemInput(BaseModel):
    """One ``<ASSURANCE>`` row inside ``AssuranceRenewInput.assurances``.

    Saldeo's spec uses a TYPE-discriminated union for the details block:
    EMPLOYEES (totals), PERSONAL (one employee), COMPANY (owner), or
    PARTNER (one partner). Pick the matching ``*DetailsInput`` subclass.
    """

    assurance_program_id: str
    details: AssuranceDetailsInput
    attachments: list[CloseAttachmentInput] = Field(default_factory=list, max_length=20)


class AssuranceRenewInput(BaseModel):
    """One ``assurance.renew`` request body (SSK03).

    Folders are 1:1 with calendar months. Saldeo answers per-assurance with
    ``RENEWED`` (existed) or ``CREATED`` (new).
    """

    year: int
    month: int
    assurances: list[AssuranceItemInput] = Field(default_factory=list, max_length=50)
