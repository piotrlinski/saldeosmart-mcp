"""SaldeoSMART MCP server.

Public API: every name listed in ``__all__`` is importable from the
top-level package. Internally the code lives in submodules organized by
concern:

  - :mod:`saldeosmart_mcp.config`  — connection settings (Pydantic Settings)
  - :mod:`saldeosmart_mcp.errors`  — exceptions + structured error payloads
  - :mod:`saldeosmart_mcp.http`    — request signing, httpx client, XML helpers
  - :mod:`saldeosmart_mcp.models`  — Pydantic models grouped by Saldeo resource
  - :mod:`saldeosmart_mcp.tools`   — the @mcp.tool registry, one file per resource
  - :mod:`saldeosmart_mcp.logging` — file-based log setup
  - :mod:`saldeosmart_mcp.server`  — main() entrypoint (console-script target)

Importing this package does **not** register MCP tools — that happens lazily
the first time ``saldeosmart_mcp.tools`` is imported (via ``server.main()``).
"""

from .config import SaldeoConfig
from .errors import ErrorResponse, ItemError, MergeResult, SaldeoError
from .http import SaldeoClient
from .models import (
    ArticleInput,
    BankAccount,
    BankAccountInput,
    BankOperation,
    BankStatement,
    BankStatementList,
    CategoryInput,
    Company,
    CompanyList,
    Contractor,
    ContractorInput,
    ContractorList,
    DescriptionInput,
    DimensionInput,
    DimensionValueInput,
    Document,
    DocumentDimensionInput,
    DocumentDimensionValueInput,
    DocumentIdGroups,
    DocumentItem,
    DocumentList,
    DocumentPolicy,
    DocumentSyncInput,
    DocumentUpdateInput,
    Employee,
    EmployeeList,
    FeeInput,
    ForeignCodeInput,
    InvoiceIdGroups,
    InvoiceList,
    PaymentMethodInput,
    PersonnelDocument,
    PersonnelDocumentList,
    RecognizeOptionInput,
    RegisterInput,
)

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
    "MergeResult",
    "PaymentMethodInput",
    "PersonnelDocument",
    "PersonnelDocumentList",
    "RecognizeOptionInput",
    "RegisterInput",
    "SaldeoClient",
    "SaldeoConfig",
    "SaldeoError",
]
__version__ = "0.1.0"
