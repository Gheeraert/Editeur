from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Paragraph
from purh_editorial.services.structure_service import StructurePreparationService


def _document_from_lines(lines: list[str], *, attrs: dict | None = None) -> Document:
    shared_attrs = attrs or {}
    blocks = [
        Paragraph(block_id=f"b{index+1}", text=line, attributes=dict(shared_attrs))
        for index, line in enumerate(lines)
    ]
    return Document(
        document_id="doc-structure-poetry-heading-confusion",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=blocks,
    )


class StructurePoetryHeadingConfusionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = StructurePreparationService()

    def test_short_paragraph_sequence_is_poetry_quote(self) -> None:
        document = _document_from_lines(
            [
                "Et j'ai vu d'un oeil satisfait",
                "La piete de sa Princesse,",
                "Son sang est un prix digne,",
                "Je la veux pour Pretresse,",
            ]
        )

        diagnostics, transformations = self.service.process(document, mode="heuristic")

        self.assertEqual(len(document.blocks), 4)
        poetry_blocks = [b for b in document.blocks if b.attributes.get("poetry_group_id")]
        self.assertEqual(len(poetry_blocks), 4)
        self.assertTrue(all(b.attributes.get("quote_kind") == "poetry" for b in poetry_blocks))
        self.assertTrue(all(b.attributes.get("protected_zone") == "poetry" for b in poetry_blocks))
        self.assertEqual(
            [b.attributes.get("poetry_line_index") for b in poetry_blocks],
            [1, 2, 3, 4],
        )
        self.assertTrue(
            any(tr.rule_id == "structure.poetry.group.annotate" for tr in transformations)
        )
        self.assertFalse(any(block.block_type == "heading" for block in document.blocks))
        self.assertTrue(any(d.rule_id == "R-CI-POETRY-001" for d in diagnostics))

    def test_short_poetry_sequence_blocks_heading_promotion(self) -> None:
        document = _document_from_lines(
            [
                "Et j'ai vu d'un oeil satisfait",
                "La piete de sa Princesse,",
                "Son sang est un prix digne,",
                "Et je celebre son estime,",
                "Je la veux pour Pretresse,",
                "Je la rends aux rives.",
            ]
        )

        self.service.process(document, mode="heuristic")

        self.assertFalse(any(block.block_type == "heading" for block in document.blocks))
        self.assertTrue(any(block.attributes.get("poetry_group_id") for block in document.blocks))

    def test_bold_short_heading_still_promoted(self) -> None:
        document = _document_from_lines(
            ["La reception du modele tragique"],
            attrs={"all_runs_bold": True, "all_runs_italic": False},
        )

        self.service.process(document, mode="heuristic")

        self.assertEqual(document.blocks[0].block_type, "heading")

    def test_list_items_are_not_poetry(self) -> None:
        document = _document_from_lines(
            [
                "1. Premier element",
                "2. Deuxieme element",
                "3. Troisieme element",
            ]
        )

        self.service.process(document, mode="heuristic")

        self.assertFalse(any(block.block_type == "quote_block" for block in document.blocks))

    def test_dash_prefixed_lines_are_not_poetry(self) -> None:
        document = _document_from_lines(
            [
                "- Element un",
                "– Element deux",
                "— Element trois",
                "• Element quatre",
            ]
        )

        self.service.process(document, mode="heuristic")

        self.assertFalse(any(block.block_type == "quote_block" for block in document.blocks))

    def test_poetry_quote_uses_line_breaks_not_paragraph_breaks(self) -> None:
        document = _document_from_lines(
            [
                "La nuit recouvre encor la rive,",
                "Le souffle passe et se delivre,",
                "Nos pas se perdent dans la voix.",
            ]
        )

        self.service.process(document, mode="heuristic")

        self.assertEqual(len(document.blocks), 3)
        for block in document.blocks:
            self.assertTrue(block.attributes.get("poetry_group_id"))
            self.assertNotIn("\n", block.text)

    def test_diane_iphigenie_sequence_forms_single_poetry_block(self) -> None:
        document = _document_from_lines(
            [
                "DIANE annonce :",
                "Je sais le respect de la Grece,",
                "Son dessein me tient lieu d'effet,",
                "Et j'ai vu d'un oeil satisfait",
                "La piete de sa Princesse,",
                "Son sang de ma faveur est un trop digne prix,",
                "Et pour faire paraitre a quel point je l'estime,",
                "Je la veux pour Pretresse et non pas pour victime,",
                "Et l'ai deja rendue aux rives de Tauris.",
                "1. Cette ligne ne doit pas etre absorbee",
                "Apres cette adressee, elle disparait.",
            ]
        )

        self.service.process(document, mode="heuristic")

        poetry_blocks = [
            block for block in document.blocks
            if block.attributes.get("poetry_group_id") and block.attributes.get("quote_kind") == "poetry"
        ]
        self.assertEqual(len(poetry_blocks), 8)
        self.assertTrue(all(block.attributes.get("protected_zone") == "poetry" for block in poetry_blocks))
        self.assertEqual([b.attributes.get("poetry_line_index") for b in poetry_blocks], list(range(1, 9)))
        self.assertFalse(any(block.block_type == "heading" for block in document.blocks))

        self.assertEqual(document.blocks[0].block_type, "paragraph")
        self.assertEqual(document.blocks[-2].block_type, "paragraph")
        self.assertEqual(document.blocks[-1].block_type, "paragraph")

    def test_existing_verse_paragraphs_are_not_merged_or_reordered(self) -> None:
        original_lines = [
            "Tu te souviens du jour qu'en Aulide assembles",
            "Nos vaisseaux par les vents semblaient etre appeles",
            "Nous partions, et deja par mille cris de joie",
            "Nous menacions de loin les Rivages de Troie.",
            "Un prodige etonnant fit taire ce transport :",
            "Le vent qui nous flattait nous laissa dans le Port.",
        ]
        document = _document_from_lines(original_lines)

        self.service.process(document, mode="heuristic")

        self.assertEqual(len(document.blocks), 6)
        self.assertEqual([b.text for b in document.blocks], original_lines)
        self.assertTrue(all("\n" not in b.text for b in document.blocks))
        self.assertTrue(all(b.attributes.get("poetry_group_id") for b in document.blocks))


if __name__ == "__main__":
    unittest.main()
