"""Tests for the file-attachment helper."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from saldeosmart_mcp.http.attachments import Attachment, prepare_attachments


def test_prepare_attachments_reads_and_base64_encodes(tmp_path: Path) -> None:
    f = tmp_path / "invoice.pdf"
    f.write_bytes(b"%PDF-1.4\nfake\n")

    prepared, form = prepare_attachments([Attachment(path=str(f))])

    assert len(prepared) == 1
    assert prepared[0].key == "1"
    assert prepared[0].form_key == "attmnt_1"
    assert prepared[0].name == "invoice.pdf"

    assert form["attmnt_1"] == base64.b64encode(b"%PDF-1.4\nfake\n").decode("ascii")


def test_prepare_attachments_indexes_keys_one_based(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    a.write_bytes(b"a")
    b = tmp_path / "b.txt"
    b.write_bytes(b"b")

    prepared, form = prepare_attachments([Attachment(path=str(a)), Attachment(path=str(b))])

    assert [p.key for p in prepared] == ["1", "2"]
    assert set(form.keys()) == {"attmnt_1", "attmnt_2"}


def test_prepare_attachments_uses_explicit_name_override(tmp_path: Path) -> None:
    f = tmp_path / "scan-001.pdf"
    f.write_bytes(b"x")

    prepared, _ = prepare_attachments([Attachment(path=str(f), name="invoice-jan-2026.pdf")])
    assert prepared[0].name == "invoice-jan-2026.pdf"


def test_prepare_attachments_raises_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.pdf"

    with pytest.raises(FileNotFoundError):
        prepare_attachments([Attachment(path=str(missing))])


def test_prepare_attachments_empty_returns_empty() -> None:
    prepared, form = prepare_attachments([])
    assert prepared == []
    assert form == {}
