"""Small XML helpers shared between the HTTP client and the response models.

These exist as a module rather than in a "utils" grab-bag so the dependency
direction stays clean: ``http`` and ``models`` both depend on this module;
nothing here depends on either.

Beyond the obvious child-text readers, ``set_text`` is the small workhorse
behind every request-XML builder: append a child only when the value is set,
serialize booleans the way Saldeo expects (``"true"``/``"false"``), skip
empty strings (an empty element would tell Saldeo "clear this field").
"""

from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree as ET

# ---- Read helpers ----------------------------------------------------------------


def el_text(parent: ET.Element, tag: str, default: str | None = None) -> str | None:
    """Return text of first child element with `tag`, or default.

    Whitespace is stripped from both ends; ``None`` is returned for missing
    or empty elements (so callers can safely chain `or default`).
    """
    child = parent.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def el_int(parent: ET.Element, tag: str) -> int | None:
    """Return the child's text parsed as int, or ``None`` if missing/non-numeric."""
    raw = el_text(parent, tag)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


_TRUE_TOKENS = frozenset({"true", "1", "yes", "y", "t"})


def el_bool(parent: ET.Element, tag: str, default: bool = False) -> bool:
    """Tolerant boolean parse — Saldeo's XML emits any of true/1/yes/T."""
    raw = el_text(parent, tag)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_TOKENS


# ---- Write helper ----------------------------------------------------------------


def set_text(parent: ET.Element, tag: str, value: object | None) -> None:
    """Append <tag>value</tag> if value is not None.

    Booleans are serialized as ``true``/``false`` (Saldeo's convention);
    ints/strings via ``str(...)``. Empty strings are skipped — Saldeo treats
    an empty element as "clear this field" which is rarely what you want.
    """
    if value is None:
        return
    text = ("true" if value else "false") if isinstance(value, bool) else str(value)
    if text == "":
        return
    ET.SubElement(parent, tag).text = text


# ---- Log redaction ---------------------------------------------------------------


def redact_params(params: dict[str, Any]) -> dict[str, Any]:
    """Hide signature in debug logs.

    Used for dict-shaped params (the ``params=`` kwarg to httpx). For
    fully-formed URL strings, see :func:`redact_url`.
    """
    return {k: ("***" if k == "req_sig" else v) for k, v in params.items()}


_URL_REDACT_RE = re.compile(r"(req_sig|api_token)=[^&\s]+", re.IGNORECASE)


def redact_url(url: str) -> str:
    """Strip the request signature from a URL for log lines.

    `req_sig` is just an MD5 hash, but it adds noise that breaks log
    grepping and makes log files awkward to share. `api_token` should
    never appear in a URL, but redact defensively.
    """
    return _URL_REDACT_RE.sub(r"\1=***", url)
