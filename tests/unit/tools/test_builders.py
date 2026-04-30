"""Tests for SaldeoSMART request-XML builders.

Two classes of bug we guard against:

1. **Element name mismatches** — builders writing `<X>` when the spec wants
   `<Y>` (the article-merge builder used to emit `<CONTRACTOR_PROGRAM_ID>`
   inside `<FOREIGN_CODE>`, which the XSD does not define).
2. **Element ordering** — Saldeo XSDs use ``<xs:sequence>``, so strict parsers
   reject the wrong order even when names are correct (``document.sync`` is
   the obvious case).

Reference shapes: ``.temp/api-html-mirror/`` (request schemas
``*_request.xsd`` and example payloads ``*_request_example.xml``).

These tests also cover ``summarize_merge`` because the merge response
shape is the symmetric counterpart of the merge request — easier to keep
the round-trip honest by testing them side by side.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from saldeosmart_mcp.http.attachments import Attachment, PreparedAttachment
from saldeosmart_mcp.models import (
    ArticleInput,
    AssuranceCompanyDetailsInput,
    AssuranceEmployeesDetailsInput,
    AssuranceItemInput,
    AssurancePartnerDetailsInput,
    AssurancePersonalDetailsInput,
    AssuranceRenewInput,
    BankAccountInput,
    CategoryInput,
    CloseAttachmentInput,
    CompanyCreateBankAccountInput,
    CompanyCreateInput,
    CompanySynchronizeInput,
    ContractorInput,
    DeclarationMergeInput,
    DeclarationTaxInput,
    DescriptionInput,
    DimensionInput,
    DimensionValueInput,
    DocumentAddInput,
    DocumentAddRecognizeInput,
    DocumentCorrectContractorInput,
    DocumentCorrectInput,
    DocumentDimensionInput,
    DocumentDimensionValueInput,
    DocumentImportAttachmentInput,
    DocumentImportCurrencyInput,
    DocumentImportDimensionInput,
    DocumentImportInput,
    DocumentImportTypeInput,
    DocumentImportVATInput,
    DocumentImportVATItemInput,
    DocumentImportVATRegistryInput,
    DocumentSyncInput,
    DocumentUpdateInput,
    EmployeeAddInput,
    EmployeeContractInput,
    FeeInput,
    FinancialBalanceMergeInput,
    FinancialBalanceVATInput,
    ForeignCodeInput,
    InvoiceAddBankAccountInput,
    InvoiceAddDiscountInput,
    InvoiceAddInput,
    InvoiceAddItemInput,
    InvoiceAddNewTransportVehicleInput,
    InvoiceAddPaymentInput,
    InvoiceAddSaleDateRangeInput,
    PaymentMethodInput,
    PersonnelDocumentAddInput,
    RecognizeOptionInput,
    RegisterInput,
    TaxDetailsInput,
)
from saldeosmart_mcp.tools._builders import (
    build_folder_xml,
    build_simple_merge_xml,
)
from saldeosmart_mcp.tools._documents_builders import (
    build_document_add_recognize_xml,
    build_document_add_xml,
    build_document_correct_xml,
    build_document_delete_xml,
    build_document_dimension_xml,
    build_document_id_groups_xml,
    build_document_import_xml,
    build_document_sync_xml,
    build_document_update_xml,
    build_ocr_id_list_xml,
    build_recognize_xml,
    build_search_xml,
)
from saldeosmart_mcp.tools._runtime import summarize_merge
from saldeosmart_mcp.tools.accounting_close import (
    _build_assurance_renew_xml,
    _build_declaration_merge_xml,
)
from saldeosmart_mcp.tools.catalog import (
    _build_article_merge_xml,
    _build_fee_merge_xml,
)
from saldeosmart_mcp.tools.companies import (
    _build_company_create_xml,
    _build_company_synchronize_xml,
)
from saldeosmart_mcp.tools.contractors import _build_contractor_merge_xml
from saldeosmart_mcp.tools.dimensions import _build_dimension_merge_xml
from saldeosmart_mcp.tools.financial_balance import _build_financial_balance_merge_xml
from saldeosmart_mcp.tools.invoices import (
    _build_invoice_add_xml,
    _build_invoice_id_groups_xml,
)
from saldeosmart_mcp.tools.personnel import (
    _build_employee_add_xml,
    _build_personnel_document_add_xml,
    _build_personnel_list_xml,
)

# ---- build_search_xml -----------------------------------------------------------


def test_build_search_xml_uses_search_policy_tag() -> None:
    """Saldeo expects <SEARCH_POLICY>, not <POLICY>. Wrong tag returns
    `4401 No SEARCH_POLICY found in file` from the live API."""
    xml = build_search_xml(document_id=123, number=None, nip=None, guid=None)
    root = ET.fromstring(xml)
    assert root.find("SEARCH_POLICY") is not None
    assert root.find("SEARCH_POLICY").text == "BY_FIELDS"  # type: ignore[union-attr]
    assert root.find("POLICY") is None  # avoid silently regressing


def test_build_search_xml_only_includes_provided_fields() -> None:
    xml = build_search_xml(document_id=None, number="FV/1/2024", nip=None, guid=None)
    root = ET.fromstring(xml)
    fields = root.find("FIELDS")
    assert fields is not None
    assert fields.find("NUMBER").text == "FV/1/2024"  # type: ignore[union-attr]
    assert fields.find("DOCUMENT_ID") is None
    assert fields.find("NIP") is None
    assert fields.find("GUID") is None


def test_build_search_xml_escapes_special_characters() -> None:
    """ElementTree must escape angle brackets, ampersands, etc. in field values."""
    xml = build_search_xml(document_id=None, number="A&B<X>", nip=None, guid=None)
    # If escaping failed, fromstring would raise.
    root = ET.fromstring(xml)
    assert root.find("FIELDS/NUMBER").text == "A&B<X>"  # type: ignore[union-attr]


# ---- 3.0 paginated id-list / listbyid builders -----------------------------------


def test_build_folder_xml_emits_year_and_month() -> None:
    root = ET.fromstring(build_folder_xml(year=2024, month=3))
    assert root.find("FOLDER/YEAR").text == "2024"  # type: ignore[union-attr]
    assert root.find("FOLDER/MONTH").text == "3"  # type: ignore[union-attr]


def test_build_document_id_groups_xml_omits_empty_buckets() -> None:
    """Empty / None buckets must not appear in the request — Saldeo treats
    a present-but-empty container as "ask me about that bucket too" which
    breaks the targeted-fetch semantics ``listbyid`` is built around."""
    xml = build_document_id_groups_xml(
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


def test_build_invoice_id_groups_xml_uses_correct_leaf_tags() -> None:
    xml = _build_invoice_id_groups_xml(
        invoices=[10],
        corrective_invoices=[11],
        pre_invoices=[12],
        corrective_pre_invoices=[13],
    )
    root = ET.fromstring(xml)
    assert root.find("INVOICES/INVOICE_ID").text == "10"  # type: ignore[union-attr]
    assert root.find("CORRECTIVE_INVOICES/CORRECTIVE_INVOICE_ID").text == "11"  # type: ignore[union-attr]
    assert root.find("PRE_INVOICES/PRE_INVOICE_ID").text == "12"  # type: ignore[union-attr]
    assert (
        root.find(  # type: ignore[union-attr]
            "CORRECTIVE_PRE_INVOICES/CORRECTIVE_PRE_INVOICE_ID"
        ).text
        == "13"
    )


def test_build_ocr_id_list_xml_emits_one_entry_per_id() -> None:
    xml = build_ocr_id_list_xml([1, 2, 3])
    root = ET.fromstring(xml)
    ids = [e.text for e in root.findall("OCR_ID_LIST/OCR_ORIGIN_ID")]
    assert ids == ["1", "2", "3"]


# ---- personnel_document.list builder ---------------------------------------------


def test_build_personnel_list_xml_picks_employee_id_when_set() -> None:
    xml = _build_personnel_list_xml(employee_id=42, year=None, month=None, only_remaining=False)
    root = ET.fromstring(xml)
    pd = root.find("PERSONNEL_DOCUMENT")
    assert pd.find("EMPLOYEE_ID").text == "42"  # type: ignore[union-attr]
    # Must NOT include either of the broad-scope flags — spec says exactly one.
    assert pd.find("ALL_PERSONNEL_DOCUMENTS") is None  # type: ignore[union-attr]
    assert pd.find("ALL_REMAINING_DOCUMENTS") is None  # type: ignore[union-attr]


def test_build_personnel_list_xml_picks_remaining_when_requested() -> None:
    xml = _build_personnel_list_xml(employee_id=None, year=None, month=None, only_remaining=True)
    root = ET.fromstring(xml)
    pd = root.find("PERSONNEL_DOCUMENT")
    assert pd.find("ALL_REMAINING_DOCUMENTS").text == "true"  # type: ignore[union-attr]
    assert pd.find("ALL_PERSONNEL_DOCUMENTS") is None  # type: ignore[union-attr]
    assert pd.find("EMPLOYEE_ID") is None  # type: ignore[union-attr]


def test_build_personnel_list_xml_default_is_all_documents() -> None:
    xml = _build_personnel_list_xml(employee_id=None, year=2024, month=3, only_remaining=False)
    root = ET.fromstring(xml)
    pd = root.find("PERSONNEL_DOCUMENT")
    assert pd.find("ALL_PERSONNEL_DOCUMENTS").text == "true"  # type: ignore[union-attr]
    assert pd.find("YEAR").text == "2024"  # type: ignore[union-attr]
    assert pd.find("MONTH").text == "3"  # type: ignore[union-attr]


# ---- merge / write XML builders --------------------------------------------------


def test_build_simple_merge_xml_skips_none_fields() -> None:
    items = [CategoryInput(name="Office", category_program_id="CAT_OFC")]
    xml = build_simple_merge_xml(
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
    assert cat.find("NAME").text == "Office"  # type: ignore[union-attr]
    assert cat.find("CATEGORY_PROGRAM_ID").text == "CAT_OFC"  # type: ignore[union-attr]
    # description was None and must NOT be present (an empty element would
    # tell Saldeo "clear the description field").
    assert cat.find("DESCRIPTION") is None  # type: ignore[union-attr]


def test_build_contractor_merge_xml_serializes_nested_lists() -> None:
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
    assert contractor.find("SUPPLIER").text == "true"  # type: ignore[union-attr]
    assert contractor.find("CUSTOMER").text == "false"  # type: ignore[union-attr]
    accounts = contractor.findall("BANK_ACCOUNTS/BANK_ACCOUNT")  # type: ignore[union-attr]
    assert len(accounts) == 2
    assert accounts[0].find("NUMBER").text == "PL11111111111111"  # type: ignore[union-attr]
    assert accounts[1].find("NAME") is None  # optional, omitted
    emails = [e.text for e in contractor.findall("EMAILS/EMAIL")]  # type: ignore[union-attr]
    assert emails == ["billing@acme.example", "ar@acme.example"]


def test_build_contractor_merge_xml_omits_empty_collections() -> None:
    """Empty bank_accounts/emails lists must not produce empty containers
    — Saldeo would interpret <BANK_ACCOUNTS/> as 'replace with no accounts'."""
    xml = _build_contractor_merge_xml([ContractorInput(short_name="A", full_name="A Sp. z o.o.")])
    root = ET.fromstring(xml)
    contractor = root.find("CONTRACTORS/CONTRACTOR")
    assert contractor.find("BANK_ACCOUNTS") is None  # type: ignore[union-attr]
    assert contractor.find("EMAILS") is None  # type: ignore[union-attr]


def test_build_dimension_merge_xml_emits_values_only_for_enum() -> None:
    dims = [
        DimensionInput(
            code="VAT_GROUP",
            name="VAT group",
            type="ENUM",
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


def test_build_article_merge_xml_serializes_foreign_codes() -> None:
    # Per XSD (.temp/api-html-mirror/1_14/article/article_merge_request.xml)
    # FOREIGN_CODE only defines <CONTRACTOR_SHORT_NAME> and <CODE>.
    articles = [
        ArticleInput(
            name="Pen",
            article_program_id="ART-1",
            code="PEN-RED",
            unit="pcs",
            for_documents=True,
            foreign_codes=[
                ForeignCodeInput(contractor_short_name="DOST_A", code="X-1"),
                ForeignCodeInput(contractor_short_name="DOST_B", code="X-2"),
            ],
        )
    ]
    xml = _build_article_merge_xml(articles)
    root = ET.fromstring(xml)
    article = root.find("ARTICLES/ARTICLE")
    codes = article.findall("FOREIGN_CODES/FOREIGN_CODE")  # type: ignore[union-attr]
    assert codes[0].find("CONTRACTOR_SHORT_NAME").text == "DOST_A"  # type: ignore[union-attr]
    assert codes[0].find("CODE").text == "X-1"  # type: ignore[union-attr]
    assert codes[1].find("CONTRACTOR_SHORT_NAME").text == "DOST_B"  # type: ignore[union-attr]
    assert codes[1].find("CODE").text == "X-2"  # type: ignore[union-attr]


def test_article_foreign_code_only_emits_short_name_and_code() -> None:
    """The article-merge spec doesn't define CONTRACTOR_PROGRAM_ID inside
    <FOREIGN_CODE>; sending it can be rejected by strict XSD validation."""
    article = ArticleInput(
        name="Towar X",
        code="X-1",
        foreign_codes=[
            ForeignCodeInput(contractor_short_name="kontr", code="EXT-1"),
        ],
    )
    root = ET.fromstring(_build_article_merge_xml([article]))
    fc = root.find("ARTICLES/ARTICLE/FOREIGN_CODES/FOREIGN_CODE")
    assert fc is not None
    children = [child.tag for child in fc]
    assert children == ["CONTRACTOR_SHORT_NAME", "CODE"]


def test_article_merge_omits_foreign_codes_when_empty() -> None:
    article = ArticleInput(name="Towar Y", code="Y-1")
    root = ET.fromstring(_build_article_merge_xml([article]))
    article_el = root.find("ARTICLES/ARTICLE")
    assert article_el is not None
    assert article_el.find("FOREIGN_CODES") is None


def test_build_fee_merge_xml_wraps_fees_in_folder() -> None:
    fees = [FeeInput(type="Service", value="100.00", maturity="2024-03-31")]
    xml = _build_fee_merge_xml(year=2024, month=3, fees=fees)
    root = ET.fromstring(xml)
    assert root.find("FOLDER/YEAR").text == "2024"  # type: ignore[union-attr]
    assert root.find("FOLDER/MONTH").text == "3"  # type: ignore[union-attr]
    assert root.find("FEES/FEE/TYPE").text == "Service"  # type: ignore[union-attr]


def test_build_document_dimension_xml_nests_dimensions_per_document() -> None:
    items = [
        DocumentDimensionInput(
            document_id=42,
            dimensions=[
                DocumentDimensionValueInput(code="KZ", value="1000.0001"),
                DocumentDimensionValueInput(code="A", value="A1"),
            ],
        )
    ]
    xml = build_document_dimension_xml(items)
    root = ET.fromstring(xml)
    doc = root.find("DOCUMENT_DIMENSIONS/DOCUMENT_DIMENSION")
    assert doc.find("DOCUMENT_ID").text == "42"  # type: ignore[union-attr]
    assert len(doc.findall("DIMENSIONS/DIMENSION")) == 2  # type: ignore[union-attr]


def test_build_document_update_xml_only_emits_set_fields() -> None:
    docs = [
        DocumentUpdateInput(document_id=10, number="FS-1"),
        DocumentUpdateInput(document_id=20, contractor_program_id="ERP-1", self_learning=True),
    ]
    xml = build_document_update_xml(docs)
    root = ET.fromstring(xml)
    documents = root.findall("DOCUMENTS/DOCUMENT")
    assert documents[0].find("NUMBER").text == "FS-1"  # type: ignore[union-attr]
    assert documents[0].find("CONTRACTOR") is None
    assert documents[1].find("CONTRACTOR/CONTRACTOR_PROGRAM_ID").text == "ERP-1"  # type: ignore[union-attr]
    assert documents[1].find("SELF_LEARNING").text == "true"  # type: ignore[union-attr]


def test_build_document_delete_xml_lists_ids() -> None:
    xml = build_document_delete_xml([1, 2, 3])
    root = ET.fromstring(xml)
    ids = [e.text for e in root.findall("DOCUMENT_DELETE_IDS/DOCUMENT_DELETE_ID")]
    assert ids == ["1", "2", "3"]


def test_build_recognize_xml_passes_split_options() -> None:
    docs = [
        RecognizeOptionInput(
            document_id=42,
            split_mode="AUTO_TWO_SIDED",
            no_rotate=True,
            overwrite_data=False,
        )
    ]
    xml = build_recognize_xml(docs)
    root = ET.fromstring(xml)
    doc = root.find("DOCUMENTS/DOCUMENT")
    assert doc.find("SPLIT_MODE").text == "AUTO_TWO_SIDED"  # type: ignore[union-attr]
    assert doc.find("NO_ROTATE").text == "true"  # type: ignore[union-attr]
    assert doc.find("OVERWRITE_DATA").text == "false"  # type: ignore[union-attr]


# ---- document.sync: element ordering is strict -----------------------------------

# XSD sequence (.temp/api-html-mirror/1_13/documentsync/document_sync_request.xsd):
#   SALDEO_ID, CONTRACTOR_PROGRAM_ID, DOCUMENT_NUMBER, GUID, DESCRIPTION,
#   NUMBERING_TYPE, ACCOUNT_DOCUMENT_NUMBER, DOCUMENT_STATUS, ISSUE_DATE,
#   SALDEO_GUID
EXPECTED_SYNC_ORDER = [
    "SALDEO_ID",
    "CONTRACTOR_PROGRAM_ID",
    "DOCUMENT_NUMBER",
    "GUID",
    "DESCRIPTION",
    "NUMBERING_TYPE",
    "ACCOUNT_DOCUMENT_NUMBER",
    "DOCUMENT_STATUS",
    "ISSUE_DATE",
    "SALDEO_GUID",
]


def test_document_sync_emits_elements_in_xsd_order() -> None:
    sync = DocumentSyncInput(
        saldeo_id="D20",
        contractor_program_id="1235",
        document_number="5120145263",
        guid="GUID",
        description="DESCRIPTION",
        numbering_type="NUMBERING_TYPE",
        account_document_number="ACCT-1",
        document_status="BUFFER",
        issue_date="2015-10-25",
        saldeo_guid="00010001-0001-3000-934a-000000000020",
    )
    root = ET.fromstring(build_document_sync_xml([sync]))
    sync_el = root.find("DOCUMENT_SYNCS/DOCUMENT_SYNC")
    assert sync_el is not None
    actual_order = [child.tag for child in sync_el]
    assert actual_order == EXPECTED_SYNC_ORDER


def test_document_sync_omits_unset_optional_fields() -> None:
    """Only the required identifiers are sent — unset Optional fields stay out."""
    sync = DocumentSyncInput(
        contractor_program_id="C1",
        document_number="N1",
        guid="G1",
        description="D",
        numbering_type="NT",
        account_document_number="ADN",
    )
    root = ET.fromstring(build_document_sync_xml([sync]))
    sync_el = root.find("DOCUMENT_SYNCS/DOCUMENT_SYNC")
    assert sync_el is not None
    tags = {child.tag for child in sync_el}
    # Optional fields not set:
    assert "SALDEO_ID" not in tags
    assert "DOCUMENT_STATUS" not in tags
    assert "ISSUE_DATE" not in tags
    assert "SALDEO_GUID" not in tags
    # Required fields still present:
    assert {"CONTRACTOR_PROGRAM_ID", "DOCUMENT_NUMBER", "GUID"}.issubset(tags)


def test_build_document_sync_xml_emits_only_provided_keys() -> None:
    syncs = [
        DocumentSyncInput(
            saldeo_id="D20",
            contractor_program_id="C-1",
            document_number="123/2024",
            document_status="BOOKED",
        )
    ]
    xml = build_document_sync_xml(syncs)
    root = ET.fromstring(xml)
    sync = root.find("DOCUMENT_SYNCS/DOCUMENT_SYNC")
    assert sync.find("SALDEO_ID").text == "D20"  # type: ignore[union-attr]
    assert sync.find("DOCUMENT_STATUS").text == "BOOKED"  # type: ignore[union-attr]
    assert sync.find("ISSUE_DATE") is None  # type: ignore[union-attr]  # not provided


# ---- summarize_merge ------------------------------------------------------------


def testsummarize_merge_counts_successes_and_errors() -> None:
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
    result = summarize_merge(root, total=2)
    assert result.operation == "contractor.merge"
    assert result.total == 2
    assert result.successful == 1
    assert len(result.errors) == 1
    assert result.errors[0].path == "VAT_NUMBER"


def testsummarize_merge_handles_envelope_without_metainf() -> None:
    xml = "<RESPONSE><STATUS>OK</STATUS></RESPONSE>"
    root = ET.fromstring(xml)
    result = summarize_merge(root, total=0)
    assert result.operation is None
    assert result.successful == 0


def test_typed_inputs_sanity_check_register_and_method_and_payment() -> None:
    """Happy-path schema check: simple merge XMLs round-trip correctly for the
    flat-field ops sharing build_simple_merge_xml."""
    reg_xml = build_simple_merge_xml(
        container_tag="REGISTERS",
        item_tag="REGISTER",
        items=[RegisterInput(name="VAT-S", register_program_id="VAT-S")],
        field_specs=[
            ("register_program_id", "REGISTER_PROGRAM_ID"),
            ("register_id", "REGISTER_ID"),
            ("name", "NAME"),
        ],
    )
    pm_xml = build_simple_merge_xml(
        container_tag="PAYMENT_METHODS",
        item_tag="PAYMENT_METHOD",
        items=[PaymentMethodInput(name="Cash")],
        field_specs=[
            ("payment_method_program_id", "PAYMENT_METHOD_PROGRAM_ID"),
            ("payment_method_id", "PAYMENT_METHOD_ID"),
            ("name", "NAME"),
        ],
    )
    desc_xml = build_simple_merge_xml(
        container_tag="DESCRIPTIONS",
        item_tag="DESCRIPTION",
        items=[DescriptionInput(value="goods purchase")],
        field_specs=[
            ("program_id", "PROGRAM_ID"),
            ("value", "VALUE"),
        ],
    )
    assert ET.fromstring(reg_xml).find("REGISTERS/REGISTER/NAME").text == "VAT-S"  # type: ignore[union-attr]
    assert ET.fromstring(pm_xml).find("PAYMENT_METHODS/PAYMENT_METHOD/NAME").text == "Cash"  # type: ignore[union-attr]
    assert (
        ET.fromstring(desc_xml)
        .find(  # type: ignore[union-attr]
            "DESCRIPTIONS/DESCRIPTION/VALUE"
        )
        .text
        == "goods purchase"
    )


# ---- _build_company_synchronize_xml ---------------------------------------------


def test_company_synchronize_emits_each_pair() -> None:
    """company.synchronize: <ROOT><COMPANIES><COMPANY><COMPANY_ID/>
    <COMPANY_PROGRAM_ID/></COMPANY>...</COMPANIES></ROOT>."""
    xml = _build_company_synchronize_xml(
        [
            CompanySynchronizeInput(company_id=42, company_program_id="ERP-001"),
            CompanySynchronizeInput(company_id=99, company_program_id="ERP-002"),
        ]
    )
    root = ET.fromstring(xml)
    items = root.findall("COMPANIES/COMPANY")
    assert len(items) == 2
    assert items[0].findtext("COMPANY_ID") == "42"
    assert items[0].findtext("COMPANY_PROGRAM_ID") == "ERP-001"
    assert items[1].findtext("COMPANY_ID") == "99"
    assert items[1].findtext("COMPANY_PROGRAM_ID") == "ERP-002"


# ---- _build_employee_add_xml ----------------------------------------------------


def test_employee_add_create_branch_includes_required_names() -> None:
    """Create branch: ACRONYM + FIRST_NAME + LAST_NAME present, EMPLOYEE_ID absent."""
    xml = _build_employee_add_xml(
        [
            EmployeeAddInput(acronym="JD", first_name="Joe", last_name="Doe", email="joe@x.io"),
        ]
    )
    el = ET.fromstring(xml).find("EMPLOYEES/EMPLOYEE")
    assert el is not None
    assert el.find("EMPLOYEE_ID") is None
    assert el.findtext("ACRONYM") == "JD"
    assert el.findtext("FIRST_NAME") == "Joe"
    assert el.findtext("LAST_NAME") == "Doe"
    assert el.findtext("EMAIL") == "joe@x.io"


def test_employee_add_update_branch_keys_off_employee_id() -> None:
    """Update branch: EMPLOYEE_ID leads, name fields optional."""
    xml = _build_employee_add_xml([EmployeeAddInput(employee_id=42, department="HR")])
    el = ET.fromstring(xml).find("EMPLOYEES/EMPLOYEE")
    assert el is not None
    assert el.findtext("EMPLOYEE_ID") == "42"
    assert el.find("ACRONYM") is None
    assert el.findtext("DEPARTMENT") == "HR"


def test_employee_add_emits_contracts_in_order() -> None:
    xml = _build_employee_add_xml(
        [
            EmployeeAddInput(
                acronym="JD",
                first_name="Joe",
                last_name="Doe",
                contracts=[
                    EmployeeContractInput(
                        type="UMOWA_O_PRACE", position="Manager", end_date="2026-12-31"
                    ),
                    EmployeeContractInput(type="UMOWA_ZLECENIE"),
                ],
            )
        ]
    )
    contracts = ET.fromstring(xml).findall("EMPLOYEES/EMPLOYEE/CONTRACTS/CONTRACT")
    assert len(contracts) == 2
    assert contracts[0].findtext("TYPE") == "UMOWA_O_PRACE"
    assert contracts[0].findtext("POSITION") == "Manager"
    assert contracts[0].findtext("ENDATE") == "2026-12-31"
    assert contracts[1].findtext("TYPE") == "UMOWA_ZLECENIE"
    assert contracts[1].find("POSITION") is None


# ---- _build_financial_balance_merge_xml -----------------------------------------


def test_financial_balance_merge_emits_folder_then_balance() -> None:
    """Order: <FOLDER><YEAR/><MONTH/></FOLDER><FINANCIAL_BALANCE>...</FINANCIAL_BALANCE>."""
    xml = _build_financial_balance_merge_xml(
        FinancialBalanceMergeInput(
            year=2026,
            month=4,
            income_month="100000.00",
            cost_month="40000.00",
            vat=FinancialBalanceVATInput(value="13800.00", value_to_shift="200.00"),
        ),
        prepared=[],
    )
    root = ET.fromstring(xml)
    children = list(root)
    assert [c.tag for c in children] == ["FOLDER", "FINANCIAL_BALANCE"]
    assert root.findtext("FOLDER/YEAR") == "2026"
    assert root.findtext("FOLDER/MONTH") == "4"
    assert root.findtext("FINANCIAL_BALANCE/INCOME_MONTH") == "100000.00"
    assert root.findtext("FINANCIAL_BALANCE/COST_MONTH") == "40000.00"
    assert root.findtext("FINANCIAL_BALANCE/VAT/VALUE") == "13800.00"
    assert root.findtext("FINANCIAL_BALANCE/VAT/VALUE_TO_SHIFT") == "200.00"


def test_financial_balance_merge_omits_optional_blocks() -> None:
    xml = _build_financial_balance_merge_xml(
        FinancialBalanceMergeInput(year=2026, month=4), prepared=[]
    )
    fb = ET.fromstring(xml).find("FINANCIAL_BALANCE")
    assert fb is not None
    assert fb.find("VAT") is None
    assert fb.find("INCOME_MONTH") is None
    assert fb.find("COST_MONTH") is None
    assert fb.find("ATTACHMENTS") is None


# ---- build_document_add_xml ----------------------------------------------------


def test_document_add_emits_year_month_attmnt_in_order() -> None:
    """document.add: <DOCUMENT> has YEAR, MONTH, ATTMNT, ATTMNT_NAME in that order."""
    docs = [DocumentAddInput(year=2026, month=4, attachment=Attachment(path="/x/inv.pdf"))]
    prepared = [PreparedAttachment(key="1", form_key="attmnt_1", name="inv.pdf")]
    xml = build_document_add_xml(docs, prepared)
    el = ET.fromstring(xml).find("DOCUMENTS/DOCUMENT")
    assert el is not None
    assert [c.tag for c in el] == ["YEAR", "MONTH", "ATTMNT", "ATTMNT_NAME"]
    assert el.findtext("ATTMNT") == "1"
    assert el.findtext("ATTMNT_NAME") == "inv.pdf"


# ---- _build_personnel_document_add_xml ------------------------------------------


def test_personnel_document_add_keeps_xsd_element_order() -> None:
    """XSD sequence: EMPLOYEE_ID, YEAR, MONTH, ATTMNT, ATTMNT_NAME, DOCUMENT_TYPE,
    NUMBER, DOCUMENT_NAME, DESCRIPTION, DATE_OF_DUTY,
    MARK_WHEN_DATE_OF_DUTY_EXPIRED, NOTIFICATION_DATE."""
    docs = [
        PersonnelDocumentAddInput(
            employee_id=42,
            year=2026,
            month=4,
            document_type="PART_A",
            attachment=Attachment(path="/x/scan.pdf"),
            number=7,
            document_name="Contract A",
            description="annex",
            date_of_duty="2026-04-01",
            mark_when_date_of_duty_expired=True,
            notification_date="2026-03-25",
        )
    ]
    prepared = [PreparedAttachment(key="1", form_key="attmnt_1", name="scan.pdf")]
    xml = _build_personnel_document_add_xml(docs, prepared)
    el = ET.fromstring(xml).find("PERSONNEL_DOCUMENTS/PERSONNEL_DOCUMENT")
    assert el is not None
    assert [c.tag for c in el] == [
        "EMPLOYEE_ID",
        "YEAR",
        "MONTH",
        "ATTMNT",
        "ATTMNT_NAME",
        "DOCUMENT_TYPE",
        "NUMBER",
        "DOCUMENT_NAME",
        "DESCRIPTION",
        "DATE_OF_DUTY",
        "MARK_WHEN_DATE_OF_DUTY_EXPIRED",
        "NOTIFICATION_DATE",
    ]
    assert el.findtext("ATTMNT") == "1"
    assert el.findtext("ATTMNT_NAME") == "scan.pdf"
    assert el.findtext("DOCUMENT_TYPE") == "PART_A"
    assert el.findtext("MARK_WHEN_DATE_OF_DUTY_EXPIRED") == "true"


# ---- build_document_add_recognize_xml ------------------------------------------


def test_document_add_recognize_emits_required_fields_only_when_set() -> None:
    """document.add_recognize: VAT_NUMBER + SPLIT_MODE always present;
    DOCUMENT_TYPE / NO_ROTATE only when caller set them. No <ATTMNT> tag —
    binary file goes through the attmnt_1 form field."""
    xml = build_document_add_recognize_xml(
        DocumentAddRecognizeInput(
            attachment=Attachment(path="/x/inv.pdf"),
            vat_number="1234567890",
            split_mode="AUTO_TWO_SIDED",
            document_type="COST",
            no_rotate=True,
        )
    )
    el = ET.fromstring(xml).find("DOCUMENT")
    assert el is not None
    assert el.findtext("VAT_NUMBER") == "1234567890"
    assert el.findtext("SPLIT_MODE") == "AUTO_TWO_SIDED"
    assert el.findtext("DOCUMENT_TYPE") == "COST"
    assert el.findtext("NO_ROTATE") == "true"
    assert el.find("ATTMNT") is None


# ---- build_document_correct_xml ------------------------------------------------


def test_document_correct_skips_contractor_when_omitted() -> None:
    xml = build_document_correct_xml(
        [DocumentCorrectInput(document_id=42, number="FV-2026-1", self_learning=True)]
    )
    el = ET.fromstring(xml).find("DOCUMENTS/DOCUMENT")
    assert el is not None
    assert el.findtext("DOCUMENT_ID") == "42"
    assert el.findtext("NUMBER") == "FV-2026-1"
    assert el.find("CONTRACTOR") is None
    assert el.findtext("SELF_LEARNING") == "true"


def test_document_correct_emits_full_contractor_block() -> None:
    xml = build_document_correct_xml(
        [
            DocumentCorrectInput(
                document_id=42,
                contractor=DocumentCorrectContractorInput(
                    short_name="ACME",
                    full_name="Acme Sp. z o.o.",
                    vat_number="1234567890",
                    street="Rynek 1",
                    city="Krakow",
                    postcode="30-001",
                ),
            )
        ]
    )
    contractor = ET.fromstring(xml).find("DOCUMENTS/DOCUMENT/CONTRACTOR")
    assert contractor is not None
    assert [c.tag for c in contractor] == [
        "SHORT_NAME",
        "FULL_NAME",
        "VAT_NUMBER",
        "STREET",
        "CITY",
        "POSTCODE",
    ]


def test_personnel_document_add_minimum_fields() -> None:
    docs = [
        PersonnelDocumentAddInput(
            year=2026,
            month=4,
            document_type="OTHER",
            attachment=Attachment(path="/x/file.pdf"),
        )
    ]
    prepared = [PreparedAttachment(key="1", form_key="attmnt_1", name="file.pdf")]
    el = ET.fromstring(_build_personnel_document_add_xml(docs, prepared)).find(
        "PERSONNEL_DOCUMENTS/PERSONNEL_DOCUMENT"
    )
    assert el is not None
    # Optional fields are omitted entirely.
    assert el.find("EMPLOYEE_ID") is None
    assert el.find("NUMBER") is None
    assert el.find("DESCRIPTION") is None


# ---- _build_declaration_merge_xml -----------------------------------------------


def test_declaration_merge_emits_folder_and_taxes_in_order() -> None:
    """SSK02: <ROOT><FOLDER/><TAXES><TAX>...</TAX></TAXES></ROOT>."""
    declarations = DeclarationMergeInput(
        year=2026,
        month=4,
        taxes=[
            DeclarationTaxInput(
                declaration_program_id="PIT-37/2026/04",
                tax_details=TaxDetailsInput(
                    type="PIT37",
                    period="04/2026",
                    period_type="MONTH",
                    deadline="2026-05-20",
                    tax_value="100.00",
                ),
            )
        ],
    )
    xml = _build_declaration_merge_xml(declarations, prepared=[])
    root = ET.fromstring(xml)
    assert [c.tag for c in root] == ["FOLDER", "TAXES"]
    assert root.findtext("FOLDER/YEAR") == "2026"
    tax = root.find("TAXES/TAX")
    assert tax is not None
    assert tax.findtext("DECLARATION_PROGRAM_ID") == "PIT-37/2026/04"
    assert tax.findtext("TAX_DETAILS/PERIOD_TYPE") == "MONTH"
    assert tax.find("ATTACHMENTS") is None


def test_declaration_merge_threads_attachments_per_tax() -> None:
    """Each TAX consumes its own slice of the prepared-attachment list."""
    declarations = DeclarationMergeInput(
        year=2026,
        month=4,
        taxes=[
            DeclarationTaxInput(
                declaration_program_id="A",
                attachments=[
                    CloseAttachmentInput(
                        type="DECLARATION",
                        name="a1",
                        attachment=Attachment(path="/x/a1.pdf"),
                    ),
                ],
            ),
            DeclarationTaxInput(
                declaration_program_id="B",
                attachments=[
                    CloseAttachmentInput(
                        type="REPORT",
                        name="b1",
                        attachment=Attachment(path="/x/b1.pdf"),
                    ),
                    CloseAttachmentInput(
                        type="REPORT",
                        name="b2",
                        attachment=Attachment(path="/x/b2.pdf"),
                    ),
                ],
            ),
        ],
    )
    prepared = [
        PreparedAttachment(key="1", form_key="attmnt_1", name="a1.pdf"),
        PreparedAttachment(key="2", form_key="attmnt_2", name="b1.pdf"),
        PreparedAttachment(key="3", form_key="attmnt_3", name="b2.pdf"),
    ]
    xml = _build_declaration_merge_xml(declarations, prepared)
    taxes = ET.fromstring(xml).findall("TAXES/TAX")
    assert len(taxes) == 2
    a_atts = taxes[0].findall("ATTACHMENTS/ATTACHMENT")
    assert len(a_atts) == 1
    assert a_atts[0].findtext("ATTMNT") == "1"
    assert a_atts[0].findtext("ATTMNT_NAME") == "a1.pdf"
    b_atts = taxes[1].findall("ATTACHMENTS/ATTACHMENT")
    assert len(b_atts) == 2
    assert b_atts[0].findtext("ATTMNT") == "2"
    assert b_atts[1].findtext("ATTMNT") == "3"


# ---- _build_assurance_renew_xml -------------------------------------------------


def test_assurance_renew_employees_variant_emits_zus_totals() -> None:
    assurances = AssuranceRenewInput(
        year=2026,
        month=4,
        assurances=[
            AssuranceItemInput(
                assurance_program_id="ZUS-04/2026",
                details=AssuranceEmployeesDetailsInput(
                    period="04/2026",
                    deadline="2026-05-15",
                    zus_51="1000.00",
                    zus_52="200.00",
                ),
            )
        ],
    )
    xml = _build_assurance_renew_xml(assurances, prepared=[])
    details = ET.fromstring(xml).find("ASSURANCES/ASSURANCE/ASSURANCE_DETAILS")
    assert details is not None
    assert details.findtext("TYPE") == "EMPLOYEES"
    assert details.findtext("ZUS-51") == "1000.00"
    assert details.findtext("ZUS-52") == "200.00"
    assert details.find("ZUS-53") is None


def test_assurance_renew_personal_variant_emits_person_block() -> None:
    assurances = AssuranceRenewInput(
        year=2026,
        month=4,
        assurances=[
            AssuranceItemInput(
                assurance_program_id="EMP-1",
                details=AssurancePersonalDetailsInput(
                    last_name="Doe",
                    first_name="Jane",
                    person_id_type="PES",
                    person_id="12345678901",
                    period="04/2026",
                    deadline="2026-05-15",
                ),
            )
        ],
    )
    details = ET.fromstring(_build_assurance_renew_xml(assurances, prepared=[])).find(
        "ASSURANCES/ASSURANCE/ASSURANCE_DETAILS"
    )
    assert details is not None
    assert details.findtext("TYPE") == "PERSONAL"
    assert details.findtext("LAST_NAME") == "Doe"
    assert details.findtext("PERSON_ID_TYPE") == "PES"


def test_assurance_renew_company_variant_uses_owner_fields() -> None:
    assurances = AssuranceRenewInput(
        year=2026,
        month=4,
        assurances=[
            AssuranceItemInput(
                assurance_program_id="OWNER",
                details=AssuranceCompanyDetailsInput(
                    period="04/2026",
                    deadline="2026-05-15",
                    zus_contribution="900.00",
                ),
            )
        ],
    )
    details = ET.fromstring(_build_assurance_renew_xml(assurances, prepared=[])).find(
        "ASSURANCES/ASSURANCE/ASSURANCE_DETAILS"
    )
    assert details is not None
    assert details.findtext("TYPE") == "COMPANY"
    assert details.findtext("ZUS_CONTRIBUTION") == "900.00"
    assert details.find("LAST_NAME") is None  # not the personal/partner branch


def test_assurance_renew_partner_variant_emits_underpayment() -> None:
    assurances = AssuranceRenewInput(
        year=2026,
        month=4,
        assurances=[
            AssuranceItemInput(
                assurance_program_id="P-1",
                details=AssurancePartnerDetailsInput(
                    last_name="Doe",
                    first_name="Pat",
                    person_id_type="NIP",
                    person_id="9876543210",
                    period="04/2026",
                    deadline="2026-05-15",
                    zus_underpayment="50.00",
                ),
            )
        ],
    )
    details = ET.fromstring(_build_assurance_renew_xml(assurances, prepared=[])).find(
        "ASSURANCES/ASSURANCE/ASSURANCE_DETAILS"
    )
    assert details is not None
    assert details.findtext("TYPE") == "PARTNER"
    assert details.findtext("ZUS_UNDERPAYMENT") == "50.00"


# ---- build_document_import_xml -------------------------------------------------


def test_document_import_emits_minimal_required_fields() -> None:
    """The 3.0 import shape: <DOCUMENT> always carries ATTMNT, ATTMNT_NAME,
    YEAR, MONTH, DOCUMENT_TYPE in that order."""
    docs = [
        DocumentImportInput(
            year=2026,
            month=4,
            document_type=DocumentImportTypeInput(short_name="DS", model_type="INVOICE_SALES"),
            attachment=Attachment(path="/x/inv.pdf"),
        )
    ]
    prepared = [PreparedAttachment(key="1", form_key="attmnt_1", name="inv.pdf")]
    el = ET.fromstring(build_document_import_xml(docs, prepared)).find("DOCUMENTS/DOCUMENT")
    assert el is not None
    leading = [c.tag for c in el][:5]
    assert leading == ["ATTMNT", "ATTMNT_NAME", "YEAR", "MONTH", "DOCUMENT_TYPE"]
    assert el.findtext("ATTMNT") == "1"
    assert el.findtext("DOCUMENT_TYPE/SHORT_NAME") == "DS"
    assert el.findtext("DOCUMENT_TYPE/MODEL_TYPE") == "INVOICE_SALES"


def test_document_import_picks_id_branch_for_document_type() -> None:
    docs = [
        DocumentImportInput(
            year=2026,
            month=4,
            document_type=DocumentImportTypeInput(id=42),
            attachment=Attachment(path="/x/a.pdf"),
        )
    ]
    prepared = [PreparedAttachment(key="1", form_key="attmnt_1", name="a.pdf")]
    type_el = ET.fromstring(build_document_import_xml(docs, prepared)).find(
        "DOCUMENTS/DOCUMENT/DOCUMENT_TYPE"
    )
    assert type_el is not None
    assert type_el.findtext("ID") == "42"
    assert type_el.find("SHORT_NAME") is None  # ID branch wins


def test_document_import_emits_currency_dimensions_vat_block() -> None:
    docs = [
        DocumentImportInput(
            year=2026,
            month=4,
            document_type=DocumentImportTypeInput(short_name="FK", model_type="INVOICE_COST"),
            attachment=Attachment(path="/x/a.pdf"),
            currency=DocumentImportCurrencyInput(iso4217="EUR", date="2026-04-01", rate="4.3000"),
            dimensions=[
                DocumentImportDimensionInput(name="Cost center", value="OPS"),
            ],
            vat_document=DocumentImportVATInput(
                vat_registries=[
                    DocumentImportVATRegistryInput(rate="23", netto="100.00", vat="23.00"),
                ],
                items=[
                    DocumentImportVATItemInput(
                        rate="23",
                        netto="100.00",
                        vat="23.00",
                        category="Materials",
                        description="Office supplies",
                    ),
                ],
            ),
        )
    ]
    prepared = [PreparedAttachment(key="1", form_key="attmnt_1", name="a.pdf")]
    doc = ET.fromstring(build_document_import_xml(docs, prepared)).find("DOCUMENTS/DOCUMENT")
    assert doc is not None
    assert doc.findtext("CURRENCY/CURRENCY_ISO4217") == "EUR"
    assert doc.findtext("CURRENCY/CURRENCY_RATE") == "4.3000"
    assert doc.findtext("DIMENSIONS/DIMENSION/NAME") == "Cost center"
    assert doc.findtext("VAT_DOCUMENT/VAT_REGISTRIES/VAT_REGISTRY/RATE") == "23"
    assert doc.findtext("VAT_DOCUMENT/ITEMS/ITEM/CATEGORY") == "Materials"
    assert doc.find("NO_VAT_DOCUMENT") is None  # VAT branch wins


def test_document_import_threads_supporting_attachments_after_source_file() -> None:
    """Each <DOCUMENT> consumes 1 + len(doc.attachments) prepared entries:
    the source file first, then each <ATTACHMENT>'s ATTMNT reference."""
    docs = [
        DocumentImportInput(
            year=2026,
            month=4,
            document_type=DocumentImportTypeInput(short_name="DS"),
            attachment=Attachment(path="/x/main.pdf"),
            attachments=[
                DocumentImportAttachmentInput(
                    attachment=Attachment(path="/x/extra1.pdf"),
                    description="annex 1",
                ),
                DocumentImportAttachmentInput(
                    attachment=Attachment(path="/x/extra2.pdf"),
                ),
            ],
        )
    ]
    prepared = [
        PreparedAttachment(key="1", form_key="attmnt_1", name="main.pdf"),
        PreparedAttachment(key="2", form_key="attmnt_2", name="extra1.pdf"),
        PreparedAttachment(key="3", form_key="attmnt_3", name="extra2.pdf"),
    ]
    doc = ET.fromstring(build_document_import_xml(docs, prepared)).find("DOCUMENTS/DOCUMENT")
    assert doc is not None
    assert doc.findtext("ATTMNT") == "1"
    assert doc.findtext("ATTMNT_NAME") == "main.pdf"
    extras = doc.findall("ATTACHMENTS/ATTACHMENT")
    assert len(extras) == 2
    assert extras[0].findtext("ATTMNT") == "2"
    assert extras[0].findtext("DESCRIPTION") == "annex 1"
    assert extras[1].findtext("ATTMNT") == "3"
    assert extras[1].find("DESCRIPTION") is None


# ---- _build_invoice_add_xml -----------------------------------------------------


def test_invoice_add_emits_required_fields_and_at_least_one_item() -> None:
    invoice = InvoiceAddInput(
        issue_date="2026-04-30",
        according_to_agreement=True,
        purchaser_contractor_id=42,
        currency_iso4217="PLN",
        payment_type="TRANSFER",
        items=[
            InvoiceAddItemInput(
                name="Office Chair",
                amount="10",
                unit="pieces",
                unit_value="159.99",
                rate="23",
            ),
        ],
    )
    el = ET.fromstring(_build_invoice_add_xml(invoice)).find("INVOICE")
    assert el is not None
    assert el.findtext("ISSUE_DATE") == "2026-04-30"
    assert el.findtext("ACCORDING_TO_AGREEMENT") == "true"
    assert el.findtext("PURCHASER_CONTRACTOR_ID") == "42"
    assert el.findtext("CURRENCY_ISO4217") == "PLN"
    assert el.findtext("PAYMENT_TYPE") == "TRANSFER"
    items = el.findall("INVOICE_ITEMS/INVOICE_ITEM")
    assert len(items) == 1
    assert items[0].findtext("NAME") == "Office Chair"
    assert items[0].findtext("RATE") == "23"


def test_invoice_add_choice_picks_sale_date_range_over_sale_date() -> None:
    """xs:choice between SALE_DATE and (SALE_DATE_FROM, SALE_DATE_TO)."""
    invoice = InvoiceAddInput(
        issue_date="2026-04-30",
        according_to_agreement=True,
        purchaser_contractor_id=1,
        currency_iso4217="PLN",
        payment_type="CASH",
        items=[InvoiceAddItemInput(name="Service", amount="1", unit="ea", unit_value="100")],
        sale_date="2026-04-30",
        sale_date_range=InvoiceAddSaleDateRangeInput(from_date="2026-04-01", to_date="2026-04-30"),
    )
    el = ET.fromstring(_build_invoice_add_xml(invoice)).find("INVOICE")
    assert el is not None
    assert el.findtext("SALE_DATE_FROM") == "2026-04-01"
    assert el.findtext("SALE_DATE_TO") == "2026-04-30"
    # SALE_DATE is suppressed when the range is set.
    assert el.find("SALE_DATE") is None


def test_invoice_add_emits_discount_payments_and_vehicle_blocks() -> None:
    invoice = InvoiceAddInput(
        issue_date="2026-04-30",
        according_to_agreement=False,
        purchaser_contractor_id=1,
        currency_iso4217="EUR",
        payment_type="TRANSFER",
        items=[
            InvoiceAddItemInput(
                name="Conf Table",
                amount="3",
                unit="pieces",
                unit_value="899.99",
                discount=InvoiceAddDiscountInput(type="PERCENTAGE", value="10"),
                rate="ZW",
            ),
        ],
        bank_account=InvoiceAddBankAccountInput(
            number="46101014690081782231000000", bic_swift="DEUTPLPK"
        ),
        payments=[
            InvoiceAddPaymentInput(payment_amount="50", payment_date="2026-05-15"),
        ],
        new_transport_vehicle=InvoiceAddNewTransportVehicleInput(
            vehicle_type="LAND",
            admission_date="2026-04-01",
            usage_metrics=5000,
        ),
    )
    el = ET.fromstring(_build_invoice_add_xml(invoice)).find("INVOICE")
    assert el is not None
    item = el.find("INVOICE_ITEMS/INVOICE_ITEM")
    assert item is not None
    assert item.findtext("DISCOUNT/DISCOUNT_TYPE") == "PERCENTAGE"
    assert item.findtext("DISCOUNT/DISCOUNT_VALUE") == "10"
    assert el.findtext("BANK_ACCOUNT/BIC_SWIFT") == "DEUTPLPK"
    assert el.findtext("INVOICE_PAYMENTS/PAYMENT_AMOUNT") == "50"
    assert el.findtext("NEW_TRANSPORT_VEHICLE/VEHICLE_TYPE") == "LAND"


# ---- _build_company_create_xml --------------------------------------------------


def test_company_create_emits_required_fields_with_bank_accounts() -> None:
    """company.create: METAINF/PRODUCER (when set) leads, then COMPANIES/COMPANY
    in XSD order."""
    companies = [
        CompanyCreateInput(
            company_program_id="ERP-001",
            username="admin1",
            email="admin@example.com",
            short_name="ACME",
            full_name="Acme Sp. z o.o.",
            vat_number="1234567890",
            city="Krakow",
            postcode="30-001",
            street="Rynek 1",
            bank_accounts=[
                CompanyCreateBankAccountInput(
                    number="46101014690081782231000000",
                    bank_name="Bank A",
                    bic_number="BKEAPLPW",
                    currency_iso4217="PLN",
                ),
            ],
            producer="ERP-X",
        )
    ]
    root = ET.fromstring(_build_company_create_xml(companies))
    assert root.findtext("METAINF/PRODUCER") == "ERP-X"
    company = root.find("COMPANIES/COMPANY")
    assert company is not None
    assert company.findtext("COMPANY_PROGRAM_ID") == "ERP-001"
    assert company.findtext("EMAIL") == "admin@example.com"
    assert company.findtext("SHORT_NAME") == "ACME"
    bank = company.find("BANK_ACCOUNTS/BANK_ACCOUNT")
    assert bank is not None
    assert bank.findtext("NUMBER") == "46101014690081782231000000"
    assert bank.findtext("BIC_NUMBER") == "BKEAPLPW"


def test_company_create_omits_metainf_when_no_producer() -> None:
    companies = [
        CompanyCreateInput(
            company_program_id="ERP-002",
            username="admin2",
            email="x@y.io",
            short_name="X",
            full_name="X Ltd",
            vat_number="9999999999",
            city="Warsaw",
            postcode="00-001",
            street="Marszalkowska 1",
        )
    ]
    root = ET.fromstring(_build_company_create_xml(companies))
    assert root.find("METAINF") is None
    assert root.find("COMPANIES/COMPANY") is not None
