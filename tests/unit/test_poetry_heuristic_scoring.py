from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Paragraph
from purh_editorial.services.structure_service import HeuristicSettings, StructurePreparationService


def _doc_from_lines(lines: list[str], *, attrs: dict | None = None) -> Document:
    block_attrs = attrs or {}
    blocks = [
        Paragraph(block_id=f"p{index+1}", text=line, attributes=dict(block_attrs))
        for index, line in enumerate(lines)
    ]
    return Document(
        document_id="doc-poetry-heuristics",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=blocks,
    )


class PoetryHeuristicScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = StructurePreparationService()

    def test_four_manifest_lines_get_high_score_without_veto(self) -> None:
        document = _doc_from_lines(
            [
                "Je marche encor, dans la brume qui se leve,",
                "Tu cherches l'aube, au bord du meme quai,",
                "Nous voyons l'eau qui tremble et se releve,",
                "Le vent rejoint nos pas, puis se defait.",
            ]
        )
        decisions = self.service.analyze_poetry_candidates(document)

        self.assertEqual(len(decisions), 1)
        decision = decisions[0]
        self.assertGreaterEqual(decision.score, 0.85)
        self.assertIn(decision.decision, {"transform", "diagnostic"})
        self.assertEqual(decision.veto_reasons, [])

    def test_three_ambiguous_short_paragraphs_get_diagnostic(self) -> None:
        document = _doc_from_lines(
            [
                "Je cherche encore une voix,",
                "Dans l'ombre d'un couloir,",
                "Un nom qui se retire.",
            ]
        )
        decisions = self.service.analyze_poetry_candidates(document)

        self.assertEqual(len(decisions), 1)
        decision = decisions[0]
        self.assertGreaterEqual(decision.score, self.service.heuristic_settings.poetry_diagnostic_threshold)
        self.assertLess(decision.score, self.service.heuristic_settings.poetry_transform_threshold)
        self.assertEqual(decision.decision, "diagnostic")

    def test_passage_reference_triggers_veto_and_ignore(self) -> None:
        document = _doc_from_lines(
            [
                "VI, I, 52",
                "Je cherche encore,",
                "Un nom.",
            ]
        )
        decisions = self.service.analyze_poetry_candidates(document)

        self.assertEqual(decisions[0].decision, "ignore")
        self.assertIn("passage_reference", decisions[0].veto_reasons)

    def test_caption_reference_triggers_veto_and_ignore(self) -> None:
        document = _doc_from_lines(
            [
                "p. 390, accolade",
                "Je cherche encore,",
                "Un nom.",
            ]
        )
        decisions = self.service.analyze_poetry_candidates(document)

        self.assertEqual(decisions[0].decision, "ignore")
        self.assertIn("caption_or_reference", decisions[0].veto_reasons)

    def test_numbered_list_triggers_veto_and_ignore(self) -> None:
        document = _doc_from_lines(
            [
                "1. Premier point",
                "2. Second point",
                "3. Troisieme point",
            ]
        )
        decisions = self.service.analyze_poetry_candidates(document)

        self.assertEqual(decisions[0].decision, "ignore")
        self.assertIn("list_like", decisions[0].veto_reasons)

    def test_short_bibliography_like_sequence_triggers_veto_and_ignore(self) -> None:
        document = _doc_from_lines(
            [
                "Dupont, 2018, Histoire des formes",
                "Martin, 2020, Lire les textes",
                "Bernard, 2016, Etudes de style",
            ]
        )
        decisions = self.service.analyze_poetry_candidates(document)

        self.assertEqual(decisions[0].decision, "ignore")
        self.assertIn("bibliography_like", decisions[0].veto_reasons)

    def test_explicit_heading_style_triggers_veto_and_ignore(self) -> None:
        document = _doc_from_lines(
            [
                "Intertitre probable",
                "Autre ligne courte",
                "Troisieme ligne courte",
            ],
            attrs={"style_name": "Heading 2"},
        )
        decisions = self.service.analyze_poetry_candidates(document)

        self.assertEqual(decisions[0].decision, "ignore")
        self.assertIn("heading_explicit", decisions[0].veto_reasons)

    def test_default_thresholds(self) -> None:
        settings = HeuristicSettings()
        self.assertEqual(settings.poetry_transform_threshold, 0.90)
        self.assertEqual(settings.poetry_diagnostic_threshold, 0.65)
        self.assertEqual(settings.poetry_ai_min_score, 0.65)
        self.assertEqual(settings.poetry_ai_max_score, 0.90)
        self.assertFalse(settings.allow_ai_for_poetry_candidates)

    def test_ai_candidate_is_true_only_in_grey_zone_without_ai_call(self) -> None:
        document = _doc_from_lines(
            [
                "Je cherche encore une voix,",
                "Dans l'ombre d'un couloir,",
                "Un nom qui se retire.",
            ]
        )
        decision = self.service.analyze_poetry_candidates(document)[0]
        self.assertGreaterEqual(decision.score, self.service.heuristic_settings.poetry_ai_min_score)
        self.assertLess(decision.score, self.service.heuristic_settings.poetry_ai_max_score)
        self.assertTrue(decision.ai_candidate)
        self.assertFalse(self.service.heuristic_settings.allow_ai_for_poetry_candidates)


if __name__ == "__main__":
    unittest.main()
