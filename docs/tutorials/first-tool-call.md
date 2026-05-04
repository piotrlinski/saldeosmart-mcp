# Your first tool call

This walkthrough has Claude (or any MCP client) call two tools end-to-end
against your SaldeoSMART account: `list_companies` to discover IDs, then
`search_documents` to find a specific document. No writes, no surprises.

## Setup

You should have completed the [Quickstart](quickstart.md) — the server is
running and your MCP client lists the SaldeoSMART tools.

## 1. List companies

Ask Claude:

> Use `list_companies` to show me every company on this SaldeoSMART account.

Behind the scenes, the server calls `GET /api/xml/2.12/company/list`, parses
the XML response, and returns a `CompanyList` Pydantic model with one
`Company` per client. The fields you'll most often need:

| Field | Notes |
|---|---|
| `program_id` | Stable external ID — pin this in your ERP, not `id`. |
| `name` | Display name. |
| `nip` | 10-digit Polish tax ID. |

Pick a company. We'll call its `program_id` `ACME` from here on.

## 2. Search for a document

Ask Claude:

> In company `ACME`, use `search_documents` to find the cost document with
> number `FV/2024/0042`.

The server narrows the search to that one document by `number`. Notice that
the tool docstring (which the LLM reads) emphasizes that `search_documents`
is the right tool when you know one of: `document_id`, `number`, `nip`,
`guid`. If you instead asked "show me everything from last month," Claude
should pick `list_documents` (with `policy=LAST_10_DAYS`) or the 3.0 ID-list
flow (`get_document_id_list` → `get_documents_by_id`) — see
[Choosing the right read tool](../how-to/index.md#choosing-the-right-read-tool).

## 3. Inspect the response

`search_documents` returns a `Document` (or `ErrorResponse` on failure).
Notable fields:

- `id` — internal Saldeo ID; pass to `update_documents` / `delete_documents`.
- `category`, `register`, `payment_method` — categorization assigned in
  Saldeo.
- `total_net`, `total_gross`, `vat` — money amounts as strings (decimals,
  not floats — exact accounting math).
- `dimensions[]` — accounting dimensions if your firm uses them.

If the server can't find the document, it returns:

```json
{
  "error": "4401",
  "message": "No SEARCH_POLICY found in file",
  "details": []
}
```

See [Error codes](../reference/error-codes.md) for the full catalog.

## What's next

- The [tool catalog](../reference/tools/index.md) — every read and write tool
  documented and grouped by resource.
- [How-to: add a new tool](../how-to/add-a-tool.md) when an endpoint isn't
  yet wrapped.
- [Architecture](../explanation/architecture.md) for the layer rules and the
  request lifecycle.
