"""
Tests for the most error-prone parts of the SaldeoSMART client:
the request signature and the gzip+base64 command encoding.

Run: python -m pytest tests/
"""

import base64
import gzip
import hashlib

from saldeosmart_mcp.client import (
    _build_signature,
    _encode_command,
    _saldeo_url_encode,
)


def test_url_encoding_uses_plus_for_space():
    # Spec: space is encoded as '+', not %20
    assert _saldeo_url_encode("a b") == "a+b"


def test_signature_matches_spec_example():
    """
    The spec gives a concrete worked example:
      base = "req_id=<req-id>username=<username>"
      sig = HEX(MD5(URL_ENCODING(base) + api_token))
    Pairs are joined with NO separator between them.
    """
    params = {"username": "demo", "req_id": "20140301123056"}
    api_token = "secret-token-xyz"

    # Sorted alphabetically: req_id < username
    expected_base = "req_id=20140301123056username=demo"
    expected = hashlib.md5(
        (_saldeo_url_encode(expected_base) + api_token).encode()
    ).hexdigest()

    assert _build_signature(params, api_token) == expected


def test_signature_sorts_keys_alphabetically():
    """Order of params in the dict must not matter — must always be sorted."""
    a = _build_signature({"username": "u", "req_id": "1", "policy": "X"}, "tok")
    b = _build_signature({"policy": "X", "req_id": "1", "username": "u"}, "tok")
    assert a == b


def test_signature_rejects_empty_values():
    import pytest
    with pytest.raises(ValueError):
        _build_signature({"username": "u", "req_id": ""}, "tok")


def test_encode_command_round_trip():
    """gzip → base64 must be reversible to original XML."""
    xml = "<?xml version='1.0'?><ROOT><HELLO>world</HELLO></ROOT>"
    encoded = _encode_command(xml)

    # Should be ASCII-safe
    encoded.encode("ascii")  # raises if not

    # Round-trip
    decoded = gzip.decompress(base64.b64decode(encoded)).decode("utf-8")
    assert decoded == xml


def test_signature_includes_extra_query_params():
    """When extra params are present (e.g. company_program_id), they must be signed."""
    base_params = {"username": "u", "req_id": "1"}
    with_extra = {**base_params, "company_program_id": "1234"}
    assert _build_signature(base_params, "tok") != _build_signature(with_extra, "tok")
