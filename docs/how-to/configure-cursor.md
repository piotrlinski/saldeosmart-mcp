# Configure Cursor

Cursor reads MCP servers from `~/.cursor/mcp.json` (global) or
`.cursor/mcp.json` (per-project). Pick Docker or `uvx`.

## uvx

```json
{
  "mcpServers": {
    "saldeosmart": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/piotrlinski/saldeosmart-mcp",
        "saldeosmart-mcp",
        "--username", "your-login",
        "--api-token", "your-token"
      ]
    }
  }
}
```

## Docker

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

## Reload

Open **Settings → Cursor Settings → MCP** and click **Reload** (or restart
Cursor). The server should appear with its 43 tools.

## Per-project vs global

A per-project `.cursor/mcp.json` overrides the global one for that workspace.
Useful when different clients have different SaldeoSMART accounts; commit a
`.cursor/mcp.json.example` to the repo and `.gitignore` the real file.

## Troubleshooting

??? failure "Cursor reports the MCP server failed to start"
    Click **View logs** in the MCP settings panel; Cursor surfaces the
    server's stderr verbatim. The server logs config errors there before
    the MCP handshake fires. See [Debug authentication](debug-auth.md).
