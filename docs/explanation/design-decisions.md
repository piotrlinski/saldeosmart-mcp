# Design decisions

A running log of the non-obvious choices made in this codebase. Each
entry explains *why* something is the way it is — useful when you're
about to "improve" something and want to know whether you'll be undoing
a deliberate trade-off.

## Why FastMCP over a hand-rolled MCP server?

FastMCP gives us decorator-based tool registration (`@mcp.tool`), JSON
schema generation from type hints, and a battle-tested stdio transport.
A hand-rolled server would mean re-implementing the MCP envelope, the
schema export, and the transport handshake — three places to introduce
bugs that aren't related to the Saldeo wrapping.

**Trade-off:** FastMCP's decorator wraps the function, so introspection
tools (mkdocstrings, the catalog generator) need to reach
`getattr(fn, "__wrapped__", fn)` to see the underlying signature.
Documented; tested.

## Why Pydantic v2 (not v1, not dataclasses)?

Three reasons:

1. **Validation at the MCP boundary.** LLMs make typos in dates,
   identifiers, and enums. Pydantic's `Annotated` aliases (`IsoDate`,
   `Nip`, `Pesel`, etc. in `models/common.py`) catch the typo with a
   readable error before a network round-trip burns a 20-req/min token.
2. **JSON Schema for free.** Every input/output model produces a
   schema FastMCP ships to the client.
3. **mypy strict compatibility.** Pydantic v2's plugin handles
   `Annotated`, `Field`, and discriminated unions cleanly.

**Trade-off:** Pydantic v2's `model_json_schema()` output for
`Annotated[str, ...]` is verbose; mkdocstrings' `griffe-pydantic`
extension flattens it for rendering.

## Why one model per direction (Input vs response)?

Read responses (`Document`, `Invoice`) and write inputs (`DocumentInput`,
`InvoiceInput`) have different shapes — the response carries server-
generated fields like `id` and `created_at`; the input doesn't. Sharing
one model would force `Optional` everywhere and lose the schema
distinction.

## Why the `_runtime` / `_builders` / `_documents_builders` split?

`tools/<resource>.py` should be tool registrations, nothing else — that
makes the file scannable by domain. The XML construction logic lives in
`_builders.py` (generic) and `_documents_builders.py` (the document-tool
flavor that's larger than every other resource combined). This keeps
each tool body to ~10 lines: build XML, post, return.

## Why MD5 in request signing?

Not our choice — Saldeo's spec mandates MD5. See
[Request signing](request-signing.md#why-md5).

## Why `threading.Lock` instead of async?

Saldeo's spec forbids concurrent requests per user. We need
serialization either way. FastMCP dispatches sync tool calls from a
thread pool, so a `threading.Lock` is the natural fit. Going async
would force every tool to be `async def` for no concurrency gain. See
[Concurrency](concurrency.md).

## Why daily-rotated file logs and no stdout?

stdio is the MCP transport. Anything written to stdout corrupts the
JSON-RPC framing. The default log path
(`/var/log/saldeosmart/saldeosmart.log`, rotated daily, 7 days
retained) is deterministic and easy to mount as a Docker volume.

## Why does the README's tool table match the code's tool registry exactly?

It used to drift. Now `scripts/gen_tool_catalog.py` generates the
catalog from the source, the docs CI fails if the generated catalog
differs from what's committed, and the README is slimmed to a one-line
"see the docs site" pointer instead of duplicating the table. Drift is
no longer possible.

## Why `mike` for versioned docs?

Each release tag (`v0.2.0`, `v0.3.0`, …) gets its own URL. Users
locked to a specific version can read the docs as they were at that
release. The default landing (`latest` alias) tracks the highest
released version, with `dev` available for master.

**Trade-off:** mike + a cancelled CI run can corrupt the `gh-pages`
branch. The `docs-deploy.yml` workflow uses
`concurrency: cancel-in-progress: false` to mitigate.

## Why MkDocs Material over Sphinx?

The repo's prose is markdown end-to-end (README, CONTRIBUTING, CHANGELOG,
SECURITY). MkDocs uses markdown natively; Sphinx wants RST and would
force a translation step or constant `myst-parser` patching. The
mkdocstrings-python handler covers Sphinx's autodoc role for our
purposes, with `griffe-pydantic` adding Pydantic v2 awareness that
Sphinx's autodoc lacks.

## What we explicitly chose not to do

- **PDF export.** `mkdocs-with-pdf` and `mkdocs-exporter` are fragile.
  Browsers' "save as PDF" works on the live site for the rare case
  someone needs offline reference.
- **Vale prose linter.** `markdownlint` + `codespell` cover ~90% of the
  value with ~10% of the configuration burden.
- **Auto-translation.** Polish docs are hand-translated. Machine
  translation would degrade the LLM-facing tool docstrings (which need
  to read precisely) — and reference docs stay English by design.
- **Async transport.** See "Why threading.Lock instead of async" above.
