"""HTTP transport — request signing, the httpx client, and XML helpers.

Layered as: ``signing`` (no in-package deps) → ``xml`` (no in-package
deps) → ``client`` (depends on ``config``, ``errors``, ``signing``,
``xml``). Models and tools depend on this package, never the other way.
"""

from .client import SaldeoClient
from .signing import RequestSigner, new_req_id, saldeo_url_encode
from .xml import el_bool, el_int, el_text, redact_params, redact_url, set_text

__all__ = [
    "RequestSigner",
    "SaldeoClient",
    "el_bool",
    "el_int",
    "el_text",
    "new_req_id",
    "redact_params",
    "redact_url",
    "saldeo_url_encode",
    "set_text",
]
