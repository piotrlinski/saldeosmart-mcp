# Reference

Auto-generated reference material. Pages here are regenerated on every
docs build from the actual source code — if a tool, model, or endpoint
exists in the codebase, it appears here. If something is missing, the
[`tool-catalog-check.yml`](https://github.com/piotrlinski/saldeosmart-mcp/blob/master/.github/workflows/tool-catalog-check.yml)
CI gate fails.

## What's here

- [**Tools**](tools/index.md) — every `@mcp.tool` registered with FastMCP,
  grouped by Saldeo resource (documents, invoices, contractors, …).
- [**Models**](models.md) — input and response Pydantic models with field
  constraints and validators.
- [**Configuration**](configuration.md) — environment variables and CLI
  flags.
- [**Error codes**](error-codes.md) — Saldeo-issued and synthetic codes,
  with recovery hints.
- [**API versions**](api-versions.md) — which Saldeo REST API version each
  tool currently targets.
- [**Changelog**](changelog.md) — release history (Keep a Changelog format).

!!! info "How auto-generation works"
    Three things ensure these pages stay current:

    1. **Build-time generation** — `mkdocs-gen-files` runs the
       `scripts/gen_*.py` generators every time the site is built.
    2. **Drift gate in CI** — `tool-catalog-check.yml` regenerates the
       catalog and fails the PR if the diff is non-empty without a commit.
    3. **Docstring contract** — `scripts/check_docstring_contract.py` (also
       a pre-commit hook) asserts every tool's docstring contains a
       one-line summary, a `Use this when …` discriminator, an `Args:`
       section, and a `Returns:` section.

    See [Architecture: documentation pipeline](../explanation/architecture.md#documentation-pipeline)
    for the full flow.
