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
from pydantic import SecretStr

from saldeosmart_mcp.config import SaldeoConfig
from saldeosmart_mcp.errors import SaldeoError, iter_item_errors
from saldeosmart_mcp.http import SaldeoClient, el_bool
from saldeosmart_mcp.http.signing import RequestSigner, saldeo_url_encode
from saldeosmart_mcp.http.xml import redact_url


def test_url_encoding_uses_plus_for_space() -> None:
    # Spec: space is encoded as '+', not %20
    assert saldeo_url_encode("a b") == "a+b"


def test_signature_matches_spec_example() -> None:
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
        (saldeo_url_encode(expected_base) + api_token).encode()
    ).hexdigest()

    assert RequestSigner.sign(params, api_token) == expected


def test_signature_sorts_keys_alphabetically() -> None:
    """Order of params in the dict must not matter — must always be sorted."""
    a = RequestSigner.sign({"username": "u", "req_id": "1", "policy": "X"}, "tok")
    b = RequestSigner.sign({"policy": "X", "req_id": "1", "username": "u"}, "tok")
    assert a == b


def test_signature_rejects_empty_values() -> None:
    with pytest.raises(ValueError):
        RequestSigner.sign({"username": "u", "req_id": ""}, "tok")


def test_encode_command_round_trip() -> None:
    """gzip → base64 must be reversible to original XML."""
    xml = "<?xml version='1.0'?><ROOT><HELLO>world</HELLO></ROOT>"
    encoded = RequestSigner.encode_command(xml)

    # Should be ASCII-safe
    encoded.encode("ascii")  # raises if not

    # Round-trip
    decoded = gzip.decompress(base64.b64decode(encoded)).decode("utf-8")
    assert decoded == xml


def test_signature_includes_extra_query_params() -> None:
    """When extra params are present (e.g. company_program_id), they must be signed."""
    base_params = {"username": "u", "req_id": "1"}
    with_extra = {**base_params, "company_program_id": "1234"}
    assert RequestSigner.sign(base_params, "tok") != RequestSigner.sign(with_extra, "tok")


# ---- Error parsing ---------------------------------------------------------------


def _client() -> SaldeoClient:
    return SaldeoClient(SaldeoConfig(username="u", api_token=SecretStr("t")))


def _resp(text: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status_code=status, text=text,
                          request=httpx.Request("GET", "http://x"))


def test_parses_top_level_error_envelope() -> None:
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


def test_status_error_with_missing_fields_falls_back_gracefully() -> None:
    """ERROR envelope without code/message must not produce 'Unknown error' silently."""
    xml = "<RESPONSE><STATUS>ERROR</STATUS></RESPONSE>"
    with pytest.raises(SaldeoError) as exc:
        _client()._parse_response(_resp(xml))
    assert exc.value.code == "UNKNOWN"
    assert "STATUS=ERROR" in exc.value.message


def test_http_error_with_xml_envelope_uses_envelope_code() -> None:
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


def test_http_error_without_xml_body() -> None:
    """When body isn't XML at all, fall back to HTTP_<status>."""
    with pytest.raises(SaldeoError) as exc:
        _client()._parse_response(_resp("Service Unavailable", status=503))
    assert exc.value.code == "HTTP_503"
    assert exc.value.http_status == 503


def test_parse_error_on_garbage_2xx_body() -> None:
    with pytest.raises(SaldeoError) as exc:
        _client()._parse_response(_resp("not xml at all", status=200))
    assert exc.value.code == "PARSE_ERROR"


def test_status_ok_returns_root() -> None:
    xml = "<RESPONSE><STATUS>OK</STATUS><DOCUMENTS/></RESPONSE>"
    root = _client()._parse_response(_resp(xml))
    assert root.tag == "RESPONSE"


def test_iter_item_errors_collects_validation_and_operational() -> None:
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


def test_iter_item_errors_handles_personnel_status_message() -> None:
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


def test_top_level_error_is_logged_at_warning(caplog: pytest.LogCaptureFixture) -> None:
    """The httpx layer logs HTTP 200 OK for these — without our log, the
    real SaldeoSMART error would be invisible in the log file."""
    xml = (
        "<RESPONSE><STATUS>ERROR</STATUS>"
        "<ERROR_CODE>4302</ERROR_CODE>"
        "<ERROR_MESSAGE>User is locked</ERROR_MESSAGE></RESPONSE>"
    )
    with (
        caplog.at_level("WARNING", logger="saldeosmart_mcp.http.client"),
        pytest.raises(SaldeoError),
    ):
        _client()._parse_response(_resp(xml))

    msgs = [r.getMessage() for r in caplog.records]
    assert any("code=4302" in m and "User is locked" in m for m in msgs)


def test_http_error_is_logged_at_warning(caplog: pytest.LogCaptureFixture) -> None:
    with (
        caplog.at_level("WARNING", logger="saldeosmart_mcp.http.client"),
        pytest.raises(SaldeoError),
    ):
        _client()._parse_response(_resp("<html>oops</html>", status=502))
    assert any("status=502" in r.getMessage() for r in caplog.records)


def test_parse_error_is_logged_at_warning(caplog: pytest.LogCaptureFixture) -> None:
    with (
        caplog.at_level("WARNING", logger="saldeosmart_mcp.http.client"),
        pytest.raises(SaldeoError),
    ):
        _client()._parse_response(_resp("not xml", status=200))
    assert any("parse error" in r.getMessage().lower() for r in caplog.records)


def test_successful_response_logs_operation_name(caplog: pytest.LogCaptureFixture) -> None:
    xml = (
        "<RESPONSE>"
        "<METAINF><OPERATION>company.list</OPERATION></METAINF>"
        "<STATUS>OK</STATUS><COMPANIES/></RESPONSE>"
    )
    with caplog.at_level("INFO", logger="saldeosmart_mcp.http.client"):
        _client()._parse_response(_resp(xml))
    assert any("operation=company.list" in r.getMessage() for r in caplog.records)


def test_redact_url_strips_signature() -> None:
    """req_sig must never appear in log lines — it's noise that breaks grep."""
    url = "https://saldeo.brainshare.pl/api/xml/1.0/company/list?username=u&req_id=42&req_sig=abc123def456"
    redacted = redact_url(url)
    assert "abc123def456" not in redacted
    assert "req_sig=***" in redacted
    # Non-sensitive params still present.
    assert "username=u" in redacted
    assert "req_id=42" in redacted


def test_redact_url_handles_api_token_defensively() -> None:
    """api_token should never be in a URL, but redact if it shows up."""
    url = "http://x?api_token=SECRET&foo=bar"
    redacted = redact_url(url)
    assert "SECRET" not in redacted
    assert "foo=bar" in redacted


def test_secret_str_protects_token_from_repr() -> None:
    """SaldeoConfig must not surface the api_token in repr/str."""
    config = SaldeoConfig(username="u", api_token=SecretStr("my-real-token"))
    assert "my-real-token" not in repr(config)
    assert "my-real-token" not in str(config)
    # But the value is still recoverable.
    assert config.api_token.get_secret_value() == "my-real-token"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("y", True),
        ("t", True),
        ("false", False),
        ("0", False),
        ("no", False),
        ("", False),
        ("anything-else", False),
    ],
)
def test_el_bool_parses_common_truthy_tokens(raw: str, expected: bool) -> None:
    el = ET.fromstring(f"<X><FLAG>{raw}</FLAG></X>")
    assert el_bool(el, "FLAG") is expected


def test_el_bool_returns_default_for_missing_tag() -> None:
    el = ET.fromstring("<X/>")
    assert el_bool(el, "MISSING") is False
    assert el_bool(el, "MISSING", default=True) is True


def test_request_lock_serializes_concurrent_calls() -> None:
    """Spec: no concurrent requests. The internal lock must serialize them."""
    import threading
    import time as _time

    client = _client()
    in_flight = 0
    max_in_flight = 0
    lock = threading.Lock()

    def fake_get(*_args: object, **_kwargs: object) -> httpx.Response:
        nonlocal in_flight, max_in_flight
        with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        _time.sleep(0.02)
        with lock:
            in_flight -= 1
        return httpx.Response(
            status_code=200,
            text="<RESPONSE><STATUS>OK</STATUS></RESPONSE>",
            request=httpx.Request("GET", "http://x"),
        )

    client._http.get = fake_get  # type: ignore[method-assign]

    threads = [threading.Thread(target=lambda: client.get("/p")) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert max_in_flight == 1, f"expected serial, saw {max_in_flight} concurrent"


def test_iter_item_errors_empty_on_all_success() -> None:
    xml = (
        "<RESPONSE><STATUS>OK</STATUS>"
        "<DOCUMENTS><DOCUMENT><UPDATE_STATUS>UPDATED</UPDATE_STATUS>"
        "<DOCUMENT_ID>1</DOCUMENT_ID></DOCUMENT></DOCUMENTS></RESPONSE>"
    )
    assert iter_item_errors(ET.fromstring(xml)) == []


def test_iter_item_errors_ignores_nested_status_inside_item_body() -> None:
    """A nested <STATUS> inside an item body must not be misread as a row result.

    Regression: a previous root.iter() walk descended into per-item bodies and
    surfaced spurious failures whenever a nested element happened to be tagged
    <STATUS>.
    """
    xml = """
    <RESPONSE>
      <STATUS>OK</STATUS>
      <DOCUMENTS>
        <DOCUMENT>
          <UPDATE_STATUS>UPDATED</UPDATE_STATUS>
          <DOCUMENT_ID>1</DOCUMENT_ID>
          <DOCUMENT_ITEMS>
            <DOCUMENT_ITEM>
              <STATUS>NOT_VALID</STATUS>
            </DOCUMENT_ITEM>
          </DOCUMENT_ITEMS>
        </DOCUMENT>
      </DOCUMENTS>
    </RESPONSE>
    """
    assert iter_item_errors(ET.fromstring(xml)) == []


# ---- post_command + extra_form (file attachments) -------------------------------


def test_post_command_passes_extra_form_through_to_httpx() -> None:
    """File-upload tools rely on extra_form keys reaching the wire as form data,
    AND on the request signature covering those keys (Saldeo signs the full
    param set — URL params + form fields)."""
    client = _client()

    captured: dict[str, object] = {}

    def fake_post(path: str, params: dict[str, str], data: dict[str, str]) -> httpx.Response:
        captured["path"] = path
        captured["params"] = params
        captured["data"] = data
        return httpx.Response(
            status_code=200,
            text="<RESPONSE><STATUS>OK</STATUS></RESPONSE>",
            request=httpx.Request("POST", f"http://x{path}"),
        )

    client._http.post = fake_post  # type: ignore[method-assign]

    client.post_command(
        "/api/xml/2.22/personnel_document/add",
        xml_command="<ROOT/>",
        query={"company_program_id": "abc"},
        extra_form={"attmnt_1": "ZmFrZQ==", "attmnt_2": "Zm9vYmFy"},
    )

    data = captured["data"]
    params = captured["params"]
    assert isinstance(data, dict)
    assert isinstance(params, dict)
    assert data["attmnt_1"] == "ZmFrZQ=="
    assert data["attmnt_2"] == "Zm9vYmFy"
    assert "command" in data  # gzipped+base64 XML still present

    # Signature must cover URL params + form fields. Recompute from scratch
    # and compare against the value in `params`.
    from saldeosmart_mcp.http.signing import RequestSigner

    signed_params = {
        "company_program_id": "abc",
        "username": params["username"],
        "req_id": params["req_id"],
        "command": data["command"],
        "attmnt_1": data["attmnt_1"],
        "attmnt_2": data["attmnt_2"],
    }
    expected_sig = RequestSigner.sign(signed_params, "t")
    assert params["req_sig"] == expected_sig
