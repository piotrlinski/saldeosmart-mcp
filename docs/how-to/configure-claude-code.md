# Configure Claude Code

The Claude Code CLI registers MCP servers via the `claude mcp add` command.
Pick Docker or `uvx`.

## Docker

```bash
claude mcp add saldeosmart -- \
    docker run --rm -i \
        -e SALDEO_USERNAME=your-login \
        -e SALDEO_API_TOKEN=your-token \
        saldeosmart-mcp:latest
```

## uvx

```bash
claude mcp add saldeosmart -- \
    uvx --from git+https://github.com/piotrlinski/saldeosmart-mcp \
    saldeosmart-mcp \
    --username your-login \
    --api-token your-token
```

## Verify

Inside any Claude Code session:

```text
/mcp
```

The output should list `saldeosmart` along with its tool count. If it isn't
there, run `claude mcp list` to confirm registration scope (user/project/local).

## Scope

`claude mcp add` accepts `--scope user|project|local` to control where the
registration lives. For sensitive accounting credentials, prefer
`--scope user` (the default) over `project` so the token doesn't leak into a
shared repo's `.claude/`.

## Troubleshooting

??? failure "`/mcp` shows the server but tools are empty"
    The MCP handshake succeeded but `tools/list` failed. Tail
    `~/.claude/logs/mcp-server-saldeosmart.log` (or check
    `claude mcp logs saldeosmart`) — almost always a credential or
    network problem. See [Debug authentication](debug-auth.md).

??? info "Removing the server"
    ```bash
    claude mcp remove saldeosmart
    ```
