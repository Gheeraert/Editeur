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

        self.assertEqual(len(document.blocks), 1)
        poetry_block = document.blocks[0]
        self.assertEqual(poetry_block.block_type, "quote_block")
        self.assertEqual(poetry_block.attributes.get("quote_kind"), "poetry")
        self.assertEqual(poetry_block.attributes.get("protected_zone"), "poetry")
        self.assertIn("\n", poetry_block.text)
        self.assertEqual(len(poetry_block.attributes.get("merged_from", [])), 4)
        self.assertTrue(
            any(tr.rule_id == "structure.poetry.short_sequence.merge" for tr in transformations)
        )
        self.assertFalse(any(block.block_type == "heading" for block in document.blocks))
        self.assertTrue(
            any(tr.rule_id == "structure.poetry.short_sequence.merge" for tr in transformations)
            or any(d.rule_id == "R-CI-POETRY-001" for d in diagnostics)
        )

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
        self.assertTrue(any(block.block_type == "quote_block" for block in document.blocks))

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

        self.assertEqual(len(document.blocks), 1)
        poetry_block = document.blocks[0]
        self.assertEqual(poetry_block.block_type, "quote_block")
        self.assertIn("\n", poetry_block.text)
        self.assertEqual(poetry_block.text.count("\n"), 2)


if __name__ == "__main__":
    unittest.main()
