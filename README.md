# SaldeoSMART MCP Server

[![CI](https://github.com/piotrlinski/saldeosmart-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/piotrlinski/saldeosmart-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-2a6db2.svg)](https://mypy-lang.org/)

MCP server for [SaldeoSMART](https://www.saldeosmart.pl/) — exposes tools to read and (optionally) modify documents, invoices, contractors, dimensions, articles, employees, and personnel documents on your account, over the [Model Context Protocol](https://modelcontextprotocol.io/). Works with any MCP-aware client (Claude Desktop, Claude Code, Cursor, Zed, MCP Inspector, custom SDK).

📖 **Full HTML documentation:** see [`docs/`](docs/index.html) — published to GitHub Pages by [`.github/workflows/pages.yml`](.github/workflows/pages.yml). Enable once under **Settings → Pages → Source: GitHub Actions**, then every push to `master` that touches `docs/**` republishes the site at `https://<owner>.github.io/<repo>/`.

## What it does

### Read-only tools

| Tool | Purpose |
| ---- | ------- |
| `list_companies`             | List companies (clients of an accounting firm) |
| `list_contractors`           | List contractors for a given company |
| `list_documents`             | Fetch cost documents (policy: last 10 days / OCR / SaldeoSMART export) |
| `search_documents`           | Find a single document by ID, number, NIP, or GUID |
| `list_invoices`              | List sales invoices issued in SaldeoSMART |
| `list_bank_statements`       | List bank statements with operations, dimensions, settlements |
| `list_employees`             | List employees (Personnel module) |
| `list_personnel_documents`   | List HR documents |
| `get_document_id_list`       | (3.0) List document IDs for a folder, grouped by kind |
| `get_documents_by_id`        | (3.0) Fetch documents by ID, grouped by kind |
| `get_invoice_id_list`        | (3.0) List invoice IDs for a folder, grouped by kind |
| `get_invoices_by_id`         | (3.0) Fetch invoices by ID, grouped by kind |
| `list_recognized_documents`  | Fetch OCR-recognized data for a list of OCR origin IDs |

### Write / merge / update tools

⚠ Every call mutates the customer's accounting data. Use with care.

| Tool | Purpose |
| ---- | ------- |
| `synchronize_companies`      | Pin Saldeo company IDs to your ERP program IDs (SS15) |
| `create_companies`           | Provision new client companies + admin users (SS01) |
| `merge_contractors`          | Add or update contractors (SS02) |
| `merge_categories`           | Add or update document categories (SS09) |
| `merge_payment_methods`      | Add or update payment methods (SS11) |
| `merge_registers`            | Add or update registers (SS10) |
| `merge_descriptions`         | Add or update business event descriptions (SS14) |
| `merge_dimensions`           | Add or update accounting dimensions (SS12) |
| `merge_articles`             | Add or update the article catalog (SS21) |
| `merge_fees`                 | Add or update accounting-firm fees for a month (SSK04) |
| `merge_financial_balance`    | Set monthly income / cost / VAT for a company (SSK01) |
| `merge_declarations`         | Sync tax declarations + attachments for a folder (SSK02) |
| `renew_assurances`           | Sync ZUS / social insurance for a folder (SSK03) |
| `merge_document_dimensions`  | Set dimension values on existing documents (SS20) |
| `add_documents`              | Upload cost documents to a (year, month) folder (SS05) |
| `add_recognize_document`     | Upload a document and trigger OCR in one round-trip (AE01) |
| `correct_documents`          | Overwrite OCR-extracted fields on existing documents (AE02) |
| `import_documents`           | Bulk import structured documents with full archival metadata (3.0) |
| `update_documents`           | Edit existing documents (SS17) |
| `delete_documents`           | Delete documents by ID (SS16, destructive) |
| `recognize_documents`        | Trigger OCR on uploaded documents (SS06) |
| `sync_documents`             | Push accounting numbering / status back to Saldeo (SS13) |
| `add_invoice`                | Issue a sales invoice with line items + payments (SSK06, 3.1) |
| `add_employees`              | Create or update employees in Personnel (P03) |
| `add_personnel_documents`    | Upload HR documents with attachments (P04) |

Every documented SaldeoSMART REST endpoint is now wrapped. Attachment-bearing endpoints accept :class:`saldeosmart_mcp.http.Attachment` inputs (path + optional display-name override); the helper at `src/saldeosmart_mcp/http/attachments.py` handles base64 encoding and the matching `attmnt_N` form-field plumbing.

### Choosing the right tool

Several SaldeoSMART resources have multiple read paths with overlapping shapes. Pick by the question you're answering:

| Goal | Tool |
| ---- | ---- |
| "Show me what's been added recently in this company" | `list_documents` (policy: `LAST_10_DAYS` / `LAST_10_DAYS_OCRED` / `SALDEO`) |
| "Find one specific document by ID/number/NIP/GUID" | `search_documents` |
| "Page through everything from a folder" (3.0) | `get_document_id_list` → `get_documents_by_id` |
| "Show me sales invoices issued in this company" | `list_invoices` |
| "Fetch invoices by a list of IDs" (3.0) | `get_invoice_id_list` → `get_invoices_by_id` |
| "What did OCR extract from these uploads?" | `list_recognized_documents` |
| "Show contractors/employees/bank statements" | `list_contractors` / `list_employees` / `list_bank_statements` |

For writes, use `merge_*` for "create or update by program ID" semantics, `update_documents` to edit existing documents, `delete_documents` to remove them, `recognize_documents` to (re)trigger OCR, and `sync_documents` to push your accounting system's numbering/status back to Saldeo.

Errors land in `ErrorResponse` — see [`docs/ERROR_CODES.md`](docs/ERROR_CODES.md) for the catalog.

## Requirements

To run the server (production), pick **one** transport:

- **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** ≥ 24 — image is built from `docker/Dockerfile`. The Docker daemon must be running.
- **[`uv`](https://docs.astral.sh/uv/) ≥ 0.4** — `uvx` (alias for `uv tool run`) launches the package straight from PyPI or git, no Docker daemon required. Handles Python ≥ 3.10 automatically.

You'll also need:

- **A SaldeoSMART account with API access** — generate the token in **Account settings → API**.
- **An MCP-aware client** — Claude Desktop, Claude Code, Cursor, Zed, MCP Inspector, or your own SDK harness. See [MCP client configuration](#mcp-client-configuration) below.

For development only:

- **GNU Make** — for `make build` / `make run` / `make test`. Standard on macOS/Linux; on Windows use WSL or `make` from chocolatey.
- **Node.js + npx** — optional, for the MCP Inspector (`make inspector`).

> ⚠ On some plans you need to email `api@saldeosmart.pl` to enable API access before you can generate a token.

## Build the image

```bash
git clone <this-repo>
cd saldeosmart-mcp
make build          # = docker build -f docker/Dockerfile -t saldeosmart-mcp:latest .
```

### Image layout

The Dockerfile (`docker/Dockerfile`) is two-stage:

1. **`builder`** — based on `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`. Runs `uv sync --frozen --no-dev` to resolve and install dependencies from `uv.lock` into an isolated `.venv`, then compiles bytecode. The uv cache is mounted as a BuildKit cache, so subsequent builds are fast.
2. **`runtime`** — based on plain `python:3.12-slim-bookworm`. Copies the prebuilt `.venv` from the builder, creates an unprivileged user `mcp`, and sets `ENTRYPOINT ["saldeosmart-mcp"]`.

Runtime details:

- `PATH="/app/.venv/bin:$PATH"` — the `saldeosmart-mcp` console script (declared in `pyproject.toml`) is on PATH.
- `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1` — keeps Python from corrupting stdio (the MCP transport) and from writing `.pyc` files into the image.
- `SALDEO_LOG_DIR=/var/log/saldeosmart` + `VOLUME` on that directory — see [Logs](#logs).
- `USER mcp` — the container does not run as root.

Final image: Python 3.12-slim + `.venv` with `fastmcp`, `httpx`, `pydantic`, `pydantic-settings` + the package code. Size: ~234 MB.

Other useful Makefile targets:

```bash
make help           # list all targets
make run            # start the server in a container (requires SALDEO_USERNAME / SALDEO_API_TOKEN in env)
make inspector      # MCP Inspector against the image
make test           # pytest locally (requires uv)
make lint           # ruff + mypy locally (requires uv)
make sync           # uv sync --extra dev — install dev dependencies
make clean          # docker image rm saldeosmart-mcp:latest
```

You can override the image tag or Dockerfile path:

```bash
IMAGE=saldeosmart-mcp:dev make build
```

## MCP client configuration

The server speaks MCP over stdio, so any MCP-aware client can launch it. Pick the transport (Docker or `uvx`) and the client from the matrix below — the same env-var or CLI-flag form works in any of them.

### Credentials: env vars or CLI flags

Both shapes are accepted; CLI flags win when both are set for the same field:

| Env var | CLI flag | Required | Default |
| ------- | -------- | -------- | ------- |
| `SALDEO_USERNAME`  | `--username`  | yes | — |
| `SALDEO_API_TOKEN` | `--api-token` | yes | — |
| `SALDEO_BASE_URL`  | `--base-url`  | no  | `https://saldeo.brainshare.pl` |

Use `https://saldeo-test.brainshare.pl` for the SaldeoSMART test environment.

### Run with Docker

After `make build` (or `docker pull` once an image is published), the launch command is:

```bash
docker run --rm -i \
    -e SALDEO_USERNAME=your-login \
    -e SALDEO_API_TOKEN=your-token \
    saldeosmart-mcp:latest
```

`-i` keeps stdin attached (MCP uses stdio); `--rm` cleans up the stopped container after the client disconnects.

### Run with `uvx`

`uvx` resolves the package on demand into an isolated venv, then runs the console script — no clone, no `pip install`, no Docker daemon. Until the package is on PyPI, point uvx at the GitHub URL:

```bash
# From PyPI (once published):
uvx saldeosmart-mcp --username your-login --api-token your-token

# From source (works today):
uvx --from git+https://github.com/piotrlinski/saldeosmart-mcp saldeosmart-mcp \
    --username your-login --api-token your-token
```

### Claude Desktop

Edit `claude_desktop_config.json`:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "saldeosmart": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "SALDEO_USERNAME=your-login",
        "-e", "SALDEO_API_TOKEN=your-token",
        "saldeosmart-mcp:latest"
      ]
    }
  }
}
```

…or, with `uvx`:

```json
{
  "mcpServers": {
    "saldeosmart": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/piotrlinski/saldeosmart-mcp",
        "saldeosmart-mcp",
        "--username", "your-login",
        "--api-token", "your-token"
      ]
    }
  }
}
```

Restart the app after editing. If the client reports it can't find `docker` / `uvx`, supply the absolute path from `which docker` / `which uvx` instead of the bare name.

### Claude Code

The CLI registers MCP servers via `claude mcp add`:

```bash
# Docker
claude mcp add saldeosmart -- \
    docker run --rm -i \
        -e SALDEO_USERNAME=your-login \
        -e SALDEO_API_TOKEN=your-token \
        saldeosmart-mcp:latest

# uvx
claude mcp add saldeosmart -- \
    uvx --from git+https://github.com/piotrlinski/saldeosmart-mcp saldeosmart-mcp \
    --username your-login --api-token your-token
```

Then `/mcp` inside Claude Code to confirm the server is registered.

### Cursor IDE

Edit `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (per-project):

```json
{
  "mcpServers": {
    "saldeosmart": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/piotrlinski/saldeosmart-mcp",
        "saldeosmart-mcp",
        "--username", "your-login",
        "--api-token", "your-token"
      ]
    }
  }
}
```

The Docker form is identical to the Claude Desktop snippet above. Reload Cursor's MCP servers from **Settings → Cursor Settings → MCP**.

### Keeping credentials out of the config file

If you'd rather not store the token in plaintext in your client config, drop it into a `chmod 600` env file and have Docker load it:

```bash
# ~/saldeosmart.env  (chmod 600)
SALDEO_USERNAME=your-login
SALDEO_API_TOKEN=your-token
```

```json
"args": [
  "run", "--rm", "-i",
  "--env-file", "/Users/you/saldeosmart.env",
  "saldeosmart-mcp:latest"
]
```

The `uvx` form works the same way if you pre-`export` the env vars in the shell that launches the MCP client (or use `direnv` per project).

## Local test (no MCP client)

```bash
export SALDEO_USERNAME=your-login
export SALDEO_API_TOKEN=your-token
make run            # = docker run --rm -i -e SALDEO_USERNAME -e SALDEO_API_TOKEN ... saldeosmart-mcp:latest
```

The server starts and waits for MCP messages on stdin/stdout.

With the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
make inspector
```

## Tests

```bash
make sync           # one-off, to set up .venv with dev deps
make test           # pytest
make lint           # ruff + mypy
```

Coverage focuses on the trickiest parts — the MD5 signing algorithm, the XML→gzip→base64 encoding, the error envelope parser (top-level + per-item), URL redaction, request-lock concurrency, and the request-XML builder for every write endpoint. The smoke test (`scripts/smoke_test.py`) hits every read endpoint against a real account.

> **Important for the smoke test:** it only invokes read endpoints (no `merge_*`, `update_*`, `delete_*`, `recognize_*`, `sync_*`). Write tools are covered exclusively by unit tests against fixture XML — never by live calls — so credentials in `.env` can never accidentally mutate the production account.

### Test layout

```
tests/
├── conftest.py                       # shared fixtures (isolated_root_logger, clean_env)
└── unit/
    ├── test_architecture.py          # import-direction layering rules
    ├── test_errors.py                # SaldeoError → MCP payload shape
    ├── test_logging.py               # setup_logging env-var handling, rotation
    ├── http/
    │   └── test_client.py            # signing, gzip+base64, error-envelope parser
    ├── models/
    │   └── test_documents.py         # XML → Pydantic for documents/invoices
    └── tools/
        └── test_builders.py          # every request-XML builder + summarize_merge
```

Test files mirror the source layout, so the home for a new test is wherever the production code it covers lives. Adding a tool? See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full step-by-step.

## Logs

Inside the image, logs default to `/var/log/saldeosmart/saldeosmart.log` (rotated daily, 7 days retained). To keep them outside the container, mount a volume:

```bash
docker run --rm -i \
    -e SALDEO_USERNAME=... -e SALDEO_API_TOKEN=... \
    -v saldeosmart-logs:/var/log/saldeosmart \
    saldeosmart-mcp:latest
```

## Architecture

The package is a strict stack — each layer may import from layers below it,
never above. A test (`tests/unit/test_architecture.py`) parses every import statement
in the source tree and fails CI if anything reaches upward.

```
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
├── models/                  # everything that crosses the MCP boundary as JSON
│   ├── common.py             # cross-resource (BankAccount, BankAccountInput)
│   ├── companies.py          # Company, CompanySynchronizeInput, CompanyCreateInput
│   ├── contractors.py        # Contractor(+List), ContractorInput
│   ├── documents.py          # Document, DocumentAddInput, DocumentImportInput,
│   │                         # DocumentCorrectInput, DocumentAddRecognizeInput, …
│   ├── invoices.py           # InvoiceList, InvoiceIdGroups, InvoiceAddInput
│   ├── bank.py               # BankStatement(+List), BankOperation
│   ├── personnel.py          # Employee, EmployeeAddInput, PersonnelDocument,
│   │                         # PersonnelDocumentAddInput
│   ├── financial_balance.py  # FinancialBalanceMergeInput
│   ├── accounting_close.py   # DeclarationMergeInput, AssuranceRenewInput,
│   │                         # CloseAttachmentInput, the four ASSURANCE_DETAILS
│   │                         # variants
│   └── catalog.py            # CategoryInput, RegisterInput, ArticleInput, FeeInput, …
│
├── tools/                   # @mcp.tool registry — one file per Saldeo resource
│   ├── _runtime.py           # mcp = FastMCP(...), saldeo_call, get_client,
│   │                         # summarize_merge, parse_collection
│   ├── _builders.py          # generic XML builders + append_close_attachments
│   ├── companies.py          # list_/synchronize_/create_companies
│   ├── contractors.py        # list_/merge_contractors
│   ├── documents.py          # list_/search_/add_/update_/delete_/recognize_/sync_/
│   │                         # add_recognize_/correct_/import_, 3.0 ID-list
│   ├── invoices.py           # list_/get_invoice_*, add_invoice
│   ├── bank.py               # list_bank_statements
│   ├── personnel.py          # list_/add_employees, list_/add_personnel_documents
│   ├── financial_balance.py  # merge_financial_balance
│   ├── accounting_close.py   # merge_declarations, renew_assurances
│   ├── dimensions.py         # merge_dimensions
│   └── catalog.py            # categories, payment_methods, registers,
│                             # descriptions, articles, fees
│
└── server.py          # main() — sets up logging, imports tools, runs mcp.run()
                       # (kept at top level for the console-script entry point)
```

Highlights:

- **Request signing** (`http/signing.py`) implements the Saldeo MD5 contract: sort params, concatenate as `key=value` with no separator, URL-encode, append token, hash. Encapsulated in a single class — easy to test, easy to mock, the only place that ever sees the raw token.
- **Two request methods** on `SaldeoClient` (`http/client.py`): `get(path, query)` for endpoints whose request fits in URL params, and `post_command(path, xml_command, query, extra_form)` for endpoints with a structured body or file attachments. The split mirrors the Saldeo spec — both reads and writes can use either.
- **The `command` form field** carries gzip-compressed, base64-encoded XML. Saldeo signs over the *full request* (URL + form), so `post_command` hashes both together.
- **`threading.Lock`** in `SaldeoClient` serializes calls because Saldeo's spec forbids concurrent requests per user; FastMCP's thread executor would otherwise issue them in parallel.
- **`SecretStr`** for the API token (never leaks via `repr()`/logs); URL redaction wipes `req_sig` and `api_token` from every logged URL.
- **Per-item error walker** (`iter_item_errors` in `errors.py`) — Saldeo answers `STATUS=OK` at the envelope level even when individual batch items fail, so write tools call this and report partial successes via `MergeResult`.

## API limits (heads-up)

The spec says:

- **20 requests per minute** per user
- **No concurrent requests** — wait for the previous response before sending the next one
- Max payload: ~70 MB after base64 encoding

The client serializes calls behind a lock to satisfy the no-concurrency rule. If you plan to make many requests, consider a server-side cache.

## API coverage

Every documented SaldeoSMART REST endpoint is wrapped as an MCP tool. The `SaldeoClient.post_command(..., extra_form=...)` form-field plumbing plus the `Attachment` / `prepare_attachments` helper handle every attachment-bearing endpoint.

## Contributing

Contributions are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the
workflow (especially the layering rules and the LLM-facing docstring contract).
Please also read the [Code of Conduct](CODE_OF_CONDUCT.md). For security
issues, see [`SECURITY.md`](SECURITY.md). Notable changes are tracked in
[`CHANGELOG.md`](CHANGELOG.md).

## License

[MIT](LICENSE) — see file for full text. Not an official SaldeoSMART/BrainShare product.
