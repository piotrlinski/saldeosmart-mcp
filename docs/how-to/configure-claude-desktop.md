# Configure Claude Desktop

Claude Desktop launches MCP servers as subprocesses listed in
`claude_desktop_config.json`. Pick **one** of Docker or `uvx` below.

## Find the config file

| OS | Path |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

If the file doesn't exist yet, create it with `{}` as the contents.

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

Restart Claude Desktop after editing.

## Keeping credentials out of the config file

Drop the token into a `chmod 600` env file and have Docker load it:

```bash
# ~/saldeosmart.env (chmod 600)
SALDEO_USERNAME=your-login
SALDEO_API_TOKEN=your-token
```

```json
"args": [
  "run", "--rm", "-i",
  "--env-file", "/Users/you/saldeosmart.env",
  "saldeosmart-mcp:latest"
]
```

## Troubleshooting

??? failure "command not found: docker / uvx"
    Claude Desktop launches MCP servers without inheriting your shell
    `PATH`. Run `which docker` (or `which uvx`) and use the absolute path
    in `"command"`.

??? failure "Tools list shows zero saldeosmart entries"
    Tail `~/Library/Logs/Claude/mcp-server-saldeosmart.log` (macOS path) —
    the server logs config errors before the MCP handshake. The most
    common cause is `SALDEO_USERNAME` or `SALDEO_API_TOKEN` missing.

See [Debug authentication](debug-auth.md) for deeper diagnostics.
