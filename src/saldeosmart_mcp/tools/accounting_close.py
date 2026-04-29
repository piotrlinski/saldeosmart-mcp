"""Accounting-close tools — declaration.merge (SSK02) and assurance.renew (SSK03)."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..http.attachments import Attachment, PreparedAttachment, prepare_attachments
from ..http.xml import set_text
from ..models import (
    AssuranceCompanyDetailsInput,
    AssuranceEmployeesDetailsInput,
    AssuranceItemInput,
    AssurancePartnerDetailsInput,
    AssurancePersonalDetailsInput,
    AssuranceRenewInput,
    DeclarationMergeInput,
    DeclarationTaxInput,
    ErrorResponse,
    MergeResult,
)
from ._builders import append_close_attachments
from ._runtime import get_client, mcp, saldeo_call, summarize_merge


@mcp.tool
@saldeo_call
def merge_declarations(
    company_program_id: str,
    declarations: DeclarationMergeInput,
) -> MergeResult | ErrorResponse:
    """Merge tax declarations into a (year, month) folder (SSK02).

    Each ``<TAX>`` row pins one declaration via ``declaration_program_id``
    and may carry optional ``tax_details`` plus a list of attachments
    (declaration PDF, supporting reports). Saldeo answers per-item with
    ``MERGED`` (existed) or ``CREATED`` (new).
    """
    if not declarations.taxes:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one tax declaration is required.",
        )
    all_attachments: list[Attachment] = []
    for tax in declarations.taxes:
        all_attachments.extend(a.attachment for a in tax.attachments)
    prepared, form = prepare_attachments(all_attachments)
    xml = _build_declaration_merge_xml(declarations, prepared)
    root = get_client().post_command(
        "/api/xml/1.0/declaration/merge",
        xml_command=xml,
        query={"company_program_id": company_program_id},
        extra_form=form,
    )
    return summarize_merge(root, total=len(declarations.taxes))


@mcp.tool
@saldeo_call
def renew_assurances(
    company_program_id: str,
    assurances: AssuranceRenewInput,
) -> MergeResult | ErrorResponse:
    """Renew ZUS / social-insurance declarations (SSK03).

    Each ``<ASSURANCE>`` row pins one assurance via ``assurance_program_id``
    and carries ``details`` discriminated by the assurance type
    (EMPLOYEES, PERSONAL, COMPANY, PARTNER). Saldeo answers per-item with
    ``RENEWED`` (existed) or ``CREATED`` (new).
    """
    if not assurances.assurances:
        return ErrorResponse(
            error="EMPTY_INPUT",
            message="At least one assurance entry is required.",
        )
    all_attachments: list[Attachment] = []
    for item in assurances.assurances:
        all_attachments.extend(a.attachment for a in item.attachments)
    prepared, form = prepare_attachments(all_attachments)
    xml = _build_assurance_renew_xml(assurances, prepared)
    root = get_client().post_command(
        "/api/xml/1.0/assurance/renew",
        xml_command=xml,
        query={"company_program_id": company_program_id},
        extra_form=form,
    )
    return summarize_merge(root, total=len(assurances.assurances))


# ---- Builders --------------------------------------------------------------------


def _build_declaration_merge_xml(
    declarations: DeclarationMergeInput,
    prepared: list[PreparedAttachment],
) -> str:
    # Element order matches declaration_merge_request.xml:
    # <ROOT><FOLDER>...</FOLDER><TAXES><TAX>...</TAX>...</TAXES></ROOT>.
    root = ET.Element("ROOT")
    folder = ET.SubElement(root, "FOLDER")
    set_text(folder, "YEAR", declarations.year)
    set_text(folder, "MONTH", declarations.month)

    taxes_el = ET.SubElement(root, "TAXES")
    cursor = 0
    for tax in declarations.taxes:
        cursor = _append_tax(taxes_el, tax, prepared, cursor)
    return ET.tostring(root, encoding="unicode")


def _append_tax(
    parent: ET.Element,
    tax: DeclarationTaxInput,
    prepared: list[PreparedAttachment],
    cursor: int,
) -> int:
    item = ET.SubElement(parent, "TAX")
    set_text(item, "DECLARATION_PROGRAM_ID", tax.declaration_program_id)
    if tax.tax_details is not None:
        details = ET.SubElement(item, "TAX_DETAILS")
        set_text(details, "TYPE", tax.tax_details.type)
        set_text(details, "CORRECTION_NO", tax.tax_details.correction_no)
        set_text(details, "PERIOD", tax.tax_details.period)
        set_text(details, "PERIOD_TYPE", tax.tax_details.period_type)
        set_text(details, "DEADLINE", tax.tax_details.deadline)
        set_text(details, "TAX_VALUE", tax.tax_details.tax_value)
        set_text(details, "DESCRIPTION", tax.tax_details.description)
    if tax.attachments:
        end = cursor + len(tax.attachments)
        append_close_attachments(item, tax.attachments, prepared[cursor:end])
        return end
    return cursor


def _build_assurance_renew_xml(
    assurances: AssuranceRenewInput,
    prepared: list[PreparedAttachment],
) -> str:
    # Element order matches assurance_renew_request.xml:
    # <ROOT><FOLDER>...</FOLDER>
    #       <ASSURANCES><ASSURANCE>...</ASSURANCE>...</ASSURANCES></ROOT>.
    root = ET.Element("ROOT")
    folder = ET.SubElement(root, "FOLDER")
    set_text(folder, "YEAR", assurances.year)
    set_text(folder, "MONTH", assurances.month)

    container = ET.SubElement(root, "ASSURANCES")
    cursor = 0
    for assurance in assurances.assurances:
        cursor = _append_assurance(container, assurance, prepared, cursor)
    return ET.tostring(root, encoding="unicode")


def _append_assurance(
    parent: ET.Element,
    assurance: AssuranceItemInput,
    prepared: list[PreparedAttachment],
    cursor: int,
) -> int:
    item = ET.SubElement(parent, "ASSURANCE")
    set_text(item, "ASSURANCE_PROGRAM_ID", assurance.assurance_program_id)
    details = ET.SubElement(item, "ASSURANCE_DETAILS")
    _append_assurance_details(details, assurance.details)
    if assurance.attachments:
        end = cursor + len(assurance.attachments)
        append_close_attachments(item, assurance.attachments, prepared[cursor:end])
        return end
    return cursor


def _append_assurance_details(
    parent: ET.Element,
    details: AssuranceEmployeesDetailsInput
    | AssurancePersonalDetailsInput
    | AssuranceCompanyDetailsInput
    | AssurancePartnerDetailsInput,
) -> None:
    # The TYPE leads in every variant; ZUS-XX field order matches the spec
    # example (zus_51 / zus_52 / zus_53 / zus_54 for headcount-based variants,
    # zus_contribution / zus_excess_payment | zus_underpayment for owner /
    # partner variants).
    if isinstance(details, AssuranceEmployeesDetailsInput):
        set_text(parent, "TYPE", "EMPLOYEES")
        set_text(parent, "PERIOD", details.period)
        set_text(parent, "DEADLINE", details.deadline)
        set_text(parent, "ZUS-51", details.zus_51)
        set_text(parent, "ZUS-52", details.zus_52)
        set_text(parent, "ZUS-53", details.zus_53)
        set_text(parent, "ZUS-54", details.zus_54)
    elif isinstance(details, AssurancePersonalDetailsInput):
        set_text(parent, "TYPE", "PERSONAL")
        set_text(parent, "LAST_NAME", details.last_name)
        set_text(parent, "FIRST_NAME", details.first_name)
        set_text(parent, "PERSON_ID_TYPE", details.person_id_type)
        set_text(parent, "PERSON_ID", details.person_id)
        set_text(parent, "PERSON_CODE", details.person_code)
        set_text(parent, "PERIOD", details.period)
        set_text(parent, "DEADLINE", details.deadline)
        set_text(parent, "ZUS-51", details.zus_51)
        set_text(parent, "ZUS-52", details.zus_52)
        set_text(parent, "ZUS-53", details.zus_53)
        set_text(parent, "ZUS-54", details.zus_54)
    elif isinstance(details, AssuranceCompanyDetailsInput):
        set_text(parent, "TYPE", "COMPANY")
        set_text(parent, "PERIOD", details.period)
        set_text(parent, "DEADLINE", details.deadline)
        set_text(parent, "ZUS_CONTRIBUTION", details.zus_contribution)
        set_text(parent, "ZUS_EXCESS_PAYMENT", details.zus_excess_payment)
        set_text(parent, "ZUS_DESCRIPTION", details.zus_description)
    elif isinstance(details, AssurancePartnerDetailsInput):
        set_text(parent, "TYPE", "PARTNER")
        set_text(parent, "LAST_NAME", details.last_name)
        set_text(parent, "FIRST_NAME", details.first_name)
        set_text(parent, "PERSON_ID_TYPE", details.person_id_type)
        set_text(parent, "PERSON_ID", details.person_id)
        set_text(parent, "PERSON_CODE", details.person_code)
        set_text(parent, "PERIOD", details.period)
        set_text(parent, "DEADLINE", details.deadline)
        set_text(parent, "ZUS_CONTRIBUTION", details.zus_contribution)
        set_text(parent, "ZUS_UNDERPAYMENT", details.zus_underpayment)
        set_text(parent, "ZUS_DESCRIPTION", details.zus_description)
