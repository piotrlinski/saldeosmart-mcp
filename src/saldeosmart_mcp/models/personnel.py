"""Personnel resource models — employees and personnel documents."""

from __future__ import annotations

from typing import Literal
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from ..http.attachments import Attachment
from ..http.xml import el_bool, el_int, el_text

ContractType = Literal[
    "KONTRAKT_MENADZERSKI",
    "UMOWA_AGENCYJNA",
    "UMOWA_O_DZIELO",
    "UMOWA_O_PRACE_TYMCZASOWA",
    "UMOWA_O_PRACE",
    "UMOWA_ZLECENIE",
]

PersonnelDocumentType = Literal[
    "REMAINING",
    "OTHER",
    "PART_A",
    "PART_B",
    "PART_C",
    "PART_D",
    "PART_E",
]


class Employee(BaseModel):
    employee_id: int | None = None
    acronym: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    pesel: str | None = None
    nip: str | None = None
    email: str | None = None
    telephone: str | None = None
    address: str | None = None
    department: str | None = None
    work_begin_date: str | None = None
    inactive: bool = False

    @classmethod
    def from_xml(cls, el: ET.Element) -> Employee:
        return cls(
            employee_id=el_int(el, "EMPLOYEE_ID"),
            acronym=el_text(el, "ACRONYM"),
            first_name=el_text(el, "FIRST_NAME"),
            last_name=el_text(el, "LAST_NAME"),
            pesel=el_text(el, "PESEL"),
            nip=el_text(el, "NIP"),
            email=el_text(el, "EMAIL"),
            telephone=el_text(el, "TELEPHONE_NUMBER"),
            address=el_text(el, "ADDRESS"),
            department=el_text(el, "DEPARTMENT"),
            work_begin_date=el_text(el, "WORK_BEGIN_DATE"),
            inactive=el_bool(el, "INACTIVE"),
        )


class EmployeeList(BaseModel):
    employees: list[Employee]
    count: int


class PersonnelDocument(BaseModel):
    personnel_document_id: int | None = None
    employee_id: int | None = None
    year: int | None = None
    month: int | None = None
    number: str | None = None
    document_name: str | None = None
    document_type: str | None = None
    description: str | None = None
    date_of_duty: str | None = None
    notification_date: str | None = None
    filename: str | None = None
    source_url: str | None = None

    @classmethod
    def from_xml(cls, el: ET.Element) -> PersonnelDocument:
        return cls(
            personnel_document_id=el_int(el, "PERSONNEL_DOCUMENT_ID"),
            employee_id=el_int(el, "EMPLOYEE_ID"),
            year=el_int(el, "YEAR"),
            month=el_int(el, "MONTH"),
            number=el_text(el, "NUMBER"),
            document_name=el_text(el, "DOCUMENT_NAME"),
            document_type=el_text(el, "DOCUMENT_TYPE"),
            description=el_text(el, "DESCRIPTION"),
            date_of_duty=el_text(el, "DATE_OF_DUTY"),
            notification_date=el_text(el, "NOTIFICATION_DATE"),
            filename=el_text(el, "DOCUMENT_FILENAME"),
            source_url=el_text(el, "SOURCE"),
        )


class PersonnelDocumentList(BaseModel):
    personnel_documents: list[PersonnelDocument]
    count: int


class EmployeeContractInput(BaseModel):
    """One ``<CONTRACT>`` row inside an ``EmployeeAddInput``."""

    type: ContractType
    position: str | None = None
    end_date: str | None = None  # ISO YYYY-MM-DD


class EmployeeAddInput(BaseModel):
    """One ``<EMPLOYEE>`` row for ``employee.add`` (P03).

    The XSD enforces a choice rule: either ``employee_id`` is set (update an
    existing employee, all other fields optional) or all of
    ``acronym`` + ``first_name`` + ``last_name`` are set (create a new one).
    Mixing them — providing ``employee_id`` plus a partial set of
    name fields — works for updates: ``acronym`` / ``first_name`` /
    ``last_name`` are optional in the update branch. Saldeo enforces the
    rest server-side.
    """

    employee_id: int | None = None
    acronym: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    parents_names: str | None = None
    birth_date: str | None = None  # ISO YYYY-MM-DD
    pesel: str | None = None
    nip: str | None = None
    id_card_number: str | None = None
    bank_account_number: str | None = None
    email: str | None = None
    telephone_number: str | None = None
    address: str | None = None
    work_begin_date: str | None = None
    medical_test_date: str | None = None
    bhp_expiry_date: str | None = None
    department: str | None = None
    comments: str | None = None
    inactive: bool | None = None
    contracts: list[EmployeeContractInput] = Field(default_factory=list, max_length=6)


class PersonnelDocumentAddInput(BaseModel):
    """One ``<PERSONNEL_DOCUMENT>`` row for ``personnel_document.add`` (P04).

    Required: ``year``, ``month``, ``document_type``, ``attachment``.
    Saldeo accepts up to 50 personnel documents per request.
    """

    year: int
    month: int
    document_type: PersonnelDocumentType
    attachment: Attachment
    employee_id: int | None = None
    number: int | None = None
    document_name: str | None = None
    description: str | None = None
    date_of_duty: str | None = None  # ISO YYYY-MM-DD
    mark_when_date_of_duty_expired: bool | None = None
    notification_date: str | None = None  # ISO YYYY-MM-DD
