"""Enforce the LLM-facing tool-docstring contract.

Every ``@mcp.tool`` function in ``saldeosmart_mcp.tools.*`` must have a
docstring that contains:

1. A one-line summary on the first line, ≤ 100 characters.
2. The literal phrase ``Use this when`` (case-insensitive) somewhere in
   the body — disambiguates this tool from related tools so the LLM
   selecting between them gets a deterministic signal.
3. A Google-style ``Args:`` section, unless the function takes no
   arguments other than self/cls.
4. A ``Returns:`` section.

The contract is enforced both as a pre-commit hook (fast feedback) and
via the ``docs.yml`` CI gate (catches commits that bypass pre-commit).
"""

from __future__ import annotations

import importlib
import inspect
import sys
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = REPO_ROOT / "src"

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


def _iter_tools() -> Iterator[tuple[str, str, object]]:
    """Yield ``(module, name, function)`` for every public function in a tools module."""
    _ensure_src_on_path()
    for domain in DOMAINS:
        module_name = f"saldeosmart_mcp.tools.{domain}"
        module = importlib.import_module(module_name)
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
            yield module_name, name, obj


def _violations(module_name: str, tool_name: str, fn: object) -> list[str]:
    """Return a list of contract violations (empty if compliant)."""
    underlying = inspect.unwrap(fn)  # type: ignore[arg-type]
    doc = inspect.getdoc(underlying) or ""
    if not doc:
        return ["missing docstring"]

    out: list[str] = []
    lines = doc.splitlines()
    summary = lines[0] if lines else ""
    if len(summary) > 100:
        out.append(f"first-line summary > 100 chars (got {len(summary)})")

    if "use this when" not in doc.lower():
        out.append("missing 'Use this when …' discriminator")

    sig = inspect.signature(underlying)  # type: ignore[arg-type]
    has_args = any(p.name not in ("self", "cls") for p in sig.parameters.values())
    if has_args and not _has_section(doc, "Args"):
        out.append("missing 'Args:' section")

    if not _has_section(doc, "Returns"):
        out.append("missing 'Returns:' section")
    return out


def _has_section(doc: str, name: str) -> bool:
    needle = f"{name}:"
    for line in doc.splitlines():
        if line.strip() == needle:
            return True
    return False


def main() -> int:
    failures: list[tuple[str, str, list[str]]] = []
    total = 0
    for module_name, tool_name, fn in _iter_tools():
        total += 1
        viol = _violations(module_name, tool_name, fn)
        if viol:
            failures.append((module_name, tool_name, viol))

    if failures:
        print(f"::error::Tool docstring contract violations ({len(failures)}/{total} tools):")
        for module_name, tool_name, viol in failures:
            print(f"  {module_name}.{tool_name}:")
            for v in viol:
                print(f"    - {v}")
        return 1

    print(f"OK: every tool ({total}) satisfies the docstring contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
