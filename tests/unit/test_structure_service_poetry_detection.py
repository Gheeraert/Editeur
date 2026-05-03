from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, InlineSpan, InlineStyle, Paragraph
from purh_editorial.model.semantics import read_block_semantics
from purh_editorial.services.pivot_canonicalizer import PivotCanonicalizer
from purh_editorial.services.structure_service import StructurePreparationService


def _doc(blocks: list[Paragraph]) -> Document:
    return Document(
        document_id="doc-structure-poetry-detection",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="docx",
        blocks=blocks,
    )


class StructureServicePoetryDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = StructurePreparationService()
        self.canonicalizer = PivotCanonicalizer()

    def test_blank_separated_short_paragraphs_become_canonical_poetry(self) -> None:
        document = _doc(
            [
                Paragraph(block_id="b1", text="Prose d'introduction.", attributes={"blank_para_after": True}),
                Paragraph(
                    block_id="b2",
                    text="Je vois Phèdre venir.",
                    attributes={"blank_para_before": True},
                ),
                Paragraph(
                    block_id="b3",
                    text="Deuxième vers du même extrait.",
                    attributes={"blank_para_after": True},
                ),
                Paragraph(block_id="b4", text="Prose de reprise.", attributes={"blank_para_before": True}),
            ]
        )

        _diagnostics, transformations = self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)

        lineated_blocks = [b for b in document.blocks if b.block_type == "lineated_block" and "Phèdre" in b.text]
        self.assertTrue(lineated_blocks)
        lineated = lineated_blocks[0]
        semantics = read_block_semantics(lineated, allow_legacy_inference=False)
        self.assertEqual(semantics.role, "lineated_block")
        self.assertEqual(semantics.layout_kind, "lineated_block")
        self.assertEqual(semantics.lineation, "lineated")
        self.assertIsNone(semantics.quote_kind)
        self.assertGreaterEqual(len(semantics.lines), 2)
        self.assertTrue(any(tr.rule_id == "structure.lineated.blank_bounded.merge" for tr in transformations))

    def test_blank_bounded_structure_emits_lineated_block_not_poetry_quote(self) -> None:
        document = _doc(
            [
                Paragraph(block_id="b1", text="Avant.", attributes={"blank_para_after": True}),
                Paragraph(block_id="b2", text="Cette hypothèse reste fragile.", attributes={"blank_para_before": True}),
                Paragraph(block_id="b3", text="Elle demande une enquête plus longue.", attributes={"blank_para_after": True}),
                Paragraph(block_id="b4", text="Après.", attributes={"blank_para_before": True}),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)
        lineated = next((b for b in document.blocks if b.block_type == "lineated_block"), None)
        self.assertIsNotNone(lineated)
        semantic_payload = lineated.attributes.get("semantic") or {}
        self.assertEqual(semantic_payload.get("role"), "lineated_block")
        self.assertEqual(semantic_payload.get("lineation"), "lineated")
        self.assertNotIn("quote_kind", semantic_payload)
        self.assertNotIn("genre_hint", semantic_payload)

    def test_blank_separated_chronology_is_not_poetry(self) -> None:
        document = _doc(
            [
                Paragraph(block_id="b1", text="Intro.", attributes={"blank_para_after": True}),
                Paragraph(block_id="b2", text="2020 — Début du projet.", attributes={"blank_para_before": True}),
                Paragraph(block_id="b3", text="2021 — Publication du volume."),
                Paragraph(block_id="b4", text="2022 — Nouvelle édition.", attributes={"blank_para_after": True}),
                Paragraph(block_id="b5", text="Fin.", attributes={"blank_para_before": True}),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)
        self.assertFalse(any(read_block_semantics(b).role == "lineated_block" for b in document.blocks))

    def test_blank_separated_bibliography_is_not_poetry(self) -> None:
        document = _doc(
            [
                Paragraph(block_id="b1", text="Intro.", attributes={"blank_para_after": True}),
                Paragraph(
                    block_id="b2",
                    text="Racine, Jean, Phèdre, Paris, 1677.",
                    attributes={"blank_para_before": True},
                ),
                Paragraph(
                    block_id="b3",
                    text="Corneille, Pierre, Œuvres complètes, Paris, 1980.",
                    attributes={"blank_para_after": True},
                ),
                Paragraph(block_id="b4", text="Fin.", attributes={"blank_para_before": True}),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)
        self.assertFalse(any(read_block_semantics(b).role == "lineated_block" for b in document.blocks))

    def test_blank_separated_bullet_like_list_is_not_poetry(self) -> None:
        document = _doc(
            [
                Paragraph(block_id="b1", text="Intro.", attributes={"blank_para_after": True}),
                Paragraph(block_id="b2", text="- premier point", attributes={"blank_para_before": True}),
                Paragraph(block_id="b3", text="- deuxième point", attributes={"blank_para_after": True}),
                Paragraph(block_id="b4", text="Fin.", attributes={"blank_para_before": True}),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)
        self.assertFalse(any(read_block_semantics(b).role == "lineated_block" for b in document.blocks))

    def test_blank_separated_numbered_list_is_not_poetry(self) -> None:
        document = _doc(
            [
                Paragraph(block_id="b1", text="Intro.", attributes={"blank_para_after": True}),
                Paragraph(block_id="b2", text="1. premier point", attributes={"blank_para_before": True}),
                Paragraph(block_id="b3", text="2. deuxième point", attributes={"blank_para_after": True}),
                Paragraph(block_id="b4", text="Fin.", attributes={"blank_para_before": True}),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)
        self.assertFalse(any(read_block_semantics(b).role == "lineated_block" for b in document.blocks))

    def test_two_short_normal_paragraphs_without_blank_boundaries_are_not_poetry(self) -> None:
        document = _doc(
            [
                Paragraph(block_id="b1", text="Je vois Phèdre venir."),
                Paragraph(block_id="b2", text="Deuxième vers du même extrait."),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)
        self.assertFalse(any(read_block_semantics(b).role == "lineated_block" for b in document.blocks))

    def test_blank_bounded_prose_like_lines_become_lineated_quote(self) -> None:
        document = _doc(
            [
                Paragraph(block_id="b1", text="Prose d'introduction.", attributes={"blank_para_after": True}),
                Paragraph(
                    block_id="b2",
                    text="Cette hypothèse reste fragile.",
                    attributes={"blank_para_before": True},
                ),
                Paragraph(
                    block_id="b3",
                    text="Elle demande une enquête plus longue.",
                    attributes={"blank_para_after": True},
                ),
                Paragraph(block_id="b4", text="Prose de reprise.", attributes={"blank_para_before": True}),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)
        lineated = next((b for b in document.blocks if b.block_type == "lineated_block"), None)
        self.assertIsNotNone(lineated)
        semantics = read_block_semantics(lineated, allow_legacy_inference=False)
        self.assertEqual(semantics.role, "lineated_block")
        self.assertEqual(semantics.layout_kind, "lineated_block")
        self.assertEqual(semantics.lineation, "lineated")
        self.assertIsNone(semantics.quote_kind)
        self.assertGreaterEqual(len(semantics.lines), 2)

    def test_blank_bounded_plain_text_merge_does_not_duplicate_inline_text(self) -> None:
        document = _doc(
            [
                Paragraph(block_id="b1", text="Avant.", attributes={"blank_para_after": True}),
                Paragraph(
                    block_id="b2",
                    text="Je vois Phèdre venir.",
                    attributes={"blank_para_before": True},
                ),
                Paragraph(
                    block_id="b3",
                    text="Deuxième vers du même extrait.",
                    attributes={"blank_para_after": True},
                ),
                Paragraph(block_id="b4", text="Après.", attributes={"blank_para_before": True}),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)
        lineated = next((b for b in document.blocks if b.block_type == "lineated_block"), None)
        self.assertIsNotNone(lineated)
        self.assertEqual(
            lineated.text,
            "Je vois Phèdre venir.\nDeuxième vers du même extrait.",
        )
        inline_text = "".join(
            ("\n" if span.kind == "line_break" else span.text) for span in lineated.inlines
        )
        self.assertEqual(inline_text, lineated.text)

    def test_heading_like_short_lines_are_not_poetry(self) -> None:
        document = _doc(
            [
                Paragraph(block_id="b1", text="INTRODUCTION", attributes={"blank_para_after": True}),
                Paragraph(block_id="b2", text="CHAPITRE PREMIER", attributes={"blank_para_before": True}),
                Paragraph(block_id="b3", text="SOMMAIRE", attributes={"blank_para_after": True}),
                Paragraph(block_id="b4", text="Corps du texte.", attributes={"blank_para_before": True}),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)
        self.assertFalse(any(read_block_semantics(b).role == "lineated_block" for b in document.blocks))

    def test_blank_bounded_poetry_merge_preserves_italic_inline(self) -> None:
        document = _doc(
            [
                Paragraph(block_id="b1", text="Prose d'introduction.", attributes={"blank_para_after": True}),
                Paragraph(
                    block_id="b2",
                    text="Je vois Phèdre venir.",
                    inlines=[
                        InlineSpan(text="Je vois "),
                        InlineSpan(text="Phèdre", style=InlineStyle(italic=True)),
                        InlineSpan(text=" venir."),
                    ],
                    attributes={"blank_para_before": True},
                ),
                Paragraph(
                    block_id="b3",
                    text="Deuxième vers du même extrait.",
                    inlines=[InlineSpan(text="Deuxième vers du même extrait.")],
                    attributes={"blank_para_after": True},
                ),
                Paragraph(block_id="b4", text="Prose de reprise.", attributes={"blank_para_before": True}),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)

        lineated = next((b for b in document.blocks if b.block_type == "lineated_block" and "Phèdre" in b.text), None)
        self.assertIsNotNone(lineated)
        self.assertIn("\n", lineated.text)
        self.assertTrue(lineated.inlines)
        inline_texts = [span.text for span in lineated.inlines]
        self.assertIn("Je vois ", inline_texts)
        self.assertIn("Phèdre", inline_texts)
        self.assertIn(" venir.", inline_texts)
        self.assertIn("Deuxième vers du même extrait.", inline_texts)
        italic_span = next((span for span in lineated.inlines if span.text == "Phèdre"), None)
        self.assertIsNotNone(italic_span)
        self.assertTrue(italic_span.style.italic)
        line_break_count = sum(1 for span in lineated.inlines if span.kind == "line_break")
        self.assertEqual(line_break_count, 1)


if __name__ == "__main__":
    unittest.main()
