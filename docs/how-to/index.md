# How-to guides

Task-oriented recipes for the questions you'll have once the server is
running. Each guide answers exactly one question. For learning the project
end-to-end, see the [tutorials](../tutorials/index.md).

## Setup

- [Install the server](install.md) — `uvx`, `pip`, or Docker.
- [Configure Claude Desktop](configure-claude-desktop.md)
- [Configure Claude Code](configure-claude-code.md)
- [Configure Cursor](configure-cursor.md)
- [Configure other clients](configure-other-clients.md) — Zed, MCP Inspector, custom SDK.

## Operate

- [Debug authentication](debug-auth.md) — interpret 401s and the synthetic
  `HTTP_*` codes.
- [Run the smoke test](run-smoke-test.md) — verify a live account hits every
  read endpoint cleanly. Read-only by policy.

## Develop

- [Add a new tool](add-a-tool.md) — wrap a SaldeoSMART endpoint in five steps.
- [Bump the Saldeo API version](bump-saldeo-api-version.md) — when the vendor
  publishes 3.2, this is the runbook.

## Choosing the right read tool

SaldeoSMART has multiple read paths with overlapping shapes. Pick by the
question you're answering:

| Question | Tool |
|---|---|
| "What's been added recently?" | `list_documents` (policy: `LAST_10_DAYS` / `LAST_10_DAYS_OCRED` / `SALDEO`) |
| "Find one specific document by ID/number/NIP/GUID." | `search_documents` |
| "Page through everything from a folder." | `get_document_id_list` → `get_documents_by_id` (3.0) |
| "Show sales invoices issued." | `list_invoices` |
| "Fetch invoices by a list of IDs." | `get_invoice_id_list` → `get_invoices_by_id` (3.0) |
| "What did OCR extract?" | `list_recognized_documents` |
| "List contractors / employees / bank statements." | `list_contractors` / `list_employees` / `list_bank_statements` |
