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


def _document(blocks: list[Paragraph]) -> Document:
    return Document("doc-biblio-boundaries", "fixture.txt", "txt", blocks=blocks)


class BibliographyCharacterizationBoundariesTests(unittest.TestCase):
    def test_current_prefix_matching_treats_sources_de_as_a_bibliography_section(self) -> None:
        document = _document([
            Paragraph("h1", text="Sources de la première partie", block_type="heading"),
            Paragraph("p1", text="Texte qui suit"),
        ])
        corrected, transformations = BibliographyNormalizer().apply(document)
        self.assertEqual(corrected.blocks[1].block_type, "bibliography_item")
        self.assertEqual(corrected.blocks[1].text, "Texte qui suit.")
        self.assertEqual({item.rule_id for item in transformations}, {"purh.biblio.ponctuation_finale"})

    def test_current_non_normalized_heading_style_does_not_close_bibliography_section(self) -> None:
        document = _document([
            Paragraph("h1", text="Bibliographie", block_type="heading"),
            Paragraph("b1", text="Dupont, Jean, Essai, Paris, 2020"),
            Paragraph("h2", text="Suite", block_type="heading", attributes={"style_id": "Heading 1"}),
            Paragraph("p2", text="Texte après titre"),
        ])
        corrected, _transformations = BibliographyNormalizer().apply(document)
        self.assertEqual([block.block_type for block in corrected.blocks], ["heading", "bibliography_item", "heading", "bibliography_item"])

    def test_missing_final_point_is_currently_added_even_to_an_intentionally_open_entry(self) -> None:
        document = _document([
            Paragraph("h1", text="Bibliographie", block_type="heading"),
            Paragraph("p1", text="Dupont, Jean, Titre ouvert"),
        ])
        corrected, transformations = BibliographyNormalizer().apply(document)
        self.assertEqual(corrected.blocks[1].text, "Dupont, Jean, Titre ouvert.")
        self.assertEqual([item.rule_id for item in transformations], ["purh.biblio.ponctuation_finale"])

    def test_general_numero_rule_is_not_applied_by_the_bibliography_normalizer(self) -> None:
        document = _document([
            Paragraph("h1", text="Bibliographie", block_type="heading"),
            Paragraph("p1", text="Dupont, Jean, Essai, n° 7"),
        ])
        corrected, transformations = BibliographyNormalizer().apply(document)
        self.assertIn("n°", corrected.blocks[1].text)
        self.assertIn("purh.biblio.numero_nnbsp", {item.rule_id for item in transformations})
        self.assertNotIn("purh.numero", {item.rule_id for item in transformations})

    def test_helper_is_not_part_of_the_public_normalization_path(self) -> None:
        # Characterisation de flux : une entrée sans section n'est pas promue, même si
        # elle ressemble à une référence. Cela documente indirectement que le helper
        # privé `_looks_like_biblio_entry` n'est pas consulté ici.
        document = _document([Paragraph("p1", text="Dupont, Jean, Un essai, Paris, 2020")])
        corrected, transformations = BibliographyNormalizer().apply(document)
        self.assertEqual(corrected.blocks[0].block_type, "paragraph")
        self.assertEqual(corrected.blocks[0].text, "Dupont, Jean, Un essai, Paris, 2020")
        self.assertEqual(transformations, [])


if __name__ == "__main__":
    unittest.main()
