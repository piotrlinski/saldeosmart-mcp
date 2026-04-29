# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- (nothing yet)

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

[Unreleased]: https://github.com/piotrlinski/saldeosmart-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/piotrlinski/saldeosmart-mcp/releases/tag/v0.1.0
