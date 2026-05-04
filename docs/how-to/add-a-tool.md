# Add a new tool

The package wraps every documented SaldeoSMART REST endpoint, but Saldeo
publishes new endpoints periodically and the project welcomes contributions.
This recipe walks through adding one new tool end-to-end.

The package is a strict stack: `config → errors → http → models → tools →
server`. A tool function lives in `tools/<resource>.py`, takes typed inputs,
returns typed outputs, and never imports upward. The architecture test at
`tests/unit/test_architecture.py` will fail CI if anything reaches upward.

## 1. Find or sketch the endpoint

The mirrored docs at `.temp/api-html-mirror/` (versions 1.0–3.1) are the
authoritative reference for shapes — `*_request.xsd`, `*_response.xsd`,
example XML files. Note the version directory: most resources have multiple
versions, and the latest stable is what you want.

Refresh the mirror (gitignored, regenerated on demand):

```bash
uv run python scripts/sync_api_mirror.py
```

## 2. Add Pydantic models in `src/saldeosmart_mcp/models/<resource>.py`

For **read responses** — a class with `from_xml(cls, el) -> Model` and one
`*List` wrapper if the endpoint returns a collection. Use the
`el_text` / `el_int` / `el_bool` helpers from `..http.xml`. Read-side date
and identifier fields stay as plain `str | None` — the source is Saldeo's
own response and we trust it.

For **write inputs** — a `*Input` class with `BaseModel`. Required fields
get no default; optional fields default to `None`. Lists of nested inputs
use `Field(default_factory=list, max_length=N)` — pick a conservative bound
so an LLM mistake can't fire a 10 MB request.

Use the validated string aliases from `models/common.py` instead of bare
`str` / `int` for fields that have a known shape. Available aliases:
`IsoDate` (`YYYY-MM-DD`), `Nip` (10 digits), `Pesel` (11 digits),
`VatNumber` (optional EU country prefix + 8–15 digits), `Year` (2000–2099),
`Month` (1–12). They strip common copy-paste decorations and raise a clean
Pydantic error on garbage so the LLM gets a useful message instead of an
opaque Saldeo `4xxx` code.

Re-export new models from `models/__init__.py`.

## 3. Add the tool in `src/saldeosmart_mcp/tools/<resource>.py`

```python
from . import endpoints                               # add the path here first
from ._runtime import (
    get_client, mcp, merge_call, parse_collection,
    require_nonempty, saldeo_call,
)


@mcp.tool
@saldeo_call
def list_widgets(
    company_program_id: str,
    policy: WidgetPolicy = "ALL",
) -> WidgetList | ErrorResponse:
    """One-line summary of what the tool does for the LLM.

    Use this when … (disambiguate vs. neighboring tools).

    Args:
        company_program_id: External program ID. Get from list_companies.
        policy: Which widgets to return:
            - ALL — every widget on the account (default)
            - ACTIVE — only widgets currently in use

    Returns:
        WidgetList of widgets with nested fields.
        On failure: ErrorResponse — see the error-codes reference.
    """
    root = get_client().get(
        endpoints.WIDGET_LIST,
        query={"company_program_id": company_program_id, "policy": policy},
    )
    items = parse_collection(root, "WIDGETS", "WIDGET", Widget.from_xml)
    return WidgetList(widgets=items, count=len(items))


@mcp.tool
@saldeo_call
@require_nonempty("widgets", message="At least one widget is required.")
def merge_widgets(
    company_program_id: str,
    widgets: list[WidgetInput],
) -> MergeResult | ErrorResponse:
    """One-line summary."""
    xml = _build_widget_merge_xml(widgets)
    return merge_call(
        endpoints.WIDGET_MERGE,
        xml,
        total=len(widgets),
        query={"company_program_id": company_program_id},
    )
```

Decorator order matters and is left-to-right outside-in. `@mcp.tool` is the
outermost so FastMCP sees the wrapped function with the
`MergeResult | ErrorResponse` return type. `@saldeo_call` translates
`SaldeoError` / `FileNotFoundError` / `PermissionError` / `ValueError` to
`ErrorResponse`. `@require_nonempty` (under `@saldeo_call`) short-circuits
empty list inputs before the network call; pass dotted paths
(`"declarations.taxes"`) to reach into nested input models.

Two helpers replace the repetitive write-tool body:

- `merge_call(endpoint, xml, *, total, query=None, extra_form=None)` wraps
  the universal `post_command(...) → summarize_merge(...)` pair.
- `endpoints.<NAME>` (in `tools/endpoints.py`) is the only place that knows
  API version numbers — never hard-code `/api/xml/...` strings in a tool
  module. When Saldeo bumps a version, the change is one line.

## 4. The docstring contract

Tool docstrings are part of the LLM-facing contract, not just code
documentation. The CI gate `scripts/check_docstring_contract.py` requires:

1. **One-line purpose** ≤ 100 chars — what it does, not how.
2. **`Use this when …`** — disambiguate from related tools (e.g.
   `list_documents` vs `search_documents` vs `get_document_id_list`).
3. **`Args:`** section — every parameter with its type, format
   (`YYYY-MM-DD` for dates), enum values listed inline, required vs
   optional, mutual exclusivity.
4. **`Returns:`** section — name the model and call out unusual fields.

Pre-commit also runs the contract check — `pre-commit install` once and
your tool is gated locally.

## 5. Add a unit test

Tests mirror the source layout. For a typical write tool:

- The `_build_*_xml` helper goes into `tests/unit/tools/test_builders.py`
  (assertions on element names, ordering, optional-field omission).
- Pure-parser tests (XML → Pydantic) go into
  `tests/unit/models/test_<resource>.py`.

The architecture test at `tests/unit/test_architecture.py` runs
automatically — it'll fail if your new file imports upward through the
layer stack.

## 6. Run the gates

```bash
make test          # all green
make lint          # ruff + mypy clean
make docs-build    # site builds, your tool appears in the catalog
```

If you have credentials, also run the read-only smoke test:

```bash
.venv/bin/python scripts/smoke_test.py
```

## What you get for free

- The tool catalog page under [Reference → Tools](../reference/tools/index.md)
  picks up your new tool on the next docs build — no manual edits.
- The CI drift gate fails any PR that introduces a tool but not its
  catalog entry, so this can't go stale.
- The README "tool count" badge updates automatically on release.
