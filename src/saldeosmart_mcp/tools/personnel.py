"""Personnel tools — employees and personnel documents.

The Personnel module is a separate Saldeo entitlement; calls return
``6001 — User does not have access`` if the account doesn't have it.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..models import (
    Employee,
    EmployeeList,
    ErrorResponse,
    PersonnelDocument,
    PersonnelDocumentList,
)
from ._runtime import get_client, mcp, parse_collection, saldeo_call


@mcp.tool
@saldeo_call
def list_employees(company_program_id: str) -> EmployeeList | ErrorResponse:
    """List employees registered in SaldeoSMART Personnel for a company.

    Requires the SaldeoSMART Personnel module to be active on the account.
    Returns headline fields (id, name, PESEL, NIP, email, address, hire date,
    inactive flag); contracts and full payroll detail are not surfaced here.
    """
    root = get_client().get(
        "/api/xml/2.20/employee/list",
        query={"company_program_id": company_program_id},
    )
    employees = parse_collection(root, "EMPLOYEES", "EMPLOYEE", Employee.from_xml)
    return EmployeeList(employees=employees, count=len(employees))


@mcp.tool
@saldeo_call
def list_personnel_documents(
    company_program_id: str,
    employee_id: int | None = None,
    year: int | None = None,
    month: int | None = None,
    only_remaining: bool = False,
) -> PersonnelDocumentList | ErrorResponse:
    """List personnel documents (HR files: contracts, declarations, etc.).

    Args:
        company_program_id: External program ID of the company.
        employee_id: Optional. Restrict to one employee.
        year, month: Optional folder filter (e.g. year=2024, month=3).
        only_remaining: If True, list documents not yet sent to the accounting
            program. Mutually exclusive with `employee_id`.

    Saldeo's spec requires exactly one of {ALL_PERSONNEL_DOCUMENTS,
    ALL_REMAINING_DOCUMENTS, EMPLOYEE_ID}; this wrapper picks the right one
    based on which arguments you set.
    """
    xml = _build_personnel_list_xml(
        employee_id=employee_id,
        year=year,
        month=month,
        only_remaining=only_remaining,
    )
    root = get_client().post_command(
        "/api/xml/2.20/personnel_document/list",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    docs = parse_collection(
        root, "PERSONNEL_DOCUMENTS", "PERSONNEL_DOCUMENT", PersonnelDocument.from_xml
    )
    return PersonnelDocumentList(personnel_documents=docs, count=len(docs))


def _build_personnel_list_xml(
    *,
    employee_id: int | None,
    year: int | None,
    month: int | None,
    only_remaining: bool,
) -> str:
    """Body for personnel_document.list. Spec: exactly one of
    {ALL_PERSONNEL_DOCUMENTS, ALL_REMAINING_DOCUMENTS, EMPLOYEE_ID}."""
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "PERSONNEL_DOCUMENT")
    if employee_id is not None:
        ET.SubElement(container, "EMPLOYEE_ID").text = str(employee_id)
    elif only_remaining:
        ET.SubElement(container, "ALL_REMAINING_DOCUMENTS").text = "true"
    else:
        ET.SubElement(container, "ALL_PERSONNEL_DOCUMENTS").text = "true"
    if year is not None:
        ET.SubElement(container, "YEAR").text = str(year)
    if month is not None:
        ET.SubElement(container, "MONTH").text = str(month)
    return ET.tostring(root, encoding="unicode")
