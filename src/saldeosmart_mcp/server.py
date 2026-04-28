"""Entrypoint for the SaldeoSMART MCP server.

Kept at the top level — and intentionally tiny — so that the
console-script declared in ``pyproject.toml``
(``saldeosmart-mcp = saldeosmart_mcp.server:main``) keeps pointing at the
same place it always has.

All the actual logic — tool definitions, request signing, response
parsing, models — lives in the submodules. ``main()`` does just three
things: configure file logging, import ``tools`` (which registers every
tool against the shared ``mcp`` instance), and run the FastMCP loop on
stdio.
"""

from __future__ import annotations

import logging

# Importing this module is what triggers @mcp.tool registration. Keep the
# import here (not at function call time) so the tools are discoverable
# even from `python -c "from saldeosmart_mcp.tools import mcp; ..."`.
from . import tools as _tools  # noqa: F401  — side-effect import
from .logging import setup_logging
from .tools._runtime import mcp, reset_client_for_tests

logger = logging.getLogger(__name__)


def main() -> None:
    """Console-script entrypoint."""
    log_file = setup_logging()
    logger.info("SaldeoSMART MCP server starting; logs at %s", log_file)
    try:
        mcp.run()  # stdio transport — what Claude Desktop expects
    finally:
        reset_client_for_tests()


if __name__ == "__main__":
    main()
