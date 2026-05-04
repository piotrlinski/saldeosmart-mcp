# Bump a Saldeo API version

When SaldeoSMART publishes a new version of an endpoint (say `document/list`
goes from 2.12 to 2.13), the change is one line in this codebase. This
recipe is the runbook.

## The contract

`src/saldeosmart_mcp/tools/endpoints.py` is the **only** place in the
codebase that knows API version numbers. Every constant looks like:

```python
DOCUMENT_LIST: Final[str] = "/api/xml/2.12/document/list"
```

No tool module hard-codes a path. Bumping a version means:

1. Update the constant.
2. Verify the request/response shape against the new XSD.
3. Run the smoke test.

## Procedure

### 1. Refresh the API mirror

```bash
uv run python scripts/sync_api_mirror.py
```

This pulls the latest HTML/XSD/example XML from
`https://saldeo.brainshare.pl/static/doc/api/` into `.temp/api-html-mirror/`
(gitignored). The script also updates `docs/_data/api_mirror_index.json` —
**that** file is committed, and a non-empty diff is the signal that
something changed upstream.

### 2. Diff the new XSD against the old

```bash
diff .temp/api-html-mirror/2_12/document/document_list_response.xsd \
     .temp/api-html-mirror/2_13/document/document_list_response.xsd
```

Look for **added** or **renamed** elements — the project's `from_xml`
parsers are tolerant of extra elements (they ignore unknown tags) but
**will silently miss** new fields you want to expose.

### 3. Update the constant

```python
# tools/endpoints.py
DOCUMENT_LIST: Final[str] = "/api/xml/2.13/document/list"  # was 2.12
```

### 4. Update the model if the XSD added or renamed fields

Add the new field to the response model in `models/<resource>.py` with a
sensible default (`None` for optional fields). For renamed fields, check
the example XML in the mirror to confirm the new tag, then update the
`from_xml` extraction.

### 5. Run the suite

```bash
make test
make lint
.venv/bin/python scripts/smoke_test.py    # if you have credentials
make docs-build                            # site rebuilds with new version
```

The auto-generated [API versions reference](../reference/api-versions.md)
picks up the change on the next docs build.

## CI also tells you

The `api-mirror-sync.yml` workflow runs weekly and opens a PR labelled
`saldeo-api-update` whenever Saldeo publishes a new version. The PR body
lists which endpoints changed, so the routine work is "look at the PR,
follow this runbook for the affected constants, merge."

## Special case: 3.0 vs 2.x coexistence

Several resources have both a legacy 2.x list endpoint (rich response
fields) and a 3.0 paginated ID-list flow. Both are wrapped as separate
tools (`list_documents` vs `get_document_id_list` + `get_documents_by_id`).
When 3.1 ships a new variant, add the new constant alongside — don't
replace existing ones; LLMs make different choices depending on the
question, and the tool docstrings disambiguate them.
