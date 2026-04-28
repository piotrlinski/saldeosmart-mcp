"""
Tests for the most error-prone parts of the SaldeoSMART client:
the request signature, the gzip+base64 command encoding, and the
error-envelope parser (top-level + per-item).

Run: python -m pytest tests/
"""

import base64
import gzip
import hashlib
from xml.etree import ElementTree as ET

import httpx
import pytest

from saldeosmart_mcp.client import (
    SaldeoClient,
    SaldeoConfig,
    SaldeoError,
    _build_signature,
    _encode_command,
    _saldeo_url_encode,
    iter_item_errors,
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


# ---- Error parsing ---------------------------------------------------------------


def _client() -> SaldeoClient:
    return SaldeoClient(SaldeoConfig(username="u", api_token="t"))


def _resp(text: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status_code=status, text=text,
                          request=httpx.Request("GET", "http://x"))


def test_parses_top_level_error_envelope():
    """ERROR_CODE / ERROR_MESSAGE are direct children of <RESPONSE> — not nested."""
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<RESPONSE>"
        "<STATUS>ERROR</STATUS>"
        "<ERROR_CODE>4302</ERROR_CODE>"
        "<ERROR_MESSAGE>User is locked</ERROR_MESSAGE>"
        "</RESPONSE>"
    )
    with pytest.raises(SaldeoError) as exc:
        _client()._parse_response(_resp(xml))
    assert exc.value.code == "4302"
    assert exc.value.message == "User is locked"
    assert exc.value.http_status is None


def test_status_error_with_missing_fields_falls_back_gracefully():
    """ERROR envelope without code/message must not produce 'Unknown error' silently."""
    xml = "<RESPONSE><STATUS>ERROR</STATUS></RESPONSE>"
    with pytest.raises(SaldeoError) as exc:
        _client()._parse_response(_resp(xml))
    assert exc.value.code == "UNKNOWN"
    assert "STATUS=ERROR" in exc.value.message


def test_http_error_with_xml_envelope_uses_envelope_code():
    """HTTP 4xx/5xx with a structured body should surface ERROR_CODE, not HTTP_xxx."""
    xml = (
        "<RESPONSE>"
        "<STATUS>ERROR</STATUS>"
        "<ERROR_CODE>4001</ERROR_CODE>"
        "<ERROR_MESSAGE>Invalid signature</ERROR_MESSAGE>"
        "</RESPONSE>"
    )
    with pytest.raises(SaldeoError) as exc:
        _client()._parse_response(_resp(xml, status=403))
    assert exc.value.code == "4001"
    assert exc.value.http_status == 403


def test_http_error_without_xml_body():
    """When body isn't XML at all, fall back to HTTP_<status>."""
    with pytest.raises(SaldeoError) as exc:
        _client()._parse_response(_resp("Service Unavailable", status=503))
    assert exc.value.code == "HTTP_503"
    assert exc.value.http_status == 503


def test_parse_error_on_garbage_2xx_body():
    with pytest.raises(SaldeoError) as exc:
        _client()._parse_response(_resp("not xml at all", status=200))
    assert exc.value.code == "PARSE_ERROR"


def test_status_ok_returns_root():
    xml = "<RESPONSE><STATUS>OK</STATUS><DOCUMENTS/></RESPONSE>"
    root = _client()._parse_response(_resp(xml))
    assert root.tag == "RESPONSE"


def test_iter_item_errors_collects_validation_and_operational():
    """Per-item errors come in two flavors — both must surface with item_id."""
    xml = """
    <RESPONSE>
      <STATUS>OK</STATUS>
      <DOCUMENTS>
        <DOCUMENT>
          <UPDATE_STATUS>UPDATED</UPDATE_STATUS>
          <DOCUMENT_ID>54</DOCUMENT_ID>
        </DOCUMENT>
        <DOCUMENT>
          <UPDATE_STATUS>NOT_VALID</UPDATE_STATUS>
          <DOCUMENT_ID>1</DOCUMENT_ID>
          <ERRORS>
            <ERROR>
              <PATH>DOCUMENT_ID</PATH>
              <MESSAGE>Id dokumentu musi być unikalne</MESSAGE>
            </ERROR>
          </ERRORS>
        </DOCUMENT>
        <DOCUMENT>
          <UPDATE_STATUS>ERROR</UPDATE_STATUS>
          <DOCUMENT_ID>2</DOCUMENT_ID>
          <ERROR_MESSAGE>Document does not exist</ERROR_MESSAGE>
        </DOCUMENT>
      </DOCUMENTS>
    </RESPONSE>
    """
    root = ET.fromstring(xml)
    errs = iter_item_errors(root)
    assert len(errs) == 2

    valid_err = next(e for e in errs if e.status == "NOT_VALID")
    assert valid_err.path == "DOCUMENT_ID"
    assert valid_err.item_id == "1"

    op_err = next(e for e in errs if e.status == "ERROR")
    assert op_err.path == ""
    assert op_err.message == "Document does not exist"
    assert op_err.item_id == "2"


def test_iter_item_errors_handles_personnel_status_message():
    """Personnel endpoints use STATUS + STATUS_MESSAGE instead of UPDATE_STATUS."""
    xml = """
    <RESPONSE>
      <STATUS>OK</STATUS>
      <PERSONNEL_DOCUMENTS>
        <PERSONNEL_DOCUMENT>
          <STATUS>CREATED</STATUS>
          <PERSONNEL_DOCUMENT_ID>10</PERSONNEL_DOCUMENT_ID>
        </PERSONNEL_DOCUMENT>
        <PERSONNEL_DOCUMENT>
          <STATUS>NOT_VALID</STATUS>
          <STATUS_MESSAGE>missing required field</STATUS_MESSAGE>
        </PERSONNEL_DOCUMENT>
      </PERSONNEL_DOCUMENTS>
    </RESPONSE>
    """
    errs = iter_item_errors(ET.fromstring(xml))
    assert len(errs) == 1
    assert errs[0].status == "NOT_VALID"
    assert errs[0].message == "missing required field"


def test_top_level_error_is_logged_at_warning(caplog):
    """The httpx layer logs HTTP 200 OK for these — without our log, the
    real SaldeoSMART error would be invisible in the log file."""
    xml = (
        "<RESPONSE><STATUS>ERROR</STATUS>"
        "<ERROR_CODE>4302</ERROR_CODE>"
        "<ERROR_MESSAGE>User is locked</ERROR_MESSAGE></RESPONSE>"
    )
    with caplog.at_level("WARNING", logger="saldeosmart_mcp.client"):
        with pytest.raises(SaldeoError):
            _client()._parse_response(_resp(xml))

    msgs = [r.getMessage() for r in caplog.records]
    assert any("code=4302" in m and "User is locked" in m for m in msgs)


def test_http_error_is_logged_at_warning(caplog):
    with caplog.at_level("WARNING", logger="saldeosmart_mcp.client"):
        with pytest.raises(SaldeoError):
            _client()._parse_response(_resp("<html>oops</html>", status=502))
    assert any("status=502" in r.getMessage() for r in caplog.records)


def test_parse_error_is_logged_at_warning(caplog):
    with caplog.at_level("WARNING", logger="saldeosmart_mcp.client"):
        with pytest.raises(SaldeoError):
            _client()._parse_response(_resp("not xml", status=200))
    assert any("parse error" in r.getMessage().lower() for r in caplog.records)


def test_successful_response_logs_operation_name(caplog):
    xml = (
        "<RESPONSE>"
        "<METAINF><OPERATION>company.list</OPERATION></METAINF>"
        "<STATUS>OK</STATUS><COMPANIES/></RESPONSE>"
    )
    with caplog.at_level("INFO", logger="saldeosmart_mcp.client"):
        _client()._parse_response(_resp(xml))
    assert any("operation=company.list" in r.getMessage() for r in caplog.records)


def test_iter_item_errors_empty_on_all_success():
    xml = (
        "<RESPONSE><STATUS>OK</STATUS>"
        "<DOCUMENTS><DOCUMENT><UPDATE_STATUS>UPDATED</UPDATE_STATUS>"
        "<DOCUMENT_ID>1</DOCUMENT_ID></DOCUMENT></DOCUMENTS></RESPONSE>"
    )
    assert iter_item_errors(ET.fromstring(xml)) == []
