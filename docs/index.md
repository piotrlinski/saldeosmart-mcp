---
title: SaldeoSMART MCP
description: Model Context Protocol server for SaldeoSMART — read and modify accounting data from any MCP-aware AI client.
hide:
  - navigation
---

# SaldeoSMART MCP

[![CI](https://github.com/piotrlinski/saldeosmart-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/piotrlinski/saldeosmart-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/piotrlinski/saldeosmart-mcp/blob/master/LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-2a6db2.svg)](https://mypy-lang.org/)

A [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes
the [SaldeoSMART](https://www.saldeosmart.pl/) REST API as a set of typed,
LLM-friendly tools. Read documents, invoices, contractors, employees, bank
statements; create, update, merge, and synchronize accounting records — from
any MCP-aware client (Claude Desktop, Claude Code, Cursor, Zed, MCP Inspector,
or your own SDK harness).

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Quickstart**

    ---

    Run the server in Docker, point Claude Desktop at it, and make your first
    tool call in five minutes.

    [:octicons-arrow-right-24: Get started](tutorials/quickstart.md)

-   :material-book-open-variant:{ .lg .middle } **How-to guides**

    ---

    Install with `uvx` or Docker, configure each MCP client, debug
    authentication, add a new tool wrapping a Saldeo endpoint.

    [:octicons-arrow-right-24: Browse guides](how-to/index.md)

-   :material-api:{ .lg .middle } **Reference**

    ---

    Auto-generated catalog of every MCP tool, every input/output model, error
    codes, configuration, and the Saldeo API-version matrix.

    [:octicons-arrow-right-24: API reference](reference/index.md)

-   :material-school:{ .lg .middle } **Explanation**

    ---

    Why FastMCP over a custom transport, how request signing works, the
    threading model, and the security posture.

    [:octicons-arrow-right-24: Concepts](explanation/index.md)

</div>

## Why this exists

Accounting firms and their clients spend a lot of time on plumbing — moving
documents, reconciling contractors, tagging dimensions, syncing tax
declarations. SaldeoSMART has a comprehensive REST API for all of it, but
wiring an LLM to that API by hand is tedious and error-prone (signed requests,
gzip+base64 XML payloads, per-item batch errors). This server is the wiring
done once, well: every documented endpoint is exposed as a typed MCP tool
with a docstring an LLM can act on.

## Highlights

- :material-tools: **43 tools** — every documented SaldeoSMART REST endpoint, grouped by domain.
- :material-shield-lock: **Privacy-first** — `SecretStr` tokens, URL redaction in logs, single-flight request lock.
- :material-test-tube: **Strict typing** — Pydantic v2 models for every input/output, mypy-strict CI.
- :material-translate: **Polski + English** — full bilingual documentation (this site).
- :material-source-branch: **MIT-licensed**, not affiliated with SaldeoSMART/BrainShare.

## At a glance

```bash
# Run with Docker
docker run --rm -i \
  -e SALDEO_USERNAME=your-login \
  -e SALDEO_API_TOKEN=your-token \
  ghcr.io/piotrlinski/saldeosmart-mcp:latest

# Or via uvx (no Docker daemon)
uvx saldeosmart-mcp \
  --username your-login \
  --api-token your-token
```

Then point your MCP client at the command above. See
[Configure Claude Desktop](how-to/configure-claude-desktop.md) for a complete
config snippet.

!!! warning "Heads-up — write tools mutate live accounting data"
    Every `merge_*`, `add_*`, `update_*`, `delete_*`, `recognize_*`, and
    `sync_*` tool changes data on the customer's account. Read the
    [tool catalog](reference/tools/index.md) before letting an agent
    autonomously call write tools.
