# Quickstart

In five minutes, you'll have the SaldeoSMART MCP server running in Docker
and your Claude Desktop client calling its tools.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 24, daemon running.
- A SaldeoSMART account with API access enabled. The token lives in
  **Konfiguracja → Konto → API → Generuj token**. On some plans you have to
  email `api@saldeosmart.pl` first to enable API access.
- [Claude Desktop](https://claude.ai/download) installed.

!!! info "Only accounting-firm users can generate tokens"
    The API token portal is gated to *biuro rachunkowe* users. Clients of an
    accounting firm cannot generate one — ask the firm to provision API
    access on the firm's account.

## 1. Build the image

```bash
git clone https://github.com/piotrlinski/saldeosmart-mcp.git
cd saldeosmart-mcp
make build
```

This runs the two-stage Dockerfile in `docker/Dockerfile`:

1. **builder** — `uv sync --frozen --no-dev` against `uv.lock`, bytecode-compiled.
2. **runtime** — Python 3.12-slim, unprivileged `mcp` user, ~234 MB.

## 2. Configure Claude Desktop

Open `claude_desktop_config.json`:

- **macOS** — `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows** — `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux** — `~/.config/Claude/claude_desktop_config.json`

Add a `saldeosmart` entry under `mcpServers`:

```json
{
  "mcpServers": {
    "saldeosmart": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "SALDEO_USERNAME=your-login",
        "-e", "SALDEO_API_TOKEN=your-token",
        "saldeosmart-mcp:latest"
      ]
    }
  }
}
```

Restart Claude Desktop.

## 3. Verify

In a new conversation, ask Claude:

> List the SaldeoSMART tools you have access to.

You should see 43 tools grouped by resource: `list_companies`,
`list_documents`, `merge_contractors`, etc.

## Next steps

- [**Your first tool call**](first-tool-call.md) — call a real read endpoint.
- [Configure other clients](../how-to/configure-other-clients.md) — Cursor,
  Claude Code, Zed, MCP Inspector.
- [Tool catalog](../reference/tools/index.md) — every tool, every parameter.

## Troubleshooting

??? failure "Claude Desktop says `command not found: docker`"
    Replace `"command": "docker"` with the absolute path from
    `which docker` (e.g. `/usr/local/bin/docker`). Claude Desktop launches
    MCP servers without inheriting your shell `PATH`.

??? failure "Tools list is empty"
    Check the log file — by default `/var/log/saldeosmart/saldeosmart.log`
    inside the container. The most common cause is a missing or rejected
    token. See [Debug authentication](../how-to/debug-auth.md).
