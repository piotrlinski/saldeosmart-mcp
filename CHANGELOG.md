# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-05-04

### Added (documentation)

- MkDocs Material documentation site at
  `https://piotrlinski.github.io/saldeosmart-mcp/`. Replaces the
  hand-written `docs/index.html` static page. Diátaxis information
  architecture: tutorials, how-to guides, auto-generated reference,
  conceptual explanation.
- Auto-generated reference pages, regenerated on every docs build:
  tool catalog (one page per Saldeo resource family with `@mcp.tool`
  signatures and Pydantic model fields rendered via mkdocstrings),
  error codes, API-version matrix, configuration (env vars + CLI flags).
- Polish (`pl`) translations for landing, tutorials index +
  quickstart, how-to index, explanation index, and reference index.
  Reference pages stay English by design (auto-generated from English
  docstrings).
- `README.pl.md` — Polish parallel of the slimmed README.
- Doctest examples on `http/signing.py` (`RequestSigner.sign`),
  `http/xml.py` (`redact_url`), and `models/common.py` validators
  (`_validate_iso_date`, `_validate_nip`, `_validate_vat_number`).
  Runs via `pytest --doctest-modules` in `docs.yml`.

### Added (CI / automation)

- `.github/workflows/docs.yml` — PR gate: strict mkdocs build, tool
  coverage gate, docstring-contract gate, lychee link check,
  markdownlint, codespell, doctest, per-PR preview artifact.
- `.github/workflows/docs-deploy.yml` — versioned deploy via mike;
  replaces the prior `pages.yml`.
- `.github/workflows/release.yml` — on tag `v*`: PyPI trusted
  publishing, `mike deploy <version> latest`, GitHub Release via
  Release Drafter.
- `.github/workflows/api-mirror-sync.yml` — weekly cron that refreshes
  `.temp/api-html-mirror/` and opens a PR if Saldeo published a new
  API version.
- `.github/workflows/tool-catalog-check.yml` — drift gate on PRs
  touching `tools/`: the rendered catalog must contain every
  `@mcp.tool` function.
- `scripts/gen_tool_catalog.py`, `gen_error_codes.py`,
  `gen_api_versions.py`, `gen_configuration.py` — pre-build
  generators that write into `docs/reference/` (gitignored).
- `scripts/check_tool_coverage.py`, `check_docstring_contract.py`,
  `check_translations.py`, `sync_api_mirror.py` — CI gates.
- `Makefile` targets: `docs-sync`, `docs-gen`, `docs-serve`,
  `docs-build`, `docs-lint`, `docs-link-check`, `docs-coverage`,
  `docs-all`.
- Pre-commit hooks: codespell, markdownlint-cli2, and the
  tool-docstring-contract local hook.
- `.markdownlint.yaml`, `.codespellrc`, `lychee.toml`,
  `.github/release-drafter.yml`.
- `__version__` exposed at the package root, sourced via
  `importlib.metadata.version("saldeosmart-mcp")`.

### Changed

- `README.md` slimmed from 459 → ~80 lines: hero badges, 30-second
  quickstart, links to the docs site for everything else. Tool table
  is now part of the auto-generated catalog at the docs site.
- `CONTRIBUTING.md` — internal cross-links rewritten to absolute
  GitHub URLs so the file remains correct when included into the docs
  site via `mkdocs-include-markdown-plugin`.
- `pyproject.toml` — `[project.optional-dependencies]` adds a `docs`
  group (mkdocs, mkdocs-material, mkdocstrings[python],
  griffe-pydantic, mkdocs-{static-i18n,redirects,
  git-revision-date-localized,literate-nav,section-index,
  include-markdown}, mike, pymdown-extensions, codespell).

### Removed

- `docs/index.html`, `docs/style.css`, `docs/.nojekyll`,
  `docs/ERROR_CODES.md` — superseded by the mkdocs build output.
- `.github/workflows/pages.yml` — superseded by `docs-deploy.yml`.

### Pre-existing in `[Unreleased]` since 0.1.0 (carried into 0.2.0)

### Added

- `tools/endpoints.py` — central registry of every `/api/xml/...` path. The
  only place that knows API version numbers; the architecture test rejects
  bare endpoint strings in the rest of `tools/`.
- `@require_nonempty(field, message=...)` decorator in `tools/_runtime.py`,
  with dotted-path support for nested-list inputs (e.g.
  `"declarations.taxes"`). Replaces 22 hand-written `EMPTY_INPUT` guards.
- `merge_call(endpoint, xml, *, total, query, extra_form)` helper in
  `tools/_runtime.py`. Replaces ~20 hand-written
  `post_command(...) → summarize_merge(...)` pairs.
- `tools/_documents_builders.py` — XML request builders for the document
  tools, split out so `tools/documents.py` is registrations only.
- Validated string aliases in `models/common.py`: `Nip`, `Pesel`,
  `VatNumber`, `Year` (2000-2099), `Month` (1-12). Applied to write inputs
  and to bare tool params (`get_document_id_list`, `get_invoice_id_list`,
  `merge_fees`, `list_personnel_documents`).
- Error-code constants in `errors.py`: `ERROR_EMPTY_INPUT`,
  `ERROR_INVALID_INPUT`, `ERROR_MISSING_CRITERIA`,
  `ERROR_TOO_MANY_DOCUMENTS`, `ERROR_ATTACHMENT_NOT_FOUND`,
  `ERROR_ATTACHMENT_PERMISSION_DENIED`.
- `_CloseAttachmentLike` Protocol in `tools/_builders.py` replaces the
  former `Sequence[Any]` duck typing on `append_close_attachments`.
- `tests/unit/models/test_validators.py` — 35 cases covering `IsoDate`,
  `Nip`, `Pesel`, `VatNumber`, `Year`, `Month`.
- `tests/unit/models/test_serialization.py` — JSON round-trip tests for
  `DocumentList` / `ErrorResponse` / `MergeResult`, plus enforcement of
  `DocumentImportInput.attachments`'s `max_length=5`.
- `make format` Makefile target (apply ruff format + ruff --fix).
- `.pre-commit-config.yaml` running ruff, ruff-format, and mypy on commit.

### Changed

- `tools/documents.py`: 855 → 468 LOC after extracting builders into
  `tools/_documents_builders.py`. No public-API change.
- `tools/_runtime.py`'s `saldeo_call` now also maps `ValueError` raised in
  builders (e.g. attachment-count mismatch in `document.import`) to a
  structured `ErrorResponse(error="INVALID_INPUT", ...)` instead of letting
  the stack trace escape.
- `logging.setup_logging` drops *any* prior `TimedRotatingFileHandler`
  instance on re-entry instead of relying on exact-path equality, so
  `SALDEO_LOG_DIR` changes between calls no longer leak handlers.
- `http.xml.redact_url` uses `urllib.parse.urlsplit` /
  `parse_qsl` / `urlunsplit` instead of a regex.
- `make lint` now also runs `ruff format --check`. `pyproject.toml` ruff
  rules expanded with `RUF`, `PERF`, `PT` (with `RUF002` / `RUF003`
  ignored for Polish-language docstrings).

### Fixed

- `_build_document_import_xml` raised `AssertionError` on attachment-count
  mismatch — `assert` is the wrong contract for input validation. Switched
  to `ValueError`, picked up by `saldeo_call` as `INVALID_INPUT`.

### Added (write tools)

- `synchronize_companies`, `create_companies`, `merge_financial_balance`,
  `merge_declarations`, `renew_assurances`, `add_documents`,
  `add_recognize_document`, `correct_documents`, `import_documents`,
  `add_invoice`, `add_employees`, `add_personnel_documents`.

### Removed

- `saldeo_url_encode` from the `saldeosmart_mcp.http` re-exports
  (still importable from `saldeosmart_mcp.http.signing` for tests).

## [0.1.0] - 2026-04-29

Initial public release.

### Added

- FastMCP server (`saldeosmart-mcp` console script) wrapping the
  SaldeoSMART REST API for use from MCP-aware clients (Claude Desktop,
  MCP Inspector, etc.).
- **Read-only tools:** `list_companies`, `list_contractors`,
  `list_documents`, `search_documents`, `list_invoices`,
  `list_bank_statements`, `list_employees`, `list_personnel_documents`,
  `get_document_id_list`, `get_documents_by_id`, `get_invoice_id_list`,
  `get_invoices_by_id`, `list_recognized_documents`.
- **Write / merge / update tools:** `merge_contractors`,
  `merge_categories`, `merge_payment_methods`, `merge_registers`,
  `merge_descriptions`, `merge_dimensions`, `merge_articles`,
  `merge_fees`, `merge_document_dimensions`, `update_documents`,
  `delete_documents`, `recognize_documents`, `sync_documents`.
- HTTP layer with MD5 request signing, gzip+base64 XML command
  encoding, per-item error walker, and URL redaction.
- Pydantic models for every resource that crosses the MCP boundary.
- `SecretStr`-typed API token; tokens never appear in logs.
- `threading.Lock` to satisfy SaldeoSMART's "no concurrent requests per
  user" rule under FastMCP's thread executor.
- Two-stage Docker image (`docker/Dockerfile`) based on `uv` +
  `python:3.12-slim-bookworm`, running as an unprivileged user.
- Architecture test (`tests/unit/test_architecture.py`) that fails CI on
  upward layer imports.
- Read-only smoke test (`scripts/smoke_test.py`) for live-account
  verification.
- HTML documentation under `docs/`, published to GitHub Pages by
  `.github/workflows/pages.yml`.

### Project scaffolding

- MIT license (`LICENSE`).
- Contributor guide (`CONTRIBUTING.md`).
- Code of conduct based on Contributor Covenant 2.1.
- Security policy (`SECURITY.md`) with private vulnerability reporting.
- CI workflow (`.github/workflows/ci.yml`): ruff, mypy strict, pytest on
  Python 3.10 / 3.11 / 3.12.
- Issue and pull-request templates under `.github/`.
- Dependabot configuration for `pip` and `github-actions`.

[Unreleased]: https://github.com/piotrlinski/saldeosmart-mcp/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/piotrlinski/saldeosmart-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/piotrlinski/saldeosmart-mcp/releases/tag/v0.1.0
