"""Pydantic models for everything that crosses the MCP boundary as JSON.

Organized by Saldeo resource family. Each submodule owns the read response
models, the input models, and any helpers exclusive to that family.
The cross-cutting error models (``ItemError`` / ``ErrorResponse`` /
``MergeResult``) live in ``saldeosmart_mcp.errors`` and are re-exported here
so the ``saldeosmart_mcp.models`` namespace is the single public face.

``__all__`` is alphabetised (enforced by ruff RUF022). To find what you
want, look up the type by category:

* **Read responses** — typed shapes returned by ``list_*`` / ``get_*``
  / ``search_*`` tools. Examples: ``Company``, ``Contractor``,
  ``Document``, ``DocumentList``, ``DocumentIdGroups``,
  ``BankStatement``, ``Employee``, ``DocumentAddRecognizeResult``.
* **Write inputs** — Pydantic inputs accepted by write tools, suffixed
  ``Input``. Examples: ``CategoryInput``, ``ContractorInput``,
  ``DocumentAddInput``, ``DocumentImportInput``,
  ``EmployeeAddInput``, ``DeclarationMergeInput``.
* **Common building blocks** (``saldeosmart_mcp.models.common``) —
  ``BankAccount``, ``BankAccountInput``, plus validated string
  aliases ``IsoDate``, ``Nip``, ``Pesel``, ``VatNumber``, ``Year``,
  ``Month``.
* **Closed enums** (Literal type aliases) — ``ContractType``,
  ``ContractorAreaType``, ``DiscountType``, ``DocumentModelType``,
  ``DocumentPolicy``, ``PeriodType``, ``PersonIdType``,
  ``PersonnelDocumentType``, ``SplitMode``, ``VehicleType``,
  ``CloseAttachmentType``.
* **Errors** (re-exported from ``saldeosmart_mcp.errors``) —
  ``ErrorResponse``, ``ItemError``, ``MergeResult``.
* **Attachment** (``saldeosmart_mcp.http.attachments``) —
  ``Attachment``, used as a field on every input that uploads a file.
"""

from __future__ import annotations

from ..errors import ErrorResponse, ItemError, MergeResult
from ..http.attachments import Attachment
from .accounting_close import (
    AssuranceCompanyDetailsInput,
    AssuranceDetailsInput,
    AssuranceEmployeesDetailsInput,
    AssuranceItemInput,
    AssurancePartnerDetailsInput,
    AssurancePersonalDetailsInput,
    AssuranceRenewInput,
    CloseAttachmentInput,
    CloseAttachmentType,
    DeclarationMergeInput,
    DeclarationTaxInput,
    PeriodType,
    PersonIdType,
    TaxDetailsInput,
)
from .bank import BankOperation, BankStatement, BankStatementList
from .catalog import (
    ArticleInput,
    CategoryInput,
    DescriptionInput,
    DimensionInput,
    DimensionValueInput,
    FeeInput,
    ForeignCodeInput,
    PaymentMethodInput,
    RegisterInput,
)
from .common import BankAccount, BankAccountInput, IsoDate, Month, Nip, Pesel, VatNumber, Year
from .companies import (
    Company,
    CompanyCreateBankAccountInput,
    CompanyCreateInput,
    CompanyList,
    CompanySynchronizeInput,
)
from .contractors import Contractor, ContractorInput, ContractorList
from .documents import (
    ContractorAreaType,
    Document,
    DocumentAddInput,
    DocumentAddRecognizeInput,
    DocumentAddRecognizeResult,
    DocumentCorrectContractorInput,
    DocumentCorrectInput,
    DocumentDimensionInput,
    DocumentDimensionValueInput,
    DocumentIdGroups,
    DocumentImportAttachmentInput,
    DocumentImportCurrencyInput,
    DocumentImportDimensionInput,
    DocumentImportInput,
    DocumentImportLineItemInput,
    DocumentImportNoVATInput,
    DocumentImportNoVATItemInput,
    DocumentImportPaymentInput,
    DocumentImportTypeInput,
    DocumentImportVATInput,
    DocumentImportVATItemInput,
    DocumentImportVATRegistryInput,
    DocumentItem,
    DocumentList,
    DocumentModelType,
    DocumentPolicy,
    DocumentSyncInput,
    DocumentUpdateInput,
    RecognizeOptionInput,
    SplitMode,
)
from .financial_balance import FinancialBalanceMergeInput, FinancialBalanceVATInput
from .invoices import (
    DiscountType,
    InvoiceAddBankAccountInput,
    InvoiceAddDiscountInput,
    InvoiceAddInput,
    InvoiceAddItemInput,
    InvoiceAddNewTransportVehicleInput,
    InvoiceAddPaymentInput,
    InvoiceAddSaleDateRangeInput,
    InvoiceIdGroups,
    InvoiceList,
    VehicleType,
)
from .personnel import (
    ContractType,
    Employee,
    EmployeeAddInput,
    EmployeeContractInput,
    EmployeeList,
    PersonnelDocument,
    PersonnelDocumentAddInput,
    PersonnelDocumentList,
    PersonnelDocumentType,
)

__all__ = [
    "ArticleInput",
    "AssuranceCompanyDetailsInput",
    "AssuranceDetailsInput",
    "AssuranceEmployeesDetailsInput",
    "AssuranceItemInput",
    "AssurancePartnerDetailsInput",
    "AssurancePersonalDetailsInput",
    "AssuranceRenewInput",
    "Attachment",
    "BankAccount",
    "BankAccountInput",
    "BankOperation",
    "BankStatement",
    "BankStatementList",
    "CategoryInput",
    "CloseAttachmentInput",
    "CloseAttachmentType",
    "Company",
    "CompanyCreateBankAccountInput",
    "CompanyCreateInput",
    "CompanyList",
    "CompanySynchronizeInput",
    "ContractType",
    "Contractor",
    "ContractorAreaType",
    "ContractorInput",
    "ContractorList",
    "DeclarationMergeInput",
    "DeclarationTaxInput",
    "DescriptionInput",
    "DimensionInput",
    "DimensionValueInput",
    "DiscountType",
    "Document",
    "DocumentAddInput",
    "DocumentAddRecognizeInput",
    "DocumentAddRecognizeResult",
    "DocumentCorrectContractorInput",
    "DocumentCorrectInput",
    "DocumentDimensionInput",
    "DocumentDimensionValueInput",
    "DocumentIdGroups",
    "DocumentImportAttachmentInput",
    "DocumentImportCurrencyInput",
    "DocumentImportDimensionInput",
    "DocumentImportInput",
    "DocumentImportLineItemInput",
    "DocumentImportNoVATInput",
    "DocumentImportNoVATItemInput",
    "DocumentImportPaymentInput",
    "DocumentImportTypeInput",
    "DocumentImportVATInput",
    "DocumentImportVATItemInput",
    "DocumentImportVATRegistryInput",
    "DocumentItem",
    "DocumentList",
    "DocumentModelType",
    "DocumentPolicy",
    "DocumentSyncInput",
    "DocumentUpdateInput",
    "Employee",
    "EmployeeAddInput",
    "EmployeeContractInput",
    "EmployeeList",
    "ErrorResponse",
    "FeeInput",
    "FinancialBalanceMergeInput",
    "FinancialBalanceVATInput",
    "ForeignCodeInput",
    "InvoiceAddBankAccountInput",
    "InvoiceAddDiscountInput",
    "InvoiceAddInput",
    "InvoiceAddItemInput",
    "InvoiceAddNewTransportVehicleInput",
    "InvoiceAddPaymentInput",
    "InvoiceAddSaleDateRangeInput",
    "InvoiceIdGroups",
    "InvoiceList",
    "IsoDate",
    "ItemError",
    "MergeResult",
    "Month",
    "Nip",
    "PaymentMethodInput",
    "PeriodType",
    "PersonIdType",
    "PersonnelDocument",
    "PersonnelDocumentAddInput",
    "PersonnelDocumentList",
    "PersonnelDocumentType",
    "Pesel",
    "RecognizeOptionInput",
    "RegisterInput",
    "SplitMode",
    "TaxDetailsInput",
    "VatNumber",
    "VehicleType",
    "Year",
]
