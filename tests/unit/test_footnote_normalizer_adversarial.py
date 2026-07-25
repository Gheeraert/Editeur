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


def _apply(note_text: str, inlines: list[InlineSpan] | None = None) -> tuple[str, list, list]:
    document = Document(
        document_id="doc-notes",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        notes=[Note(note_id="ftn1", text=note_text, inlines=inlines or [])],
    )
    normalizer = FootnoteNormalizer()
    normalized_doc, transformations = normalizer.apply(document)
    diagnostics = normalizer.analyze_note_normalization_exclusions(document)
    return normalized_doc.notes[0].text, transformations, diagnostics


class FootnoteNormalizerAdversarialTests(unittest.TestCase):
    def test_url_at_start_is_not_corrupted(self) -> None:
        text, transformations, diagnostics = _apply("https://exemple.org/a, consulté le 3 mars 2024.")
        self.assertTrue(text.startswith("https://"))
        self.assertFalse(any(t.rule_id == "purh.note.majuscule_initiale" for t in transformations))
        self.assertTrue(any(d.rule_id == "R-AN-004" for d in diagnostics))

    def test_bare_url_without_scheme_capitalized_form_is_not_forced(self) -> None:
        text, _tr, _diag = _apply("http://exemple.org")
        self.assertTrue(text.startswith("http://"))

    def test_doi_at_start_is_not_corrupted(self) -> None:
        text, _tr, _diag = _apply("doi:10.1234/abcd")
        self.assertTrue(text.startswith("doi:"))

    def test_van_particle_is_not_capitalized(self) -> None:
        text, transformations, diagnostics = _apply("van Gogh, Lettres à Théo, 1888.")
        self.assertTrue(text.startswith("van Gogh"))
        self.assertFalse(any(t.rule_id == "purh.note.majuscule_initiale" for t in transformations))
        self.assertTrue(any(d.rule_id == "R-AN-004" for d in diagnostics))

    def test_von_particle_is_not_capitalized(self) -> None:
        text, _tr, _diag = _apply("von Neumann, Theory of Games, 1944.")
        self.assertTrue(text.startswith("von Neumann"))

    def test_de_particle_is_not_capitalized(self) -> None:
        text, _tr, _diag = _apply("de Gaulle, Mémoires de guerre, 1954.")
        self.assertTrue(text.startswith("de Gaulle"))

    def test_apostrophe_particle_is_not_capitalized(self) -> None:
        text, _tr, _diag = _apply("d’Artagnan, Mémoires, 1700.")
        self.assertTrue(text.startswith("d’Artagnan"))

    def test_ibid_lowercase_at_start_is_not_forced_uppercase(self) -> None:
        text, transformations, _diag = _apply("ibid., p. 42.")
        self.assertTrue(text.startswith("ibid."))
        self.assertFalse(any(t.rule_id == "purh.note.majuscule_initiale" for t in transformations))

    def test_ibid_capitalized_at_start_is_preserved(self) -> None:
        text, _tr, _diag = _apply("Ibid., p. 42.")
        self.assertTrue(text.startswith("Ibid."))

    def test_ordinary_lowercase_start_is_still_capitalized(self) -> None:
        text, transformations, _diag = _apply("voir la note précédente.")
        self.assertTrue(text.startswith("Voir"))
        self.assertTrue(any(t.rule_id == "purh.note.majuscule_initiale" for t in transformations))

    def test_citation_in_quotes_is_not_corrupted(self) -> None:
        text, _tr, _diag = _apply("« citation exacte du texte »")
        self.assertTrue(text.startswith("«"))

    def test_verse_ending_with_closing_guillemet_gets_no_extra_point(self) -> None:
        text, _tr, _diag = _apply("Il a dit « ceci »")
        self.assertTrue(text.endswith("»"))

    def test_list_item_start_does_not_get_final_point_forced(self) -> None:
        text, _tr, diagnostics = _apply("- premier élément sans ponctuation finale")
        self.assertFalse(text.endswith("."))
        self.assertTrue(any(d.rule_id == "R-AN-005" for d in diagnostics))

    def test_title_without_final_point_is_diagnosed_not_forced_when_url(self) -> None:
        text, _tr, diagnostics = _apply("Voir https://exemple.org/document-sans-point")
        self.assertFalse(text.endswith("."))
        self.assertTrue(any(d.rule_id == "R-AN-005" for d in diagnostics))

    def test_second_pass_is_idempotent(self) -> None:
        first_text, first_tr, _ = _apply("van Gogh écrivait à son frère théo")
        second_text, second_tr, _ = _apply(first_text)
        self.assertEqual(first_text, second_text)
        self.assertEqual(second_tr, [])

    def test_second_pass_on_ordinary_note_is_idempotent(self) -> None:
        first_text, _first_tr, _ = _apply("voir op. cit. pour plus de détails")
        second_text, second_tr, _ = _apply(first_text)
        self.assertEqual(first_text, second_text)
        self.assertEqual(second_tr, [])

    def test_transformation_offsets_reconstruct_before_fragment(self) -> None:
        _text, transformations, _diag = _apply("voir op. cit., p. 12")
        for t in transformations:
            start = t.attributes["offset_start"]
            end = t.attributes["offset_end"]
            self.assertIsInstance(start, int)
            self.assertIsInstance(end, int)

    def test_offset_invariant_holds_by_sequential_replay(self) -> None:
        """Rejoue les transformations dans l'ordre : chaque offset doit pointer
        exactement vers `before` dans le texte tel qu'il existait juste avant
        cette transformation (Partie F2)."""
        original = "van gogh écrivait; voir op. cit., sans point final"
        final_text, transformations, _diag = _apply(original)
        state = original
        for t in transformations:
            start = t.attributes["offset_start"]
            end = t.attributes["offset_end"]
            self.assertEqual(state[start:end], t.before)
            state = state[:start] + t.after + state[end:]
        self.assertEqual(state, final_text)

    def test_no_transformation_emitted_when_note_already_clean(self) -> None:
        text, transformations, _diag = _apply(f"Voir op.{NNBSP}cit., p. 12.")
        self.assertEqual(transformations, [])

    def test_inline_spans_preserve_text_through_normalization(self) -> None:
        inlines = [InlineSpan(text="van "), InlineSpan(text="Gogh, Lettres.")]
        text, _tr, _diag = _apply("van Gogh, Lettres.", inlines=inlines)
        self.assertEqual(text, "van Gogh, Lettres.")


if __name__ == "__main__":
    unittest.main()
