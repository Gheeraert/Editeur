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
        document_id="doc-offsets",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[Paragraph(block_id="p1", text=text)],
    )
    _corrected, transformations = OrthotypoService().apply(document)
    return transformations


class OrthotypoTransformationOffsetsTests(unittest.TestCase):
    """
    Phase 6 bis : chaque Transformation porte offset_start/offset_end (position du
    fragment "before" dans le texte tel qu'il existait juste avant l'application de
    cette règle précise — coordinate_space="pre_rule_text"), et sequence (ordre réel
    d'application). Localisation acquise ; ancrage OOXML précis par run Word et
    génération de w:ins/w:del restent hors périmètre (voir
    docs/PHASE6BIS_ASSAINISSEMENT.md).
    """

    def test_two_identical_occurrences_of_the_same_rule_get_distinct_offsets(self) -> None:
        text = 'Il dit "bonjour". Puis "au revoir".'
        transformations = _apply(text)
        guillemets_tr = [t for t in transformations if t.rule_id == "purh.guillemets.droits"]
        self.assertEqual(len(guillemets_tr), 2)
        offsets = [(t.attributes["offset_start"], t.attributes["offset_end"]) for t in guillemets_tr]
        self.assertEqual(len(set(offsets)), 2, "les deux occurrences doivent avoir des offsets distincts")
        for t in guillemets_tr:
            start, end = t.attributes["offset_start"], t.attributes["offset_end"]
            # L'offset pointe exactement vers le fragment "before" dans le texte
            # d'entrée de cette règle (ici le texte du bloc, aucune règle antérieure
            # dans la chaîne ne l'ayant modifié).
            self.assertEqual(text[start:end], t.before)

    def test_two_successive_rules_modifying_nearby_zones_have_distinct_sequence(self) -> None:
        text = 'Voici: "bonjour".'
        transformations = _apply(text)
        rule_ids = {t.rule_id for t in transformations}
        self.assertIn("purh.espaces.avant_ponct_forte", rule_ids)
        self.assertIn("purh.guillemets.droits", rule_ids)
        sequences = [t.attributes["sequence"] for t in transformations]
        self.assertEqual(sequences, sorted(set(sequences)), "sequence doit être strictement croissante et unique")

    def test_purely_textual_transformation_has_no_styling_flag(self) -> None:
        transformations = _apply("Attendez...")
        self.assertEqual(len(transformations), 1)
        t = transformations[0]
        self.assertEqual(t.rule_id, "purh.points_suspension")
        self.assertNotIn("century_styling", t.attributes)
        self.assertNotIn("numero_styling", t.attributes)

    def test_purely_stylistic_transformation_is_flagged_and_located(self) -> None:
        transformations = _apply("n° 5")
        styling_tr = [t for t in transformations if t.rule_id == "R-NO-001"]
        self.assertEqual(len(styling_tr), 1)
        t = styling_tr[0]
        self.assertTrue(t.attributes.get("numero_styling"))
        self.assertEqual(t.attributes["coordinate_space"], "pre_rule_text")
        self.assertIsInstance(t.attributes["offset_start"], int)
        self.assertIsInstance(t.attributes["offset_end"], int)

    def test_note_transformations_carry_offsets_too(self) -> None:
        document = Document(
            document_id="doc-offsets-note",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            notes=[Note(note_id="ftn1", text='Voici: "une note".')],
        )
        _corrected, transformations = OrthotypoService().apply(document)
        self.assertTrue(transformations)
        for t in transformations:
            self.assertIn("offset_start", t.attributes)
            self.assertIn("offset_end", t.attributes)
            self.assertIn("sequence", t.attributes)

    def test_sequence_order_matches_application_order(self) -> None:
        text = 'Il dit "bonjour": "au revoir" du xviie au xixe siècles, sans doute...'
        transformations = _apply(text)
        by_sequence = sorted(transformations, key=lambda t: t.attributes["sequence"])
        # purh.points_suspension (le premier "..." à droite) puis guillemets puis
        # ponctuation forte puis purh.siecles puis R-SO-001 : voir _build_rules pour
        # l'ordre des règles et _apply_special_stylings pour le stylage en aval.
        self.assertEqual(by_sequence[-1].rule_id, "R-SO-001")
        self.assertLess(
            [t.rule_id for t in by_sequence].index("purh.siecles"),
            [t.rule_id for t in by_sequence].index("R-SO-001"),
        )


if __name__ == "__main__":
    unittest.main()
