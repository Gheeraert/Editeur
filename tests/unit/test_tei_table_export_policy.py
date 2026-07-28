from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

import pytest

from purh_editorial.config import load_settings
from purh_editorial.io.tei_xml_exporter import (
    TEI_NS,
    TeiTableExportError,
    TeiXmlExporter,
)
from purh_editorial.model import Block, Document, ImageAsset, ImageOccurrence, InlineSpan, Note, Paragraph
from purh_editorial.pipeline.step1 import Step1Options, Step1Pipeline


def _table_ooxml(*, rows: int = 1) -> str:
    row_xml = "<w:tr><w:tc><w:p><w:r><w:t>one</w:t></w:r></w:p><w:p><w:r><w:t>two</w:t></w:r></w:p></w:tc></w:tr>"
    return (
        '<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        + row_xml * rows
        + "</w:tbl>"
    )


def _table(block_id: str, ooxml: str | None) -> Block:
    attributes = {} if ooxml is None else {"table_ooxml": ooxml}
    return Block(block_id=block_id, block_type="table", attributes=attributes)


def test_valid_table_is_exported_and_document_is_unchanged() -> None:
    document = Document("doc", "source.docx", "docx", blocks=[_table("table-1", _table_ooxml())])
    before = deepcopy(document)

    result = TeiXmlExporter().export_document_result(document)
    root = ET.fromstring(result.xml)

    assert root.find(f".//{{{TEI_NS}}}table/{{{TEI_NS}}}row/{{{TEI_NS}}}cell").text == "one\ntwo"
    assert result.table_diagnostics == [
        {"code": "table_exported_to_tei", "block_id": "table-1", "rows": 1, "cells": 1}
    ]
    assert result.table_exported_count == 1
    assert result.table_not_exported_count == 0
    assert document == before


@pytest.mark.parametrize(
    ("ooxml", "reason"),
    [
        (None, "missing_table_ooxml"),
        ("<w:tbl", "invalid_table_ooxml"),
        ('<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>', "no_rows"),
    ],
)
def test_non_exportable_table_blocks_strict_export_without_mutating_document(
    ooxml: str | None, reason: str
) -> None:
    document = Document("doc", "source.docx", "docx", blocks=[_table("table-3", ooxml)])
    before = deepcopy(document)

    with pytest.raises(TeiTableExportError) as raised:
        TeiXmlExporter().export_document(document)

    assert "table-3" in str(raised.value)
    assert raised.value.diagnostics[0]["reason"] == reason
    assert "[Table not exported:" not in str(raised.value)
    assert document == before


def test_one_invalid_table_blocks_a_document_with_other_valid_tables() -> None:
    document = Document(
        "doc", "source.docx", "docx", blocks=[_table("table-ok", _table_ooxml()), _table("table-bad", None)]
    )

    with pytest.raises(TeiTableExportError) as raised:
        TeiXmlExporter().export_document(document)

    assert [item["code"] for item in raised.value.diagnostics] == [
        "table_exported_to_tei",
        "table_not_exported_to_tei",
    ]


def test_explicit_degraded_mode_returns_diagnostics_and_marked_fallback() -> None:
    document = Document("doc", "source.docx", "docx", blocks=[_table("table-3", None)])

    result = TeiXmlExporter().export_document_result(
        document, allow_degraded_table_output=True
    )

    assert result.degraded is True
    assert result.table_not_exported_count == 1
    assert "[Table not exported: missing OOXML]" in result.xml
    assert result.table_diagnostics[0]["block_id"] == "table-3"
    assert "tei_table_diagnostics" not in document.annotations


def test_valid_table_stays_between_paragraph_note_and_figure() -> None:
    asset = ImageAsset("asset-1", "image.png", "image/png", b"png", "hash")
    document = Document(
        "doc",
        "source.docx",
        "docx",
        blocks=[
            Paragraph("before", text="Before", inlines=[InlineSpan("Before"), InlineSpan("", kind="note_call", note_ref="n1")]),
            _table("table-1", _table_ooxml()),
            Paragraph("after", text="After"),
        ],
        notes=[Note("n1", text="Footnote")],
        image_assets={asset.asset_id: asset},
        image_occurrences=[ImageOccurrence("figure-1", asset.asset_id, "inline", "table-1", 1)],
    )

    xml = TeiXmlExporter().export_document(document)
    body = ET.fromstring(xml).find(f".//{{{TEI_NS}}}body")
    assert body is not None
    assert [child.tag for child in body] == [
        f"{{{TEI_NS}}}p",
        f"{{{TEI_NS}}}table",
        f"{{{TEI_NS}}}figure",
        f"{{{TEI_NS}}}p",
    ]


def test_pipeline_records_table_error_and_does_not_write_tei(tmp_path: Path) -> None:
    source_path = tmp_path / "source.txt"
    source_path.write_text("source", encoding="utf-8")
    output_path = tmp_path / "failed.xml"
    table_error = TeiTableExportError(
        [{"code": "table_not_exported_to_tei", "block_id": "table-7", "reason": "missing_table_ooxml", "rows": 0, "cells": 0}]
    )

    with patch("purh_editorial.pipeline.step1.export_tei_for_production", side_effect=table_error):
        result = Step1Pipeline(settings=load_settings()).run(
            source_path,
            Step1Options(enable_ai=False, output_path=None, tei_output_path=output_path),
        )

    report = result.pipeline_result.report
    assert result.pipeline_result.tei_xml is None
    assert output_path.exists() is False
    assert any("table-7: missing_table_ooxml" in error for error in report.errors)
    assert any(run.module_name == "tei_xml_export" and run.status == "failed" for run in report.module_runs)
