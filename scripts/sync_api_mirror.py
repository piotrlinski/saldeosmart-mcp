"""Refresh ``.temp/api-html-mirror/`` and emit a summary index.

Run on a weekly cron via ``api-mirror-sync.yml``. The mirror itself is
not committed (3.5 MB of vendor HTML/XSD), but the summary JSON at
``docs/_data/api_mirror_index.json`` is — that is the file that, if
changed, signals "Saldeo published a new API version" and triggers a
PR.

The mirror lives at https://saldeo.brainshare.pl/static/doc/api/ and is
organised as ``<version>/<resource>/<request_or_response>.{xml,xsd}``.
We don't fetch it as a file tree; we walk the indexes via HTML scrape.

Usage::

    uv run python scripts/sync_api_mirror.py            # mirror + summary
    uv run python scripts/sync_api_mirror.py --check    # summary only; no fetch
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
MIRROR_ROOT = REPO_ROOT / ".temp" / "api-html-mirror"
SUMMARY_JSON = REPO_ROOT / "docs" / "_data" / "api_mirror_index.json"
BASE_URL = "https://saldeo.brainshare.pl/static/doc/api/"

VERSION_DIR_RE = re.compile(r'href="(\d+_\d+(?:_\d+)?)/?"')
FILE_LINK_RE = re.compile(r'href="([^"?]+\.(?:xml|xsd|html))"')


def _http() -> httpx.Client:
    return httpx.Client(timeout=30.0, follow_redirects=True)


def _list_dir(client: httpx.Client, url: str, pattern: re.Pattern[str]) -> list[str]:
    response = client.get(url)
    response.raise_for_status()
    return sorted(set(pattern.findall(response.text)))


def _fetch_tree(client: httpx.Client, version_url: str, dest: Path) -> dict[str, str]:
    """Recursively fetch a version directory; return {relative_path: sha256}."""
    out: dict[str, str] = {}
    stack: list[tuple[str, Path]] = [(version_url, dest)]
    while stack:
        url, target = stack.pop()
        response = client.get(url)
        response.raise_for_status()
        target.mkdir(parents=True, exist_ok=True)
        for href in sorted(set(FILE_LINK_RE.findall(response.text))):
            file_url = urljoin(url, href)
            file_response = client.get(file_url)
            file_response.raise_for_status()
            file_path = target / href
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(file_response.content)
            digest = hashlib.sha256(file_response.content).hexdigest()
            rel = str(file_path.relative_to(MIRROR_ROOT))
            out[rel] = digest
        # Recurse into subdirectories.
        for sub in sorted(set(re.findall(r'href="([^"?/]+/)"', response.text))):
            if sub.startswith(("..", "?")):
                continue
            stack.append((urljoin(url, sub), target / sub.rstrip("/")))
    return out


def _summary_only() -> int:
    """Recompute the summary JSON from the local mirror without fetching."""
    if not MIRROR_ROOT.is_dir():
        print(f"::warning::mirror directory not present: {MIRROR_ROOT}", file=sys.stderr)
        SUMMARY_JSON.write_text(json.dumps({"versions": []}, indent=2) + "\n", encoding="utf-8")
        return 0
    versions: dict[str, dict[str, object]] = {}
    for version_dir in sorted(MIRROR_ROOT.iterdir()):
        if not version_dir.is_dir():
            continue
        files = sorted(p.relative_to(MIRROR_ROOT).as_posix() for p in version_dir.rglob("*") if p.is_file())
        versions[version_dir.name] = {
            "file_count": len(files),
            "sha256_index": hashlib.sha256("\n".join(files).encode()).hexdigest(),
        }
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps({"versions": versions}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OK: summary written for {len(versions)} versions.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="Recompute summary from existing local mirror only; no network.",
    )
    args = ap.parse_args()

    if args.check:
        return _summary_only()

    MIRROR_ROOT.mkdir(parents=True, exist_ok=True)
    versions: dict[str, dict[str, object]] = {}
    with _http() as client:
        version_dirs = _list_dir(client, BASE_URL, VERSION_DIR_RE)
        if not version_dirs:
            print("::error::no version directories found at the mirror root", file=sys.stderr)
            return 1
        for vdir in version_dirs:
            print(f"  syncing {vdir} ...", file=sys.stderr)
            digests = _fetch_tree(client, urljoin(BASE_URL, f"{vdir}/"), MIRROR_ROOT / vdir)
            versions[vdir] = {
                "file_count": len(digests),
                "sha256_index": hashlib.sha256(
                    "\n".join(f"{k}:{v}" for k, v in sorted(digests.items())).encode()
                ).hexdigest(),
            }
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps({"versions": versions}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OK: synced {len(versions)} versions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
