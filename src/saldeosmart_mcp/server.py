"""Entrypoint for the SaldeoSMART MCP server.

Kept at the top level — and intentionally tiny — so that the
console-script declared in ``pyproject.toml``
(``saldeosmart-mcp = saldeosmart_mcp.server:main``) keeps pointing at the
same place it always has.

All the actual logic — tool definitions, request signing, response
parsing, models — lives in the submodules. ``main()`` does four things:
parse optional CLI overrides, configure file logging, import ``tools``
(which registers every tool against the shared ``mcp`` instance), and run
the FastMCP loop on stdio.

Credentials can be supplied via environment variables (``SALDEO_USERNAME``,
``SALDEO_API_TOKEN``, ``SALDEO_BASE_URL``) or the equivalent CLI flags
(``--username``, ``--api-token``, ``--base-url``). CLI flags win when both
are set — useful for MCP-client launch configs that prefer args to env.
"""

from __future__ import annotations

import argparse
import logging
import os

# Importing this module is what triggers @mcp.tool registration. Keep the
# import here (not at function call time) so the tools are discoverable
# even from `python -c "from saldeosmart_mcp.tools import mcp; ..."`.
from . import tools as _tools  # noqa: F401  — side-effect import
from .logging import setup_logging
from .tools._runtime import close_client, get_client, mcp

logger = logging.getLogger(__name__)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="saldeosmart-mcp",
        description=(
            "MCP server for the SaldeoSMART REST API. "
            "Speaks MCP over stdio; works with any MCP-aware client."
        ),
    )
    parser.add_argument(
        "--username",
        help="SaldeoSMART username (overrides $SALDEO_USERNAME).",
    )
    parser.add_argument(
        "--api-token",
        help="SaldeoSMART API token (overrides $SALDEO_API_TOKEN).",
    )
    parser.add_argument(
        "--base-url",
        help="SaldeoSMART base URL (overrides $SALDEO_BASE_URL). "
        "Default: https://saldeo.brainshare.pl",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Console-script entrypoint."""
    args = _build_arg_parser().parse_args(argv)
    # CLI flags win over env vars by overwriting the env entry before
    # SaldeoConfig is constructed. Pydantic-settings reads from os.environ.
    if args.username:
        os.environ["SALDEO_USERNAME"] = args.username
    if args.api_token:
        os.environ["SALDEO_API_TOKEN"] = args.api_token
    if args.base_url:
        os.environ["SALDEO_BASE_URL"] = args.base_url

    log_file = setup_logging()
    logger.info("SaldeoSMART MCP server starting; logs at %s", log_file)
    # Fail fast on missing/invalid credentials instead of surfacing the
    # error mid-conversation on the first tool call. Warms the shared client
    # too, so the first tool call doesn't pay the connection-pool setup cost.
    try:
        get_client()
    except RuntimeError as e:
        logger.error("Startup aborted: %s", e)
        raise
    try:
        mcp.run()  # stdio transport — what MCP clients expect
    finally:
        close_client()


if __name__ == "__main__":
    main()
