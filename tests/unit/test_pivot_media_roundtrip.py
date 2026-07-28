from __future__ import annotations

import json

import pytest

from purh_editorial.model import (
    Block,
    ComplexObjectOccurrence,
    Diagnostic,
    Document,
    Evidence,
    ImageAsset,
    ImageOccurrence,
    InlineSpan,
    InlineStyle,
    Note,
    ProcessingReport,
    Suggestion,
    Transformation,
)
from purh_editorial.serialization.pivot_json import (
    build_pivot_payload,
    parse_pivot_payload,
    pivot_to_json,
)


def _document_with_media() -> Document:
    asset = ImageAsset(
        asset_id="image-1",
        filename="illustration.png",
        content_type="image/png",
        data=b"\x89PNG\r\n\x1a\n\x00\xffPURH",
        sha256="2b8d3a6a",
        width_emu=914400,
        height_emu=457200,
        alt_text="Une illustration",
        title="Planche I",
        source_part="/word/media/image1.png",
    )
    return Document(
        document_id="doc-media",
        source_path="source.docx",
        source_format="docx",
        blocks=[
            Block(
                block_id="p-1",
                block_type="paragraph",
                text="Texte enrichi",
                inlines=[InlineSpan("Texte", InlineStyle(italic=True, bold=True))],
            ),
            Block(
                block_id="table-1",
                block_type="table",
                attributes={"source_ooxml": "<w:tbl><w:tr/></w:tbl>"},
            ),
        ],
        notes=[
            Note(
                note_id="note-1",
                text="Note enrichie",
                inlines=[InlineSpan("Note", InlineStyle(superscript=True))],
            )
        ],
        image_assets={asset.asset_id: asset},
        image_occurrences=[
            ImageOccurrence(
                occurrence_id="occ-block",
                asset_ref=asset.asset_id,
                placement="inline",
                target_ref="p-1",
                order=1,
                width_emu=914400,
                height_emu=457200,
                alt_text="Texte alternatif local",
                title="Titre local",
                caption="Légende complète",
                external_link="https://example.test/illustration",
                original_xml="<w:drawing/>",
                attributes={"provenance": "word:drawing"},
            ),
            ImageOccurrence(
                occurrence_id="occ-note",
                asset_ref=asset.asset_id,
                placement="note",
                target_ref="note-1",
                order=2,
                anchor_normalized_to_inline=True,
                attributes={"provenance": "word:footnote"},
            ),
        ],
        complex_objects=[
            ComplexObjectOccurrence(
                occurrence_id="chart-1",
                object_type="chart",
                target_ref="p-1",
                order=3,
                attributes={"original_xml": "<c:chart/>"},
            ),
            ComplexObjectOccurrence(
                occurrence_id="ole-1",
                object_type="ole",
                target_ref="table-1",
                order=4,
                placement="table",
                fallback_asset_ref=asset.asset_id,
                attributes={"original_xml": "<o:OLEObject/>", "source_part": "/word/embeddings/ole1.bin"},
            ),
        ],
    )


def _report() -> ProcessingReport:
    return ProcessingReport(
        report_id="report-1",
        document_id="doc-media",
        diagnostics=[
            Diagnostic(
                diagnostic_id="diag-1",
                module="orthotypo",
                severity="warning",
                category="spacing",
                message="Diagnostic",
                target_ref="p-1",
                evidence=Evidence(excerpt="Texte", offset_start=0, offset_end=5),
                rule_id="spacing-1",
            )
        ],
        suggestions=[
            Suggestion(
                suggestion_id="suggestion-1",
                module="ai_editorial",
                target_ref="p-1",
                message="Suggestion",
                rationale="Revue humaine",
                proposed_text="Texte proposé",
                confidence=0.6,
            )
        ],
        transformations=[
            Transformation(
                transformation_id="transformation-1",
                module="orthotypo",
                target_ref="p-1",
                operation="replace",
                before="Texte",
                after="Texte",
                rule_id="spacing-1",
                applied=True,
            )
        ],
    )


def test_pivot_round_trip_preserves_media_and_report() -> None:
    document = _document_with_media()
    report = _report()

    json_text = pivot_to_json(document, report=report)
    payload = json.loads(json_text)
    restored_document, restored_report = parse_pivot_payload(json_text)

    assert payload["schema_version"] == "pivot-1.0"
    assert payload["document"]["image_assets"]["image-1"]["data"] == {
        "encoding": "base64",
        "value": "iVBORw0KGgoA/1BVUkg=",
    }
    assert restored_document.image_assets == document.image_assets
    assert restored_document.image_assets["image-1"].data == document.image_assets["image-1"].data
    assert restored_document.image_occurrences == document.image_occurrences
    assert restored_document.complex_objects == document.complex_objects
    assert restored_document.blocks[0].inlines == document.blocks[0].inlines
    assert restored_document.blocks[1].attributes == {"source_ooxml": "<w:tbl><w:tr/></w:tbl>"}
    assert restored_document.notes[0].inlines == document.notes[0].inlines
    assert restored_report == report


def test_invalid_base64_media_is_rejected() -> None:
    payload = build_pivot_payload(_document_with_media())
    payload["document"]["image_assets"]["image-1"]["data"]["value"] = "not base64!"

    with pytest.raises(ValueError, match="Invalid base64 image data"):
        parse_pivot_payload(payload)


def test_orphan_image_occurrence_is_rejected() -> None:
    payload = build_pivot_payload(_document_with_media())
    payload["document"]["image_occurrences"][0]["asset_ref"] = "missing-image"

    with pytest.raises(ValueError, match="references missing asset 'missing-image'"):
        parse_pivot_payload(payload)


def test_complex_object_with_missing_fallback_is_rejected() -> None:
    payload = build_pivot_payload(_document_with_media())
    payload["document"]["complex_objects"][1]["fallback_asset_ref"] = "missing-image"

    with pytest.raises(ValueError, match="references missing fallback asset 'missing-image'"):
        parse_pivot_payload(payload)


def test_malformed_media_entry_is_rejected() -> None:
    payload = build_pivot_payload(_document_with_media())
    payload["document"]["image_assets"] = []

    with pytest.raises(ValueError, match="image_assets must be an object"):
        parse_pivot_payload(payload)


def test_legacy_pivot_without_media_is_readable() -> None:
    document, report = parse_pivot_payload(
        {
            "schema_version": "pivot-1.0",
            "document": {
                "document_id": "legacy",
                "source_path": "legacy.docx",
                "source_format": "docx",
            },
        }
    )

    assert document.document_id == "legacy"
    assert document.image_assets == {}
    assert document.image_occurrences == []
    assert document.complex_objects == []
    assert report is None
