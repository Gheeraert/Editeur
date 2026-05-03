from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.io.tei_xml_exporter import TEI_NS, TeiXmlExporter
from purh_editorial.model import (
    BlockSemantics,
    Document,
    Heading,
    InlineSpan,
    InlineStyle,
    Metadata,
    Paragraph,
    ProcessingReport,
    QuoteBlock,
    read_block_semantics,
    write_block_semantics,
)
from purh_editorial.serialization import build_pivot_payload, parse_pivot_payload, pivot_to_json
from purh_editorial.services.metopes_mapper import MetopesMapper
from purh_editorial.services.pivot_canonicalizer import PivotCanonicalizer
from purh_editorial.services.pivot_validator import PivotValidator
from purh_editorial.services.structure_service import StructurePreparationService


def _q(local_name: str) -> str:
    return f"{{{TEI_NS}}}{local_name}"


class PivotSemanticContractTests(unittest.TestCase):
    def test_legacy_poetry_is_written_to_canonical_semantic(self) -> None:
        block = QuoteBlock(
            block_id="q-legacy-poetry",
            text="Premier vers\nDeuxieme vers",
            attributes={
                "quote_kind": "poetry",
                "protected_zone": "poetry",
            },
        )
        document = Document(
            document_id="doc-legacy-poetry",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        transformations = PivotCanonicalizer().apply(document)

        self.assertTrue(transformations)
        semantic_payload = document.blocks[0].attributes.get("semantic")
        self.assertIsInstance(semantic_payload, dict)
        self.assertEqual(
            semantic_payload,
            {
                "role": "quote",
                "quote_kind": "poetry",
                "lineation": "verse",
                "lines": ["Premier vers", "Deuxieme vers"],
            },
        )

    def test_export_requires_canonical_semantic(self) -> None:
        block = QuoteBlock(
            block_id="q-legacy-only",
            text="Premier vers\nDeuxieme vers",
            attributes={
                "quote_kind": "poetry",
                "protected_zone": "poetry",
            },
        )
        document = Document(
            document_id="doc-export-strict",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        xml_without_canonicalization = TeiXmlExporter().export_document(document)
        root_without = ET.fromstring(xml_without_canonicalization)
        self.assertEqual(len(root_without.findall(f".//{_q('lg')}")), 0)

        PivotCanonicalizer().apply(document)
        xml_with_canonicalization = TeiXmlExporter().export_document(document)
        root_with = ET.fromstring(xml_with_canonicalization)
        lines = root_with.findall(f".//{_q('lg')}/{_q('l')}")
        self.assertEqual([line.text for line in lines], ["Premier vers", "Deuxieme vers"])

    def test_paragraph_legacy_poetry_markers_are_not_canonical(self) -> None:
        block = Paragraph(
            block_id="p-legacy-poetry",
            text="Ligne breve",
            attributes={
                "semantic_role": "quote",
                "quote_kind": "poetry",
                "lineation": "verse",
                "protected_zone": "poetry",
            },
        )
        document = Document(
            document_id="doc-paragraph-cleanup",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        PivotCanonicalizer().apply(document)
        semantic_payload = document.blocks[0].attributes.get("semantic")
        self.assertEqual(semantic_payload, {"role": "paragraph"})
        self.assertNotIn("quote_kind", semantic_payload)
        self.assertNotIn("lineation", semantic_payload)
        self.assertNotIn("lines", semantic_payload)
        self.assertNotIn("quote_kind", document.blocks[0].attributes)
        self.assertNotIn("lineation", document.blocks[0].attributes)

        xml_text = TeiXmlExporter().export_document(document)
        root = ET.fromstring(xml_text)
        self.assertEqual(len(root.findall(f".//{_q('lg')}")), 0)

    def test_heading_does_not_retain_quote_semantics(self) -> None:
        block = Heading(
            block_id="h-stray-quote",
            text="Titre",
            attributes={
                "heading_level": 1,
                "quote_kind": "poetry",
                "lineation": "verse",
            },
        )
        document = Document(
            document_id="doc-heading-cleanup",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        PivotCanonicalizer().apply(document)
        semantic_payload = document.blocks[0].attributes.get("semantic")
        self.assertEqual(semantic_payload, {"role": "heading"})
        self.assertNotIn("quote_kind", semantic_payload)
        self.assertNotIn("lineation", semantic_payload)
        self.assertNotIn("lines", semantic_payload)
        self.assertNotIn("quote_kind", document.blocks[0].attributes)
        self.assertNotIn("lineation", document.blocks[0].attributes)

    def test_prose_quote_clears_poetry_lines(self) -> None:
        block = QuoteBlock(
            block_id="q-prose-clean",
            text="Citation en prose.",
            attributes={
                "semantic": {
                    "role": "quote",
                    "lineation": "prose",
                    "lines": ["ligne residuelle"],
                }
            },
        )
        document = Document(
            document_id="doc-prose-cleanup",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        PivotCanonicalizer().apply(document)
        semantic_payload = document.blocks[0].attributes.get("semantic")
        self.assertEqual(
            semantic_payload,
            {
                "role": "quote",
                "quote_kind": "prose",
                "lineation": "prose",
            },
        )
        self.assertNotIn("lines", semantic_payload)

    def test_validator_reports_bad_manual_semantic_payload(self) -> None:
        block = Paragraph(
            block_id="p-bad-semantic",
            text="Paragraphe invalide",
            attributes={
                "semantic": {
                    "role": "paragraph",
                    "quote_kind": "poetry",
                    "lineation": "verse",
                    "lines": ["bad"],
                }
            },
        )
        document = Document(
            document_id="doc-validator-bad-semantic",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        diagnostics = PivotValidator().validate(document)
        rule_ids = {diag.rule_id for diag in diagnostics}
        self.assertIn("pivot.semantic.quote_fields_on_non_quote", rule_ids)
        self.assertIn("pivot.semantic.verse_on_non_poetry", rule_ids)
        self.assertIn("pivot.semantic.lines_on_non_poetry", rule_ids)

    def test_canonical_payload_still_cleans_stale_legacy_quote_keys(self) -> None:
        block = Paragraph(
            block_id="p-canonical-with-stale-legacy",
            text="Paragraphe stable",
            attributes={
                "semantic": {"role": "paragraph"},
                "quote_kind": "poetry",
                "lineation": "verse",
                "poetry_group_id": "grp1",
                "poetry_line_index": 1,
            },
        )
        document = Document(
            document_id="doc-cleanup-stale-legacy-paragraph",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        transformations = PivotCanonicalizer().apply(document)
        self.assertTrue(transformations)
        self.assertEqual(document.blocks[0].attributes.get("semantic"), {"role": "paragraph"})
        self.assertNotIn("quote_kind", document.blocks[0].attributes)
        self.assertNotIn("lineation", document.blocks[0].attributes)
        self.assertNotIn("poetry_group_id", document.blocks[0].attributes)
        self.assertNotIn("poetry_line_index", document.blocks[0].attributes)

    def test_heading_canonical_payload_still_cleans_stale_legacy_quote_keys(self) -> None:
        block = Heading(
            block_id="h-canonical-with-stale-legacy",
            text="Titre",
            attributes={
                "heading_level": 1,
                "semantic": {"role": "heading"},
                "quote_kind": "poetry",
                "lineation": "verse",
            },
        )
        document = Document(
            document_id="doc-cleanup-stale-legacy-heading",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        transformations = PivotCanonicalizer().apply(document)
        self.assertTrue(transformations)
        self.assertEqual(document.blocks[0].attributes.get("semantic"), {"role": "heading"})
        self.assertNotIn("quote_kind", document.blocks[0].attributes)
        self.assertNotIn("lineation", document.blocks[0].attributes)

    def test_json_round_trip_preserves_canonical_semantics(self) -> None:
        poetry_block = QuoteBlock(
            block_id="q-poetry",
            text="Premier vers\nDeuxieme vers",
        )
        write_block_semantics(
            poetry_block,
            BlockSemantics(
                role="quote",
                quote_kind="poetry",
                lineation="verse",
                lines=["Premier vers", "Deuxieme vers"],
            ),
        )

        prose_quote = QuoteBlock(block_id="q-prose", text="Une citation en prose.")
        write_block_semantics(
            prose_quote,
            BlockSemantics(
                role="quote",
                quote_kind="prose",
                lineation="prose",
            ),
        )

        document = Document(
            document_id="doc-roundtrip",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            metadata=Metadata(title="Titre", authors=["Auteur"]),
            blocks=[
                Heading(block_id="h1", text="Intertitre", attributes={"heading_level": 2}),
                Paragraph(
                    block_id="p1",
                    text="",
                    inlines=[
                        InlineSpan(text="Texte "),
                        InlineSpan(text="italique", style=InlineStyle(italic=True)),
                        InlineSpan(text="", kind="line_break"),
                        InlineSpan(text="suite"),
                    ],
                ),
                prose_quote,
                poetry_block,
            ],
        )
        report = ProcessingReport(report_id="report-1", document_id=document.document_id)

        payload = build_pivot_payload(document, report=report)
        self.assertEqual(payload["schema_version"], "pivot-1.0")

        json_text = pivot_to_json(document, report=report)
        parsed_payload = json.loads(json_text)
        self.assertEqual(parsed_payload["schema_version"], "pivot-1.0")

        reconstructed_document, reconstructed_report = parse_pivot_payload(json_text)
        self.assertIsNotNone(reconstructed_report)
        self.assertEqual(reconstructed_document.document_id, "doc-roundtrip")
        self.assertEqual(reconstructed_document.blocks[0].attributes.get("heading_level"), 2)
        self.assertEqual(reconstructed_document.blocks[1].inlines[1].style.italic, True)
        self.assertEqual(reconstructed_document.blocks[1].inlines[2].kind, "line_break")

        reconstructed_poetry = reconstructed_document.blocks[3]
        poetry_semantics = read_block_semantics(reconstructed_poetry)
        self.assertEqual(poetry_semantics.role, "quote")
        self.assertEqual(poetry_semantics.quote_kind, "poetry")
        self.assertEqual(poetry_semantics.lineation, "verse")
        self.assertEqual(poetry_semantics.lines, ["Premier vers", "Deuxieme vers"])

    def test_poetry_invariant_exports_to_lg_l(self) -> None:
        block = QuoteBlock(block_id="q1", text="Premier vers\nDeuxieme vers")
        write_block_semantics(
            block,
            BlockSemantics(
                role="quote",
                quote_kind="poetry",
                lineation="verse",
                lines=["Premier vers", "Deuxieme vers"],
            ),
        )
        document = Document(
            document_id="doc-xml-poetry",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        xml_text = TeiXmlExporter().export_document(document)
        root = ET.fromstring(xml_text)
        lines = root.findall(f".//{_q('lg')}/{_q('l')}")
        self.assertEqual([line.text for line in lines], ["Premier vers", "Deuxieme vers"])

    def test_no_exporter_local_guessing_from_style_or_protected_zone(self) -> None:
        document = Document(
            document_id="doc-no-guess",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Paragraph(
                    block_id="p1",
                    text="Ligne courte potentiellement ambigue",
                    attributes={"style_name": "TEI_verse", "protected_zone": "poetry"},
                )
            ],
        )

        mapped_document, _ = MetopesMapper().apply(document)
        self.assertNotEqual(mapped_document.blocks[0].attributes.get("metopes_style"), "TEI_verse")

        xml_text = TeiXmlExporter().export_document(mapped_document)
        root = ET.fromstring(xml_text)
        self.assertEqual(len(root.findall(f".//{_q('lg')}")), 0)

    def test_docx_xml_consistency_from_same_canonical_poetry_semantics(self) -> None:
        poetry_block = QuoteBlock(block_id="q1", text="Vers 1\nVers 2")
        write_block_semantics(
            poetry_block,
            BlockSemantics(
                role="quote",
                quote_kind="poetry",
                lineation="verse",
                lines=["Vers 1", "Vers 2"],
            ),
        )
        document = Document(
            document_id="doc-consistency",
            source_path="source.docx",
            source_format="docx",
            blocks=[poetry_block],
        )

        mapped_document, _ = MetopesMapper().apply(document)
        self.assertEqual(mapped_document.blocks[0].attributes.get("metopes_style"), "TEI_verse")

        xml_text = TeiXmlExporter().export_document(mapped_document)
        root = ET.fromstring(xml_text)
        lines = root.findall(f".//{_q('lg')}/{_q('l')}")
        self.assertEqual([line.text for line in lines], ["Vers 1", "Vers 2"])

    def test_chronology_is_not_classified_as_poetry(self) -> None:
        document = Document(
            document_id="doc-chronology",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Paragraph(block_id="c1", text="1789. Etats generaux"),
                Paragraph(block_id="c2", text="1791. Premiere constitution"),
                Paragraph(block_id="c3", text="1792. Proclamation de la Republique"),
            ],
        )

        StructurePreparationService().process(document, mode="heuristic")
        PivotCanonicalizer().apply(document)
        diagnostics = PivotValidator().validate(document)

        self.assertFalse(any(read_block_semantics(block).quote_kind == "poetry" for block in document.blocks))
        self.assertFalse(any(diag.rule_id == "pivot.poetry.lines.required" for diag in diagnostics))

        xml_text = TeiXmlExporter().export_document(document)
        root = ET.fromstring(xml_text)
        self.assertEqual(len(root.findall(f".//{_q('lg')}")), 0)


if __name__ == "__main__":
    unittest.main()
