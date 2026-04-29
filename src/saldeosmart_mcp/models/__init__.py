"""Pydantic models for everything that crosses the MCP boundary as JSON.

Organized by Saldeo resource family. Each submodule owns the read response
models, the input models, and any helpers exclusive to that family.
The cross-cutting error models (``ItemErrorPayload`` / ``ErrorResponse`` /
``MergeResult``) live in ``saldeosmart_mcp.errors`` and are re-exported here
so the ``saldeosmart_mcp.models`` namespace is the single public face.
"""

from __future__ import annotations

from ..errors import ErrorResponse, ItemError, ItemErrorPayload, MergeResult
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
from .common import BankAccount, BankAccountInput
from .companies import Company, CompanyList, CompanySynchronizeInput
from .contractors import Contractor, ContractorInput, ContractorList
from .documents import (
    Document,
    DocumentDimensionInput,
    DocumentDimensionValueInput,
    DocumentIdGroups,
    DocumentItem,
    DocumentList,
    DocumentPolicy,
    DocumentSyncInput,
    DocumentUpdateInput,
    RecognizeOptionInput,
)
from .invoices import InvoiceIdGroups, InvoiceList
from .personnel import Employee, EmployeeList, PersonnelDocument, PersonnelDocumentList

__all__ = [
    "ArticleInput",
    "BankAccount",
    "BankAccountInput",
    "BankOperation",
    "BankStatement",
    "BankStatementList",
    "CategoryInput",
    "Company",
    "CompanyList",
    "CompanySynchronizeInput",
    "Contractor",
    "ContractorInput",
    "ContractorList",
    "DescriptionInput",
    "DimensionInput",
    "DimensionValueInput",
    "Document",
    "DocumentDimensionInput",
    "DocumentDimensionValueInput",
    "DocumentIdGroups",
    "DocumentItem",
    "DocumentList",
    "DocumentPolicy",
    "DocumentSyncInput",
    "DocumentUpdateInput",
    "Employee",
    "EmployeeList",
    "ErrorResponse",
    "FeeInput",
    "ForeignCodeInput",
    "InvoiceIdGroups",
    "InvoiceList",
    "ItemError",
    "ItemErrorPayload",
    "MergeResult",
    "PaymentMethodInput",
    "PersonnelDocument",
    "PersonnelDocumentList",
    "RecognizeOptionInput",
    "RegisterInput",
]
