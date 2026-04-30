"""Shared runtime for the @mcp.tool registry.

Owns:
- the single ``mcp = FastMCP(...)`` instance every tool registers against,
- the lazy process-wide ``SaldeoClient`` cache,
- the ``saldeo_call`` decorator (turns ``SaldeoError`` into ``ErrorResponse``),
- the per-merge-batch summary helper.

Tool modules import ``mcp`` and the helpers from here; this module imports
nothing from ``tools.*`` (its submodules) to keep the dependency direction
clean.
"""

from __future__ import annotations

import functools
import logging
import threading
from collections.abc import Callable
from typing import ParamSpec, TypeVar
from xml.etree import ElementTree as ET

from fastmcp import FastMCP
from pydantic import ValidationError

from ..config import SaldeoConfig
from ..errors import (
    ERROR_ATTACHMENT_NOT_FOUND,
    ERROR_ATTACHMENT_PERMISSION_DENIED,
    ERROR_EMPTY_INPUT,
    ERROR_INVALID_INPUT,
    ErrorResponse,
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
_CLIENT_LOCK = threading.Lock()


def init_client(config: SaldeoConfig) -> SaldeoClient:
    """Create the shared SaldeoClient from an explicit config.

    Called once by ``server.main()`` after CLI args + env vars are resolved
    into a ``SaldeoConfig``. Idempotent: a second call returns the existing
    cached client without rebuilding it.
    """
    global _SHARED_CLIENT
    with _CLIENT_LOCK:
        if _SHARED_CLIENT is None:
            _SHARED_CLIENT = SaldeoClient(config)
        return _SHARED_CLIENT


def get_client() -> SaldeoClient:
    """Return the process-wide SaldeoClient.

    Initialised eagerly by ``server.main()`` via :func:`init_client`. As a
    convenience for ad-hoc scripts and tests, falls back to constructing a
    config from ``SALDEO_*`` env vars when no client has been initialised yet.
    A single client lets httpx pool connections across tool calls and matches
    the spec's "no concurrent requests" rule.
    """
    global _SHARED_CLIENT
    with _CLIENT_LOCK:
        if _SHARED_CLIENT is None:
            try:
                # BaseSettings loads username/api_token from SALDEO_* env vars.
                config = SaldeoConfig()  # type: ignore[call-arg]
            except ValidationError as e:
                missing = ", ".join(
                    f"SALDEO_{str(err['loc'][0]).upper()}" if err.get("loc") else "SALDEO_?"
                    for err in e.errors()
                )
                raise RuntimeError(
                    f"Missing SaldeoSMART credentials ({missing}). The token is generated "
                    f"in SaldeoSMART under Settings → API."
                ) from e
            _SHARED_CLIENT = SaldeoClient(config)
        return _SHARED_CLIENT


def close_client() -> None:
    """Close the shared SaldeoClient and drop the cache.

    Called from ``server.main()``'s ``finally`` block on shutdown, and from
    tests that need to swap configs between runs.
    """
    global _SHARED_CLIENT
    with _CLIENT_LOCK:
        if _SHARED_CLIENT is not None:
            _SHARED_CLIENT.close()
            _SHARED_CLIENT = None


# ---- Decorators ------------------------------------------------------------------


def require_nonempty(
    field: str,
    *,
    message: str,
) -> Callable[[Callable[_P, _T]], Callable[_P, _T | ErrorResponse]]:
    """Short-circuit a tool when a named (possibly nested) field is empty.

    ``field`` is the name of a keyword argument on the wrapped tool, or a
    dotted path into a Pydantic model passed as a kwarg (e.g.
    ``"declarations.taxes"``). When the resolved value is empty/falsy the
    decorator returns ``ErrorResponse(error="EMPTY_INPUT", message=...)``
    without invoking the tool body — saves the network round-trip and
    gives callers a deterministic error code.

    Stack BELOW ``@saldeo_call`` so this decorator runs first; the
    short-circuit returns an ``ErrorResponse`` directly, bypassing the
    SaldeoError handler.
    """
    parts = field.split(".")

    def decorator(fn: Callable[_P, _T]) -> Callable[_P, _T | ErrorResponse]:
        @functools.wraps(fn)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T | ErrorResponse:
            value: object = kwargs.get(parts[0])
            for attr in parts[1:]:
                if value is None:
                    break
                value = getattr(value, attr)
            if value is not None and not value:
                return ErrorResponse(error=ERROR_EMPTY_INPUT, message=message)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


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
            return ErrorResponse(
                error=e.code,
                message=e.message,
                http_status=e.http_status,
                details=list(e.details),
            )
        except FileNotFoundError as e:
            return ErrorResponse(error=ERROR_ATTACHMENT_NOT_FOUND, message=str(e))
        except PermissionError as e:
            return ErrorResponse(error=ERROR_ATTACHMENT_PERMISSION_DENIED, message=str(e))
        except ValueError as e:
            # Builders raise ValueError when an internal invariant on the input
            # batch fails (e.g. attachment-count mismatch in document/import).
            # Surface as a structured error rather than a stack trace.
            return ErrorResponse(error=ERROR_INVALID_INPUT, message=str(e))

    return wrapper


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


def merge_call(
    endpoint: str,
    xml_command: str,
    *,
    total: int,
    query: dict[str, str] | None = None,
    extra_form: dict[str, str] | None = None,
) -> MergeResult:
    """POST a merge/update/delete batch and summarize the per-item result.

    Collapses the universal ``post_command(...) → summarize_merge(...)``
    pair that every write tool in this package would otherwise hand-write.
    Use this for any operation that returns a Saldeo merge envelope (per
    spec: ``STATUS=OK`` at the top, per-item statuses below). Reads that
    POST a search criteria block but parse a typed collection in response
    keep using ``get_client().post_command(...)`` directly.
    """
    root = get_client().post_command(
        endpoint,
        xml_command=xml_command,
        query=query,
        extra_form=extra_form,
    )
    return summarize_merge(root, total=total)


def summarize_merge(root: ET.Element, *, total: int) -> MergeResult:
    """Walk a merge response and produce a MergeResult summary.

    Saldeo answers ``STATUS=OK`` at the envelope level even when individual
    items fail; callers must inspect each item to detect partial failure.
    """
    metainf = root.find("METAINF")
    operation = el_text(metainf, "OPERATION") if metainf is not None else None
    item_errors = iter_item_errors(root)
    return MergeResult(
        operation=operation,
        total=total,
        successful=max(total - len(item_errors), 0),
        errors=item_errors,
    )
