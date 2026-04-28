"""
Pydantic models for SaldeoSMART MCP responses.

Each domain model carries a `from_xml` classmethod that knows how to read its
own XML representation. Tool functions in `server.py` stay thin: hit the API,
hand the root element to a model, return a typed response.

FastMCP picks up these types and publishes a JSON Schema to Claude — the LLM
sees field names, types, and descriptions instead of opaque dicts.
"""

from __future__ import annotations

from typing import Literal
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from .client import ItemError, el_bool, el_int, el_text

DocumentPolicy = Literal["LAST_10_DAYS", "LAST_10_DAYS_OCRED", "SALDEO"]


class Company(BaseModel):
    company_id: int | None = None
    program_id: str | None = None
    name: str | None = None
    short_name: str | None = None
    vat_number: str | None = None
    regon: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None

    @classmethod
    def from_xml(cls, el: ET.Element) -> Company:
        return cls(
            company_id=el_int(el, "COMPANY_ID"),
            program_id=el_text(el, "COMPANY_PROGRAM_ID"),
            name=el_text(el, "NAME"),
            short_name=el_text(el, "SHORT_NAME"),
            vat_number=el_text(el, "VAT_NUMBER"),
            regon=el_text(el, "REGON"),
            address=el_text(el, "ADDRESS"),
            city=el_text(el, "CITY"),
            postal_code=el_text(el, "POSTAL_CODE"),
        )


class Contractor(BaseModel):
    contractor_id: int | None = None
    program_id: str | None = None
    short_name: str | None = None
    full_name: str | None = None
    vat_number: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    inactive: bool = False

    @classmethod
    def from_xml(cls, el: ET.Element) -> Contractor:
        return cls(
            contractor_id=el_int(el, "CONTRACTOR_ID"),
            program_id=el_text(el, "CONTRACTOR_PROGRAM_ID"),
            short_name=el_text(el, "SHORT_NAME"),
            full_name=el_text(el, "FULL_NAME"),
            vat_number=el_text(el, "VAT_NUMBER"),
            address=el_text(el, "ADDRESS"),
            city=el_text(el, "CITY"),
            postal_code=el_text(el, "POSTAL_CODE"),
            inactive=el_bool(el, "INACTIVE"),
        )


class DocumentItem(BaseModel):
    name: str | None = None
    quantity: str | None = None
    unit_price_net: str | None = None
    value_net: str | None = None
    value_gross: str | None = None
    vat_rate: str | None = None
    category: str | None = None

    @classmethod
    def from_xml(cls, el: ET.Element) -> DocumentItem:
        return cls(
            name=el_text(el, "NAME"),
            quantity=el_text(el, "QUANTITY"),
            unit_price_net=el_text(el, "UNIT_PRICE_NET"),
            value_net=el_text(el, "VALUE_NET"),
            value_gross=el_text(el, "VALUE_GROSS"),
            vat_rate=el_text(el, "VAT_RATE"),
            category=el_text(el, "CATEGORY"),
        )


class Document(BaseModel):
    document_id: int | None = None
    guid: str | None = None
    number: str | None = None
    type: str | None = None
    issue_date: str | None = None
    sale_date: str | None = None
    payment_due_date: str | None = None
    value_net: str | None = None
    value_gross: str | None = None
    value_vat: str | None = None
    currency: str | None = None
    is_paid: bool = False
    is_mpp: bool = False
    source_url: str | None = None
    preview_url: str | None = None
    contractor: Contractor | None = None
    items: list[DocumentItem] = Field(default_factory=list)

    @classmethod
    def from_xml(cls, el: ET.Element) -> Document:
        contractor_el = el.find("CONTRACTOR")
        items_el = el.find("DOCUMENT_ITEMS")
        items = (
            [DocumentItem.from_xml(i) for i in items_el.findall("DOCUMENT_ITEM")]
            if items_el is not None
            else []
        )
        return cls(
            document_id=el_int(el, "DOCUMENT_ID"),
            guid=el_text(el, "GUID"),
            number=el_text(el, "NUMBER"),
            type=el_text(el, "TYPE"),
            issue_date=el_text(el, "ISSUE_DATE"),
            sale_date=el_text(el, "SALE_DATE"),
            payment_due_date=el_text(el, "PAYMENT_DUE_DATE"),
            value_net=el_text(el, "VALUE_NET"),
            value_gross=el_text(el, "VALUE_GROSS"),
            value_vat=el_text(el, "VALUE_VAT"),
            currency=el_text(el, "CURRENCY"),
            is_paid=el_bool(el, "IS_DOCUMENT_PAID"),
            is_mpp=el_bool(el, "IS_MPP"),
            source_url=el_text(el, "SOURCE_URL"),
            preview_url=el_text(el, "PREVIEW_URL"),
            contractor=Contractor.from_xml(contractor_el) if contractor_el is not None else None,
            items=items,
        )


class CompanyList(BaseModel):
    companies: list[Company]
    count: int


class ContractorList(BaseModel):
    contractors: list[Contractor]
    count: int


class DocumentList(BaseModel):
    documents: list[Document]
    count: int


class InvoiceList(BaseModel):
    invoices: list[Document]
    count: int


class BankAccount(BaseModel):
    name: str | None = None
    number: str | None = None

    @classmethod
    def from_xml(cls, el: ET.Element) -> BankAccount:
        return cls(name=el_text(el, "NAME"), number=el_text(el, "NUMBER"))


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


class DocumentIdGroups(BaseModel):
    """Document IDs grouped by Saldeo's logical buckets (SS22 response).

    Saldeo's 3.0 endpoint returns one container per kind so callers can decide
    which subset to fetch via ``listbyid``. Empty buckets are omitted.
    """

    contracts: list[int] = Field(default_factory=list)
    invoices_cost: list[int] = Field(default_factory=list)
    invoices_internal: list[int] = Field(default_factory=list)
    invoices_material: list[int] = Field(default_factory=list)
    invoices_sale: list[int] = Field(default_factory=list)
    orders: list[int] = Field(default_factory=list)
    writings: list[int] = Field(default_factory=list)
    other_documents: list[int] = Field(default_factory=list)

    @classmethod
    def from_xml(cls, root: ET.Element) -> DocumentIdGroups:
        def ints(container: str, leaf: str) -> list[int]:
            container_el = root.find(container)
            if container_el is None:
                return []
            out: list[int] = []
            for el in container_el.findall(leaf):
                if el.text and el.text.strip().isdigit():
                    out.append(int(el.text.strip()))
            return out

        return cls(
            contracts=ints("CONTRACTS", "CONTRACT"),
            invoices_cost=ints("INVOICES_COST", "INVOICE_COST"),
            invoices_internal=ints("INVOICES_INTERNAL", "INVOICE_INTERNAL"),
            invoices_material=ints("INVOICES_MATERIAL", "INVOICE_MATERIAL"),
            invoices_sale=ints("INVOICES_SALE", "INVOICE_SALE"),
            orders=ints("ORDERS", "ORDER"),
            writings=ints("WRITINGS", "WRITING"),
            other_documents=ints("OTHER_DOCUMENTS", "OTHER_DOCUMENT"),
        )


class InvoiceIdGroups(BaseModel):
    """Invoice IDs grouped by kind (SSK07 response)."""

    invoices: list[int] = Field(default_factory=list)
    corrective_invoices: list[int] = Field(default_factory=list)
    pre_invoices: list[int] = Field(default_factory=list)
    corrective_pre_invoices: list[int] = Field(default_factory=list)

    @classmethod
    def from_xml(cls, root: ET.Element) -> InvoiceIdGroups:
        def ints(container: str, leaf: str) -> list[int]:
            container_el = root.find(container)
            if container_el is None:
                return []
            out: list[int] = []
            for el in container_el.findall(leaf):
                if el.text and el.text.strip().isdigit():
                    out.append(int(el.text.strip()))
            return out

        return cls(
            invoices=ints("INVOICES", "INVOICE_ID"),
            corrective_invoices=ints("CORRECTIVE_INVOICES", "CORRECTIVE_INVOICE_ID"),
            pre_invoices=ints("PRE_INVOICES", "PRE_INVOICE_ID"),
            corrective_pre_invoices=ints(
                "CORRECTIVE_PRE_INVOICES", "CORRECTIVE_PRE_INVOICE_ID"
            ),
        )


class ItemErrorPayload(BaseModel):
    """Per-item error nested inside a structured SaldeoError response."""

    status: str
    path: str
    message: str
    item_id: str | None = None

    @classmethod
    def from_dataclass(cls, e: ItemError) -> ItemErrorPayload:
        return cls(status=e.status, path=e.path, message=e.message, item_id=e.item_id)


class ErrorResponse(BaseModel):
    """Uniform error shape returned to MCP clients on SaldeoSMART failures."""

    error: str
    message: str
    http_status: int | None = None
    details: list[ItemErrorPayload] = Field(default_factory=list)
