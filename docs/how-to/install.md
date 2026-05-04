# Install

Three supported transports, pick whichever fits your setup. All three give
you the same behavior — they differ only in how the runtime is provisioned.

=== "Docker"

    Best for shared/reproducible deployments and the only way to get the
    sandboxed unprivileged-user runtime out of the box.

    ```bash
    git clone https://github.com/piotrlinski/saldeosmart-mcp.git
    cd saldeosmart-mcp
    make build
    ```

    The image is two-stage (`docker/Dockerfile`):

    1. **builder** (`ghcr.io/astral-sh/uv:python3.12-bookworm-slim`) — `uv sync --frozen --no-dev`, bytecode-compile.
    2. **runtime** (`python:3.12-slim-bookworm`) — copy prebuilt `.venv`, unprivileged `mcp` user, `ENTRYPOINT ["saldeosmart-mcp"]`.

    Final size: ~234 MB. Logs default to `/var/log/saldeosmart/saldeosmart.log` (rotated daily, 7 days retained); mount a volume to persist them.

=== "uvx"

    Best for local development and ad-hoc usage. No Docker daemon, no clone.

    ```bash
    # From PyPI (once published):
    uvx saldeosmart-mcp --username your-login --api-token your-token

    # From source today:
    uvx --from git+https://github.com/piotrlinski/saldeosmart-mcp \
        saldeosmart-mcp --username your-login --api-token your-token
    ```

    `uvx` is `uv tool run`. It resolves the package into an isolated venv on
    first run and caches it. Requires `uv ≥ 0.4`.

=== "pip"

    Best when you have an existing Python environment you want the server
    to live in (e.g. inside a CI image).

    ```bash
    pip install saldeosmart-mcp        # once on PyPI
    saldeosmart-mcp --username your-login --api-token your-token
    ```

    Or from source:

    ```bash
    pip install git+https://github.com/piotrlinski/saldeosmart-mcp
    ```

## Verify the install

```bash
saldeosmart-mcp --help
```

You should see the argparse help with `--username`, `--api-token`, and
`--base-url` flags. If any arg is missing the env-var fallback fires
(`SALDEO_USERNAME`, `SALDEO_API_TOKEN`, `SALDEO_BASE_URL`).

## Next

- Pick a client and configure it: [Claude Desktop](configure-claude-desktop.md), [Claude Code](configure-claude-code.md), [Cursor](configure-cursor.md), [other](configure-other-clients.md).
- Run a [smoke test](run-smoke-test.md) against your account before pointing an LLM at it.
