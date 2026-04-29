"""Tests for Document.from_xml against the real shapes returned by SaldeoSMART.

These guard against the regression where the parser used invented field names
(VALUE_NET / VALUE_GROSS / VALUE_VAT / CURRENCY / DOCUMENT_ITEMS) instead of
the names the API actually emits (SUM, VAT_REGISTRIES/NETTO+VAT,
CURRENCY_ISO4217, plus ITEMS for invoice/list and DOCUMENT_ITEMS for
document/list). When that mismatch was in place every monetary field came
back empty and ``items`` was always [] for sales invoices.

Fixtures here mirror the structure documented in
``.temp/api-html-mirror/1_20/invoice/`` and ``.temp/api-html-mirror/2_12/document/``.
"""

from xml.etree import ElementTree as ET

from saldeosmart_mcp.models.companies import Company
from saldeosmart_mcp.models.contractors import Contractor
from saldeosmart_mcp.models.documents import Document, _sum_vat_registries

# ---- invoice/list (v1.20) shape --------------------------------------------------

INVOICE_LIST_EXAMPLE = """
<INVOICE>
  <INVOICE_ID>64</INVOICE_ID>
  <NUMBER>1/12/2015</NUMBER>
  <ISSUE_DATE>2015-12-31</ISSUE_DATE>
  <SALE_DATE>2015-12-31</SALE_DATE>
  <PAYMENT_DATE>2016-01-15</PAYMENT_DATE>
  <CONTRACTOR>
    <CONTRACTOR_ID>2</CONTRACTOR_ID>
    <NIP>9355066730</NIP>
  </CONTRACTOR>
  <SUM>184.50</SUM>
  <PAID_SUM>10.00</PAID_SUM>
  <VAT_REGISTRIES>
    <VAT_REGISTRY>
      <RATE>23</RATE>
      <NETTO>150.00</NETTO>
      <VAT>34.50</VAT>
    </VAT_REGISTRY>
  </VAT_REGISTRIES>
  <CURRENCY_ISO4217>PLN</CURRENCY_ISO4217>
  <SOURCE>/docs/1/122015-fakt/faktura-1-12-2015.pdf</SOURCE>
  <ITEMS>
    <ITEM>
      <RATE>23</RATE>
      <NETTO>100.00</NETTO>
      <VAT>23.00</VAT>
      <GROSS>123.00</GROSS>
      <CATEGORY>cat</CATEGORY>
      <DESCRIPTION>desc</DESCRIPTION>
    </ITEM>
    <ITEM>
      <RATE>23</RATE>
      <NETTO>50</NETTO>
      <VAT>11.50</VAT>
      <GROSS>61.50</GROSS>
      <CATEGORY>cat2</CATEGORY>
      <DESCRIPTION>desc2</DESCRIPTION>
    </ITEM>
  </ITEMS>
</INVOICE>
"""


def test_invoice_list_amounts_populate_from_sum_and_vat_registries() -> None:
    doc = Document.from_xml(ET.fromstring(INVOICE_LIST_EXAMPLE))
    assert doc.value_gross == "184.50"
    assert doc.value_net == "150.00"
    assert doc.value_vat == "34.50"
    assert doc.currency == "PLN"


def test_invoice_list_uses_invoice_id_as_document_id() -> None:
    doc = Document.from_xml(ET.fromstring(INVOICE_LIST_EXAMPLE))
    assert doc.document_id == 64
    assert doc.number == "1/12/2015"


def test_invoice_list_payment_date_falls_back_to_payment_due_date() -> None:
    doc = Document.from_xml(ET.fromstring(INVOICE_LIST_EXAMPLE))
    assert doc.payment_due_date == "2016-01-15"


def test_invoice_list_items_parsed_from_items_container() -> None:
    doc = Document.from_xml(ET.fromstring(INVOICE_LIST_EXAMPLE))
    assert len(doc.items) == 2
    first, second = doc.items
    assert first.value_net == "100.00"
    assert first.value_gross == "123.00"
    assert first.vat_rate == "23"
    assert first.category == "cat"
    # Invoice items have no <NAME>; parser falls back to <DESCRIPTION>.
    assert first.name == "desc"
    assert second.value_net == "50"


def test_invoice_list_source_falls_back_to_source_when_url_absent() -> None:
    doc = Document.from_xml(ET.fromstring(INVOICE_LIST_EXAMPLE))
    assert doc.source_url == "/docs/1/122015-fakt/faktura-1-12-2015.pdf"


# ---- document/list (v2.12) shape -------------------------------------------------

DOCUMENT_LIST_EXAMPLE = """
<DOCUMENT>
  <DOCUMENT_ID>9001</DOCUMENT_ID>
  <NUMBER>FV/2026/04/15</NUMBER>
  <ISSUE_DATE>2026-04-15</ISSUE_DATE>
  <SALE_DATE>2026-04-15</SALE_DATE>
  <PAYMENT_DATE>2026-04-29</PAYMENT_DATE>
  <SUM>1230.00</SUM>
  <VAT_REGISTRIES>
    <VAT_REGISTRY><RATE>23</RATE><NETTO>500.00</NETTO><VAT>115.00</VAT></VAT_REGISTRY>
    <VAT_REGISTRY><RATE>8</RATE><NETTO>500.00</NETTO><VAT>40.00</VAT></VAT_REGISTRY>
  </VAT_REGISTRIES>
  <CURRENCY_ISO4217>PLN</CURRENCY_ISO4217>
  <SOURCE_URL>https://saldeo/example/source</SOURCE_URL>
  <IS_MPP>true</IS_MPP>
  <DOCUMENT_ITEMS>
    <DOCUMENT_ITEM>
      <NAME>Towar A</NAME>
      <AMOUNT>2.5</AMOUNT>
      <UNIT>kg</UNIT>
      <RATE>23</RATE>
      <UNIT_VALUE>200.00</UNIT_VALUE>
      <NETTO>500.00</NETTO>
      <VAT>115.00</VAT>
      <GROSS>615.00</GROSS>
      <CATEGORY>X</CATEGORY>
    </DOCUMENT_ITEM>
  </DOCUMENT_ITEMS>
</DOCUMENT>
"""


def test_document_list_aggregates_value_net_and_vat_across_registries() -> None:
    doc = Document.from_xml(ET.fromstring(DOCUMENT_LIST_EXAMPLE))
    assert doc.value_gross == "1230.00"
    assert doc.value_net == "1000.00"
    assert doc.value_vat == "155.00"
    assert doc.currency == "PLN"


def test_document_list_items_parsed_from_document_items_container() -> None:
    doc = Document.from_xml(ET.fromstring(DOCUMENT_LIST_EXAMPLE))
    assert len(doc.items) == 1
    item = doc.items[0]
    assert item.name == "Towar A"
    assert item.quantity == "2.5"
    assert item.unit_price_net == "200.00"
    assert item.value_net == "500.00"
    assert item.value_gross == "615.00"
    assert item.vat_rate == "23"


def test_document_list_prefers_source_url_when_present() -> None:
    doc = Document.from_xml(ET.fromstring(DOCUMENT_LIST_EXAMPLE))
    assert doc.source_url == "https://saldeo/example/source"
    assert doc.is_mpp is True


# ---- edge cases ------------------------------------------------------------------


def test_currency_falls_back_from_iso4217_to_legacy_currency() -> None:
    xml = "<DOCUMENT><DOCUMENT_ID>1</DOCUMENT_ID><CURRENCY>EUR</CURRENCY></DOCUMENT>"
    doc = Document.from_xml(ET.fromstring(xml))
    assert doc.currency == "EUR"


def test_missing_vat_registries_yields_none_for_value_net_and_vat() -> None:
    xml = "<DOCUMENT><DOCUMENT_ID>1</DOCUMENT_ID><SUM>99.00</SUM></DOCUMENT>"
    doc = Document.from_xml(ET.fromstring(xml))
    assert doc.value_gross == "99.00"
    assert doc.value_net is None
    assert doc.value_vat is None


def test_sum_vat_registries_skips_unparseable_entries() -> None:
    xml = """
    <X>
      <VAT_REGISTRIES>
        <VAT_REGISTRY><NETTO>10.00</NETTO></VAT_REGISTRY>
        <VAT_REGISTRY><NETTO>not-a-number</NETTO></VAT_REGISTRY>
        <VAT_REGISTRY><NETTO>5.50</NETTO></VAT_REGISTRY>
      </VAT_REGISTRIES>
    </X>
    """
    assert _sum_vat_registries(ET.fromstring(xml), "NETTO") == "15.50"


def test_empty_document_does_not_crash() -> None:
    doc = Document.from_xml(ET.fromstring("<DOCUMENT/>"))
    assert doc.document_id is None
    assert doc.value_net is None
    assert doc.value_gross is None
    assert doc.items == []


# ---- Contractor.from_xml --------------------------------------------------------
#
# The dictionary form (under <CONTRACTORS><CONTRACTOR>) carries STREET/POSTCODE,
# while embedded contractors (under <DOCUMENT><CONTRACTOR>) carry only ID +
# CONTRACTOR_PROGRAM_ID + NIP. The parser accepts both shapes.

CONTRACTOR_LIST_EXAMPLE = """
<CONTRACTOR>
  <CONTRACTOR_ID>2</CONTRACTOR_ID>
  <CONTRACTOR_PROGRAM_ID>EXT-7</CONTRACTOR_PROGRAM_ID>
  <SHORT_NAME>kontr</SHORT_NAME>
  <FULL_NAME>Kontrahent S.A.</FULL_NAME>
  <VAT_NUMBER>9355066730</VAT_NUMBER>
  <CITY>Krakow</CITY>
  <POSTCODE>30-072</POSTCODE>
  <STREET>ulica Testowa 1</STREET>
  <INACTIVE>false</INACTIVE>
</CONTRACTOR>
"""


def test_contractor_reads_street_and_postcode_not_address() -> None:
    c = Contractor.from_xml(ET.fromstring(CONTRACTOR_LIST_EXAMPLE))
    assert c.address == "ulica Testowa 1"
    assert c.postal_code == "30-072"
    assert c.city == "Krakow"


def test_contractor_legacy_address_postal_code_still_parsed() -> None:
    """If Saldeo ever ships the alternative spellings, fall back to them."""
    xml = (
        "<CONTRACTOR>"
        "<ADDRESS>ul. Stara 5</ADDRESS>"
        "<POSTAL_CODE>00-001</POSTAL_CODE>"
        "</CONTRACTOR>"
    )
    c = Contractor.from_xml(ET.fromstring(xml))
    assert c.address == "ul. Stara 5"
    assert c.postal_code == "00-001"


def test_contractor_embedded_in_document_uses_nip_for_vat_number() -> None:
    """In <DOCUMENT><CONTRACTOR> the VAT number is sent as <NIP>, not <VAT_NUMBER>."""
    xml = (
        "<CONTRACTOR>"
        "<CONTRACTOR_ID>5</CONTRACTOR_ID>"
        "<NIP>5242910139</NIP>"
        "</CONTRACTOR>"
    )
    c = Contractor.from_xml(ET.fromstring(xml))
    assert c.vat_number == "5242910139"
    assert c.contractor_id == 5


def test_contractor_inactive_flag() -> None:
    xml = "<CONTRACTOR><INACTIVE>true</INACTIVE></CONTRACTOR>"
    assert Contractor.from_xml(ET.fromstring(xml)).inactive is True


# ---- Company.from_xml -----------------------------------------------------------

COMPANY_LIST_EXAMPLE = """
<COMPANY>
  <COMPANY_PROGRAM_ID>72c905b6</COMPANY_PROGRAM_ID>
  <COMPANY_ID>5202</COMPANY_ID>
  <SHORT_NAME>PMB</SHORT_NAME>
  <FULL_NAME>PMB Sp. z o.o.</FULL_NAME>
  <VAT_NUMBER>PL8921393139</VAT_NUMBER>
  <CITY>Warszawa</CITY>
  <POSTCODE>02-001</POSTCODE>
  <STREET>ul. Przykladowa 12</STREET>
</COMPANY>
"""


def test_company_name_falls_back_from_full_name_to_name() -> None:
    c = Company.from_xml(ET.fromstring(COMPANY_LIST_EXAMPLE))
    assert c.name == "PMB Sp. z o.o."
    assert c.short_name == "PMB"


def test_company_address_reads_street_not_address() -> None:
    c = Company.from_xml(ET.fromstring(COMPANY_LIST_EXAMPLE))
    assert c.address == "ul. Przykladowa 12"
    assert c.postal_code == "02-001"
    assert c.city == "Warszawa"


def test_company_program_id_and_vat_number() -> None:
    c = Company.from_xml(ET.fromstring(COMPANY_LIST_EXAMPLE))
    assert c.company_id == 5202
    assert c.program_id == "72c905b6"
    assert c.vat_number == "PL8921393139"


def test_company_legacy_name_address_still_parsed() -> None:
    xml = (
        "<COMPANY>"
        "<NAME>Old Co.</NAME>"
        "<ADDRESS>ul. Stara 5</ADDRESS>"
        "<POSTAL_CODE>00-001</POSTAL_CODE>"
        "</COMPANY>"
    )
    c = Company.from_xml(ET.fromstring(xml))
    assert c.name == "Old Co."
    assert c.address == "ul. Stara 5"
    assert c.postal_code == "00-001"
