"""End-to-end smoke test: hit every MCP tool against the real SaldeoSMART API.

Loads SALDEO_USERNAME/SALDEO_API_TOKEN/SALDEO_BASE_URL from a `.env` file at the
repo root, then walks every @mcp.tool exported by `saldeosmart_mcp.server`,
printing pass/fail for each. Designed to surface which endpoints are broken
without needing an MCP client in the loop.

Run:
    uv run python scripts/smoke_test.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_env_file() -> None:
    """Tiny .env reader — avoids adding python-dotenv as a runtime dep.

    Recognises KEY=VALUE lines, skips comments/blank, strips one wrapping
    layer of quotes. Existing env vars win (so `SALDEO_BASE_URL=... uv run`
    still overrides what's in the file).
    """
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        print(f"!! no .env at {env_path}", file=sys.stderr)
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file()  # must precede the saldeosmart_mcp imports — they read env eagerly

from saldeosmart_mcp.models import (  # noqa: E402
    CompanyList,
    DocumentIdGroups,
    DocumentList,
    ErrorResponse,
    InvoiceIdGroups,
)
from saldeosmart_mcp.tools import (  # noqa: E402
    get_document_id_list,
    get_documents_by_id,
    get_invoice_id_list,
    get_invoices_by_id,
    list_bank_statements,
    list_companies,
    list_contractors,
    list_documents,
    list_employees,
    list_invoices,
    list_personnel_documents,
    list_recognized_documents,
    search_documents,
)

OK = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"

results: list[tuple[str, bool, str]] = []


def report(name: str, result: Any) -> Any:
    """Print one line per call, accumulate pass/fail for the summary."""
    if isinstance(result, ErrorResponse):
        line = f"  {FAIL} {name}: {result.error} — {result.message}"
        if result.http_status:
            line += f" (HTTP {result.http_status})"
        print(line)
        results.append((name, False, f"{result.error}: {result.message}"))
        return None
    detail = ""
    if hasattr(result, "count"):
        detail = f" — count={result.count}"
    print(f"  {OK} {name}: ok{detail}")
    results.append((name, True, f"ok{detail}"))
    return result


def main() -> int:
    print("=== SaldeoSMART MCP smoke test ===")
    print(f"base_url={os.environ.get('SALDEO_BASE_URL', '<default>')}")
    print(f"username={os.environ.get('SALDEO_USERNAME', '<missing>')}\n")

    print("[1] list_companies()")
    companies = report("list_companies", list_companies())
    program_id: str | None = None
    if isinstance(companies, CompanyList) and companies.companies:
        program_id = companies.companies[0].program_id
        print(f"     using company_program_id={program_id!r} "
              f"(of {companies.count} total)")

    if not program_id:
        print("\n!! no usable company_program_id — cannot exercise the rest.")
        return _summarize()

    print("\n[2] list_contractors")
    report("list_contractors", list_contractors(program_id))

    print("\n[3] list_documents (each policy)")
    docs_by_policy: dict[str, DocumentList | None] = {}
    for policy in ("LAST_10_DAYS", "LAST_10_DAYS_OCRED", "SALDEO"):
        result = list_documents(program_id, policy=policy)  # type: ignore[arg-type]
        docs_by_policy[policy] = (
            result if isinstance(result, DocumentList) else None
        )
        report(f"list_documents[{policy}]", result)

    print("\n[4] search_documents")
    sample_doc = next(
        (d for docs in docs_by_policy.values() if docs for d in docs.documents),
        None,
    )
    if sample_doc and sample_doc.document_id is not None:
        report(
            f"search_documents[document_id={sample_doc.document_id}]",
            search_documents(program_id, document_id=sample_doc.document_id),
        )
    if sample_doc and sample_doc.number:
        report(
            f"search_documents[number={sample_doc.number!r}]",
            search_documents(program_id, number=sample_doc.number),
        )
    if not sample_doc:
        print("     (no sample document found in any policy — skipping)")

    print("\n[5] list_invoices")
    report("list_invoices", list_invoices(program_id))

    print("\n[6] list_bank_statements")
    report("list_bank_statements", list_bank_statements(program_id))

    print("\n[7] list_employees / list_personnel_documents (Personnel module)")
    report("list_employees", list_employees(program_id))
    report(
        "list_personnel_documents[all]",
        list_personnel_documents(program_id),
    )

    print("\n[8] 3.0 paginated id-list / listbyid")
    from datetime import date as _date
    today = _date.today()
    doc_groups_result = get_document_id_list(program_id, year=today.year, month=today.month)
    doc_groups = report(
        f"get_document_id_list[{today.year}-{today.month}]",
        doc_groups_result,
    )
    if isinstance(doc_groups, DocumentIdGroups):
        # Pull a small slice of cost invoices to exercise listbyid.
        sample_ids = doc_groups.invoices_cost[:3]
        if sample_ids:
            report(
                f"get_documents_by_id[invoices_cost x{len(sample_ids)}]",
                get_documents_by_id(program_id, invoices_cost=sample_ids),
            )
        else:
            print("     (no document IDs in this folder — skipping listbyid)")

    inv_groups_result = get_invoice_id_list(program_id, year=today.year, month=today.month)
    inv_groups = report(
        f"get_invoice_id_list[{today.year}-{today.month}]",
        inv_groups_result,
    )
    if isinstance(inv_groups, InvoiceIdGroups):
        sample_ids = inv_groups.invoices[:3]
        if sample_ids:
            report(
                f"get_invoices_by_id[invoices x{len(sample_ids)}]",
                get_invoices_by_id(program_id, invoices=sample_ids),
            )
        else:
            print("     (no invoice IDs in this folder — skipping listbyid)")

    print("\n[9] list_recognized_documents (needs OCR origin IDs from a prior recognize call)")
    print("     (skipping live call — would need fresh document.recognize OCR IDs)")
    # Sanity check the empty-criteria path returns ErrorResponse, not a network call.
    empty_check = list_recognized_documents(program_id, ocr_origin_ids=[])
    if isinstance(empty_check, ErrorResponse) and empty_check.error == "MISSING_CRITERIA":
        results.append(
            ("list_recognized_documents[empty-validation]", True, "ok — rejected as expected")
        )
        print(f"  {OK} list_recognized_documents[empty-validation]: ok — rejected as expected")
    else:
        results.append(
            ("list_recognized_documents[empty-validation]", False, "did not reject empty input")
        )
        print(f"  {FAIL} list_recognized_documents[empty-validation]: did not reject empty input")

    return _summarize()


def _summarize() -> int:
    print("\n=== Summary ===")
    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    for name, ok, msg in results:
        marker = OK if ok else FAIL
        print(f"  {marker} {name}: {msg}")
    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
