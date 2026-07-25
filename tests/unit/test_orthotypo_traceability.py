from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Note, Paragraph
from purh_editorial.services.orthotypo_service import OrthotypoService


def _apply(text: str) -> list:
    document = Document(
        document_id="doc-traceability",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[Paragraph(block_id="p1", text=text)],
    )
    _corrected, transformations = OrthotypoService().apply(document)
    return transformations


class OrthotypoTraceabilityTests(unittest.TestCase):
    """
    Phase 6 : une transformation distincte par occurrence corrigée, taguée par son
    propre rule_id, plutôt qu'une seule transformation "purh.orthotypo.batch" agrégeant
    tout un bloc — condition nécessaire pour générer plus tard des révisions Word
    commentées par règle appliquée.
    """

    def test_multiple_rules_in_one_block_produce_distinct_tagged_transformations(self) -> None:
        text = 'Il dit "bonjour": "au revoir" du xviie au xixe siècles, sans doute...'
        transformations = _apply(text)

        rule_ids = [t.rule_id for t in transformations]
        self.assertIn("purh.points_suspension", rule_ids)
        self.assertIn("purh.guillemets.droits", rule_ids)
        self.assertIn("purh.espaces.avant_ponct_forte", rule_ids)
        self.assertIn("purh.siecles", rule_ids)
        self.assertIn("R-SO-001", rule_ids)
        # Pas de transformation générique fourre-tout : chaque occurrence a sa propre règle.
        self.assertNotIn("purh.orthotypo.batch", rule_ids)

    def test_each_transformation_carries_only_its_own_fragment(self) -> None:
        text = "Attendez... Pourquoi?"
        transformations = _apply(text)
        by_rule = {t.rule_id: t for t in transformations}

        self.assertEqual(by_rule["purh.points_suspension"].before, "...")
        self.assertEqual(by_rule["purh.points_suspension"].after, "…")
        # Le fragment ne contient pas tout le bloc : "Attendez" n'apparaît pas dans le
        # before/after de la correction de ponctuation forte.
        self.assertNotIn("Attendez", by_rule["purh.espaces.avant_ponct_forte"].before)

    def test_same_rule_firing_twice_produces_two_transformations(self) -> None:
        text = 'Il dit "bonjour". Puis "au revoir".'
        transformations = _apply(text)
        guillemets_tr = [t for t in transformations if t.rule_id == "purh.guillemets.droits"]
        self.assertEqual(len(guillemets_tr), 2)
        self.assertEqual({t.before for t in guillemets_tr}, {'"bonjour"', '"au revoir"'})

    def test_note_transformations_are_also_tagged_per_occurrence(self) -> None:
        document = Document(
            document_id="doc-traceability-note",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            notes=[Note(note_id="ftn1", text='Voici: "une note".')],
        )
        _corrected, transformations = OrthotypoService().apply(document)
        rule_ids = {t.rule_id for t in transformations}
        self.assertIn("purh.espaces.avant_ponct_forte", rule_ids)
        self.assertIn("purh.guillemets.droits", rule_ids)


if __name__ == "__main__":
    unittest.main()
