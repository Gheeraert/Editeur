from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Paragraph
from purh_editorial.services.structure_service import (
    StructurePreparationService,
    settings_for_heuristic_profile,
)


class HeuristicProfileTests(unittest.TestCase):
    def test_conservative_profile_thresholds(self) -> None:
        settings, warnings = settings_for_heuristic_profile("conservative")
        self.assertEqual(warnings, [])
        self.assertEqual(settings.heading_transform_threshold, 0.90)
        self.assertEqual(settings.heading_diagnostic_threshold, 0.70)
        self.assertEqual(settings.poetry_transform_threshold, 0.92)
        self.assertEqual(settings.poetry_diagnostic_threshold, 0.70)
        self.assertEqual(settings.heading_ai_min_score, 0.70)
        self.assertEqual(settings.heading_ai_max_score, 0.90)
        self.assertEqual(settings.poetry_ai_min_score, 0.70)
        self.assertEqual(settings.poetry_ai_max_score, 0.92)

    def test_balanced_profile_thresholds(self) -> None:
        settings, _ = settings_for_heuristic_profile("balanced")
        self.assertEqual(settings.heading_transform_threshold, 0.85)
        self.assertEqual(settings.heading_diagnostic_threshold, 0.60)
        self.assertEqual(settings.poetry_transform_threshold, 0.90)
        self.assertEqual(settings.poetry_diagnostic_threshold, 0.65)
        self.assertEqual(settings.heading_ai_min_score, 0.60)
        self.assertEqual(settings.heading_ai_max_score, 0.85)
        self.assertEqual(settings.poetry_ai_min_score, 0.65)
        self.assertEqual(settings.poetry_ai_max_score, 0.90)

    def test_exploratory_profile_thresholds(self) -> None:
        settings, _ = settings_for_heuristic_profile("exploratory")
        self.assertEqual(settings.heading_transform_threshold, 0.75)
        self.assertEqual(settings.heading_diagnostic_threshold, 0.50)
        self.assertEqual(settings.poetry_transform_threshold, 0.80)
        self.assertEqual(settings.poetry_diagnostic_threshold, 0.55)
        self.assertEqual(settings.heading_ai_min_score, 0.50)
        self.assertEqual(settings.heading_ai_max_score, 0.75)
        self.assertEqual(settings.poetry_ai_min_score, 0.55)
        self.assertEqual(settings.poetry_ai_max_score, 0.80)

    def test_override_explicit_threshold(self) -> None:
        settings, warnings = settings_for_heuristic_profile(
            "balanced",
            heading_transform_threshold=0.93,
            heading_diagnostic_threshold=0.55,
        )
        self.assertEqual(settings.heading_transform_threshold, 0.93)
        self.assertEqual(settings.heading_diagnostic_threshold, 0.55)
        self.assertEqual(settings.heading_ai_min_score, 0.55)
        self.assertEqual(settings.heading_ai_max_score, 0.93)
        self.assertEqual(warnings, [])

    def test_override_poetry_threshold_updates_ai_zone(self) -> None:
        settings, warnings = settings_for_heuristic_profile(
            "balanced",
            poetry_transform_threshold=0.88,
            poetry_diagnostic_threshold=0.58,
        )
        self.assertEqual(settings.poetry_transform_threshold, 0.88)
        self.assertEqual(settings.poetry_diagnostic_threshold, 0.58)
        self.assertEqual(settings.poetry_ai_min_score, 0.58)
        self.assertEqual(settings.poetry_ai_max_score, 0.88)
        self.assertEqual(warnings, [])

    def test_out_of_range_threshold_is_clamped(self) -> None:
        settings, warnings = settings_for_heuristic_profile(
            "balanced",
            heading_transform_threshold=1.6,
        )
        self.assertEqual(settings.heading_transform_threshold, 1.0)
        self.assertTrue(any("Out-of-range threshold" in warning for warning in warnings))

    def test_inconsistent_thresholds_restore_profile_values(self) -> None:
        settings, warnings = settings_for_heuristic_profile(
            "balanced",
            heading_transform_threshold=0.40,
            heading_diagnostic_threshold=0.80,
        )
        self.assertEqual(settings.heading_transform_threshold, 0.85)
        self.assertEqual(settings.heading_diagnostic_threshold, 0.60)
        self.assertEqual(settings.heading_ai_min_score, 0.60)
        self.assertEqual(settings.heading_ai_max_score, 0.85)
        self.assertTrue(any("Inconsistent heading thresholds" in warning for warning in warnings))

    def test_inconsistent_poetry_thresholds_restore_profile_ai_zone(self) -> None:
        settings, warnings = settings_for_heuristic_profile(
            "balanced",
            poetry_transform_threshold=0.40,
            poetry_diagnostic_threshold=0.80,
        )
        self.assertEqual(settings.poetry_transform_threshold, 0.90)
        self.assertEqual(settings.poetry_diagnostic_threshold, 0.65)
        self.assertEqual(settings.poetry_ai_min_score, 0.65)
        self.assertEqual(settings.poetry_ai_max_score, 0.90)
        self.assertTrue(any("Inconsistent poetry thresholds" in warning for warning in warnings))

    def test_veto_blocks_even_with_exploratory_profile(self) -> None:
        settings, _ = settings_for_heuristic_profile("exploratory")
        service = StructurePreparationService(heuristic_settings=settings)
        doc = Document(
            document_id="doc-veto",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="VI, I, 52", attributes={"all_runs_bold": True})],
        )
        diagnostics, _ = service.process(doc)
        self.assertNotEqual(doc.blocks[0].block_type, "heading")
        self.assertFalse(any(d.rule_id == "R-STRUCT-HEADING-001" for d in diagnostics))

    def test_disable_scored_heuristics_keeps_non_explicit_heading_as_paragraph(self) -> None:
        settings, _ = settings_for_heuristic_profile(
            "exploratory",
            enable_scored_heuristics=False,
        )
        service = StructurePreparationService(heuristic_settings=settings)
        doc = Document(
            document_id="doc-det",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="La reception du modele tragique", attributes={"all_runs_bold": True})],
        )
        service.process(doc, mode="deterministic")
        self.assertNotEqual(doc.blocks[0].block_type, "heading")

    def test_deterministic_mode_bold_short_paragraph_not_promoted_to_heading(self) -> None:
        settings, _ = settings_for_heuristic_profile("balanced")
        service = StructurePreparationService(heuristic_settings=settings)
        doc = Document(
            document_id="doc-det-bold",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="La reception du modele tragique", attributes={"all_runs_bold": True})],
        )
        diagnostics, _ = service.process(doc, mode="deterministic")
        self.assertEqual(doc.blocks[0].block_type, "paragraph")
        self.assertFalse(any(d.rule_id == "R-STRUCT-HEADING-001" for d in diagnostics))

    def test_heuristic_mode_bold_short_paragraph_promoted_to_heading(self) -> None:
        settings, _ = settings_for_heuristic_profile("balanced")
        service = StructurePreparationService(heuristic_settings=settings)
        doc = Document(
            document_id="doc-heur-bold",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="La reception du modele tragique", attributes={"all_runs_bold": True})],
        )
        service.process(doc, mode="heuristic")
        self.assertEqual(doc.blocks[0].block_type, "heading")

    def test_deterministic_mode_explicit_heading_style_is_promoted(self) -> None:
        settings, _ = settings_for_heuristic_profile("conservative")
        service = StructurePreparationService(heuristic_settings=settings)
        doc = Document(
            document_id="doc-det-style-heading",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="Intertitre", attributes={"style_name": "Heading 2"})],
        )
        service.process(doc, mode="deterministic")
        self.assertEqual(doc.blocks[0].block_type, "heading")
        self.assertEqual(doc.blocks[0].attributes.get("heading_level"), 2)

    def test_deterministic_mode_no_poetry_diagnostic(self) -> None:
        settings, _ = settings_for_heuristic_profile("exploratory")
        service = StructurePreparationService(heuristic_settings=settings)
        doc = Document(
            document_id="doc-det-poetry",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                Paragraph(block_id="p1", text="Je vois deja la rame, et la barque fatale."),
                Paragraph(block_id="p2", text="Le vent du soir descend sur les eaux sans retour."),
                Paragraph(block_id="p3", text="La nuit ouvre un passage ou s'effacent nos traces."),
            ],
        )
        diagnostics, _ = service.process(doc, mode="deterministic")
        self.assertFalse(any(d.rule_id == "R-CI-POETRY-001" for d in diagnostics))

    def test_deterministic_mode_no_quote_block_by_guillemets(self) -> None:
        settings, _ = settings_for_heuristic_profile("balanced")
        service = StructurePreparationService(heuristic_settings=settings)
        quoted = "« " + ("texte " * 40).strip() + " »"
        doc = Document(
            document_id="doc-det-quote",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text=quoted)],
        )
        service.process(doc, mode="deterministic")
        self.assertEqual(doc.blocks[0].block_type, "paragraph")

    def test_heuristic_mode_quote_block_by_guillemets_is_preserved(self) -> None:
        settings, _ = settings_for_heuristic_profile("balanced")
        service = StructurePreparationService(heuristic_settings=settings)
        quoted = "« " + ("texte " * 40).strip() + " »"
        doc = Document(
            document_id="doc-heur-quote",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                Paragraph(block_id="h1", text="Titre", block_type="heading"),
                Paragraph(block_id="p1", text=quoted),
            ],
        )
        service.process(doc, mode="heuristic")
        self.assertEqual(doc.blocks[1].block_type, "quote_block")

    def test_ai_candidate_true_only_in_grey_zone_for_heading(self) -> None:
        settings, _ = settings_for_heuristic_profile("balanced")
        service = StructurePreparationService(heuristic_settings=settings)
        block = Paragraph(block_id="p1", text="Cadre theorique")
        decision = service._score_heading_candidate(block=block, settings=settings)
        self.assertEqual(settings.heading_ai_min_score, settings.heading_diagnostic_threshold)
        self.assertEqual(settings.heading_ai_max_score, settings.heading_transform_threshold)
        self.assertEqual(decision.ai_candidate, settings.heading_ai_min_score <= decision.score < settings.heading_ai_max_score)

    def test_deterministic_scoring_keeps_ai_candidate_false(self) -> None:
        settings, _ = settings_for_heuristic_profile("balanced", enable_scored_heuristics=False)
        service = StructurePreparationService(heuristic_settings=settings)
        block = Paragraph(block_id="p1", text="Cadre theorique")
        decision = service._score_heading_candidate(block=block, settings=settings)
        self.assertFalse(decision.ai_candidate)


if __name__ == "__main__":
    unittest.main()
