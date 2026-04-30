from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Heading, Paragraph
from purh_editorial.services.structure_service import StructurePreparationService


def _document_with_block(block) -> Document:
    return Document(
        document_id="doc-structure-guardrails",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[block],
    )


def _bold_paragraph(text: str) -> Paragraph:
    return Paragraph(
        block_id="p1",
        text=text,
        attributes={"all_runs_bold": True, "all_runs_italic": False},
    )


class StructureServiceHeadingGuardrailsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = StructurePreparationService()

    def _process(self, block):
        document = _document_with_block(block)
        self.service.process(document)
        return document.blocks[0]

    def test_reference_vi_i_not_promoted_to_heading(self) -> None:
        block = self._process(_bold_paragraph("VI, I,"))
        self.assertNotEqual(block.block_type, "heading")

    def test_reference_vi_i_52_not_promoted_to_heading(self) -> None:
        block = self._process(_bold_paragraph("VI, I, 52"))
        self.assertNotEqual(block.block_type, "heading")

    def test_reference_viii_pr_18_not_promoted_to_heading(self) -> None:
        block = self._process(_bold_paragraph("VIII, Pr., 18"))
        self.assertNotEqual(block.block_type, "heading")

    def test_page_accolade_not_promoted_to_heading(self) -> None:
        block = self._process(_bold_paragraph("page 305, accolade"))
        self.assertNotEqual(block.block_type, "heading")

    def test_p_accolade_not_promoted_to_heading(self) -> None:
        block = self._process(_bold_paragraph("p. 390, accolade"))
        self.assertNotEqual(block.block_type, "heading")

    def test_face_a_la_partie_soulignee_not_promoted_to_heading(self) -> None:
        block = self._process(_bold_paragraph("face à la partie soulignée"))
        self.assertNotEqual(block.block_type, "heading")

    def test_poetry_like_line_not_promoted_to_heading(self) -> None:
        block = self._process(_bold_paragraph("Je vois déjà la rame, et la barque fatale."))
        self.assertNotEqual(block.block_type, "heading")

    def test_italic_poetry_like_line_not_promoted_to_heading(self) -> None:
        block = self._process(
            Paragraph(
                block_id="p1",
                text="Je vois déjà la rame, et la barque fatale.",
                attributes={"all_runs_italic": True, "all_runs_bold": False},
            )
        )
        self.assertNotEqual(block.block_type, "heading")

    def test_short_bibliography_entry_not_promoted_to_heading(self) -> None:
        block = self._process(_bold_paragraph("Dupont, 2018, Histoire des formes"))
        self.assertNotEqual(block.block_type, "heading")

    def test_short_numbered_list_item_not_promoted_to_heading(self) -> None:
        block = self._process(_bold_paragraph("1. Élément de liste"))
        self.assertNotEqual(block.block_type, "heading")

    def test_source_heading_2_style_is_promoted_with_level_2(self) -> None:
        block = self._process(
            Paragraph(block_id="p1", text="Intertitre", attributes={"style_name": "Heading 2"})
        )
        self.assertEqual(block.block_type, "heading")
        self.assertEqual(block.attributes.get("heading_level"), 2)

    def test_source_titre_2_style_is_promoted_with_level_2(self) -> None:
        block = self._process(
            Paragraph(block_id="p1", text="Intertitre", attributes={"style_name": "Titre 2"})
        )
        self.assertEqual(block.block_type, "heading")
        self.assertEqual(block.attributes.get("heading_level"), 2)

    def test_existing_heading_levels_do_not_regress(self) -> None:
        document = Document(
            document_id="doc-existing-headings",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                Heading(block_id="h1", text="Titre 1", attributes={"heading_level": 1}),
                Heading(block_id="h2", text="Titre 2", attributes={"heading_level": 2}),
                Heading(block_id="h3", text="Titre 3", attributes={"heading_level": 3}),
            ],
        )
        self.service.process(document)
        self.assertEqual(document.blocks[0].attributes.get("heading_level"), 1)
        self.assertEqual(document.blocks[1].attributes.get("heading_level"), 2)
        self.assertEqual(document.blocks[2].attributes.get("heading_level"), 3)

    def test_typical_short_intertitle_can_still_use_conservative_heuristic(self) -> None:
        block = self._process(Paragraph(block_id="p1", text="Cadre théorique"))
        self.assertEqual(block.block_type, "heading")


if __name__ == "__main__":
    unittest.main()

