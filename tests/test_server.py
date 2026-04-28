"""
Tests for server-side concerns: log setup and the SaldeoError → MCP payload
shape. The MCP tool functions themselves hit the network, so we test their
plumbing rather than the tools end-to-end.
"""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from saldeosmart_mcp.errors import ItemError, SaldeoError
from saldeosmart_mcp.logging import setup_logging as _setup_logging
from saldeosmart_mcp.models import (
    ArticleInput,
    BankAccountInput,
    CategoryInput,
    ContractorInput,
    DescriptionInput,
    DimensionInput,
    DimensionValueInput,
    DocumentDimensionInput,
    DocumentDimensionValueInput,
    DocumentSyncInput,
    DocumentUpdateInput,
    FeeInput,
    ForeignCodeInput,
    PaymentMethodInput,
    RecognizeOptionInput,
    RegisterInput,
)
from saldeosmart_mcp.tools._builders import (
    _build_folder_xml,
    _build_simple_merge_xml,
)
from saldeosmart_mcp.tools._runtime import (
    _error_payload,
    _summarize_merge,
)
from saldeosmart_mcp.tools.catalog import (
    _build_article_merge_xml,
    _build_fee_merge_xml,
)
from saldeosmart_mcp.tools.contractors import _build_contractor_merge_xml
from saldeosmart_mcp.tools.dimensions import _build_dimension_merge_xml
from saldeosmart_mcp.tools.documents import (
    _build_document_delete_xml,
    _build_document_dimension_xml,
    _build_document_id_groups_xml,
    _build_document_sync_xml,
    _build_document_update_xml,
    _build_ocr_id_list_xml,
    _build_recognize_xml,
    _build_search_xml,
)
from saldeosmart_mcp.tools.invoices import _build_invoice_id_groups_xml
from saldeosmart_mcp.tools.personnel import _build_personnel_list_xml


@pytest.fixture
def isolated_root_logger():
    """
    `_setup_logging` mutates the global root logger. Snapshot and restore so
    tests don't bleed handlers/levels into each other.
    """
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    root.handlers.clear()
    yield root
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()
    for h in saved_handlers:
        root.addHandler(h)
    root.setLevel(saved_level)


@pytest.fixture
def clean_env(monkeypatch):
    """Remove any SALDEO_LOG_* env vars so we exercise defaults predictably."""
    for var in ("SALDEO_LOG_DIR", "SALDEO_LOG_LEVEL", "SALDEO_LOG_RETENTION_DAYS"):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


# ---- _setup_logging --------------------------------------------------------------


def test_setup_logging_writes_to_configured_dir(tmp_path, isolated_root_logger, clean_env):
    """Custom SALDEO_LOG_DIR must override the default ~/.saldeosmart/logs."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))

    log_file = _setup_logging()

    assert log_file == tmp_path / "saldeosmart.log"
    assert log_file.parent.exists()


def test_setup_logging_routes_client_and_server_loggers(tmp_path, isolated_root_logger, clean_env):
    """Records from both `saldeosmart_mcp.http.client` and `.server` must land in the file."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))
    log_file = _setup_logging()

    logging.getLogger("saldeosmart_mcp.http.client").warning("hello from client")
    logging.getLogger("saldeosmart_mcp.server").warning("hello from server")
    for h in logging.getLogger().handlers:
        h.flush()

    contents = log_file.read_text(encoding="utf-8")
    assert "hello from client" in contents
    assert "hello from server" in contents
    assert "saldeosmart_mcp.http.client" in contents
    assert "saldeosmart_mcp.server" in contents


def test_setup_logging_default_retention_is_one_week(tmp_path, isolated_root_logger, clean_env):
    """Default SALDEO_LOG_RETENTION_DAYS must be 7 (one week)."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))

    _setup_logging()

    handler = next(
        h for h in logging.getLogger().handlers
        if isinstance(h, TimedRotatingFileHandler)
    )
    assert handler.backupCount == 7
    assert handler.when == "MIDNIGHT"


def test_setup_logging_respects_custom_retention(tmp_path, isolated_root_logger, clean_env):
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))
    clean_env.setenv("SALDEO_LOG_RETENTION_DAYS", "3")

    _setup_logging()

    handler = next(
        h for h in logging.getLogger().handlers
        if isinstance(h, TimedRotatingFileHandler)
    )
    assert handler.backupCount == 3


def test_setup_logging_invalid_retention_falls_back_to_default(
    tmp_path, isolated_root_logger, clean_env
):
    """Garbage in SALDEO_LOG_RETENTION_DAYS shouldn't break startup."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))
    clean_env.setenv("SALDEO_LOG_RETENTION_DAYS", "not-a-number")

    _setup_logging()

    handler = next(
        h for h in logging.getLogger().handlers
        if isinstance(h, TimedRotatingFileHandler)
    )
    assert handler.backupCount == 7


def test_setup_logging_zero_retention_is_clamped_to_one(
    tmp_path, isolated_root_logger, clean_env
):
    """A retention of 0 or negative would disable rotation entirely; clamp to 1."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))
    clean_env.setenv("SALDEO_LOG_RETENTION_DAYS", "0")

    _setup_logging()

    handler = next(
        h for h in logging.getLogger().handlers
        if isinstance(h, TimedRotatingFileHandler)
    )
    assert handler.backupCount >= 1


def test_setup_logging_is_idempotent(tmp_path, isolated_root_logger, clean_env):
    """Calling main() twice (tests, reloads) must not stack file handlers."""
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))

    _setup_logging()
    _setup_logging()
    _setup_logging()

    file_handlers = [
        h for h in logging.getLogger().handlers
        if isinstance(h, TimedRotatingFileHandler)
    ]
    assert len(file_handlers) == 1


def test_setup_logging_creates_missing_directory(tmp_path, isolated_root_logger, clean_env):
    """First run must create ~/.saldeosmart/logs/ if it doesn't exist."""
    target = tmp_path / "nested" / "does" / "not" / "exist"
    clean_env.setenv("SALDEO_LOG_DIR", str(target))

    log_file = _setup_logging()

    assert target.is_dir()
    assert log_file.parent == target


def test_setup_logging_default_location_is_under_home(
    isolated_root_logger, clean_env, monkeypatch, tmp_path
):
    """Without SALDEO_LOG_DIR, the file lives under $HOME/.saldeosmart/logs."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    log_file = _setup_logging()

    assert log_file == fake_home / ".saldeosmart" / "logs" / "saldeosmart.log"


def test_setup_logging_honors_log_level(tmp_path, isolated_root_logger, clean_env):
    clean_env.setenv("SALDEO_LOG_DIR", str(tmp_path))
    clean_env.setenv("SALDEO_LOG_LEVEL", "DEBUG")

    _setup_logging()

    assert logging.getLogger().level == logging.DEBUG


# ---- _error_payload --------------------------------------------------------------


def test_error_payload_minimal():
    e = SaldeoError(code="4302", message="User is locked")
    assert _error_payload(e) == {"error": "4302", "message": "User is locked"}


def test_error_payload_includes_http_status_when_present():
    e = SaldeoError(code="4001", message="Invalid signature", http_status=403)
    payload = _error_payload(e)
    assert payload["http_status"] == 403


def test_error_payload_includes_per_item_details():
    e = SaldeoError(
        code="VALIDATION",
        message="some items failed",
        details=[
            ItemError(status="NOT_VALID", path="DOCUMENT_ID",
                      message="must be unique", item_id="1"),
            ItemError(status="ERROR", path="", message="not found", item_id="2"),
        ],
    )
    payload = _error_payload(e)
    assert len(payload["details"]) == 2
    assert payload["details"][0]["path"] == "DOCUMENT_ID"
    assert payload["details"][1]["item_id"] == "2"


def test_error_payload_omits_optional_fields_when_absent():
    e = SaldeoError(code="X", message="y")
    payload = _error_payload(e)
    assert "http_status" not in payload
    assert "details" not in payload


# ---- _build_search_xml -----------------------------------------------------------


def test_build_search_xml_uses_search_policy_tag():
    """Saldeo expects <SEARCH_POLICY>, not <POLICY>. Wrong tag returns
    `4401 No SEARCH_POLICY found in file` from the live API."""
    xml = _build_search_xml(document_id=123, number=None, nip=None, guid=None)
    root = ET.fromstring(xml)
    assert root.find("SEARCH_POLICY") is not None
    assert root.find("SEARCH_POLICY").text == "BY_FIELDS"
    assert root.find("POLICY") is None  # avoid silently regressing


def test_build_search_xml_only_includes_provided_fields():
    xml = _build_search_xml(document_id=None, number="FV/1/2024", nip=None, guid=None)
    root = ET.fromstring(xml)
    fields = root.find("FIELDS")
    assert fields is not None
    assert fields.find("NUMBER").text == "FV/1/2024"
    assert fields.find("DOCUMENT_ID") is None
    assert fields.find("NIP") is None
    assert fields.find("GUID") is None


def test_build_search_xml_escapes_special_characters():
    """ElementTree must escape angle brackets, ampersands, etc. in field values."""
    xml = _build_search_xml(
        document_id=None, number="A&B<X>", nip=None, guid=None
    )
    # If escaping failed, fromstring would raise.
    root = ET.fromstring(xml)
    assert root.find("FIELDS/NUMBER").text == "A&B<X>"


# ---- 3.0 paginated id-list / listbyid builders -----------------------------------


def test_build_folder_xml_emits_year_and_month():
    root = ET.fromstring(_build_folder_xml(year=2024, month=3))
    assert root.find("FOLDER/YEAR").text == "2024"
    assert root.find("FOLDER/MONTH").text == "3"


def test_build_document_id_groups_xml_omits_empty_buckets():
    """Empty / None buckets must not appear in the request — Saldeo treats
    a present-but-empty container as "ask me about that bucket too" which
    breaks the targeted-fetch semantics ``listbyid`` is built around."""
    xml = _build_document_id_groups_xml(
        contracts=[1, 2],
        invoices_cost=None,
        invoices_internal=None,
        invoices_material=None,
        invoices_sale=[],
        orders=None,
        writings=None,
        other_documents=None,
    )
    root = ET.fromstring(xml)
    assert [e.text for e in root.findall("CONTRACTS/CONTRACT")] == ["1", "2"]
    assert root.find("INVOICES_COST") is None
    assert root.find("INVOICES_SALE") is None  # empty list still suppressed


def test_build_invoice_id_groups_xml_uses_correct_leaf_tags():
    xml = _build_invoice_id_groups_xml(
        invoices=[10],
        corrective_invoices=[11],
        pre_invoices=[12],
        corrective_pre_invoices=[13],
    )
    root = ET.fromstring(xml)
    assert root.find("INVOICES/INVOICE_ID").text == "10"
    assert root.find("CORRECTIVE_INVOICES/CORRECTIVE_INVOICE_ID").text == "11"
    assert root.find("PRE_INVOICES/PRE_INVOICE_ID").text == "12"
    assert root.find(
        "CORRECTIVE_PRE_INVOICES/CORRECTIVE_PRE_INVOICE_ID"
    ).text == "13"


def test_build_ocr_id_list_xml_emits_one_entry_per_id():
    xml = _build_ocr_id_list_xml([1, 2, 3])
    root = ET.fromstring(xml)
    ids = [e.text for e in root.findall("OCR_ID_LIST/OCR_ORIGIN_ID")]
    assert ids == ["1", "2", "3"]


# ---- personnel_document.list builder ---------------------------------------------


def test_build_personnel_list_xml_picks_employee_id_when_set():
    xml = _build_personnel_list_xml(
        employee_id=42, year=None, month=None, only_remaining=False
    )
    root = ET.fromstring(xml)
    pd = root.find("PERSONNEL_DOCUMENT")
    assert pd.find("EMPLOYEE_ID").text == "42"
    # Must NOT include either of the broad-scope flags — spec says exactly one.
    assert pd.find("ALL_PERSONNEL_DOCUMENTS") is None
    assert pd.find("ALL_REMAINING_DOCUMENTS") is None


def test_build_personnel_list_xml_picks_remaining_when_requested():
    xml = _build_personnel_list_xml(
        employee_id=None, year=None, month=None, only_remaining=True
    )
    root = ET.fromstring(xml)
    pd = root.find("PERSONNEL_DOCUMENT")
    assert pd.find("ALL_REMAINING_DOCUMENTS").text == "true"
    assert pd.find("ALL_PERSONNEL_DOCUMENTS") is None
    assert pd.find("EMPLOYEE_ID") is None


def test_build_personnel_list_xml_default_is_all_documents():
    xml = _build_personnel_list_xml(
        employee_id=None, year=2024, month=3, only_remaining=False
    )
    root = ET.fromstring(xml)
    pd = root.find("PERSONNEL_DOCUMENT")
    assert pd.find("ALL_PERSONNEL_DOCUMENTS").text == "true"
    assert pd.find("YEAR").text == "2024"
    assert pd.find("MONTH").text == "3"


# ---- merge / write XML builders --------------------------------------------------


def test_build_simple_merge_xml_skips_none_fields():
    items = [CategoryInput(name="Office", category_program_id="CAT_OFC")]
    xml = _build_simple_merge_xml(
        container_tag="CATEGORIES",
        item_tag="CATEGORY",
        items=items,
        field_specs=[
            ("category_program_id", "CATEGORY_PROGRAM_ID"),
            ("name", "NAME"),
            ("description", "DESCRIPTION"),
        ],
    )
    root = ET.fromstring(xml)
    cat = root.find("CATEGORIES/CATEGORY")
    assert cat.find("NAME").text == "Office"
    assert cat.find("CATEGORY_PROGRAM_ID").text == "CAT_OFC"
    # description was None and must NOT be present (an empty element would
    # tell Saldeo "clear the description field").
    assert cat.find("DESCRIPTION") is None


def test_build_contractor_merge_xml_serializes_nested_lists():
    contractors = [
        ContractorInput(
            short_name="ACME",
            full_name="Acme Sp. z o.o.",
            supplier=True,
            customer=False,
            bank_accounts=[
                BankAccountInput(name="main", number="PL11111111111111"),
                BankAccountInput(number="PL22222222222222"),  # name None
            ],
            emails=["billing@acme.example", "ar@acme.example"],
        )
    ]
    xml = _build_contractor_merge_xml(contractors)
    root = ET.fromstring(xml)
    contractor = root.find("CONTRACTORS/CONTRACTOR")
    # Booleans serialized as "true"/"false", not Python repr.
    assert contractor.find("SUPPLIER").text == "true"
    assert contractor.find("CUSTOMER").text == "false"
    accounts = contractor.findall("BANK_ACCOUNTS/BANK_ACCOUNT")
    assert len(accounts) == 2
    assert accounts[0].find("NUMBER").text == "PL11111111111111"
    assert accounts[1].find("NAME") is None  # optional, omitted
    emails = [e.text for e in contractor.findall("EMAILS/EMAIL")]
    assert emails == ["billing@acme.example", "ar@acme.example"]


def test_build_contractor_merge_xml_omits_empty_collections():
    """Empty bank_accounts/emails lists must not produce empty containers
    — Saldeo would interpret <BANK_ACCOUNTS/> as 'replace with no accounts'."""
    xml = _build_contractor_merge_xml(
        [ContractorInput(short_name="A", full_name="A Sp. z o.o.")]
    )
    root = ET.fromstring(xml)
    contractor = root.find("CONTRACTORS/CONTRACTOR")
    assert contractor.find("BANK_ACCOUNTS") is None
    assert contractor.find("EMAILS") is None


def test_build_dimension_merge_xml_emits_values_only_for_enum():
    dims = [
        DimensionInput(
            code="VAT_GROUP", name="VAT group", type="ENUM",
            values=[
                DimensionValueInput(code="A", description="Group A"),
                DimensionValueInput(code="B"),
            ],
        ),
        DimensionInput(code="HOURS", name="Hours", type="NUM"),
    ]
    xml = _build_dimension_merge_xml(dims)
    root = ET.fromstring(xml)
    enum_dim = root.findall("DIMENSIONS/DIMENSION")[0]
    num_dim = root.findall("DIMENSIONS/DIMENSION")[1]
    assert len(enum_dim.findall("VALUES/VALUE")) == 2
    assert num_dim.find("VALUES") is None


def test_build_article_merge_xml_serializes_foreign_codes():
    articles = [
        ArticleInput(
            name="Pen",
            article_program_id="ART-1",
            code="PEN-RED",
            unit="pcs",
            for_documents=True,
            foreign_codes=[
                ForeignCodeInput(contractor_short_name="DOST_A", code="X-1"),
                ForeignCodeInput(contractor_program_id="ERP-42", code="X-2"),
            ],
        )
    ]
    xml = _build_article_merge_xml(articles)
    root = ET.fromstring(xml)
    article = root.find("ARTICLES/ARTICLE")
    codes = article.findall("FOREIGN_CODES/FOREIGN_CODE")
    assert codes[0].find("CONTRACTOR_SHORT_NAME").text == "DOST_A"
    assert codes[1].find("CONTRACTOR_PROGRAM_ID").text == "ERP-42"


def test_build_fee_merge_xml_wraps_fees_in_folder():
    fees = [FeeInput(type="Service", value="100.00", maturity="2024-03-31")]
    xml = _build_fee_merge_xml(year=2024, month=3, fees=fees)
    root = ET.fromstring(xml)
    assert root.find("FOLDER/YEAR").text == "2024"
    assert root.find("FOLDER/MONTH").text == "3"
    assert root.find("FEES/FEE/TYPE").text == "Service"


def test_build_document_dimension_xml_nests_dimensions_per_document():
    items = [
        DocumentDimensionInput(
            document_id=42,
            dimensions=[
                DocumentDimensionValueInput(code="KZ", value="1000.0001"),
                DocumentDimensionValueInput(code="A", value="A1"),
            ],
        )
    ]
    xml = _build_document_dimension_xml(items)
    root = ET.fromstring(xml)
    doc = root.find("DOCUMENT_DIMENSIONS/DOCUMENT_DIMENSION")
    assert doc.find("DOCUMENT_ID").text == "42"
    assert len(doc.findall("DIMENSIONS/DIMENSION")) == 2


def test_build_document_update_xml_only_emits_set_fields():
    docs = [
        DocumentUpdateInput(document_id=10, number="FS-1"),
        DocumentUpdateInput(
            document_id=20, contractor_program_id="ERP-1", self_learning=True
        ),
    ]
    xml = _build_document_update_xml(docs)
    root = ET.fromstring(xml)
    documents = root.findall("DOCUMENTS/DOCUMENT")
    assert documents[0].find("NUMBER").text == "FS-1"
    assert documents[0].find("CONTRACTOR") is None
    assert documents[1].find("CONTRACTOR/CONTRACTOR_PROGRAM_ID").text == "ERP-1"
    assert documents[1].find("SELF_LEARNING").text == "true"


def test_build_document_delete_xml_lists_ids():
    xml = _build_document_delete_xml([1, 2, 3])
    root = ET.fromstring(xml)
    ids = [e.text for e in root.findall("DOCUMENT_DELETE_IDS/DOCUMENT_DELETE_ID")]
    assert ids == ["1", "2", "3"]


def test_build_recognize_xml_passes_split_options():
    docs = [
        RecognizeOptionInput(
            document_id=42, split_mode="AUTO_TWO_SIDED",
            no_rotate=True, overwrite_data=False,
        )
    ]
    xml = _build_recognize_xml(docs)
    root = ET.fromstring(xml)
    doc = root.find("DOCUMENTS/DOCUMENT")
    assert doc.find("SPLIT_MODE").text == "AUTO_TWO_SIDED"
    assert doc.find("NO_ROTATE").text == "true"
    assert doc.find("OVERWRITE_DATA").text == "false"


def test_build_document_sync_xml_emits_only_provided_keys():
    syncs = [
        DocumentSyncInput(
            saldeo_id="D20",
            contractor_program_id="C-1",
            document_number="123/2024",
            document_status="BOOKED",
        )
    ]
    xml = _build_document_sync_xml(syncs)
    root = ET.fromstring(xml)
    sync = root.find("DOCUMENT_SYNCS/DOCUMENT_SYNC")
    assert sync.find("SALDEO_ID").text == "D20"
    assert sync.find("DOCUMENT_STATUS").text == "BOOKED"
    assert sync.find("ISSUE_DATE") is None  # not provided


# ---- _summarize_merge ------------------------------------------------------------


def test_summarize_merge_counts_successes_and_errors():
    """Saldeo answers STATUS=OK at the envelope even when items fail.
    Counts must reflect per-item outcomes, not the envelope."""
    xml = """
    <RESPONSE>
      <METAINF><OPERATION>contractor.merge</OPERATION></METAINF>
      <STATUS>OK</STATUS>
      <CONTRACTORS>
        <CONTRACTOR>
          <UPDATE_STATUS>UPDATED</UPDATE_STATUS>
          <CONTRACTOR_ID>1</CONTRACTOR_ID>
        </CONTRACTOR>
        <CONTRACTOR>
          <UPDATE_STATUS>NOT_VALID</UPDATE_STATUS>
          <CONTRACTOR_ID>2</CONTRACTOR_ID>
          <ERRORS>
            <ERROR>
              <PATH>VAT_NUMBER</PATH>
              <MESSAGE>required field</MESSAGE>
            </ERROR>
          </ERRORS>
        </CONTRACTOR>
      </CONTRACTORS>
    </RESPONSE>
    """
    root = ET.fromstring(xml)
    result = _summarize_merge(root, total=2)
    assert result.operation == "contractor.merge"
    assert result.total == 2
    assert result.successful == 1
    assert len(result.errors) == 1
    assert result.errors[0].path == "VAT_NUMBER"


def test_summarize_merge_handles_envelope_without_metainf():
    xml = "<RESPONSE><STATUS>OK</STATUS></RESPONSE>"
    root = ET.fromstring(xml)
    result = _summarize_merge(root, total=0)
    assert result.operation is None
    assert result.successful == 0


def test_typed_inputs_sanity_check_register_and_method_and_payment():
    """Happy-path schema check: simple merge XMLs round-trip correctly for the
    flat-field ops sharing _build_simple_merge_xml."""
    reg_xml = _build_simple_merge_xml(
        container_tag="REGISTERS",
        item_tag="REGISTER",
        items=[RegisterInput(name="VAT-S", register_program_id="VAT-S")],
        field_specs=[
            ("register_program_id", "REGISTER_PROGRAM_ID"),
            ("register_id", "REGISTER_ID"),
            ("name", "NAME"),
        ],
    )
    pm_xml = _build_simple_merge_xml(
        container_tag="PAYMENT_METHODS",
        item_tag="PAYMENT_METHOD",
        items=[PaymentMethodInput(name="Cash")],
        field_specs=[
            ("payment_method_program_id", "PAYMENT_METHOD_PROGRAM_ID"),
            ("payment_method_id", "PAYMENT_METHOD_ID"),
            ("name", "NAME"),
        ],
    )
    desc_xml = _build_simple_merge_xml(
        container_tag="DESCRIPTIONS",
        item_tag="DESCRIPTION",
        items=[DescriptionInput(value="goods purchase")],
        field_specs=[
            ("program_id", "PROGRAM_ID"),
            ("value", "VALUE"),
        ],
    )
    assert ET.fromstring(reg_xml).find("REGISTERS/REGISTER/NAME").text == "VAT-S"
    assert ET.fromstring(pm_xml).find("PAYMENT_METHODS/PAYMENT_METHOD/NAME").text == "Cash"
    assert ET.fromstring(desc_xml).find(
        "DESCRIPTIONS/DESCRIPTION/VALUE"
    ).text == "goods purchase"
