# Architecture

The package is a strict stack — each layer may import from layers below
it, never above. A test (`tests/unit/test_architecture.py`) parses every
import statement in the source tree and fails CI if anything reaches
upward.

## Layer stack

```mermaid
graph TD
    server["server.py — main(), arg-parsing, FastMCP stdio"]
    tools["tools/* — 43 @mcp.tool functions, _runtime, _builders"]
    models["models/* — Pydantic input/output types"]
    http["http/* — SaldeoClient, RequestSigner, xml, attachments"]
    errors["errors.py — SaldeoError, ErrorResponse, MergeResult"]
    config["config.py — SaldeoConfig (pydantic-settings)"]
    logging["logging.py — daily-rotated file handler"]

    server --> tools
    tools --> models
    tools --> http
    tools --> errors
    http --> errors
    http --> config
    models --> errors
    server --> config
    server --> logging
```

The architecture test asserts: no upward edge ever appears. If your new
module needs a helper from an upper layer, the helper belongs at or below
your layer instead.

## Source tree

```text
src/saldeosmart_mcp/
├── config.py          # SaldeoConfig (Pydantic Settings) — env vars, base URL
├── errors.py          # SaldeoError, ItemError, ErrorResponse, MergeResult,
│                      # iter_item_errors (per-item failure walker)
├── logging.py         # daily-rotated file logger (stdio is the MCP transport)
│
├── http/              # transport layer
│   ├── signing.py     # RequestSigner — MD5(URL-encode(sorted params) + token)
│   ├── client.py      # SaldeoClient — httpx pool + threading.Lock + envelope parser
│   ├── xml.py         # el_text/el_int/el_bool/set_text + URL redaction
│   └── attachments.py # Attachment + prepare_attachments — file → base64 + form
│
├── models/            # everything that crosses the MCP boundary as JSON
│   ├── common.py             # cross-resource: BankAccount(+Input), validated
│   │                         # string aliases IsoDate / Nip / Pesel / VatNumber,
│   │                         # range-bounded Year / Month
│   ├── companies.py          # Company, CompanySynchronizeInput, CompanyCreateInput
│   ├── contractors.py        # Contractor(+List), ContractorInput
│   ├── documents.py          # Document, DocumentAddInput, DocumentImportInput, …
│   ├── invoices.py           # InvoiceList, InvoiceIdGroups, InvoiceAddInput
│   ├── bank.py               # BankStatement(+List), BankOperation
│   ├── personnel.py          # Employee, EmployeeAddInput, PersonnelDocument, …
│   ├── financial_balance.py  # FinancialBalanceMergeInput
│   ├── accounting_close.py   # DeclarationMergeInput, AssuranceRenewInput, …
│   └── catalog.py            # CategoryInput, RegisterInput, ArticleInput, FeeInput, …
│
├── tools/             # @mcp.tool registry — one file per Saldeo resource
│   ├── _runtime.py           # mcp = FastMCP(...), saldeo_call, require_nonempty,
│   │                         # merge_call, get_client, summarize_merge, parse_collection
│   ├── _builders.py          # generic XML builders + append_close_attachments
│   ├── _documents_builders.py # document-tool XML builders
│   ├── endpoints.py          # one Final[str] constant per /api/xml/... path
│   ├── companies.py          # list_/synchronize_/create_companies
│   ├── contractors.py        # list_/merge_contractors
│   ├── documents.py          # list_/search_/add_/update_/delete_/recognize_/sync_/ …
│   ├── invoices.py           # list_/get_invoice_*, add_invoice
│   ├── bank.py               # list_bank_statements
│   ├── personnel.py          # list_/add_employees, list_/add_personnel_documents
│   ├── financial_balance.py  # merge_financial_balance
│   ├── accounting_close.py   # merge_declarations, renew_assurances
│   ├── dimensions.py         # merge_dimensions
│   └── catalog.py            # categories, payment_methods, registers, …
│
└── server.py          # main() — sets up logging, imports tools, runs mcp.run()
```

## Request lifecycle

```mermaid
sequenceDiagram
    participant LLM
    participant FastMCP as FastMCP (stdio)
    participant Tool as @mcp.tool fn
    participant Decorators as @saldeo_call + @require_nonempty
    participant Client as SaldeoClient
    participant Signer as RequestSigner
    participant Saldeo as Saldeo REST API

    LLM->>FastMCP: tools/call list_documents(company_program_id, policy)
    FastMCP->>Tool: invoke
    Tool->>Decorators: validate (non-empty inputs, …)
    Decorators->>Client: get(endpoint, query)
    Client->>Signer: sign(query)
    Signer-->>Client: req_id + req_sig (MD5)
    Client->>Saldeo: HTTPS GET
    Saldeo-->>Client: <RESPONSE><STATUS>OK</STATUS> …
    Client->>Client: parse envelope, raise SaldeoError on STATUS=ERROR
    Client-->>Tool: XML root element
    Tool->>Tool: parse_collection → Pydantic models
    Tool-->>Decorators: typed return value
    Decorators-->>FastMCP: DocumentList | ErrorResponse
    FastMCP-->>LLM: tool result
```

## Highlights

- **Request signing** (`http/signing.py`) — Saldeo's MD5 contract: sort
  params, concatenate as `key=value` with no separator, URL-encode,
  append token, hash. Encapsulated in a single class — easy to test, easy
  to mock, the only place that ever sees the raw token.
- **Two request methods on `SaldeoClient`** — `get(path, query)` for
  endpoints whose request fits in URL params, and
  `post_command(path, xml_command, query, extra_form)` for endpoints with
  a structured body or file attachments. The split mirrors the Saldeo
  spec — both reads and writes can use either.
- **The `command` form field** carries gzip-compressed, base64-encoded
  XML. Saldeo signs over the *full request* (URL + form), so
  `post_command` hashes both together.
- **`threading.Lock`** in `SaldeoClient` serializes calls because Saldeo's
  spec forbids concurrent requests per user; FastMCP's thread executor
  would otherwise issue them in parallel. See
  [Concurrency](concurrency.md).
- **`SecretStr`** for the API token (never leaks via `repr()`/logs); URL
  redaction wipes `req_sig` and `api_token` from every logged URL. See
  [Security & privacy](security-and-privacy.md).
- **Per-item error walker** (`iter_item_errors` in `errors.py`) — Saldeo
  answers `STATUS=OK` at the envelope level even when individual batch
  items fail, so write tools call this and report partial successes via
  `MergeResult`.
- **Two-decorator boundary on write tools** — `@saldeo_call` maps
  `SaldeoError` / `FileNotFoundError` / `PermissionError` / `ValueError`
  to `ErrorResponse`; `@require_nonempty(field, message=...)` short-
  circuits empty-list batches before the network call. Stack
  `@require_nonempty` *under* `@saldeo_call`. The
  `merge_call(endpoint, xml, *, total, query, extra_form)` helper wraps
  the universal `post_command(...) → summarize_merge(...)` pair.
- **Validation at the MCP boundary** — write inputs are typed with
  `Annotated` aliases from `models/common.py` (`IsoDate`, `Nip`, `Pesel`,
  `VatNumber`, `Year`, `Month`); typos fail Pydantic validation
  client-side instead of returning an opaque Saldeo error code.

## Documentation pipeline

The docs site is itself derived from the source tree. Every PR runs:

```mermaid
graph LR
    src[src/] -->|gen_tool_catalog.py| tools_md[reference/tools/*.md]
    src -->|gen_error_codes.py| errors_md[reference/error-codes.md]
    src -->|gen_api_versions.py| versions_md[reference/api-versions.md]
    src -->|gen_configuration.py| config_md[reference/configuration.md]
    tools_md -->|mkdocs build --strict| site[site/]
    errors_md --> site
    versions_md --> site
    config_md --> site
    site -->|lychee, markdownlint, codespell| pass{Gates pass?}
    pass -->|yes, master| mike[mike deploy]
    pass -->|yes, PR| preview[per-PR preview]
    pass -->|no| fail[CI fails]
```

The `tool-catalog-check.yml` workflow regenerates the catalog on every PR
that touches `src/saldeosmart_mcp/tools/**` and fails if the diff against
committed stubs is non-empty — code and docs cannot drift apart.
