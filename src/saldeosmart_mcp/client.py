"""
SaldeoSMART REST API-XML client.

Handles the quirks of the SaldeoSMART API:
- Request signing: MD5(URL_ENCODE(sorted_params) + api_token) in hex
- XML payloads sent in `command` parameter, encoded as gzip → base64
- All requests require: username, req_id (unique), req_sig
- Response is gzipped XML when Accept-Encoding header is set

API spec version 4.0.0 (02.2024). Default endpoint: https://saldeo.brainshare.pl
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://saldeo.brainshare.pl"
DEFAULT_TIMEOUT = 30.0


class SaldeoError(Exception):
    """Raised when SaldeoSMART API returns an error response."""

    def __init__(self, code: str, message: str, raw_xml: str | None = None):
        self.code = code
        self.message = message
        self.raw_xml = raw_xml
        super().__init__(f"[{code}] {message}")


@dataclass
class SaldeoConfig:
    username: str
    api_token: str
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT


def _saldeo_url_encode(s: str) -> str:
    """
    SaldeoSMART URL-encoding: almost RFC-3986 but encodes space as '+'.
    quote_plus does exactly this.
    """
    return quote_plus(s)


def _build_signature(params: dict[str, str], api_token: str) -> str:
    """
    Algorithm from spec section "Uwierzytelnianie":
    1. Sort params alphabetically by key (no empty, no duplicates)
    2. Concatenate as key=value (no separator between pairs - per spec example)
    3. URL-encode the result
    4. Append api_token
    5. MD5, hex (case-insensitive)

    Spec example shows: "req_id=<req-id>username=<username>" — pairs are joined
    with NO separator. We mirror that exactly.
    """
    if any(not k or v is None or v == "" for k, v in params.items()):
        raise ValueError("Signature params must not be empty or null")

    sorted_pairs = sorted(params.items(), key=lambda kv: kv[0])
    base_string = "".join(f"{k}={v}" for k, v in sorted_pairs)
    encoded = _saldeo_url_encode(base_string)
    return hashlib.md5((encoded + api_token).encode("utf-8")).hexdigest()


def _encode_command(xml: str) -> str:
    """XML → gzip → base64 string. Used for the `command` parameter."""
    gz = gzip.compress(xml.encode("utf-8"))
    return base64.b64encode(gz).decode("ascii")


def _new_req_id() -> str:
    """Unique-per-user request ID. Spec allows up to 255 chars."""
    return f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"


class SaldeoClient:
    """
    Synchronous client for SaldeoSMART REST API-XML.

    Usage:
        client = SaldeoClient(SaldeoConfig(username="...", api_token="..."))
        xml_root = client.get("/api/xml/2.12/document/list",
                              query={"company_program_id": "1234",
                                     "policy": "LAST_10_DAYS"})
    """

    def __init__(self, config: SaldeoConfig):
        self.config = config
        self._http = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            headers={"Accept-Encoding": "gzip, deflate"},
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> SaldeoClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ---- Public request helpers -------------------------------------------------

    def get(self, path: str, query: dict[str, str] | None = None) -> ET.Element:
        """
        Saldeo → APP direction. Always GET. Adds username + req_id + req_sig.
        Returns the parsed XML root element.
        """
        params = self._auth_params(extra=query or {})
        logger.debug("GET %s params=%s", path, _redact(params))
        resp = self._http.get(path, params=params)
        return self._parse_response(resp)

    def post_command(
        self,
        path: str,
        xml_command: str,
        query: dict[str, str] | None = None,
        extra_form: dict[str, str] | None = None,
    ) -> ET.Element:
        """
        APP → Saldeo direction. POST with `command` param holding the encoded XML.
        `query` are URL params (e.g. company_program_id).
        `extra_form` is for binary attachments (attmnt_X) when uploading documents.
        """
        encoded = _encode_command(xml_command)
        form: dict[str, str] = {"command": encoded}
        if extra_form:
            form.update(extra_form)

        # Auth signature is computed over ALL request params (URL + form), per spec.
        all_params = {**(query or {}), **form}
        auth = self._auth_params(extra=all_params)
        # Username/req_id/req_sig go on the URL (typical pattern).
        url_params = {**(query or {}), **auth}

        logger.debug("POST %s url_params=%s form_keys=%s", path,
                     _redact(url_params), list(form.keys()))
        resp = self._http.post(path, params=url_params, data=form)
        return self._parse_response(resp)

    # ---- Internals --------------------------------------------------------------

    def _auth_params(self, extra: dict[str, str]) -> dict[str, str]:
        """
        Build {username, req_id, req_sig}. Signature is over (username + req_id + extra).
        """
        req_id = _new_req_id()
        signed = {
            "username": self.config.username,
            "req_id": req_id,
            **{k: str(v) for k, v in extra.items()},
        }
        sig = _build_signature(signed, self.config.api_token)
        return {"username": self.config.username, "req_id": req_id, "req_sig": sig}

    def _parse_response(self, resp: httpx.Response) -> ET.Element:
        """
        SaldeoSMART responses are XML (httpx auto-decompresses gzip thanks to
        the Accept-Encoding header). Parses, then checks for STATUS=ERROR.
        """
        text = resp.text  # httpx handles gzip transparently
        if resp.status_code >= 400:
            raise SaldeoError(
                code=f"HTTP_{resp.status_code}",
                message=f"HTTP error from SaldeoSMART: {text[:500]}",
                raw_xml=text,
            )

        try:
            root = ET.fromstring(text)
        except ET.ParseError as e:
            raise SaldeoError(
                code="PARSE_ERROR",
                message=f"Could not parse XML response: {e}",
                raw_xml=text,
            ) from e

        # Standard error envelope: <RESPONSE><STATUS>ERROR</STATUS><ERROR>...
        status_el = root.find("STATUS")
        if status_el is not None and (status_el.text or "").strip().upper() == "ERROR":
            err_el = root.find("ERROR")
            code = ""
            msg = ""
            if err_el is not None:
                code_el = err_el.find("CODE")
                msg_el = err_el.find("MESSAGE")
                code = (code_el.text or "") if code_el is not None else ""
                msg = (msg_el.text or "") if msg_el is not None else ""
            raise SaldeoError(code=code or "UNKNOWN", message=msg or "Unknown error",
                              raw_xml=text)

        return root


def _redact(params: dict[str, Any]) -> dict[str, Any]:
    """Hide signature in debug logs."""
    return {k: ("***" if k == "req_sig" else v) for k, v in params.items()}


# ---- XML helpers used by tools ---------------------------------------------------

def el_text(parent: ET.Element, tag: str, default: str | None = None) -> str | None:
    """Return text of first child element with `tag`, or default."""
    child = parent.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def el_int(parent: ET.Element, tag: str) -> int | None:
    raw = el_text(parent, tag)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None
