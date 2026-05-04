"""Generate ``docs/reference/api-versions.md``.

Reads the ``Final[str]`` constants from
``saldeosmart_mcp/tools/endpoints.py`` and renders a table mapping each
constant to its endpoint and the API version embedded in the URL.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = REPO_ROOT / "docs"
ENDPOINTS_PY = REPO_ROOT / "src" / "saldeosmart_mcp" / "tools" / "endpoints.py"

API_VERSION_RE = re.compile(r"^/api/xml/(\d+(?:\.\d+)*)/(.+)$")


def _emit(path: str, content: str) -> None:
    out = DOCS_ROOT / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")


def _parse_endpoints() -> list[tuple[str, str, str, str]]:
    """Return [(constant, endpoint, version, suffix)] sorted by version then path."""
    tree = ast.parse(ENDPOINTS_PY.read_text(encoding="utf-8"))
    out: list[tuple[str, str, str, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
            continue
        name = node.target.id
        endpoint = node.value.value
        m = API_VERSION_RE.match(endpoint)
        if not m:
            continue
        version, suffix = m.group(1), m.group(2)
        out.append((name, endpoint, version, suffix))
    # Sort by (version-as-tuple, suffix) so the table groups naturally.
    out.sort(key=lambda r: ([int(p) for p in r[2].split(".")], r[3]))
    return out


def _render() -> str:
    rows = _parse_endpoints()
    versions = sorted({v for _, _, v, _ in rows}, key=lambda s: [int(p) for p in s.split(".")])
    lines = [
        "---",
        "title: API versions",
        "description: Auto-generated mapping from each MCP tool's endpoint constant to the SaldeoSMART REST API version it targets.",
        "---",
        "",
        "# API versions",
        "",
        "SaldeoSMART versions endpoints independently — `document/list` is at",
        "2.12 while `document/import` is at 3.0. Every endpoint constant lives",
        "in `src/saldeosmart_mcp/tools/endpoints.py`, which is the **only**",
        "place in the codebase that knows API version numbers. Bumping a",
        "version is a one-line change there; see",
        "[How to bump a Saldeo API version](../how-to/bump-saldeo-api-version.md).",
        "",
        f"Total endpoints wrapped: **{len(rows)}** across **{len(versions)}** API versions.",
        "",
        "## By version",
        "",
    ]
    grouped: dict[str, list[tuple[str, str, str, str]]] = {}
    for row in rows:
        grouped.setdefault(row[2], []).append(row)
    for version in versions:
        lines += [
            f"### Version {version}",
            "",
            "| Constant | Endpoint |",
            "| --- | --- |",
        ]
        for name, endpoint, _, _ in grouped[version]:
            lines.append(f"| `{name}` | `{endpoint}` |")
        lines.append("")
    lines += [
        "## All endpoints",
        "",
        "| Constant | Version | Endpoint |",
        "| --- | --- | --- |",
    ]
    for name, endpoint, version, _ in sorted(rows, key=lambda r: r[0]):
        lines.append(f"| `{name}` | {version} | `{endpoint}` |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    _emit("reference/api-versions.md", _render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
