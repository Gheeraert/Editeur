from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Paragraph
from purh_editorial.services.bibliography_normalizer import BibliographyNormalizer


def _doc(entry_text: str, *, entry_attributes: dict | None = None) -> Document:
    return Document(
        document_id="doc-biblio",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[
            Paragraph(block_id="h1", text="Bibliographie", block_type="heading"),
            Paragraph(block_id="p1", text=entry_text, attributes=entry_attributes or {}),
        ],
    )


class BibliographyNormalizerTests(unittest.TestCase):
    def test_entry_is_promoted_and_normalized(self) -> None:
        doc = _doc("Dupont, Jean, Un essai, Paris, PUF, 2020, p. 12")
        newdoc, transformations = BibliographyNormalizer().apply(doc)
        entry = newdoc.blocks[1]
        self.assertEqual(entry.block_type, "bibliography_item")
        self.assertEqual(entry.text, "Dupont, Jean, Un essai, Paris, PUF, 2020, p. 12.")
        self.assertTrue(transformations)

    def test_transformations_carry_distinct_rule_ids_per_correction(self) -> None:
        doc = _doc("Dupont, Jean, Un essai, Paris, PUF, 2020, p. 12")
        _newdoc, transformations = BibliographyNormalizer().apply(doc)
        rule_ids = {t.rule_id for t in transformations}
        self.assertIn("purh.biblio.pagination_nnbsp", rule_ids)
        self.assertIn("purh.biblio.ponctuation_finale", rule_ids)
        self.assertNotIn("purh.biblio.batch", rule_ids)
        for t in transformations:
            self.assertNotEqual(t.rule_id, "purh.biblio.batch")

    def test_numero_rule_gets_its_own_rule_id(self) -> None:
        doc = _doc("Dupont, Jean, Un essai, Paris, PUF, 2020, n° 42.")
        _newdoc, transformations = BibliographyNormalizer().apply(doc)
        rule_ids = {t.rule_id for t in transformations}
        self.assertIn("purh.biblio.numero_nnbsp", rule_ids)

    def test_already_clean_entry_produces_no_transformation(self) -> None:
        doc = _doc("Dupont, Jean, Un essai, Paris, PUF, 2020, p. 12.")
        _newdoc, transformations = BibliographyNormalizer().apply(doc)
        self.assertEqual(transformations, [])

    def test_explicit_protected_zone_on_entry_is_respected(self) -> None:
        doc = _doc(
            "Dupont, Jean, Un essai, Paris, PUF, 2020, p. 12",
            entry_attributes={"protected_zone": "bibliography"},
        )
        newdoc, transformations = BibliographyNormalizer().apply(doc)
        entry = newdoc.blocks[1]
        # Promotion to bibliography_item still happens (structural fact), but
        # the text itself must not be rewritten under an explicit veto.
        self.assertEqual(entry.text, "Dupont, Jean, Un essai, Paris, PUF, 2020, p. 12")
        self.assertEqual(transformations, [])


if __name__ == "__main__":
    unittest.main()
