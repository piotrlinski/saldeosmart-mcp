"""Warn (don't fail) on docs pages missing their ``.pl.md`` counterpart.

Strategy:

* Iterate every ``.md`` file under ``docs/`` excluding ``_data/``,
  ``_snippets/`` and the ``reference/`` subtree (reference pages are
  auto-generated from English docstrings and intentionally not
  translated).
* For each, check whether a sibling ``<name>.pl.md`` exists.
* Print missing translations as ``::warning::`` annotations so they
  surface in the GitHub Actions UI without blocking PRs.

The intent is to make translation drift visible. Run via the
``docs.yml`` PR workflow.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = REPO_ROOT / "docs"

# Paths that are intentionally English-only.
EXCLUDED_DIRS = {
    DOCS_ROOT / "reference",
    DOCS_ROOT / "_data",
    DOCS_ROOT / "_snippets",
}


def _is_excluded(path: Path) -> bool:
    return any(str(path).startswith(str(excl)) for excl in EXCLUDED_DIRS)


def _english_pages() -> list[Path]:
    out: list[Path] = []
    for p in DOCS_ROOT.rglob("*.md"):
        if _is_excluded(p):
            continue
        # Skip Polish files themselves and any non-default language siblings.
        if p.name.endswith(".pl.md"):
            continue
        if any(part.endswith(".pl") for part in p.parts):
            continue
        out.append(p)
    return out


def main() -> int:
    missing: list[Path] = []
    total = 0
    for english in _english_pages():
        total += 1
        polish = english.with_name(english.stem + ".pl.md")
        if not polish.exists():
            missing.append(english)

    if missing:
        print(f"::warning::Translation drift: {len(missing)}/{total} English pages have no Polish counterpart.")
        for p in missing:
            rel = p.relative_to(REPO_ROOT)
            polish_rel = rel.with_name(p.stem + ".pl.md")
            print(f"::warning file={rel}::missing translation at {polish_rel}")
        # Warn-only — return 0.
        return 0

    print(f"OK: every translatable page ({total}) has a Polish counterpart.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
