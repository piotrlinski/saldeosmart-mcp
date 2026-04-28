"""Personnel resource models — employees and personnel documents."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from pydantic import BaseModel

from ..http.xml import el_bool, el_int, el_text


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
