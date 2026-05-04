"""Request signing — the most error-prone part of the SaldeoSMART contract.

Lives in its own module so it's easy to unit-test, easy to mock, and the
only place that ever sees the raw API token. Stateless apart from the
credentials.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import time
import uuid
from urllib.parse import quote_plus


def saldeo_url_encode(s: str) -> str:
    """SaldeoSMART URL-encoding: almost RFC-3986 but encodes space as '+'.

    quote_plus does exactly this.
    """
    return quote_plus(s)


def new_req_id() -> str:
    """Unique-per-user request ID. Spec allows up to 255 chars."""
    return f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"


class RequestSigner:
    """Build the auth params (`username`, `req_id`, `req_sig`) every request needs.

    The signing algorithm is the most error-prone bit of the API contract, so it
    lives in its own object — easy to unit-test, easy to mock, and the only
    place that knows the API token. Stateless apart from the credentials.
    """

    def __init__(self, username: str, api_token: str):
        self._username = username
        self._api_token = api_token

    def auth_params(self, extra: dict[str, str]) -> dict[str, str]:
        """Return {username, req_id, req_sig} for a request whose other params are `extra`.

        The signature is computed over (username + req_id + extra), per spec.
        """
        req_id = new_req_id()
        signed = {
            "username": self._username,
            "req_id": req_id,
            **{k: str(v) for k, v in extra.items()},
        }
        sig = self.sign(signed, self._api_token)
        return {"username": self._username, "req_id": req_id, "req_sig": sig}

    @staticmethod
    def sign(params: dict[str, str], api_token: str) -> str:
        """Algorithm from the spec's "Authentication" section.

        1. Sort params alphabetically by key (no empty, no duplicates).
        2. Concatenate as key=value (no separator between pairs — per spec example).
        3. URL-encode the result.
        4. Append api_token.
        5. MD5, hex (case-insensitive).

        Spec example shows: ``req_id=<req-id>username=<username>`` — pairs are
        joined with NO separator. We mirror that exactly.

        Pure function: stable output for stable input. Doctest pins the
        contract so a refactor that re-orders or adds separators fails
        immediately.

        >>> RequestSigner.sign({"username": "alice", "req_id": "abc"}, "tok")
        '6b251312c323aee01827df308beb7083'
        >>> # Sort order matters — different key order, same signature:
        >>> RequestSigner.sign({"req_id": "abc", "username": "alice"}, "tok")
        '6b251312c323aee01827df308beb7083'
        >>> # Empty values are rejected before hashing:
        >>> RequestSigner.sign({"username": ""}, "tok")
        Traceback (most recent call last):
            ...
        ValueError: Signature param 'username' must not be empty or null
        """
        for k, v in params.items():
            if not k:
                raise ValueError("Signature param has empty key")
            if v is None or v == "":
                raise ValueError(f"Signature param {k!r} must not be empty or null")

        sorted_pairs = sorted(params.items(), key=lambda kv: kv[0])
        base_string = "".join(f"{k}={v}" for k, v in sorted_pairs)
        encoded = saldeo_url_encode(base_string)
        # usedforsecurity=False: spec mandates MD5 — flag prevents FIPS/Bandit
        # complaints without sacrificing the algorithm Saldeo requires.
        return hashlib.md5((encoded + api_token).encode("utf-8"), usedforsecurity=False).hexdigest()

    @staticmethod
    def encode_command(xml: str) -> str:
        """XML → gzip → base64 string. Used for the `command` parameter."""
        gz = gzip.compress(xml.encode("utf-8"))
        return base64.b64encode(gz).decode("ascii")
