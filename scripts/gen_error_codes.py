"""Generate ``docs/reference/error-codes.md``.

Sources, in priority order:

1. Synthetic codes parsed from ``saldeosmart_mcp.errors`` (the
   ``ERROR_*`` constants and their docstrings).
2. Saldeo-issued codes loaded from
   ``docs/_data/error_meanings.yaml`` (hand-curated; the previous
   ``ERROR_CODES.md`` content lives here, structured).
3. Best-effort enrichment from ``<ERROR_CODE>`` elements found in
   ``.temp/api-html-mirror/**/*_response.xml`` (only used when the
   mirror is locally present; CI builds may not have it).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = REPO_ROOT / "docs"
ERRORS_PY = REPO_ROOT / "src" / "saldeosmart_mcp" / "errors.py"
MEANINGS_YAML = DOCS_ROOT / "_data" / "error_meanings.yaml"


def _emit(path: str, content: str) -> None:
    out = DOCS_ROOT / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")


def _parse_synthetic_codes() -> list[tuple[str, str, str]]:
    """Return [(constant_name, code_string, docstring)] parsed from errors.py.

    Pure AST parse — no import, so this works even if errors.py grows
    a side-effect import in the future.
    """
    tree = ast.parse(ERRORS_PY.read_text(encoding="utf-8"))
    out: list[tuple[str, str, str]] = []
    body = tree.body
    for i, node in enumerate(body):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        name = node.target.id
        if not name.startswith("ERROR_"):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
            continue
        code = node.value.value
        # Following statement may be a string-expression docstring for the constant.
        doc = ""
        if i + 1 < len(body):
            nxt = body[i + 1]
            if (
                isinstance(nxt, ast.Expr)
                and isinstance(nxt.value, ast.Constant)
                and isinstance(nxt.value.value, str)
            ):
                doc = nxt.value.value.strip()
        out.append((name, code, doc))
    return out


_YAML_LIST_HEADER = re.compile(r"^([A-Z0-9_]+):\s*$")


def _parse_yaml_meanings() -> dict[str, dict[str, str]]:
    """Tiny YAML subset parser — avoids pulling in PyYAML for one file.

    Expected shape::

        codes:
          "4401":
            meaning: ...
            recovery: ...

    Returns mapping of code → fields. Returns empty dict if the file is
    missing.
    """
    if not MEANINGS_YAML.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    current_code: str | None = None
    current_field: str | None = None
    with MEANINGS_YAML.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if indent == 0:
                # top-level key — only "codes:" is meaningful here.
                continue
            if indent == 2:
                # code key
                m = re.match(r'^"?([^":]+)"?:\s*$', stripped)
                if m:
                    current_code = m.group(1)
                    out[current_code] = {}
                    current_field = None
                continue
            if indent >= 4 and current_code is not None:
                m = re.match(r"^([a-zA-Z_][\w]*):\s*(.*)$", stripped)
                if m:
                    current_field = m.group(1)
                    value = m.group(2).strip().strip('"')
                    out[current_code][current_field] = value
    return out


def _render() -> str:
    synthetic = _parse_synthetic_codes()
    saldeo = _parse_yaml_meanings()
    lines = [
        "---",
        "title: Error codes",
        "description: Catalog of error codes the MCP server may surface in `ErrorResponse.error` — Saldeo-issued, synthetic, and per-item validation.",
        "---",
        "",
        "# Error codes",
        "",
        "Codes the MCP server may surface in `ErrorResponse.error`. Three classes:",
        "",
        "1. **SaldeoSMART-issued** — returned in `<ERROR_CODE>` from the API.",
        "2. **Synthetic** — minted by the client when a transport / parsing /",
        "   validation problem prevented the API call.",
        "3. **Per-item** — the envelope succeeded (`STATUS=OK`) but individual",
        "   batch items failed; one entry per failed item in",
        "   `ErrorResponse.details[]`.",
        "",
        "## SaldeoSMART-issued codes",
        "",
    ]
    if saldeo:
        lines += [
            "| Code | Meaning | Recovery |",
            "| --- | --- | --- |",
        ]
        for code in sorted(saldeo):
            entry = saldeo[code]
            meaning = entry.get("meaning", "—")
            recovery = entry.get("recovery", "—")
            lines.append(f"| `{code}` | {meaning} | {recovery} |")
    else:
        lines.append("_The hand-curated catalog at `docs/_data/error_meanings.yaml` is empty. Append entries as you encounter new Saldeo error codes._")
    lines += [
        "",
        "## Synthetic codes",
        "",
        "Defined in `src/saldeosmart_mcp/errors.py` and `src/saldeosmart_mcp/http/client.py`.",
        "",
        "| Code | Constant | Meaning |",
        "| --- | --- | --- |",
        "| `HTTP_<status>` | _(transport)_ | Non-2xx HTTP status with no `<RESPONSE>` envelope. Status drives the suffix (e.g. `HTTP_500`, `HTTP_403`). |",
        "| `PARSE_ERROR` | _(transport)_ | 2xx body wasn't valid XML — usually an HTML error page from a proxy or load balancer. First 500 chars in `message`. |",
        "| `UNKNOWN` | _(transport)_ | Envelope had `<STATUS>ERROR</STATUS>` but `<ERROR_CODE>` was empty. |",
    ]
    for name, code, doc in synthetic:
        meaning = doc.replace("|", "\\|") if doc else "—"
        lines.append(f"| `{code}` | `{name}` | {meaning} |")
    lines += [
        "",
        "## Per-item validation errors",
        "",
        "Batch operations (`*.merge`, `update_documents`, `import_documents`, …) succeed at the envelope level even when individual items fail. Each failed item is an entry in `ErrorResponse.details[]`:",
        "",
        "```json",
        "{",
        '  "error": "VALIDATION",',
        '  "message": "some items failed",',
        '  "details": [',
        '    {"status": "NOT_VALID", "path": "VAT_NUMBER", "message": "required field", "item_id": "2"}',
        "  ]",
        "}",
        "```",
        "",
        "The `path` field names the offending element from the request XML; use it to locate which field of which input model needs fixing. See `iter_item_errors` in `src/saldeosmart_mcp/errors.py` for the walker.",
        "",
        "## Authoritative source",
        "",
        "SaldeoSMART's official error-code list lives in their API documentation",
        "portal (the same place where the API token is generated). When in",
        "doubt, consult that — and append anything useful to",
        "[`docs/_data/error_meanings.yaml`](https://github.com/piotrlinski/saldeosmart-mcp/blob/master/docs/_data/error_meanings.yaml).",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    """Generate the error-codes reference page."""
    src_path = str(REPO_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    _emit("reference/error-codes.md", _render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
