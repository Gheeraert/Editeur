from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, InlineSpan, Note, Paragraph
from purh_editorial.services.footnote_normalizer import FootnoteNormalizer
from purh_editorial.services.orthotypo_service import NNBSP


def _apply(text: str, *, note_attributes: dict | None = None, inlines: list[InlineSpan] | None = None):
    document = Document(
        document_id="doc-footnote-matrix",
        source_path="fixture.txt",
        source_format="txt",
        notes=[Note(note_id="n1", text=text, attributes=note_attributes or {}, inlines=inlines or [])],
    )
    service = FootnoteNormalizer()
    corrected, transformations = service.apply(document)
    diagnostics = service.analyze_note_normalization_exclusions(document)
    return corrected.notes[0].text, transformations, diagnostics


class FootnoteCharacterizationMatrixTests(unittest.TestCase):
    def test_current_normalization_matrix(self) -> None:
        cases = [
            ("  voir op. cit. et s. l.", f"Voir op.{NNBSP}cit. et s.{NNBSP}l.", {"purh.note.espace_initiale", "purh.note.majuscule_initiale", "purh.note.espace_op_cit", "purh.note.espace_sans_lieu_date"}),
            ("art. cit. et loc. cit.", f"art.{NNBSP}cit. et loc.{NNBSP}cit.", {"purh.note.espace_op_cit"}),
            ("fragment bibliographique sans point", "Fragment bibliographique sans point.", {"purh.note.majuscule_initiale", "purh.note.ponctuation_finale"}),
            ("doi:10.1234/exemple", "doi:10.1234/exemple.", {"purh.note.ponctuation_finale"}),
            ("van Gogh, Lettres", "van Gogh, Lettres.", {"purh.note.ponctuation_finale"}),
            ("ibid., p. 12", "ibid., p. 12.", {"purh.note.ponctuation_finale"}),
            ("- élément de liste", "- élément de liste", set()),
            ("Il a dit « ceci »", "Il a dit « ceci »", set()),
        ]
        for source, expected, expected_rule_ids in cases:
            with self.subTest(source=source):
                text, transformations, _diagnostics = _apply(source)
                self.assertEqual(text, expected)
                self.assertEqual({item.rule_id for item in transformations}, expected_rule_ids)

    def test_exclusion_diagnostics_are_non_mutating(self) -> None:
        source = "https://exemple.org/ressource"
        text, transformations, diagnostics = _apply(source)
        self.assertEqual(text, source)
        self.assertEqual(transformations, [])
        self.assertEqual({item.rule_id for item in diagnostics}, {"R-AN-004", "R-AN-005"})

    def test_inline_protection_prevents_note_normalization(self) -> None:
        source = "note sans point"
        text, transformations, diagnostics = _apply(
            source,
            inlines=[InlineSpan(text=source, attributes={"protected": True})],
        )
        self.assertEqual(text, source)
        self.assertEqual(transformations, [])
        self.assertEqual(diagnostics, [])

    def test_note_call_diagnostics_do_not_change_owning_block_text(self) -> None:
        block = Paragraph(
            block_id="p1",
            text="Texte. ",
            inlines=[InlineSpan(text="Texte. "), InlineSpan(text="", kind="note_call", note_ref="n1")],
        )
        document = Document("doc", "fixture.txt", "txt", blocks=[block])
        diagnostics = FootnoteNormalizer().analyze_note_call_placement(document)
        self.assertEqual(block.text, "Texte. ")
        self.assertEqual([item.rule_id for item in diagnostics], ["R-AN-003"])


if __name__ == "__main__":
    unittest.main()
