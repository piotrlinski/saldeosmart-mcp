"""Entrypoint for the SaldeoSMART MCP server.

Kept at the top level — and intentionally tiny — so that the
console-script declared in ``pyproject.toml``
(``saldeosmart-mcp = saldeosmart_mcp.server:main``) keeps pointing at the
same place it always has.

All the actual logic — tool definitions, request signing, response
parsing, models — lives in the submodules. ``main()`` does four things:
parse CLI args (with env-var fallbacks), configure file logging, import
``tools`` (which registers every tool against the shared ``mcp``
instance), and run the FastMCP loop on stdio.

Credentials can be supplied two ways and the precedence is straightforward:
each argparse flag falls back to its corresponding ``SALDEO_*`` env var,
so an explicit ``--username`` wins, an unset flag picks up
``$SALDEO_USERNAME``, and if neither is set the config validation
surfaces a "missing credentials" error.
"""

from __future__ import annotations

import argparse
import logging
import os

from pydantic import SecretStr, ValidationError

from . import tools as _tools  # noqa: F401  — side-effect import (registers @mcp.tool)
from .config import DEFAULT_BASE_URL, SaldeoConfig
from .logging import setup_logging
from .tools._runtime import close_client, init_client, mcp

logger = logging.getLogger(__name__)


def _env_default(name: str, default: str | None = None) -> str | None:
    """Read ``$SALDEO_<NAME>`` for argparse fallback defaults."""
    return os.environ.get(f"SALDEO_{name}", default)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="saldeosmart-mcp",
        description=(
            "MCP server for the SaldeoSMART REST API. "
            "Speaks MCP over stdio; works with any MCP-aware client."
        ),
    )
    # default=_env_default(...) makes each flag fall back to its env var
    # without argparse leaking the value via --help (defaults are not shown
    # unless ArgumentDefaultsHelpFormatter is used, which we deliberately don't).
    parser.add_argument(
        "--username",
        default=_env_default("USERNAME"),
        help="SaldeoSMART username. Falls back to $SALDEO_USERNAME.",
    )
    parser.add_argument(
        "--api-token",
        default=_env_default("API_TOKEN"),
        help="SaldeoSMART API token. Falls back to $SALDEO_API_TOKEN.",
    )
    parser.add_argument(
        "--base-url",
        default=_env_default("BASE_URL", DEFAULT_BASE_URL),
        help=(f"SaldeoSMART base URL. Falls back to $SALDEO_BASE_URL, then to {DEFAULT_BASE_URL}."),
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Console-script entrypoint."""
    args = _build_arg_parser().parse_args(argv)

    log_file = setup_logging()
    logger.info("SaldeoSMART MCP server starting; logs at %s", log_file)
    # Fail fast on missing/invalid credentials instead of surfacing the
    # error mid-conversation on the first tool call. Warms the shared client
    # too, so the first tool call doesn't pay the connection-pool setup cost.
    try:
        config = SaldeoConfig(
            username=args.username,
            api_token=SecretStr(args.api_token) if args.api_token else None,  # type: ignore[arg-type]
            base_url=args.base_url,
        )
    except ValidationError as e:
        missing = ", ".join(
            f"--{str(err['loc'][0]).replace('_', '-')}" if err.get("loc") else "--?"
            for err in e.errors()
        )
        logger.error("Startup aborted: missing credentials (%s)", missing)
        raise RuntimeError(
            f"Missing SaldeoSMART credentials ({missing}). Pass them as "
            f"CLI flags or set the corresponding SALDEO_* env vars. The API "
            f"token is generated in SaldeoSMART under Settings → API."
        ) from e
    init_client(config)

    try:
        mcp.run()  # stdio transport — what MCP clients expect
    finally:
        close_client()


if __name__ == "__main__":
    main()
