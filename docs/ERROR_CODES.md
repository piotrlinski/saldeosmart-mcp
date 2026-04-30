# SaldeoSMART error codes

Codes the MCP server may surface in `ErrorResponse.error`. The list mixes
**SaldeoSMART-issued** codes (returned in `<ERROR_CODE>` from the API) with
**synthetic** codes the client emits when something fails before or after the
API call.

This is a working reference — extend it whenever you encounter a new code in
the wild rather than letting future-you re-derive its meaning.

## SaldeoSMART-issued codes

These come from `<ERROR_CODE>` inside an `<RESPONSE>` envelope where
`<STATUS>ERROR</STATUS>`.

| Code   | Meaning                            | Likely cause / how to recover |
| ------ | ---------------------------------- | ----------------------------- |
| `4401` | No `SEARCH_POLICY` found in file   | The `document/search` request body is missing `<SEARCH_POLICY>` or has the wrong tag (`<POLICY>`). Confirmed via the `_build_search_xml` builder. |

> Add new codes here as you hit them. Include the literal string Saldeo
> returns and a one-line action — that's the part the LLM consuming our
> tool output benefits from.

## Synthetic codes (emitted by `SaldeoClient`)

These are not Saldeo codes — the client mints them when the response itself
is broken or missing. Defined in `src/saldeosmart_mcp/http/client.py`.

| Code               | Meaning                                                                    |
| ------------------ | -------------------------------------------------------------------------- |
| `HTTP_<status>`    | The server returned a non-2xx HTTP status with no `<RESPONSE>` envelope. The bare HTTP status drives the suffix (e.g. `HTTP_500`, `HTTP_403`). |
| `PARSE_ERROR`      | The 2xx body wasn't valid XML — usually an HTML error page from a proxy or load balancer. The first 500 chars of the body are in `message`. |
| `UNKNOWN`          | The envelope had `<STATUS>ERROR</STATUS>` but `<ERROR_CODE>` was empty.    |

## Tool-level synthetic codes (emitted before / instead of an API call)

These come from the tool layer — `@require_nonempty`, `@saldeo_call`, and
hand-written validation guards in individual tools. The string constants
live in `src/saldeosmart_mcp/errors.py` (`ERROR_*`) so call sites stay
typo-proof.

| Code                            | Meaning                                                                  |
| ------------------------------- | ------------------------------------------------------------------------ |
| `EMPTY_INPUT`                   | A required list argument was empty. Emitted by `@require_nonempty` before any network call. The `message` field names the resource (e.g. "At least one document is required."). |
| `INVALID_INPUT`                 | A builder-level invariant on the input batch failed (currently: `document.import` attachment-count mismatch). |
| `MISSING_CRITERIA`              | A search/lookup tool was called without enough criteria to be specific (e.g. `search_documents` with all of `document_id` / `number` / `nip` / `guid` set to `None`). |
| `TOO_MANY_DOCUMENTS`            | A batch endpoint was asked to process more than its per-request cap. Currently only `import_documents` enforces this (cap = 50). |
| `ATTACHMENT_NOT_FOUND`          | An `Attachment.path` does not exist on disk. Emitted by `@saldeo_call` when the tool body raises `FileNotFoundError`. |
| `ATTACHMENT_PERMISSION_DENIED`  | An `Attachment.path` exists but isn't readable by the server process. Emitted by `@saldeo_call` when the tool body raises `PermissionError`. |

## Per-item validation errors

Batch operations (`*.merge`, `update_documents`, etc.) succeed at the envelope
level even when individual items fail. Each failed item is in
`ErrorResponse.details[]`:

```json
{
  "error": "VALIDATION",
  "message": "some items failed",
  "details": [
    {"status": "NOT_VALID", "path": "VAT_NUMBER", "message": "required field", "item_id": "2"}
  ]
}
```

The `path` field names the offending element from the request XML; use it
to locate which field of which input model needs fixing.

## Authoritative source

SaldeoSMART's official error-code list lives in their API documentation
portal (the same place where the API token is generated). When in doubt,
consult that — and append anything useful here.
