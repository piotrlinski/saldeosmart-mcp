# Configure other MCP clients

Any MCP-aware client works — the server speaks the protocol over stdio. The
same Docker or `uvx` launch command from
[Configure Claude Desktop](configure-claude-desktop.md) plugs into:

## Zed

`~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "saldeosmart": {
      "command": {
        "path": "uvx",
        "args": [
          "--from", "git+https://github.com/piotrlinski/saldeosmart-mcp",
          "saldeosmart-mcp",
          "--username", "your-login",
          "--api-token", "your-token"
        ]
      },
      "settings": {}
    }
  }
}
```

## MCP Inspector

The official debugger from
[modelcontextprotocol/inspector](https://github.com/modelcontextprotocol/inspector).
The repo's `Makefile` ships a one-liner:

```bash
export SALDEO_USERNAME=your-login
export SALDEO_API_TOKEN=your-token
make inspector
```

Equivalent to:

```bash
npx @modelcontextprotocol/inspector \
    docker run --rm -i \
        -e SALDEO_USERNAME -e SALDEO_API_TOKEN \
        saldeosmart-mcp:latest
```

The Inspector lets you call any tool with hand-crafted arguments and inspect
both the request and response — great for debugging input shapes before
wiring an LLM up.

## Continue.dev

`.continue/config.json`:

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "transport": {
          "type": "stdio",
          "command": "uvx",
          "args": [
            "--from", "git+https://github.com/piotrlinski/saldeosmart-mcp",
            "saldeosmart-mcp",
            "--username", "your-login",
            "--api-token", "your-token"
          ]
        }
      }
    ]
  }
}
```

## Custom SDK

If you're calling the server from your own code, the
[MCP SDKs](https://modelcontextprotocol.io/sdks) (Python, TypeScript, Go,
Rust, …) all support stdio transport. Spawn the same `docker run` or `uvx`
command and connect a stdio transport to its stdin/stdout pair.
