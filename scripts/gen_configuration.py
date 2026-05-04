"""Generate ``docs/reference/configuration.md``.

Renders the env-var/CLI-flag matrix from ``SaldeoConfig`` (the
authoritative source) and the argparse help from ``server._build_arg_parser``.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import mkdocs_gen_files  # type: ignore[import-not-found]

    _GEN_FILES = True
except ImportError:  # pragma: no cover — standalone path
    mkdocs_gen_files = None  # type: ignore[assignment]
    _GEN_FILES = False


REPO_ROOT = Path(__file__).resolve().parent.parent


def _emit(path: str, content: str) -> None:
    if _GEN_FILES and mkdocs_gen_files is not None:
        with mkdocs_gen_files.open(path, "w") as fh:
            fh.write(content)
    else:
        out = REPO_ROOT / "docs" / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")


def _render() -> str:
    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    from saldeosmart_mcp.config import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, SaldeoConfig
    from saldeosmart_mcp.server import _build_arg_parser

    fields = SaldeoConfig.model_fields

    lines = [
        "---",
        "title: Configuration",
        "description: Environment variables and CLI flags that configure the SaldeoSMART MCP server.",
        "---",
        "",
        "# Configuration",
        "",
        "The server reads its configuration from CLI flags or environment",
        "variables. CLI flags win when both are set for the same field.",
        "",
        "## Settings",
        "",
        "| Env var | CLI flag | Required | Default | Notes |",
        "| --- | --- | --- | --- | --- |",
        f"| `SALDEO_USERNAME` | `--username` | yes | — | SaldeoSMART login (firm-portal user, not client). |",
        f"| `SALDEO_API_TOKEN` | `--api-token` | yes | — | 64-char token from **Konfiguracja → Konto → API**. Held as `SecretStr`. |",
        f"| `SALDEO_BASE_URL` | `--base-url` | no | `{DEFAULT_BASE_URL}` | Use `https://saldeo-test.brainshare.pl` for the test environment. |",
        f"| `SALDEO_TIMEOUT` | _(env only)_ | no | `{DEFAULT_TIMEOUT}` | httpx request timeout in seconds. |",
        "",
        "## Logging",
        "",
        "The server logs every request to a daily-rotated file (7 days retained).",
        "Configuration env vars (read by `setup_logging` in `src/saldeosmart_mcp/logging.py`):",
        "",
        "| Env var | Default | Notes |",
        "| --- | --- | --- |",
        "| `SALDEO_LOG_DIR` | `/var/log/saldeosmart` (Docker) or platform default | Directory for `saldeosmart.log`. |",
        "| `SALDEO_LOG_LEVEL` | `INFO` | Set to `DEBUG` to log full XML envelopes (still token-redacted). |",
        "",
        "## CLI help",
        "",
        "```text",
    ]
    parser = _build_arg_parser()
    lines.append(parser.format_help().rstrip())
    lines += [
        "```",
        "",
        "## SaldeoConfig fields",
        "",
        "Pydantic-Settings model defined in",
        "[`src/saldeosmart_mcp/config.py`](https://github.com/piotrlinski/saldeosmart-mcp/blob/master/src/saldeosmart_mcp/config.py).",
        "",
        "| Field | Type | Default | Constraints |",
        "| --- | --- | --- | --- |",
    ]
    for name, info in fields.items():
        annotation = getattr(info.annotation, "__name__", str(info.annotation))
        default = "—" if info.is_required() else repr(info.default)
        constraints = []
        for m in info.metadata:
            constraints.append(repr(m))
        constraint_str = ", ".join(constraints) or "—"
        lines.append(f"| `{name}` | `{annotation}` | {default} | {constraint_str} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    _emit("reference/configuration.md", _render())
    return 0


main()


if __name__ == "__main__":
    raise SystemExit(0)
