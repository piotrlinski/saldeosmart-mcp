"""Verify every ``@mcp.tool`` has a rendered page in the built site.

Run after ``mkdocs build`` (or as a CI gate) to catch the case where a
new tool was added but the catalog generator silently dropped it (or
the gen-files plugin output didn't make it into the navigation).

Usage::

    uv run python scripts/check_tool_coverage.py site/

Exit codes:
    0 — every tool has a rendered HTML page somewhere under
        ``<site>/reference/tools/<domain>/`` whose source contains the
        tool's qualified name.
    1 — at least one tool is missing or the site directory is malformed.
"""

from __future__ import annotations

import importlib
import inspect
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = REPO_ROOT / "src"

# Domains in the same order as docs/reference/tools/ subdirectories.
DOMAINS = (
    "documents",
    "invoices",
    "companies",
    "contractors",
    "catalog",
    "dimensions",
    "bank",
    "personnel",
    "financial_balance",
    "accounting_close",
)


def _ensure_src_on_path() -> None:
    p = str(SRC_PATH)
    if p not in sys.path:
        sys.path.insert(0, p)


def _collect_tools() -> dict[str, list[str]]:
    """Walk tools modules and return ``{domain: [tool_name, ...]}``."""
    _ensure_src_on_path()
    out: dict[str, list[str]] = {}
    for domain in DOMAINS:
        module = importlib.import_module(f"saldeosmart_mcp.tools.{domain}")
        names: list[str] = []
        for name in sorted(getattr(module, "__all__", []) or dir(module)):
            if name.startswith("_"):
                continue
            obj = getattr(module, name, None)
            if not callable(obj):
                continue
            if getattr(obj, "__module__", "") != module.__name__:
                continue
            if not inspect.isfunction(inspect.unwrap(obj)):
                continue
            names.append(name)
        out[domain] = names
    return out


def _site_text(site_dir: Path, domain: str) -> str | None:
    """Find the rendered page for ``domain`` under ``site/reference/tools/``."""
    candidates = [
        site_dir / "reference" / "tools" / domain / "index.html",
        site_dir / "reference" / "tools" / f"{domain}.html",
    ]
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0]} <site-dir>", file=sys.stderr)
        return 2
    site_dir = Path(argv[1]).resolve()
    if not site_dir.is_dir():
        print(f"::error::site directory not found: {site_dir}", file=sys.stderr)
        return 1

    catalog = _collect_tools()
    missing: list[tuple[str, str]] = []
    for domain, tools in catalog.items():
        if not tools:
            continue
        page_text = _site_text(site_dir, domain)
        if page_text is None:
            for tool in tools:
                missing.append((domain, tool))
            continue
        for tool in tools:
            # mkdocstrings renders the qualified path as an anchor; check
            # for any case-insensitive occurrence to tolerate minor changes.
            pattern = re.compile(rf"\b{re.escape(tool)}\b")
            if not pattern.search(page_text):
                missing.append((domain, tool))

    total = sum(len(t) for t in catalog.values())
    if missing:
        print(f"::error::{len(missing)}/{total} tools missing from rendered docs:", file=sys.stderr)
        for domain, tool in missing:
            print(f"  - {domain}: {tool}", file=sys.stderr)
        return 1

    print(f"OK: every tool ({total} across {sum(1 for v in catalog.values() if v)} domains) is rendered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
