from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, InlineSpan, Note
from purh_editorial.services.footnote_normalizer import FootnoteNormalizer
from purh_editorial.services.orthotypo_service import NNBSP


def _normalize_note_text(note_text: str) -> str:
    document = Document(
        document_id="doc-notes",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        notes=[Note(note_id="ftn1", text=note_text)],
    )
    normalized_doc, _ = FootnoteNormalizer().apply(document)
    return normalized_doc.notes[0].text


class FootnoteNormalizerAbbreviationsTests(unittest.TestCase):
    def test_op_cit_space_is_normalized(self) -> None:
        self.assertEqual(_normalize_note_text("Voir op. cit."), f"Voir op.{NNBSP}cit.")

    def test_art_cit_space_is_normalized(self) -> None:
        self.assertEqual(_normalize_note_text("Voir art. cit."), f"Voir art.{NNBSP}cit.")

    def test_loc_cit_space_is_normalized(self) -> None:
        self.assertEqual(_normalize_note_text("Voir loc. cit."), f"Voir loc.{NNBSP}cit.")

    def test_s_l_space_is_normalized(self) -> None:
        self.assertEqual(_normalize_note_text("Voir s. l."), f"Voir s.{NNBSP}l.")

    def test_s_d_space_is_normalized(self) -> None:
        self.assertEqual(_normalize_note_text("Voir s. d."), f"Voir s.{NNBSP}d.")

    def test_already_correct_nnbsp_variant_is_preserved(self) -> None:
        text = f"Voir op.{NNBSP}cit."
        self.assertEqual(_normalize_note_text(text), text)

    def test_final_note_point_is_not_duplicated(self) -> None:
        self.assertEqual(_normalize_note_text("Voir op. cit."), f"Voir op.{NNBSP}cit.")

    def test_ibid_preceded_by_export_nbsp_separator_stays_capitalized(self) -> None:
        # DocxExporter insere un espace insecable entre l'appel de note et le texte ;
        # au reimport, ce caractere devient le premier inline de la note (voir
        # docs/PHASE1_FIABILITE_PIPELINE.md, defaut 1). "Ibid." reste le premier mot
        # reel de la note et ne doit pas etre mis en minuscule.
        document = Document(
            document_id="doc-notes",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            notes=[Note(
                note_id="ftn1",
                text="Ibid., p. 12.",
                inlines=[InlineSpan(text=" "), InlineSpan(text="Ibid., p. 12.")],
            )],
        )
        normalized_doc, _ = FootnoteNormalizer().apply(document)
        self.assertTrue(normalized_doc.notes[0].text.startswith("Ibid."))


if __name__ == "__main__":
    unittest.main()
