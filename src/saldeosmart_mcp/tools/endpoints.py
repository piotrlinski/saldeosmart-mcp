"""SaldeoSMART REST API-XML endpoint paths.

One named constant per ``(resource, operation)`` pair so version bumps
become a one-line edit instead of a global grep across every tool
module. The naming pattern is ``<RESOURCE>_<OPERATION>`` in
``SCREAMING_SNAKE_CASE``; the *value* keeps the wire-format API path
including the version number, which is what the spec keys off.

Architecture invariant: nothing under ``saldeosmart_mcp.tools`` should
hard-code ``/api/xml/...`` strings — always reference a constant from
this module. The architecture suite enforces this.
"""

from __future__ import annotations

from typing import Final

# ---- Catalog (write-only resources, no read counterpart) -------------------------

CATEGORY_MERGE: Final[str] = "/api/xml/1.0/category/merge"
PAYMENT_METHOD_MERGE: Final[str] = "/api/xml/1.0/payment_method/merge"
REGISTER_MERGE: Final[str] = "/api/xml/1.0/register/merge"
DESCRIPTION_MERGE: Final[str] = "/api/xml/1.13/description/merge"
ARTICLE_MERGE: Final[str] = "/api/xml/1.14/article/merge"
FEE_MERGE: Final[str] = "/api/xml/1.13/fee/merge"

# ---- Companies -------------------------------------------------------------------

COMPANY_LIST: Final[str] = "/api/xml/1.0/company/list"
COMPANY_SYNCHRONIZE: Final[str] = "/api/xml/1.0/company/synchronize"
COMPANY_CREATE: Final[str] = "/api/xml/2.19/company/create"

# ---- Contractors -----------------------------------------------------------------

CONTRACTOR_LIST: Final[str] = "/api/xml/1.23/contractor/list"
CONTRACTOR_MERGE: Final[str] = "/api/xml/1.23/contractor/merge"

# ---- Dimensions ------------------------------------------------------------------

DIMENSION_MERGE: Final[str] = "/api/xml/1.12/dimension/merge"
DOCUMENT_DIMENSION_MERGE: Final[str] = "/api/xml/1.13/document_dimension/merge"

# ---- Documents -------------------------------------------------------------------

DOCUMENT_LIST: Final[str] = "/api/xml/2.12/document/list"
DOCUMENT_SEARCH: Final[str] = "/api/xml/1.8/document/search"
DOCUMENT_GET_ID_LIST: Final[str] = "/api/xml/3.0/document/getidlist"
DOCUMENT_LIST_BY_ID: Final[str] = "/api/xml/3.0/document/listbyid"
DOCUMENT_LIST_RECOGNIZED: Final[str] = "/api/xml/2.18/document/list_recognized"
DOCUMENT_ADD: Final[str] = "/api/xml/1.0/document/add"
DOCUMENT_ADD_RECOGNIZE: Final[str] = "/api/xml/2.0/document/add_recognize"
DOCUMENT_CORRECT: Final[str] = "/api/xml/2.5/document/correct"
DOCUMENT_IMPORT: Final[str] = "/api/xml/3.0/document/import"
DOCUMENT_UPDATE: Final[str] = "/api/xml/2.4/document/update"
DOCUMENT_DELETE: Final[str] = "/api/xml/1.13/document/delete"
DOCUMENT_RECOGNIZE: Final[str] = "/api/xml/1.20/document/recognize"
DOCUMENT_SYNC: Final[str] = "/api/xml/1.13/document/sync"

# ---- Invoices --------------------------------------------------------------------

INVOICE_LIST: Final[str] = "/api/xml/1.20/invoice/list"
INVOICE_GET_ID_LIST: Final[str] = "/api/xml/3.0/invoice/getidlist"
INVOICE_LIST_BY_ID: Final[str] = "/api/xml/3.0/invoice/listbyid"
INVOICE_ADD: Final[str] = "/api/xml/3.1/invoice/add"

# ---- Bank ------------------------------------------------------------------------

BANK_STATEMENT_LIST: Final[str] = "/api/xml/2.18/bank_statement/list"

# ---- Personnel -------------------------------------------------------------------

EMPLOYEE_LIST: Final[str] = "/api/xml/2.20/employee/list"
EMPLOYEE_ADD: Final[str] = "/api/xml/2.21/employee/add"
PERSONNEL_DOCUMENT_LIST: Final[str] = "/api/xml/2.20/personnel_document/list"
PERSONNEL_DOCUMENT_ADD: Final[str] = "/api/xml/2.22/personnel_document/add"

# ---- Accounting close ------------------------------------------------------------

DECLARATION_MERGE: Final[str] = "/api/xml/1.0/declaration/merge"
ASSURANCE_RENEW: Final[str] = "/api/xml/1.0/assurance/renew"
FINANCIAL_BALANCE_MERGE: Final[str] = "/api/xml/1.15/financial_balance/merge"
