"""File-attachment plumbing for SaldeoSMART endpoints.

The SaldeoSMART spec carries attachments in additional form fields named
``attmnt_<key>`` alongside the standard gzipped ``command`` field. The
matching XML element is ``<ATTMNT>{key}</ATTMNT>`` (just the alphanumeric
suffix — the ``attmnt_`` prefix is implicit in the form encoding).

Endpoints that use this pattern: ``document.add``, ``document.import``,
``document.add_recognize``, ``document.correct``, ``personnel_document.add``,
``declaration.merge``, ``assurance.renew``, optionally
``financial_balance.merge``.

This module owns:

- :class:`Attachment` — Pydantic input model accepted by tool functions.
  Holds a filesystem path and an optional display name.
- :class:`PreparedAttachment` — what :func:`prepare_attachments` returns
  for the XML builder to reference.
- :func:`prepare_attachments` — read + base64-encode each attachment and
  build the form-data dict to pass as ``extra_form=`` to
  :meth:`SaldeoClient.post_command`.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel


class Attachment(BaseModel):
    """One file to upload alongside an MCP write tool.

    ``path`` is read at the time the tool runs — the file must be readable
    by the process running the MCP server. ``name`` overrides the display
    name carried in ``<ATTMNT_NAME>``; defaults to the file's basename.
    """

    path: str
    name: str | None = None


@dataclass(frozen=True)
class PreparedAttachment:
    """Result of reading an :class:`Attachment` from disk.

    ``key`` is what goes inside ``<ATTMNT>`` in the XML payload; ``form_key``
    is the corresponding key in the form-data dict (``attmnt_<key>``);
    ``name`` is the resolved display name for ``<ATTMNT_NAME>``.
    """

    key: str
    form_key: str
    name: str


def prepare_attachments(
    attachments: list[Attachment],
) -> tuple[list[PreparedAttachment], dict[str, str]]:
    """Read each attachment, base64-encode, return XML refs + form data.

    Keys are 1-indexed integers (``"1"``, ``"2"``, …). XSD restricts
    ``<ATTMNT>`` to alphanumeric tokens, so digits are the safe default.

    Raises:
        FileNotFoundError: if any attachment path doesn't exist.
        PermissionError: if the file isn't readable.
    """
    prepared: list[PreparedAttachment] = []
    form: dict[str, str] = {}
    for index, att in enumerate(attachments, start=1):
        key = str(index)
        form_key = f"attmnt_{key}"
        path = Path(att.path)
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        prepared.append(PreparedAttachment(key=key, form_key=form_key, name=att.name or path.name))
        form[form_key] = data
    return prepared, form
