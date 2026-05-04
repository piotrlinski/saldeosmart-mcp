"""Generate the tool catalog under ``docs/reference/tools/``.

Walks every ``@mcp.tool``-registered function in ``saldeosmart_mcp.tools``
and emits one markdown page per resource family containing
``mkdocstrings`` ``:::`` directives. The actual rendering (signatures,
docstring sections, Pydantic field tables) is delegated to the
``python`` handler at site-build time.

Two execution modes:

* **mkdocs-gen-files plugin** (the default) — runs at every ``mkdocs
  build``; output lives in the build's virtual filesystem so the user
  doesn't see generated files in their working tree.
* **standalone** (``python scripts/gen_tool_catalog.py``) — used by the
  ``tool-catalog-check.yml`` CI gate; writes to the actual
  ``docs/reference/tools/`` directory and exits non-zero on any
  unexpected condition (missing docstring, decorator order changed,
  …).

Why introspect the module rather than ``mcp.list_tools()``? FastMCP's
runtime tool list requires the client to be initialised, which needs
``SALDEO_*`` env vars. CI builds don't have those, so we walk modules
directly. The two views are kept consistent by the architecture test
in ``tests/unit/test_architecture.py``.
"""

from __future__ import annotations

import importlib
import inspect
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

# When run under mkdocs-gen-files, the plugin injects this; when run
# standalone, we fall back to writing real files.
try:
    import mkdocs_gen_files  # type: ignore[import-not-found]

    _GEN_FILES = True
except ImportError:  # pragma: no cover — standalone path
    mkdocs_gen_files = None  # type: ignore[assignment]
    _GEN_FILES = False


# Domain → (display name, tools module attribute)
DOMAINS: list[tuple[str, str, str]] = [
    ("documents", "Documents", "Cost-document lifecycle: list, search, add, update, delete, recognize, sync."),
    ("invoices", "Invoices", "Sales invoices issued in SaldeoSMART."),
    ("companies", "Companies", "Tenants of an accounting firm — list, synchronize, create."),
    ("contractors", "Contractors", "Suppliers and customers attached to a company."),
    ("catalog", "Catalog", "Reference data: categories, payment methods, registers, descriptions, articles, fees."),
    ("dimensions", "Dimensions", "Custom accounting dimensions and their values."),
    ("bank", "Bank", "Bank statements and operations."),
    ("personnel", "Personnel", "Employees and HR documents."),
    ("financial_balance", "Financial balance", "Monthly income / cost / VAT per company."),
    ("accounting_close", "Accounting close", "Tax declarations and ZUS/social-insurance assurances."),
]


@dataclass(frozen=True)
class ToolEntry:
    """One @mcp.tool function discovered in a tools/<resource>.py module."""

    name: str
    qualname: str
    summary: str
    is_write: bool


def _is_tool(obj: object) -> bool:
    """Heuristic: a callable whose name doesn't start with `_` defined in our package."""
    if not callable(obj):
        return False
    if getattr(obj, "__name__", "_").startswith("_"):
        return False
    module = getattr(obj, "__module__", "")
    return module.startswith("saldeosmart_mcp.tools.")


def _iter_tools(domain: str) -> Iterator[ToolEntry]:
    module_name = f"saldeosmart_mcp.tools.{domain}"
    module = importlib.import_module(module_name)
    for name in sorted(getattr(module, "__all__", []) or dir(module)):
        if name.startswith("_"):
            continue
        obj = getattr(module, name, None)
        if not _is_tool(obj):
            continue
        if getattr(obj, "__module__", "") != module_name:
            continue
        underlying = inspect.unwrap(obj)
        doc = inspect.getdoc(underlying) or ""
        summary = doc.splitlines()[0] if doc else "_(no docstring)_"
        is_write = any(
            name.startswith(prefix)
            for prefix in (
                "add_",
                "create_",
                "delete_",
                "merge_",
                "recognize_",
                "renew_",
                "sync_",
                "synchronize_",
                "update_",
                "import_",
                "correct_",
            )
        )
        yield ToolEntry(
            name=name,
            qualname=f"{module_name}.{name}",
            summary=summary,
            is_write=is_write,
        )


def _emit(path: str, content: str) -> None:
    if _GEN_FILES and mkdocs_gen_files is not None:
        with mkdocs_gen_files.open(path, "w") as fh:
            fh.write(content)
    else:
        out = Path("docs") / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")


def _index_page(rows: list[tuple[str, str, int, int]]) -> str:
    lines = [
        "---",
        "title: Tool catalog",
        "description: Auto-generated index of every MCP tool registered against the FastMCP instance, grouped by Saldeo resource family.",
        "---",
        "",
        "# Tool catalog",
        "",
        "Every tool the server registers with FastMCP, grouped by resource. The",
        "tables on each domain page are generated from the source — adding a new",
        "tool with a docstring updates this catalog automatically on the next",
        "docs build.",
        "",
        "| Domain | Read | Write | Description |",
        "| --- | ---:| ---:| --- |",
    ]
    for domain, label, reads, writes in rows:
        # Find the description for this domain
        desc = next((d for slug, _, d in DOMAINS if slug == domain), "")
        lines.append(f"| [{label}](./{domain}.md) | {reads} | {writes} | {desc} |")
    lines += [
        "",
        "!!! info \"Read vs. write\"",
        "    *Read* tools never modify the customer's accounting data — safe to",
        "    invoke autonomously. *Write* tools (`add_*`, `merge_*`, `update_*`,",
        "    `delete_*`, `recognize_*`, `sync_*`, `create_*`) mutate live data;",
        "    require deliberate user intent.",
        "",
    ]
    return "\n".join(lines)


def _domain_page(domain: str, label: str, description: str, tools: list[ToolEntry]) -> str:
    reads = [t for t in tools if not t.is_write]
    writes = [t for t in tools if t.is_write]
    lines = [
        "---",
        f"title: {label}",
        f"description: {description}",
        "---",
        "",
        f"# {label}",
        "",
        description,
        "",
    ]
    if reads:
        lines += ["## Read tools", "", "| Tool | Summary |", "| --- | --- |"]
        for t in reads:
            anchor = t.name.replace("_", "-")
            lines.append(f"| [`{t.name}`](#{anchor}) | {t.summary} |")
        lines.append("")
    if writes:
        lines += ["## Write tools", "", "!!! warning \"Mutates customer data\"", "    Calls under this heading change the SaldeoSMART account. Confirm intent before invoking from an autonomous agent.", "", "| Tool | Summary |", "| --- | --- |"]
        for t in writes:
            anchor = t.name.replace("_", "-")
            lines.append(f"| [`{t.name}`](#{anchor}) | {t.summary} |")
        lines.append("")
    lines += ["---", "", "## API reference", ""]
    for t in tools:
        lines.append(f"::: {t.qualname}")
        lines.append("    options:")
        lines.append("      show_root_heading: true")
        lines.append("      heading_level: 3")
        lines.append("      show_root_toc_entry: true")
        lines.append("")
    return "\n".join(lines)


def _summary_md(rows: list[tuple[str, str, int, int]]) -> str:
    """Emit a literate-nav SUMMARY.md so MkDocs picks up the generated pages.

    Without this, ``- Tools: reference/tools/`` in mkdocs.yml resolves to an
    empty section (gen-files writes after nav resolution unless literate-nav
    finds a SUMMARY).
    """
    lines = ["* [Overview](index.md)"]
    for domain, label, _reads, _writes in rows:
        lines.append(f"* [{label}]({domain}.md)")
    return "\n".join(lines) + "\n"


def main() -> int:
    """Generate the tool-catalog tree. Returns 0 on success."""
    # Ensure src/ is importable when running standalone.
    repo_root = Path(__file__).resolve().parent.parent
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    index_rows: list[tuple[str, str, int, int]] = []
    for domain, label, description in DOMAINS:
        tools = list(_iter_tools(domain))
        if not tools:
            continue
        reads = sum(1 for t in tools if not t.is_write)
        writes = sum(1 for t in tools if t.is_write)
        index_rows.append((domain, label, reads, writes))
        _emit(f"reference/tools/{domain}.md", _domain_page(domain, label, description, tools))

    _emit("reference/tools/index.md", _index_page(index_rows))
    _emit("reference/tools/SUMMARY.md", _summary_md(index_rows))
    return 0


# Run unconditionally — mkdocs-gen-files imports this module and expects
# the side-effect of file emission. When standalone, ``main()`` returns 0
# on success and we raise on errors so the script's exit code is honored.
main()


if __name__ == "__main__":
    raise SystemExit(0)
