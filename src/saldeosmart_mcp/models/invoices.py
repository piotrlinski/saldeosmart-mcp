"""Invoice resource models — sales invoices issued in SaldeoSMART.

The wire shape overlaps with cost ``Document`` enough that the parser is
reused; only the container/leaf names differ.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field

from .documents import Document


class InvoiceList(BaseModel):
    invoices: list[Document]
    count: int


class InvoiceIdGroups(BaseModel):
    """Invoice IDs grouped by kind (SSK07 response)."""

    invoices: list[int] = Field(default_factory=list)
    corrective_invoices: list[int] = Field(default_factory=list)
    pre_invoices: list[int] = Field(default_factory=list)
    corrective_pre_invoices: list[int] = Field(default_factory=list)

    @classmethod
    def from_xml(cls, root: ET.Element) -> InvoiceIdGroups:
        def ints(container: str, leaf: str) -> list[int]:
            container_el = root.find(container)
            if container_el is None:
                return []
            out: list[int] = []
            for el in container_el.findall(leaf):
                if el.text and el.text.strip().isdigit():
                    out.append(int(el.text.strip()))
            return out

        return cls(
            invoices=ints("INVOICES", "INVOICE_ID"),
            corrective_invoices=ints("CORRECTIVE_INVOICES", "CORRECTIVE_INVOICE_ID"),
            pre_invoices=ints("PRE_INVOICES", "PRE_INVOICE_ID"),
            corrective_pre_invoices=ints(
                "CORRECTIVE_PRE_INVOICES", "CORRECTIVE_PRE_INVOICE_ID"
            ),
        )
