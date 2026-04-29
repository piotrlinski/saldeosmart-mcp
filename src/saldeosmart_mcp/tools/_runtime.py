"""Shared runtime for the @mcp.tool registry.

Owns:
- the single ``mcp = FastMCP(...)`` instance every tool registers against,
- the lazy process-wide ``SaldeoClient`` cache,
- the ``_saldeo_call`` decorator (turns ``SaldeoError`` into ``ErrorResponse``),
- the per-merge-batch summary helper.

Tool modules import ``mcp`` and the helpers from here; this module imports
nothing from ``tools.*`` (its submodules) to keep the dependency direction
clean.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar
from xml.etree import ElementTree as ET

from fastmcp import FastMCP
from pydantic import ValidationError

from ..config import SaldeoConfig
from ..errors import (
    ErrorResponse,
    ItemErrorPayload,
    MergeResult,
    SaldeoError,
    iter_item_errors,
)
from ..http import SaldeoClient
from ..http.xml import el_text

logger = logging.getLogger(__name__)

mcp = FastMCP("SaldeoSMART")

_T = TypeVar("_T")
_P = ParamSpec("_P")

# ---- Client lifecycle ------------------------------------------------------------

_SHARED_CLIENT: SaldeoClient | None = None


def get_client() -> SaldeoClient:
    """Return the process-wide SaldeoClient, initialising it on first use.

    A single client lets httpx pool connections across tool calls and matches
    the spec's "no concurrent requests" rule.
    """
    global _SHARED_CLIENT
    if _SHARED_CLIENT is None:
        try:
            # BaseSettings loads username/api_token from SALDEO_* env vars.
            config = SaldeoConfig()  # type: ignore[call-arg]
        except ValidationError as e:
            missing = ", ".join(f"SALDEO_{str(err['loc'][0]).upper()}" for err in e.errors())
            raise RuntimeError(
                f"Missing SaldeoSMART credentials ({missing}). The token is generated "
                f"in SaldeoSMART under Settings → API."
            ) from e
        _SHARED_CLIENT = SaldeoClient(config)
    return _SHARED_CLIENT


def reset_client_for_tests() -> None:
    """Drop the cached client. Tests use this to swap configs between runs."""
    global _SHARED_CLIENT
    if _SHARED_CLIENT is not None:
        _SHARED_CLIENT.close()
        _SHARED_CLIENT = None


# Back-compat aliases for the older underscore-prefixed names.
_client = get_client
_reset_client_for_tests = reset_client_for_tests


# ---- Decorators ------------------------------------------------------------------


def saldeo_call(fn: Callable[_P, _T]) -> Callable[_P, _T | ErrorResponse]:
    """Decorator: turn a SaldeoError raised inside a tool into ErrorResponse.

    Tool bodies stay focused on the happy path; the error envelope is uniform.
    Uses ``ParamSpec`` so the wrapper preserves the wrapped tool's signature
    for both mypy and IDE autocomplete.
    """

    @functools.wraps(fn)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T | ErrorResponse:
        try:
            return fn(*args, **kwargs)
        except SaldeoError as e:
            return error_response(e)

    return wrapper


# Underscore alias used pre-reorg.
_saldeo_call = saldeo_call


# ---- Helpers shared across tool modules ------------------------------------------


def parse_collection(
    root: ET.Element,
    container_tag: str,
    item_tag: str,
    parser: Callable[[ET.Element], _T],
) -> list[_T]:
    """Find <container_tag>/<item_tag>* and parse each child with `parser`."""
    container = root.find(container_tag)
    if container is None:
        return []
    return [parser(el) for el in container.findall(item_tag)]


_parse_collection = parse_collection


def error_response(e: SaldeoError) -> ErrorResponse:
    """Map a SaldeoError exception into the public ErrorResponse model."""
    return ErrorResponse(
        error=e.code,
        message=e.message,
        http_status=e.http_status,
        details=[ItemErrorPayload.from_dataclass(d) for d in e.details],
    )


_error_response = error_response


def error_payload(e: SaldeoError) -> dict[str, Any]:
    """Render SaldeoError as a JSON-friendly dict for the MCP boundary.

    Kept for backwards compatibility with legacy tests that expect a plain
    dict shape; new code should prefer :func:`error_response`.
    """
    payload: dict[str, Any] = {"error": e.code, "message": e.message}
    if e.http_status is not None:
        payload["http_status"] = e.http_status
    if e.details:
        payload["details"] = [
            {"status": d.status, "path": d.path, "message": d.message, "item_id": d.item_id}
            for d in e.details
        ]
    return payload


_error_payload = error_payload


def summarize_merge(root: ET.Element, *, total: int) -> MergeResult:
    """Walk a merge response and produce a MergeResult summary.

    Saldeo answers ``STATUS=OK`` at the envelope level even when individual
    items fail; callers must inspect each item to detect partial failure.
    """
    metainf = root.find("METAINF")
    operation = el_text(metainf, "OPERATION") if metainf is not None else None
    item_errors = iter_item_errors(root)
    payloads = [ItemErrorPayload.from_dataclass(e) for e in item_errors]
    return MergeResult(
        operation=operation,
        total=total,
        successful=max(total - len(payloads), 0),
        errors=payloads,
    )


_summarize_merge = summarize_merge
