"""Synchronous HTTP client for SaldeoSMART REST API-XML.

Owns the ``httpx.Client`` connection pool, the request lock that serializes
calls (Saldeo's "no concurrent requests" rule), and the response parser
that translates ``<RESPONSE>`` envelopes into XML elements or raises
``SaldeoError``.

Two request methods, mirroring the two patterns in the SaldeoSMART spec:

- :meth:`SaldeoClient.get` — for endpoints whose request fits in URL query
  params alone. Used by all the simple list reads (company/list,
  contractor/list, document/list, invoice/list, bank_statement/list,
  employee/list).
- :meth:`SaldeoClient.post_command` — for endpoints whose request needs a
  structured XML body. Saldeo carries that body in a single form field
  literally named ``command`` (gzipped+base64'd). Used by every write
  operation, plus the reads with rich criteria (document/search, the 3.0
  getidlist/listbyid endpoints, document/list_recognized, personnel
  document/list).

The split isn't read-vs-write — it's URL-only vs command-body, dictated by
the spec. The signature must cover the *full request* (URL + form), so the
two methods differ in which params get hashed.
"""

from __future__ import annotations

import logging
import threading
from typing import NoReturn
from xml.etree import ElementTree as ET

import httpx

from ..config import SaldeoConfig
from ..errors import SaldeoError
from .signing import RequestSigner
from .xml import el_text, redact_params, redact_url

logger = logging.getLogger(__name__)


class SaldeoClient:
    """Synchronous client for SaldeoSMART REST API-XML.

    Hold one of these for the lifetime of your process — `httpx.Client` keeps
    a connection pool, and the spec forbids concurrent requests anyway, so a
    singleton is the right shape.

    Usage:
        with SaldeoClient(SaldeoConfig()) as client:
            xml_root = client.get(
                "/api/xml/2.12/document/list",
                query={"company_program_id": "1234", "policy": "LAST_10_DAYS"},
            )
    """

    def __init__(self, config: SaldeoConfig):
        self.config = config
        self._signer = RequestSigner(config.username, config.api_token.get_secret_value())
        self._http = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            headers={"Accept-Encoding": "gzip, deflate"},
            verify=True,  # explicit: SaldeoSMART traffic must use TLS verification
        )
        # Spec: "no concurrent requests" — Saldeo refuses concurrent calls per
        # user. FastMCP can dispatch tools concurrently from the thread executor,
        # so serialize at the client boundary.
        self._lock = threading.Lock()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> SaldeoClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ---- Public request helpers -------------------------------------------------

    def get(self, path: str, query: dict[str, str] | None = None) -> ET.Element:
        """Plain GET — for endpoints whose request fits in URL params.

        Adds ``username`` + ``req_id`` + ``req_sig`` to whatever ``query``
        you supply, signs the combined param set, hits the path, and returns
        the parsed XML root.

        Used by every "list everything for a company" read endpoint.
        """
        params = self._signer.auth_params(extra=query or {})
        all_params = {**(query or {}), **params}
        logger.debug("GET %s params=%s", path, redact_params(all_params))
        with self._lock:
            resp = self._http.get(path, params=all_params)
        return self._parse_response(resp)

    def post_command(
        self,
        path: str,
        xml_command: str,
        query: dict[str, str] | None = None,
        extra_form: dict[str, str] | None = None,
    ) -> ET.Element:
        """POST with a gzipped+base64'd XML body in the ``command`` form field.

        Used by:
          - Every write/mutating operation (``contractor/merge``,
            ``document/update``, ``document/delete``, every ``*.merge``).
          - Reads that need structured criteria too rich for URL params:
            ``document/search``, the 3.0 ``getidlist``/``listbyid`` endpoints,
            ``document/list_recognized``, ``personnel_document/list``.
          - File uploads — pass ``extra_form={"attmnt_1": base64_blob, ...}``
            for endpoints like ``document/add`` that carry attachments.

        The auth signature is computed over the full param set (URL + form),
        per spec, so URL params and form fields are hashed together.
        """
        encoded = RequestSigner.encode_command(xml_command)
        form: dict[str, str] = {"command": encoded}
        if extra_form:
            form.update(extra_form)

        # Auth signature is computed over ALL request params (URL + form), per spec.
        all_params = {**(query or {}), **form}
        auth = self._signer.auth_params(extra=all_params)
        # Username/req_id/req_sig go on the URL (typical pattern).
        url_params = {**(query or {}), **auth}

        logger.debug(
            "POST %s url_params=%s form_keys=%s",
            path,
            redact_params(url_params),
            list(form),
        )
        with self._lock:
            resp = self._http.post(path, params=url_params, data=form)
        return self._parse_response(resp)

    # ---- Internals --------------------------------------------------------------

    def _parse_response(self, resp: httpx.Response) -> ET.Element:
        """SaldeoSMART responses are XML (httpx auto-decompresses gzip thanks to
        the Accept-Encoding header). Parses, then checks for STATUS=ERROR.

        Order of checks (mirrors the numbered comments below):
          1. If parsed body has <STATUS>ERROR</STATUS>, raise SaldeoError
             with ERROR_CODE / ERROR_MESSAGE from the envelope. This wins
             over HTTP status — even on HTTP 4xx/5xx, the server often
             returns the standard error envelope, and ERROR_CODE there is
             much more useful than the bare HTTP status.
          2. Else if HTTP status is non-2xx, raise an HTTP_<code> error.
          3. Else if XML parse failed entirely, raise PARSE_ERROR.
          4. Else log the success line and return the parsed root.
        """
        text = resp.text  # httpx handles gzip transparently
        http_status = resp.status_code
        url = redact_url(str(resp.request.url)) if resp.request is not None else "<unknown>"

        root, parse_error = _try_parse_xml(text)

        # 1. Structured error envelope wins over HTTP status.
        if root is not None:
            self._raise_if_envelope_error(root, text, http_status, url)

        # 2. HTTP-level failure with no structured envelope.
        if http_status >= 400:
            self._raise_http_error(text, http_status, url, resp.reason_phrase)

        # 3. 2xx but body wasn't valid XML.
        if root is None:
            self._raise_parse_error(text, url, parse_error)

        # 4. STATUS=OK (or absent — some endpoints just stream data) — log
        # the operation at INFO so a successful flow is visible alongside
        # the httpx request line.
        metainf = root.find("METAINF")
        operation = el_text(metainf, "OPERATION") if metainf is not None else None
        logger.info("SaldeoSMART OK: operation=%s url=%s", operation or "?", url)

        return root

    @staticmethod
    def _raise_if_envelope_error(root: ET.Element, text: str, http_status: int, url: str) -> None:
        """Raise SaldeoError if the parsed body has <STATUS>ERROR</STATUS>."""
        status_el = root.find("STATUS")
        if status_el is None or (status_el.text or "").strip().upper() != "ERROR":
            return
        code = (el_text(root, "ERROR_CODE") or "").strip() or "UNKNOWN"
        msg = (
            el_text(root, "ERROR_MESSAGE") or ""
        ).strip() or "SaldeoSMART returned STATUS=ERROR with no ERROR_MESSAGE"
        logger.warning(
            "SaldeoSMART API error: code=%s message=%s http_status=%s url=%s",
            code,
            msg,
            http_status,
            url,
        )
        raise SaldeoError(
            code=code,
            message=msg,
            raw_xml=text,
            http_status=http_status if http_status >= 400 else None,
        )

    @staticmethod
    def _raise_http_error(text: str, http_status: int, url: str, reason: str) -> NoReturn:
        """Raise SaldeoError for an HTTP 4xx/5xx with no structured envelope."""
        snippet = (text or "").strip()[:500] or reason or "<empty body>"
        logger.warning(
            "SaldeoSMART HTTP error: status=%s url=%s body=%s", http_status, url, snippet
        )
        raise SaldeoError(
            code=f"HTTP_{http_status}",
            message=f"HTTP {http_status} from SaldeoSMART: {snippet}",
            raw_xml=text,
            http_status=http_status,
        )

    @staticmethod
    def _raise_parse_error(text: str, url: str, parse_error: ET.ParseError | None) -> NoReturn:
        """Raise SaldeoError when the 2xx body isn't valid XML."""
        logger.warning(
            "SaldeoSMART parse error: %s url=%s body=%r",
            parse_error,
            url,
            (text or "")[:500],
        )
        raise SaldeoError(
            code="PARSE_ERROR",
            message=f"Could not parse XML response: {parse_error}",
            raw_xml=text,
        ) from parse_error


def _try_parse_xml(text: str) -> tuple[ET.Element | None, ET.ParseError | None]:
    """Parse `text` as XML; return (root, None) on success or (None, error)."""
    if not text:
        return None, None
    try:
        return ET.fromstring(text), None
    except ET.ParseError as e:
        return None, e
