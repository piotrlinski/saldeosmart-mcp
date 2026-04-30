# Contributing to saldeosmart-mcp

This guide walks through the workflow that's most likely to come up:
**adding a new MCP tool that wraps a SaldeoSMART API endpoint**. The package
is small, but it has a strict layering and a docstring contract that the
LLM consuming the tools depends on, so following the steps below saves
review cycles.

## Setup

```bash
make sync          # creates .venv, installs runtime + dev deps
make test          # 321 tests should pass
make lint          # ruff check + ruff format --check + mypy
make format        # apply ruff format + ruff --fix
```

A `.pre-commit-config.yaml` is wired up — `pre-commit install` once and the
same gate runs on every `git commit`.

You'll also need a `.env` (see `.env.example`) for the smoke test in
`scripts/smoke_test.py`. It only hits read endpoints, so credentials in
`.env` cannot mutate production data — but treat the smoke test as the
final check, not the first one.

## Adding a tool

The package is a strict stack: `config → errors → http → models → tools →
server`. A tool function lives in `tools/<resource>.py`, takes typed
inputs, returns typed outputs, and never imports upward.

### 1. Find or sketch the API endpoint

The mirrored docs at `.temp/api-html-mirror/` (versions 1.0–3.1) are the
authoritative reference for shapes — `*_request.xsd`, `*_response.xsd`,
plus example XML files. Note the version directory: most resources have
multiple versions, and the latest stable is what you want.

### 2. Add Pydantic models in `src/saldeosmart_mcp/models/<resource>.py`

- For **read responses**: a class with `from_xml(cls, el) -> Model` and one
  `*List` wrapper if the endpoint returns a collection. Use the
  `el_text` / `el_int` / `el_bool` helpers from `..http.xml`. Read-side
  date / identifier fields stay as plain `str | None` — the source is
  Saldeo's own response and we trust it (see the docstring at the top of
  `models/common.py`).
- For **write inputs**: a `*Input` class with `BaseModel`. Required fields
  get no default; optional fields default to `None`. Lists of nested
  inputs use `Field(default_factory=list, max_length=N)` — pick a
  conservative bound so an LLM mistake can't fire a 10 MB request.
- Use the validated string aliases from `models/common.py` instead of bare
  `str` / `int` for fields that have a known shape. The available aliases
  are `IsoDate` (`YYYY-MM-DD`), `Nip` (10 digits), `Pesel` (11 digits),
  `VatNumber` (optional EU country prefix + 8–15 digits), `Year` (2000–
  2099), `Month` (1–12). They strip common copy-paste decorations and
  raise a clean Pydantic error on garbage so the LLM gets a useful
  message instead of an opaque Saldeo `4xxx` code.

Re-export new models from `models/__init__.py` so tool modules can
`from ..models import …` cleanly.

### 3. Add the tool in `src/saldeosmart_mcp/tools/<resource>.py`

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
        On failure: ErrorResponse — see docs/ERROR_CODES.md.
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
`SaldeoError` / `FileNotFoundError` / `PermissionError` / `ValueError`
to `ErrorResponse`. `@require_nonempty` (under `@saldeo_call`) short-
circuits empty list inputs before the network call; pass dotted paths
(`"declarations.taxes"`) to reach into nested input models.

Two helpers replace the repetitive write-tool body:

- `merge_call(endpoint, xml, *, total, query=None, extra_form=None)`
  wraps the universal `post_command(...) → summarize_merge(...)` pair.
- `endpoints.<NAME>` (in `tools/endpoints.py`) is the only place that
  knows API version numbers — never hard-code `/api/xml/...` strings in
  a tool module. When Saldeo bumps a version, the change is one line.

#### Docstring standard

Tool docstrings are part of the LLM-facing contract, not just code
documentation. Every tool's docstring must include:

1. **One-line purpose** — what it does, not how.
2. **"Use this when …"** — disambiguate from related tools (e.g.
   `list_documents` vs `search_documents` vs `get_document_id_list`).
3. **Each parameter** — type, format (`YYYY-MM-DD` for dates, `int` IDs),
   enum values listed inline, required vs optional, mutual exclusivity.
4. **Return shape** — name the model and call out unusual fields.
5. **Error path** — point at `docs/ERROR_CODES.md` for the
   `ErrorResponse` shape.

### 4. Add a unit test

Tests mirror the source layout — see `tests/` README section. For a
typical write tool, the `_build_*_xml` helper goes into
`tests/unit/tools/test_builders.py` (assertions on element names, ordering,
optional-field omission). Pure-parser tests (XML → Pydantic) go into
`tests/unit/models/test_<resource>.py`.

The architecture test at `tests/unit/test_architecture.py` runs
automatically — it'll fail if your new file imports upward through the
layer stack.

### 5. Run the gates

```bash
make test          # all green
make lint          # ruff + mypy clean
```

If you have credentials, also run the smoke test to confirm the read path
works against a real account:

```bash
.venv/bin/python scripts/smoke_test.py
```

### 6. Update the README tool table

`README.md` has a table of read-only and write tools — keep it current,
and update the decision matrix in the "Choosing the right tool" section
if your new tool overlaps with an existing one.

## House rules

- **Never write to production from tests.** The smoke test is read-only by
  policy. Write coverage is unit-test-only against fixture XML.
- **Tokens are `SecretStr`.** Never `str()` or log them. URL redaction in
  `http/xml.py` is the only place req_sig/api_token can appear in a log.
- **No upward imports.** `tests/unit/test_architecture.py` enforces the
  layer order. If your tool needs a helper, put it at or below the
  `tools/` layer.
- **Don't bypass `saldeo_call`.** Tools must catch `SaldeoError` via the
  decorator so the MCP boundary returns `ErrorResponse`, not stack traces.

## Reporting bugs and security issues

- **Bugs and feature requests:** open an issue using one of the templates in
  [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/).
- **Security vulnerabilities:** do **not** open a public issue. See
  [`SECURITY.md`](SECURITY.md) for the private disclosure path.

## License

By contributing to this project, you agree that your contributions will be
licensed under the [MIT License](LICENSE) that covers the project.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By
participating, you are expected to uphold it.
