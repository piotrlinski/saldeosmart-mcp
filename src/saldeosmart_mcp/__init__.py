"""SaldeoSMART MCP server."""

from .client import ItemError, SaldeoClient, SaldeoConfig, SaldeoError
from .models import (
    Company,
    CompanyList,
    Contractor,
    ContractorList,
    Document,
    DocumentItem,
    DocumentList,
    DocumentPolicy,
    ErrorResponse,
    InvoiceList,
    ItemErrorPayload,
)

__all__ = [
    "Company",
    "CompanyList",
    "Contractor",
    "ContractorList",
    "Document",
    "DocumentItem",
    "DocumentList",
    "DocumentPolicy",
    "ErrorResponse",
    "InvoiceList",
    "ItemError",
    "ItemErrorPayload",
    "SaldeoClient",
    "SaldeoConfig",
    "SaldeoError",
]
__version__ = "0.1.0"
