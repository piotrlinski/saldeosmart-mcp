"""Dimension tools — analytical dimensions (the standalone resource).

``merge_document_dimensions`` lives in ``tools.documents`` because it pins
values to existing documents — its primary subject is the document, not
the dimension. This file owns just the dimension catalog itself.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from ..http.xml import set_text
from ..models import DimensionInput, ErrorResponse, MergeResult
from ._runtime import get_client, mcp, saldeo_call, summarize_merge


@mcp.tool
@saldeo_call
def merge_dimensions(
    company_program_id: str,
    dimensions: list[DimensionInput],
) -> MergeResult | ErrorResponse:
    """Create or update analytical dimensions (custom document attributes).

    A "dimension" is a custom column you can attach to any document (e.g.
    "Cost center", "Project"). Match on ``code`` to update an existing
    dimension. Saldeo op: ``dimension.merge`` (SS12). To set values on
    documents themselves, use ``merge_document_dimensions``.

    Args:
        company_program_id: External program ID of the company.
        dimensions: One DimensionInput per dimension. ``code``, ``name``,
            and ``type`` are required.
            - ``type=ENUM``: populate ``values`` with the allowed options.
            - ``type=NUM`` / ``LONG_NUM`` / ``DATE``: free-form, leave
              ``values`` empty.

    Returns:
        MergeResult on success, ErrorResponse on failure.
    """
    xml = _build_dimension_merge_xml(dimensions)
    root = get_client().post_command(
        "/api/xml/1.12/dimension/merge",
        xml_command=xml,
        query={"company_program_id": company_program_id},
    )
    return summarize_merge(root, total=len(dimensions))


def _build_dimension_merge_xml(dimensions: list[DimensionInput]) -> str:
    root = ET.Element("ROOT")
    container = ET.SubElement(root, "DIMENSIONS")
    for d in dimensions:
        item = ET.SubElement(container, "DIMENSION")
        set_text(item, "CODE", d.code)
        set_text(item, "NAME", d.name)
        set_text(item, "TYPE", d.type)
        if d.values:
            values = ET.SubElement(item, "VALUES")
            for v in d.values:
                v_el = ET.SubElement(values, "VALUE")
                set_text(v_el, "CODE", v.code)
                set_text(v_el, "DESCRIPTION", v.description)
    return ET.tostring(root, encoding="unicode")
