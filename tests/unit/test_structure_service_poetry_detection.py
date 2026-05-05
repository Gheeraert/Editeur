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
                Paragraph(block_id="b3", text="Deuxième vers du même extrait."),
                Paragraph(
                    block_id="b3b",
                    text="Troisième vers : minimum requis.",
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
        semantics = read_block_semantics(lineated, )
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
                Paragraph(block_id="b3", text="Elle demande une enquête plus longue."),
                Paragraph(block_id="b3b", text="Le résultat mérite discussion.", attributes={"blank_para_after": True}),
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
                Paragraph(block_id="b3", text="Elle demande une enquête plus longue."),
                Paragraph(
                    block_id="b3b",
                    text="Un troisième argument s'impose.",
                    attributes={"blank_para_after": True},
                ),
                Paragraph(block_id="b4", text="Prose de reprise.", attributes={"blank_para_before": True}),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)
        lineated = next((b for b in document.blocks if b.block_type == "lineated_block"), None)
        self.assertIsNotNone(lineated)
        semantics = read_block_semantics(lineated, )
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
                Paragraph(block_id="b3", text="Deuxième vers du même extrait."),
                Paragraph(
                    block_id="b3b",
                    text="Troisième vers pour déclencher la fusion.",
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
            "Je vois Phèdre venir.\nDeuxième vers du même extrait.\nTroisième vers pour déclencher la fusion.",
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
                ),
                Paragraph(
                    block_id="b3b",
                    text="Troisième vers pour déclencher la fusion.",
                    inlines=[InlineSpan(text="Troisième vers pour déclencher la fusion.")],
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
        self.assertEqual(line_break_count, 2)

    def test_racine_lineated_block_does_not_promote_internal_heading(self) -> None:
        document = _doc(
            [
                Paragraph(block_id="p0", text="Commentaire avant la citation.", attributes={"blank_para_after": True}),
                Paragraph(
                    block_id="v1",
                    text="A peine son sang coule et fait rougir la terre ;",
                    attributes={"blank_para_before": True, "ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""},
                ),
                Paragraph(block_id="v2", text="Les Dieux font sur l'Autel entendre le tonnerre,", attributes={"ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""}),
                Paragraph(block_id="v3", text="Les Vents agitent l'air d'heureux fremissements,", attributes={"ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""}),
                Paragraph(block_id="v4", text="Et la Mer leur repond par ses mugissements.", attributes={"ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""}),
                Paragraph(block_id="v5", text="La Rive au loin gemit blanchissante d'ecume.", attributes={"ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""}),
                Paragraph(block_id="v6", text="La flamme du Bucher d'elle-meme s'allume.", attributes={"ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""}),
                Paragraph(block_id="v7", text="Le Ciel brille d'eclairs, s'entr'ouvre, et parmi nous", attributes={"ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""}),
                Paragraph(block_id="v8", text="Jette une sainte horreur, qui nous rassure tous.", attributes={"ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""}),
                Paragraph(block_id="v9", text="Le soldat etonne dit que dans une nue", attributes={"ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""}),
                Paragraph(block_id="v10", text="Jusque sur le bucher Diane est descendue,", attributes={"ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""}),
                Paragraph(block_id="v11", text="Et croit que s'elevant au travers de ses feux,", attributes={"ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""}),
                Paragraph(block_id="v12", text="Elle portait au ciel notre encens et nos voeux.", attributes={"ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""}),
                Paragraph(block_id="v13", text="Tout s'empresse, tout part. La seule Iphigenie", attributes={"ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""}),
                Paragraph(
                    block_id="v14",
                    text="Dans ce commun bonheur pleure son Ennemie.",
                    attributes={"blank_para_after": True, "ind_left": 708, "jc": "both", "all_runs_bold": False, "any_run_bold": False, "style_name": "", "style_id": ""},
                ),
                Paragraph(block_id="p1", text="Commentaire apres la citation.", attributes={"blank_para_before": True}),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)

        lineated_blocks = [b for b in document.blocks if b.block_type == "lineated_block"]
        self.assertEqual(len(lineated_blocks), 1)
        lineated = lineated_blocks[0]
        semantics = read_block_semantics(lineated, )
        self.assertEqual(semantics.role, "lineated_block")
        self.assertEqual(semantics.layout_kind, "lineated_block")
        self.assertEqual(semantics.lineation, "lineated")
        self.assertIn("Le Ciel brille d'eclairs, s'entr'ouvre, et parmi nous", semantics.lines)
        self.assertNotIn("quote_kind", lineated.attributes.get("semantic", {}))

        matching_blocks = [b for b in document.blocks if "Le Ciel brille d'eclairs, s'entr'ouvre, et parmi nous" in b.text]
        self.assertTrue(matching_blocks)
        for block in matching_blocks:
            self.assertNotEqual(block.block_type, "heading")
            self.assertNotIn("heading_level", block.attributes)
            self.assertNotEqual(block.attributes.get("metopes_style"), "Heading 3")


    def test_two_line_blank_bounded_author_attribution_is_not_lineated(self) -> None:
        """Régression : 'Nom / Institution' sur deux lignes ne doit pas devenir lineated_block."""
        document = _doc(
            [
                Paragraph(block_id="b0", text="Titre de l'article.", attributes={"blank_para_after": True}),
                Paragraph(
                    block_id="b1",
                    text="Caroline Labrune",
                    attributes={"blank_para_before": True},
                ),
                Paragraph(
                    block_id="b2",
                    text="CÉRÉdI (Université de Rouen Normandie)",
                    attributes={"blank_para_after": True},
                ),
                Paragraph(block_id="b3", text="Introduction.", attributes={"blank_para_before": True}),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)
        lineated = next((b for b in document.blocks if b.block_type == "lineated_block"), None)
        self.assertIsNone(lineated, "Une attribution auteur/institution sur 2 lignes ne doit pas être classée comme poésie.")

    def test_two_line_blank_bounded_title_author_paratextual_is_not_lineated(self) -> None:
        """Régression : titre + 'par Auteur' sur deux lignes ne doit pas devenir lineated_block."""
        document = _doc(
            [
                Paragraph(block_id="b0", text="Avant.", attributes={"blank_para_after": True}),
                Paragraph(
                    block_id="b1",
                    text="L'expiration mythologique racinienne",
                    attributes={"blank_para_before": True},
                ),
                Paragraph(
                    block_id="b2",
                    text="par Hubert Aupetit",
                    attributes={"blank_para_after": True},
                ),
                Paragraph(block_id="b3", text="Après.", attributes={"blank_para_before": True}),
            ]
        )

        self.service.process(document, mode="heuristic")
        self.canonicalizer.apply(document)
        lineated = next((b for b in document.blocks if b.block_type == "lineated_block"), None)
        self.assertIsNone(lineated, "Un titre + 'par Auteur' sur 2 lignes ne doit pas être classé comme poésie.")


if __name__ == "__main__":
    unittest.main()
