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
    LineatedBlock,
    Metadata,
    Paragraph,
    ProcessingReport,
    QuoteBlock,
    is_canonical_lineated_block,
    is_canonical_poetry_block,
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
    def test_lineated_block_semantic_survives_canonicalization(self) -> None:
        block = LineatedBlock(block_id="lb-verse", text="Premier vers\nDeuxieme vers")
        write_block_semantics(
            block,
            BlockSemantics(
                role="lineated_block",
                layout_kind="lineated_block",
                lineation="lineated",
                lines=["Premier vers", "Deuxieme vers"],
            ),
        )
        document = Document(
            document_id="doc-lineated-survives",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        transformations = PivotCanonicalizer().apply(document)

        self.assertFalse(transformations)
        semantic_payload = document.blocks[0].attributes.get("semantic")
        self.assertIsInstance(semantic_payload, dict)
        self.assertEqual(semantic_payload.get("lineation"), "lineated")
        self.assertEqual(semantic_payload.get("layout_kind"), "lineated_block")
        self.assertEqual(semantic_payload.get("lines"), ["Premier vers", "Deuxieme vers"])
        self.assertNotIn("quote_kind", semantic_payload)

    def test_lineated_block_semantic_round_trip(self) -> None:
        block = LineatedBlock(block_id="lb1", text="A\nB")
        write_block_semantics(
            block,
            BlockSemantics(
                role="lineated_block",
                layout_kind="lineated_block",
                lineation="lineated",
                lines=["A", "B"],
            ),
        )
        document = Document(
            document_id="doc-lineated-roundtrip",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )
        report = ProcessingReport(report_id="report-lineated-roundtrip", document_id=document.document_id)

        payload = build_pivot_payload(document, report=report)
        self.assertEqual(payload["schema_version"], "pivot-1.0")

        json_text = pivot_to_json(document, report=report)
        reconstructed_document, _ = parse_pivot_payload(json_text)
        semantics = read_block_semantics(reconstructed_document.blocks[0], )
        self.assertEqual(semantics.role, "lineated_block")
        self.assertEqual(semantics.layout_kind, "lineated_block")
        self.assertEqual(semantics.lineation, "lineated")
        self.assertEqual(semantics.lines, ["A", "B"])
        self.assertIsNone(semantics.quote_kind)

    def test_lineated_block_does_not_require_genre_hint(self) -> None:
        block = LineatedBlock(
            block_id="lb-no-genre",
            text="A\nB",
            attributes={
                "semantic": {
                    "role": "lineated_block",
                    "layout_kind": "lineated_block",
                    "lineation": "lineated",
                    "lines": ["A", "B"],
                }
            },
        )
        document = Document(
            document_id="doc-lineated-no-genre",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        diagnostics = PivotValidator().validate(document)
        self.assertFalse(any(diag.rule_id == "pivot.semantic.lineated_block_without_lines" for diag in diagnostics))
        self.assertFalse(any(diag.rule_id == "pivot.semantic.quote_fields_on_non_quote" for diag in diagnostics))

    def test_lineated_block_validator_accepts_non_quote(self) -> None:
        block = LineatedBlock(
            block_id="lb-validator-ok",
            text="A\nB",
            attributes={
                "semantic": {
                    "role": "lineated_block",
                    "layout_kind": "lineated_block",
                    "lineation": "lineated",
                    "lines": ["A", "B"],
                }
            },
        )
        document = Document(
            document_id="doc-lineated-validator-ok",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        diagnostics = PivotValidator().validate(document)
        rule_ids = {diag.rule_id for diag in diagnostics}
        self.assertNotIn("pivot.semantic.quote_fields_on_non_quote", rule_ids)

    def test_lineated_block_survives_canonicalizer(self) -> None:
        block = LineatedBlock(
            block_id="lb-canon",
            text="A\nB",
            attributes={
                "semantic": {
                    "role": "lineated_block",
                    "layout_kind": "lineated_block",
                    "lineation": "lineated",
                    "lines": ["A", "B"],
                }
            },
        )
        document = Document(
            document_id="doc-lineated-canon",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        PivotCanonicalizer().apply(document)
        semantics = read_block_semantics(document.blocks[0], )
        self.assertEqual(semantics.role, "lineated_block")
        self.assertEqual(semantics.lineation, "lineated")
        self.assertIsNone(semantics.quote_kind)

    def test_lineated_block_canonicalizes_to_lineated_semantics(self) -> None:
        block = LineatedBlock(
            block_id="lb-canonical-lineated",
            text="Premier vers\nDeuxieme vers",
        )
        write_block_semantics(
            block,
            BlockSemantics(
                role="lineated_block",
                layout_kind="lineated_block",
                lineation="lineated",
                lines=["Premier vers", "Deuxieme vers"],
            ),
        )
        document = Document(
            document_id="doc-canonical-lineated",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        PivotCanonicalizer().apply(document)
        semantic_payload = document.blocks[0].attributes.get("semantic")
        self.assertEqual(semantic_payload.get("lineation"), "lineated")
        self.assertEqual(semantic_payload.get("layout_kind"), "lineated_block")
        self.assertTrue(semantic_payload.get("lines"))
        self.assertNotIn("quote_kind", semantic_payload)

    def test_block_without_semantic_payload_returns_empty_semantics(self) -> None:
        block = QuoteBlock(
            block_id="q-no-semantic",
            text="Premier vers\nDeuxieme vers",
            attributes={"quote_kind": "poetry", "lineation": "verse"},
        )
        semantics = read_block_semantics(block)
        self.assertIsNone(semantics.role)
        self.assertIsNone(semantics.lineation)
        self.assertEqual(semantics.lines, [])

    def test_lineated_block_predicate_is_not_poetry_predicate(self) -> None:
        block = LineatedBlock(
            block_id="lb-predicate",
            text="A\nB",
            attributes={
                "semantic": {
                    "role": "lineated_block",
                    "layout_kind": "lineated_block",
                    "lineation": "lineated",
                    "lines": ["A", "B"],
                }
            },
        )

        self.assertTrue(is_canonical_lineated_block(block))
        self.assertFalse(is_canonical_poetry_block(block))

    def test_paragraph_with_lineated_semantic_is_not_canonical_lineated(self) -> None:
        block = Paragraph(
            block_id="p-not-canonical-lineated",
            text="A\nB",
            attributes={
                "semantic": {
                    "role": "lineated_block",
                    "layout_kind": "lineated_block",
                    "lineation": "lineated",
                    "lines": ["A", "B"],
                }
            },
        )
        self.assertFalse(is_canonical_lineated_block(block))

    def test_lineated_block_role_is_canonical_lineated(self) -> None:
        block = LineatedBlock(
            block_id="lb-canonical-lineated",
            text="A\nB",
            attributes={
                "semantic": {
                    "role": "lineated_block",
                    "layout_kind": "lineated_block",
                    "lineation": "lineated",
                    "lines": ["A", "B"],
                }
            },
        )
        self.assertTrue(is_canonical_lineated_block(block))

    def test_lineated_quote_role_is_canonical_lineated(self) -> None:
        block = QuoteBlock(
            block_id="q-canonical-lineated",
            text="A\nB",
            attributes={
                "semantic": {
                    "role": "quote",
                    "layout_kind": "lineated_block",
                    "lineation": "lineated",
                    "lines": ["A", "B"],
                }
            },
        )
        self.assertTrue(is_canonical_lineated_block(block))

    def test_export_requires_canonical_semantic(self) -> None:
        prose_block = QuoteBlock(
            block_id="q-prose",
            text="Citation en prose.",
        )
        lineated_block = LineatedBlock(
            block_id="lb-verse",
            text="Premier vers\nDeuxieme vers",
        )
        write_block_semantics(
            lineated_block,
            BlockSemantics(
                role="lineated_block",
                layout_kind="lineated_block",
                lineation="lineated",
                lines=["Premier vers", "Deuxieme vers"],
            ),
        )
        document = Document(
            document_id="doc-export-strict",
            source_path="source.docx",
            source_format="docx",
            blocks=[prose_block, lineated_block],
        )

        xml_text = TeiXmlExporter().export_document(document)
        root = ET.fromstring(xml_text)
        self.assertEqual(len(root.findall(f".//{_q('lg')}")), 1)
        lines = root.findall(f".//{_q('lg')}/{_q('l')}")
        self.assertEqual(len(lines), 2)
        self.assertEqual(len(root.findall(f".//{_q('cit')}")), 1)

    def test_paragraph_without_semantic_gets_canonical_role(self) -> None:
        block = Paragraph(
            block_id="p-no-semantic",
            text="Ligne breve",
        )
        document = Document(
            document_id="doc-paragraph-canonical",
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

        xml_text = TeiXmlExporter().export_document(document)
        root = ET.fromstring(xml_text)
        self.assertEqual(len(root.findall(f".//{_q('lg')}")), 0)

    def test_heading_gets_canonical_heading_role(self) -> None:
        block = Heading(
            block_id="h-canonical",
            text="Titre",
            attributes={"heading_level": 1},
        )
        document = Document(
            document_id="doc-heading-canonical",
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
        self.assertIn("pivot.semantic.lines_on_non_poetry", rule_ids)
        self.assertIn("pivot.semantic.quote_kind_used_as_lineation_legacy", rule_ids)

    def test_already_canonical_paragraph_needs_no_transformation(self) -> None:
        block = Paragraph(
            block_id="p-already-canonical",
            text="Paragraphe stable",
            attributes={"semantic": {"role": "paragraph"}},
        )
        document = Document(
            document_id="doc-already-canonical-paragraph",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        transformations = PivotCanonicalizer().apply(document)
        self.assertFalse(transformations)
        self.assertEqual(document.blocks[0].attributes.get("semantic"), {"role": "paragraph"})

    def test_already_canonical_heading_needs_no_transformation(self) -> None:
        block = Heading(
            block_id="h-already-canonical",
            text="Titre",
            attributes={
                "heading_level": 1,
                "semantic": {"role": "heading"},
            },
        )
        document = Document(
            document_id="doc-already-canonical-heading",
            source_path="source.docx",
            source_format="docx",
            blocks=[block],
        )

        transformations = PivotCanonicalizer().apply(document)
        self.assertFalse(transformations)
        self.assertEqual(document.blocks[0].attributes.get("semantic"), {"role": "heading"})

    def test_json_round_trip_preserves_canonical_semantics(self) -> None:
        poetry_block = LineatedBlock(
            block_id="q-poetry",
            text="Premier vers\nDeuxieme vers",
        )
        write_block_semantics(
            poetry_block,
            BlockSemantics(
                role="lineated_block",
                layout_kind="lineated_block",
                lineation="lineated",
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
        self.assertEqual(poetry_semantics.role, "lineated_block")
        self.assertEqual(poetry_semantics.layout_kind, "lineated_block")
        self.assertIsNone(poetry_semantics.quote_kind)
        self.assertEqual(poetry_semantics.lineation, "lineated")
        self.assertEqual(poetry_semantics.lines, ["Premier vers", "Deuxieme vers"])

    def test_poetry_invariant_exports_to_lg_l(self) -> None:
        block = LineatedBlock(block_id="q1", text="Premier vers\nDeuxieme vers")
        write_block_semantics(
            block,
            BlockSemantics(
                role="lineated_block",
                layout_kind="lineated_block",
                lineation="lineated",
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
        poetry_block = LineatedBlock(block_id="q1", text="Vers 1\nVers 2")
        write_block_semantics(
            poetry_block,
            BlockSemantics(
                role="lineated_block",
                layout_kind="lineated_block",
                lineation="lineated",
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

        self.assertFalse(any(read_block_semantics(block).role == "lineated_block" for block in document.blocks))
        self.assertFalse(any(diag.rule_id == "pivot.poetry.lines.required" for diag in diagnostics))

        xml_text = TeiXmlExporter().export_document(document)
        root = ET.fromstring(xml_text)
        self.assertEqual(len(root.findall(f".//{_q('lg')}")), 0)


if __name__ == "__main__":
    unittest.main()
