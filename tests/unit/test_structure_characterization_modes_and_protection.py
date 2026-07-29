from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Paragraph
from purh_editorial.services.structure_service import StructurePreparationService, settings_for_heuristic_profile


def _document(blocks: list[Paragraph]) -> Document:
    return Document("doc-structure-characterization", "fixture.txt", "txt", blocks=blocks)


class StructureCharacterizationModesAndProtectionTests(unittest.TestCase):
    def test_profile_auto_apply_diagnostics_is_true_only_for_exploratory(self) -> None:
        expected = {"conservative": False, "balanced": False, "exploratory": True}
        for profile, auto_apply in expected.items():
            with self.subTest(profile=profile):
                settings, warnings = settings_for_heuristic_profile(profile)
                self.assertEqual(warnings, [])
                self.assertEqual(settings.auto_apply_diagnostics, auto_apply)

    def test_deterministic_mode_still_assigns_frontmatter_and_promotes_explicit_source_heading(self) -> None:
        document = _document([
            Paragraph("a", text="Résumé :"),
            Paragraph("h", text="Intertitre", attributes={"style_name": "Heading 3"}),
            Paragraph("b", text="Titre gras", attributes={"all_runs_bold": True}),
        ])
        diagnostics, transformations = StructurePreparationService().process(document, mode="deterministic")
        self.assertEqual([block.block_type for block in document.blocks], ["paragraph", "heading", "paragraph"])
        self.assertEqual(document.blocks[0].attributes["semantic"]["role"], "abstract")
        self.assertEqual(document.blocks[1].attributes["heading_level"], 3)
        self.assertEqual(
            [item.rule_id for item in transformations],
            ["structure.frontmatter.abstract", "structure.source_style.heading"],
        )
        self.assertEqual(diagnostics, [])

    def test_explicitly_protected_paragraph_is_not_a_transversal_structure_veto_today(self) -> None:
        document = _document([
            Paragraph(
                "p1",
                text="TITRE PROTÉGÉ",
                attributes={"protected_zone": "code", "all_runs_bold": True},
            )
        ])
        _diagnostics, transformations = StructurePreparationService().process(document, mode="heuristic")
        self.assertEqual(document.blocks[0].block_type, "heading")
        self.assertIn("structure.allcaps.heading", {item.rule_id for item in transformations})

    def test_blank_bounded_lineation_preserves_first_id_and_removes_merged_ids(self) -> None:
        document = _document([
            Paragraph("before", text="Avant.", attributes={"blank_para_after": True}),
            Paragraph("v1", text="Premier vers,", attributes={"blank_para_before": True}),
            Paragraph("v2", text="Deuxième vers,"),
            Paragraph("v3", text="Troisième vers.", attributes={"blank_para_after": True}),
            Paragraph("after", text="Après.", attributes={"blank_para_before": True}),
        ])
        _diagnostics, transformations = StructurePreparationService().process(document, mode="heuristic")
        self.assertEqual([block.block_id for block in document.blocks], ["before", "v1", "after"])
        self.assertEqual(document.blocks[1].block_type, "lineated_block")
        self.assertEqual(document.blocks[1].attributes["merged_from"], ["v1", "v2", "v3"])
        self.assertIn("structure.lineated.blank_bounded.merge", {item.rule_id for item in transformations})


if __name__ == "__main__":
    unittest.main()
