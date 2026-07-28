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


def _unvalidated_rule_ids(text: str) -> set[str]:
    document = Document(
        document_id="doc-offsets-diagnostics",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[Paragraph(block_id="p1", text=text)],
    )
    return {
        diagnostic.rule_id
        for diagnostic in OrthotypoService().analyze_unvalidated_rules(document)
    }


class OrthotypoTransformationOffsetsTests(unittest.TestCase):
    """Offset tracing applies only to rules authorised for automatic correction."""

    def test_unvalidated_straight_quotes_are_diagnosed_without_transformation(self) -> None:
        text = 'Il dit "bonjour". Puis "au revoir".'
        self.assertEqual(_apply(text), [])
        self.assertIn("purh.guillemets.droits", _unvalidated_rule_ids(text))

    def test_unvalidated_nearby_rules_are_diagnosed_without_sequence(self) -> None:
        text = 'Voici: "bonjour".'
        self.assertEqual(_apply(text), [])
        rule_ids = _unvalidated_rule_ids(text)
        self.assertIn("purh.espaces.avant_ponct_forte", rule_ids)
        self.assertIn("purh.guillemets.droits", rule_ids)

    def test_unvalidated_points_suspension_have_no_transformation(self) -> None:
        text = "Attendez..."
        self.assertEqual(_apply(text), [])
        self.assertIn("purh.points_suspension", _unvalidated_rule_ids(text))

    def test_purely_stylistic_transformation_is_flagged_and_located(self) -> None:
        transformations = _apply("n° 5")
        styling_tr = [t for t in transformations if t.rule_id == "R-NO-001"]
        self.assertEqual(len(styling_tr), 1)
        transformation = styling_tr[0]
        self.assertTrue(transformation.attributes.get("numero_styling"))
        self.assertEqual(transformation.attributes["coordinate_space"], "pre_rule_text")
        self.assertIsInstance(transformation.attributes["offset_start"], int)
        self.assertIsInstance(transformation.attributes["offset_end"], int)

    def test_unvalidated_note_text_is_not_transformed(self) -> None:
        document = Document(
            document_id="doc-offsets-note",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            notes=[Note(note_id="ftn1", text='Voici: "une note".')],
        )
        corrected, transformations = OrthotypoService().apply(document)
        self.assertEqual(transformations, [])
        self.assertEqual(corrected.notes[0].text, 'Voici: "une note".')

    def test_offset_invariant_holds_by_sequential_replay(self) -> None:
        text = "n° 5"
        transformations = _apply(text)
        by_sequence = sorted(transformations, key=lambda t: t.attributes["sequence"])
        state = text
        for transformation in by_sequence:
            start, end = transformation.attributes["offset_start"], transformation.attributes["offset_end"]
            self.assertEqual(state[start:end], transformation.before, msg=transformation.rule_id)
            state = state[:start] + transformation.after + state[end:]

    def test_unvalidated_rules_do_not_reach_automatic_styling(self) -> None:
        text = 'Il dit "bonjour": "au revoir" du xviie au xixe siècles, sans doute...'
        self.assertEqual(_apply(text), [])
        self.assertIn("purh.points_suspension", _unvalidated_rule_ids(text))


if __name__ == "__main__":
    unittest.main()
