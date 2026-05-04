# SaldeoSMART MCP Server

[![CI](https://github.com/piotrlinski/saldeosmart-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/piotrlinski/saldeosmart-mcp/actions/workflows/ci.yml)
[![Docs](https://github.com/piotrlinski/saldeosmart-mcp/actions/workflows/docs-deploy.yml/badge.svg)](https://piotrlinski.github.io/saldeosmart-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-2a6db2.svg)](https://mypy-lang.org/)

A [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes
the [SaldeoSMART](https://www.saldeosmart.pl/) REST API as typed, LLM-friendly
tools — read documents, invoices, contractors, employees, bank statements;
create, update, merge, and synchronize accounting records — from any MCP-aware
client (Claude Desktop, Claude Code, Cursor, Zed, MCP Inspector).

## :rocket: 30-second quickstart

```bash
# Build the image
git clone https://github.com/piotrlinski/saldeosmart-mcp.git
cd saldeosmart-mcp && make build

# Run, pointing your MCP client at this command:
docker run --rm -i \
  -e SALDEO_USERNAME=your-login \
  -e SALDEO_API_TOKEN=your-token \
  saldeosmart-mcp:latest
```

Or without Docker:

```bash
uvx --from git+https://github.com/piotrlinski/saldeosmart-mcp \
    saldeosmart-mcp --username your-login --api-token your-token
```

[**Full documentation →**](https://piotrlinski.github.io/saldeosmart-mcp/) ·
[Polish version](https://piotrlinski.github.io/saldeosmart-mcp/pl/) ·
[Tool catalog](https://piotrlinski.github.io/saldeosmart-mcp/reference/tools/) ·
[Configure your MCP client](https://piotrlinski.github.io/saldeosmart-mcp/how-to/) ·
[Contributing](CONTRIBUTING.md)

## Highlights

- :material-tools: **43 tools** wrapping every documented SaldeoSMART REST endpoint.
- :material-shield-lock: **Privacy-first** — `SecretStr` tokens, URL redaction in logs, single-flight request lock.
- :material-test-tube: **Strict typing** — Pydantic v2 models, mypy-strict CI.
- :material-translate: **English + Polski** — bilingual docs at the published site.
- :material-source-branch: **MIT-licensed**, not affiliated with SaldeoSMART/BrainShare.

## Requirements

- A SaldeoSMART account with API access enabled
  ([generate token](https://piotrlinski.github.io/saldeosmart-mcp/tutorials/quickstart/#prerequisites)).
- One of: [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 24,
  or [`uv`](https://docs.astral.sh/uv/) ≥ 0.4.
- An MCP-aware client.

## :warning: Write tools mutate live accounting data

Every `merge_*`, `add_*`, `update_*`, `delete_*`, `recognize_*`, `sync_*`, and
`create_*` tool changes data on the customer's SaldeoSMART account. Read the
[tool catalog](https://piotrlinski.github.io/saldeosmart-mcp/reference/tools/)
before letting an autonomous agent call write tools.

## API limits

- 20 requests per minute per user.
- No concurrent requests — the client serializes calls behind a `threading.Lock`.
- Max payload: ~70 MB after base64 encoding.

## Development

```bash
make sync          # uv sync --extra dev
make test          # pytest
make lint          # ruff + mypy
make docs-serve    # live-reload docs at http://127.0.0.1:8000
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the workflow (especially the
layering rules and the LLM-facing docstring contract).
[`SECURITY.md`](SECURITY.md) covers the disclosure path. Notable changes are
in [`CHANGELOG.md`](CHANGELOG.md).

## License

[MIT](LICENSE) — see file for full text. Not an official SaldeoSMART/BrainShare
product.
