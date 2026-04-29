"""Personnel tools — employees and personnel documents.

The Personnel module is a separate Saldeo entitlement; calls return
``6001 — User does not have access`` if the account doesn't have it.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..http.xml import set_text
from ..models import (
    Employee,
    EmployeeAddInput,
    EmployeeList,
    ErrorResponse,
    MergeResult,
    PersonnelDocument,
    PersonnelDocumentList,
)
from ._runtime import get_client, mcp, parse_collection, saldeo_call, summarize_merge


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


@mcp.tool
@saldeo_call
def add_employees(
    company_program_id: str,
    employees: list[EmployeeAddInput],
) -> MergeResult | ErrorResponse:
    """Create or update employees in SaldeoSMART Personnel (P03).

    Each entry either updates an existing employee (set ``employee_id``) or
    creates a new one (set ``acronym`` + ``first_name`` + ``last_name``).
    Saldeo enforces the choice rule via per-item ``NOT_VALID`` responses;
    fields not in the active branch are simply ignored.

    Requires the SaldeoSMART Personnel module on the account.
    """
    if not employees:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one employee is required.",
        )
    xml = _build_employee_add_xml(employees)
    root = get_client().post_command(
        "/api/xml/2.21/employee/add",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(employees))


def _build_employee_add_xml(employees: list[EmployeeAddInput]) -> str:
    # Element order matches employee_add_request.xsd. The choice between the
    # update branch (EMPLOYEE_ID-leading) and the create branch (ACRONYM-
    # leading) is decided by which fields the caller set; both branches still
    # share ACRONYM/FIRST_NAME/LAST_NAME positions in the same sequence.
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "EMPLOYEES")
    for e in employees:
        item = ET.SubElement(container, "EMPLOYEE")
        set_text(item, "EMPLOYEE_ID", e.employee_id)
        set_text(item, "ACRONYM", e.acronym)
        set_text(item, "FIRST_NAME", e.first_name)
        set_text(item, "LAST_NAME", e.last_name)
        set_text(item, "PARENTS_NAMES", e.parents_names)
        set_text(item, "BIRTH_DATE", e.birth_date)
        set_text(item, "PESEL", e.pesel)
        set_text(item, "NIP", e.nip)
        set_text(item, "ID_CARD_NUMBER", e.id_card_number)
        set_text(item, "BANK_ACCOUNT_NUMBER", e.bank_account_number)
        set_text(item, "EMAIL", e.email)
        set_text(item, "TELEPHONE_NUMBER", e.telephone_number)
        set_text(item, "ADDRESS", e.address)
        set_text(item, "WORK_BEGIN_DATE", e.work_begin_date)
        set_text(item, "MEDICAL_TEST_DATE", e.medical_test_date)
        set_text(item, "BHP_EXPIRY_DATE", e.bhp_expiry_date)
        set_text(item, "DEPARTMENT", e.department)
        set_text(item, "COMMENTS", e.comments)
        set_text(item, "INACTIVE", e.inactive)
        if e.contracts:
            contracts = ET.SubElement(item, "CONTRACTS")
            for c in e.contracts:
                contract = ET.SubElement(contracts, "CONTRACT")
                set_text(contract, "TYPE", c.type)
                set_text(contract, "POSITION", c.position)
                set_text(contract, "ENDATE", c.end_date)
    return ET.tostring(root, encoding="unicode")


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
