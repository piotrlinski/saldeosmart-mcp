"""Tests for SaldeoSMART request-XML builders.

Two classes of bug we guard against:

1. **Element name mismatches.** The same kind of bug we found in the response
   parsers: builders writing `<X>` while the spec wants `<Y>`. The catalog
   builder used to emit `<CONTRACTOR_PROGRAM_ID>` inside `<FOREIGN_CODE>`,
   which the article-merge XSD does not define.

2. **Element ordering.** Some Saldeo XSDs declare ``<xs:sequence>``, which
   strict parsers enforce — the wrong order is rejected even when every
   element name is correct. ``document.sync`` is the obvious one.

Reference: ``.temp/api-html-mirror/`` — request schemas (``*_request.xsd``)
and shape examples (``*_request_example.xml``).
"""

from xml.etree import ElementTree as ET

from saldeosmart_mcp.models import (
    ArticleInput,
    DocumentSyncInput,
    ForeignCodeInput,
)
from saldeosmart_mcp.tools.catalog import _build_article_merge_xml
from saldeosmart_mcp.tools.documents import _build_document_sync_xml


# ---- document.sync: element ordering is strict --------------------------------

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


def test_document_sync_emits_elements_in_xsd_order():
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
    root = ET.fromstring(_build_document_sync_xml([sync]))
    sync_el = root.find("DOCUMENT_SYNCS/DOCUMENT_SYNC")
    assert sync_el is not None
    actual_order = [child.tag for child in sync_el]
    assert actual_order == EXPECTED_SYNC_ORDER


def test_document_sync_omits_unset_optional_fields():
    """Only the required identifiers are sent — unset Optional fields stay out."""
    sync = DocumentSyncInput(
        contractor_program_id="C1",
        document_number="N1",
        guid="G1",
        description="D",
        numbering_type="NT",
        account_document_number="ADN",
    )
    root = ET.fromstring(_build_document_sync_xml([sync]))
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


# ---- article.merge: FOREIGN_CODE only allows two fields -----------------------

# XSD-equivalent shape (.temp/api-html-mirror/1_14/article/article_merge_request.xml):
#   <FOREIGN_CODE><CONTRACTOR_SHORT_NAME/><CODE/></FOREIGN_CODE>


def test_article_foreign_code_only_emits_short_name_and_code():
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


def test_article_merge_omits_foreign_codes_when_empty():
    article = ArticleInput(name="Towar Y", code="Y-1")
    root = ET.fromstring(_build_article_merge_xml([article]))
    article_el = root.find("ARTICLES/ARTICLE")
    assert article_el is not None
    assert article_el.find("FOREIGN_CODES") is None
