"""Generic XML request-body builders shared across multiple tool modules.

Resource-specific builders (e.g. ``_build_contractor_merge_xml``,
``_build_search_xml``) live next to their tools; only the patterns reused
across resources land here.

Building blocks:
  - :func:`build_folder_xml` — body for the 3.0 ``*.getidlist`` endpoints
  - :func:`append_id_group` — append ``<CONTAINER><ITEM>id</ITEM>...</CONTAINER>``
  - :func:`build_simple_merge_xml` — generic
    ``<ROOT><CONTAINER><ITEM><FIELD/>...</ITEM>...</CONTAINER></ROOT>``
  - :func:`append_close_attachments` — shared ``<ATTACHMENTS>`` block used
    by financial_balance.merge, declaration.merge, and assurance.renew.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol
from xml.etree import ElementTree as ET

from ..http.attachments import PreparedAttachment
from ..http.xml import set_text


class _CloseAttachmentLike(Protocol):
    """Structural type that close-attachment input models conform to.

    Lets ``append_close_attachments`` stay generic across
    ``CloseAttachmentInput`` (declarations, assurances) and any future
    look-alike without importing those models from this generic helper.

    Declared as ``@property`` so subtypes can narrow ``type`` to a
    ``Literal`` without breaking Protocol invariance.
    """

    @property
    def type(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str | None: ...
    @property
    def short_description(self) -> str | None: ...


def build_folder_xml(year: int, month: int) -> str:
    """Body for the 3.0 *.getidlist operations.

    Shape: ``<ROOT><FOLDER><YEAR/><MONTH/></FOLDER></ROOT>``.
    """
    root = ET.Element("ROOT")
    folder = ET.SubElement(root, "FOLDER")
    ET.SubElement(folder, "YEAR").text = str(year)
    ET.SubElement(folder, "MONTH").text = str(month)
    return ET.tostring(root, encoding="unicode")


def append_id_group(
    root: ET.Element,
    container_tag: str,
    item_tag: str,
    ids: list[int] | None,
) -> None:
    """Append <CONTAINER><ITEM>id</ITEM>...</CONTAINER> if `ids` is non-empty."""
    if not ids:
        return
    container = ET.SubElement(root, container_tag)
    for value in ids:
        ET.SubElement(container, item_tag).text = str(value)


def build_simple_merge_xml(
    *,
    container_tag: str,
    item_tag: str,
    items: list[Any],
    field_specs: list[tuple[str, str]],
) -> str:
    """Build ``<ROOT><CONTAINER><ITEM><F1/>...</ITEM>...</CONTAINER></ROOT>``.

    ``field_specs`` is a list of (python_attr_name, xml_tag_name) tuples.
    Used by the ops whose items are flat field maps (category, register,
    payment_method, description). More structured items (contractor, article,
    dimension) get hand-rolled builders next to their tools.
    """
    root = ET.Element("ROOT")
    container = ET.SubElement(root, container_tag)
    for item in items:
        item_el = ET.SubElement(container, item_tag)
        for attr, tag in field_specs:
            set_text(item_el, tag, getattr(item, attr, None))
    return ET.tostring(root, encoding="unicode")


def append_close_attachments(
    parent: ET.Element,
    attachments: Sequence[_CloseAttachmentLike],
    prepared: list[PreparedAttachment],
) -> None:
    """Append ``<ATTACHMENTS><ATTACHMENT>...</ATTACHMENT></ATTACHMENTS>``.

    Element order per the SSK0X spec: TYPE, NAME, DESCRIPTION,
    SHORT_DESCRIPTION, ATTMNT, ATTMNT_NAME. ``attachments`` and
    ``prepared`` must be the same length and in the same order — caller
    slices the global ``prepare_attachments`` output to match each item's
    attachments list.

    The ``Sequence[_CloseAttachmentLike]`` parameter is structurally typed
    so this helper stays decoupled from any specific input model;
    ``CloseAttachmentInput`` (declarations, assurances) and any future
    look-alike with the right attributes both work.
    """
    container = ET.SubElement(parent, "ATTACHMENTS")
    for att, p in zip(attachments, prepared, strict=True):
        item = ET.SubElement(container, "ATTACHMENT")
        set_text(item, "TYPE", att.type)
        set_text(item, "NAME", att.name)
        set_text(item, "DESCRIPTION", att.description)
        set_text(item, "SHORT_DESCRIPTION", att.short_description)
        set_text(item, "ATTMNT", p.key)
        set_text(item, "ATTMNT_NAME", p.name)
