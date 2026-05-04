# Run the smoke test

`scripts/smoke_test.py` exercises every read endpoint against a live
SaldeoSMART account. It's how you confirm a fresh deployment can actually
talk to Saldeo before pointing an LLM at it.

!!! warning "Read-only by policy"
    The smoke test invokes **only** read endpoints (`list_*`, `search_*`,
    `get_*`). Write tools (`merge_*`, `update_*`, `delete_*`,
    `recognize_*`, `sync_*`) are covered exclusively by unit tests against
    fixture XML. **Credentials in `.env` cannot accidentally mutate the
    production account from this script** — and that policy must be
    preserved if you extend the script.

## 1. Install dev dependencies

```bash
make sync
```

Equivalent to `uv sync --extra dev`. The smoke test runs in the same venv
as the unit tests.

## 2. Provision credentials

Copy `.env.example` to `.env` and fill in the three variables:

```bash
cp .env.example .env
$EDITOR .env
```

```ini
SALDEO_USERNAME=your-login
SALDEO_API_TOKEN=your-token
SALDEO_BASE_URL=https://saldeo-test.brainshare.pl
```

For first runs, **always** point at the test environment
(`saldeo-test.brainshare.pl`). Test-env tokens never see production
documents.

## 3. Run

```bash
.venv/bin/python scripts/smoke_test.py
```

The script:

1. Loads `.env`.
2. Calls `list_companies`. If empty, exits with a clear error.
3. For the first company in the response, calls every read tool that
   takes a `company_program_id` argument.
4. Prints a summary: tool name, response status, count of items
   returned.
5. Exits non-zero if any read failed.

Typical output:

```
✓ list_companies                        12 companies
✓ list_contractors      [ACME]          47 contractors
✓ list_documents        [ACME]          138 documents
✓ list_invoices         [ACME]          22 invoices
✓ list_bank_statements  [ACME]          1 statement
✓ list_employees        [ACME]          8 employees
✓ list_personnel_documents [ACME]       54 documents
✓ get_document_id_list  [ACME]          28 ids in 3 groups
…
12/12 read tools OK in 8.4s
```

## When it fails

- **`HTTP_401` everywhere** — credentials wrong; see [Debug auth](debug-auth.md).
- **One tool fails, the rest pass** — likely a Saldeo bug or a recently
  added field the parser doesn't yet handle. Check the latest XSD in
  `.temp/api-html-mirror/`.
- **`PARSE_ERROR`** — usually a network proxy mangling responses; same
  page covers it.

## In CI

The smoke test is **not** part of the standard CI matrix because it
requires a live token. To run it manually on a workflow dispatch, set the
`SALDEO_USERNAME` / `SALDEO_API_TOKEN` repository secrets and trigger
`.github/workflows/smoke-test.yml` (not yet shipped — track in the issue
tracker).
