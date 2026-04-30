from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Paragraph
from purh_editorial.services.structure_service import HeuristicSettings, StructurePreparationService, _SECTION_BIBLIO_RE


def _process_one(block: Paragraph):
    doc = Document(
        document_id="doc-heading-score",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[block],
    )
    service = StructurePreparationService()
    diagnostics, _ = service.process(doc)
    return doc.blocks[0], diagnostics, service


class HeadingHeuristicScoringTests(unittest.TestCase):
    def test_source_style_heading2_transforms_level2(self) -> None:
        block, _, _ = _process_one(Paragraph(block_id="p1", text="Intertitre", attributes={"style_name": "Heading 2"}))
        self.assertEqual(block.block_type, "heading")
        self.assertEqual(block.attributes.get("heading_level"), 2)

    def test_passage_reference_is_ignored(self) -> None:
        block, diagnostics, _ = _process_one(Paragraph(block_id="p1", text="VI, I, 52", attributes={"all_runs_bold": True}))
        self.assertNotEqual(block.block_type, "heading")
        self.assertFalse(any(d.rule_id == "R-STRUCT-HEADING-001" for d in diagnostics))

    def test_caption_reference_is_ignored(self) -> None:
        block, diagnostics, _ = _process_one(Paragraph(block_id="p1", text="page 305, accolade", attributes={"all_runs_bold": True}))
        self.assertNotEqual(block.block_type, "heading")
        self.assertFalse(any(d.rule_id == "R-STRUCT-HEADING-001" for d in diagnostics))

    def test_poetry_like_line_not_transformed(self) -> None:
        block, diagnostics, _ = _process_one(Paragraph(block_id="p1", text="Et j'ai vu d'un œil satisfait.", attributes={"all_runs_bold": True}))
        self.assertNotEqual(block.block_type, "heading")
        self.assertIn(len(diagnostics), {0, 1})

    def test_italic_poetry_line_veto(self) -> None:
        block, diagnostics, _ = _process_one(
            Paragraph(block_id="p1", text="Le vent emporte encore nos ombres,", attributes={"all_runs_italic": True})
        )
        self.assertNotEqual(block.block_type, "heading")
        self.assertFalse(any(d.rule_id == "R-STRUCT-HEADING-001" for d in diagnostics))

    def test_nominal_intertitle_transforms(self) -> None:
        block, _, _ = _process_one(Paragraph(block_id="p1", text="La réception du modèle tragique", attributes={"all_runs_bold": True}))
        self.assertEqual(block.block_type, "heading")

    def test_bold_short_sentence_like_not_promoted(self) -> None:
        block, diagnostics, _ = _process_one(
            Paragraph(block_id="p1", text="Il faut conclure rapidement.", attributes={"all_runs_bold": True})
        )
        self.assertNotEqual(block.block_type, "heading")
        self.assertFalse(any(d.rule_id == "R-STRUCT-HEADING-001" for d in diagnostics))

    def test_short_sentence_not_heading(self) -> None:
        block, diagnostics, _ = _process_one(Paragraph(block_id="p1", text="Il faut conclure rapidement."))
        self.assertNotEqual(block.block_type, "heading")
        self.assertFalse(any(d.rule_id == "R-STRUCT-HEADING-001" for d in diagnostics))

    def test_nominal_intertitle_without_bold_keeps_prudent_behavior(self) -> None:
        block, _, _ = _process_one(Paragraph(block_id="p1", text="La réception du modèle tragique"))
        self.assertEqual(block.block_type, "epigraph")

    def test_numbered_list_veto(self) -> None:
        block, _, _ = _process_one(Paragraph(block_id="p1", text="1. Élément de liste", attributes={"all_runs_bold": True}))
        self.assertNotEqual(block.block_type, "heading")

    def test_dash_en_list_item_is_detected(self) -> None:
        self.assertTrue(StructurePreparationService._looks_like_list_item("– Élément"))

    def test_dash_em_list_item_is_detected(self) -> None:
        self.assertTrue(StructurePreparationService._looks_like_list_item("— Élément"))

    def test_bullet_list_item_is_detected(self) -> None:
        self.assertTrue(StructurePreparationService._looks_like_list_item("• Élément"))

    def test_bibliography_like_veto(self) -> None:
        block, _, _ = _process_one(Paragraph(block_id="p1", text="Dupont, 2018, Histoire des formes", attributes={"all_runs_bold": True}))
        self.assertNotEqual(block.block_type, "heading")

    def test_grey_zone_emits_diagnostic_with_ai_candidate(self) -> None:
        service = StructurePreparationService(
            heuristic_settings=HeuristicSettings(
                heading_transform_threshold=0.95,
                heading_diagnostic_threshold=0.50,
                heading_ai_min_score=0.50,
                heading_ai_max_score=0.95,
            )
        )
        doc = Document(
            document_id="doc-heading-grey",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="Cadre théorique")],
        )
        diagnostics, _ = service.process(doc)
        diag = next(d for d in diagnostics if d.rule_id == "R-STRUCT-HEADING-001")
        self.assertEqual(diag.category, "heading_candidate")
        self.assertTrue(diag.attributes.get("ai_candidate"))

    def test_transform_decision_not_applied_is_reported(self) -> None:
        service = StructurePreparationService(
            heuristic_settings=HeuristicSettings(
                heading_transform_threshold=0.10,
                heading_diagnostic_threshold=0.05,
                heading_ai_min_score=0.05,
                heading_ai_max_score=0.10,
            )
        )
        doc = Document(
            document_id="doc-heading-transform-not-applied",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                Paragraph(block_id="h0", text="Titre de section", block_type="heading"),
                Paragraph(block_id="p1", text="Cadre theorique pour analyse comparee des formes narratives et argumentatives"),
            ],
        )

        diagnostics, _ = service.process(doc)

        diag = next(d for d in diagnostics if d.rule_id == "R-STRUCT-HEADING-001")
        self.assertEqual(diag.attributes.get("decision"), "transform")
        self.assertEqual(diag.attributes.get("reason"), "transform_not_applied")
        self.assertIn("score", diag.attributes)
        self.assertIn("evidence", diag.attributes)
        self.assertIn("veto_reasons", diag.attributes)
        self.assertIn("ai_candidate", diag.attributes)
        self.assertNotEqual(doc.blocks[1].block_type, "heading")

    def test_reference_section_and_guillemets_and_numero_markers_remain_detectable(self) -> None:
        service = StructurePreparationService()
        self.assertTrue(service._looks_like_block_quote("\u00ab " + "texte " * 30 + "\u00bb"))
        self.assertTrue(service._looks_like_bibliography_reference("Dupont, \u00e9d., t. II, n\u00b0 4, 2025"))
        self.assertTrue(bool(_SECTION_BIBLIO_RE.match("r\u00e9f\u00e9rences bibliographiques")))


if __name__ == "__main__":
    unittest.main()
