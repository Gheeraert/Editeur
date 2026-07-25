from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, InlineSpan, Paragraph
from purh_editorial.services.orthotypo_service import NNBSP, OrthotypoService


class OrthotypoNumeroStylingTests(unittest.TestCase):
    """
    purh.numero produit désormais la forme demandée par le guide PURH
    (CONSIGNES_AUTEURS_PURH_2025.pdf, p. 12) : "n"/"N" + "o" en exposant + espace fine
    insécable + chiffre, au lieu du symbole degré "n°". Voir
    docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md.
    """

    def _apply(self, paragraph: Paragraph) -> tuple[Paragraph, list]:
        document = Document(
            document_id="doc-numero",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[paragraph],
        )
        service = OrthotypoService()
        corrected, transformations = service.apply(document)
        return corrected.blocks[0], transformations

    def test_degree_sign_form_is_normalized_and_o_is_superscript(self) -> None:
        paragraph = Paragraph(block_id="p1", text="n° 5", inlines=[InlineSpan(text="n° 5")])
        block, _tr = self._apply(paragraph)
        self.assertEqual(block.text, f"no{NNBSP}5")
        self.assertEqual("".join(s.text for s in block.inlines), f"no{NNBSP}5")
        superscript_text = "".join(s.text for s in block.inlines if s.style.superscript)
        self.assertEqual(superscript_text, "o")

    def test_no_space_form_is_normalized(self) -> None:
        paragraph = Paragraph(block_id="p1", text="n°5", inlines=[InlineSpan(text="n°5")])
        block, _tr = self._apply(paragraph)
        self.assertEqual(block.text, f"no{NNBSP}5")

    def test_letter_o_form_gets_styled(self) -> None:
        paragraph = Paragraph(block_id="p1", text="no 5", inlines=[InlineSpan(text="no 5")])
        block, _tr = self._apply(paragraph)
        self.assertEqual(block.text, f"no{NNBSP}5")
        self.assertTrue(block.inlines[1].style.superscript)

    def test_uppercase_form_preserves_capital_n(self) -> None:
        paragraph = Paragraph(block_id="p1", text="No 12", inlines=[InlineSpan(text="No 12")])
        block, _tr = self._apply(paragraph)
        self.assertEqual(block.text, f"No{NNBSP}12")
        self.assertEqual(block.inlines[0].text, "N")

    def test_masculine_ordinal_indicator_form_is_normalized(self) -> None:
        paragraph = Paragraph(block_id="p1", text="nº 7", inlines=[InlineSpan(text="nº 7")])
        block, _tr = self._apply(paragraph)
        self.assertEqual(block.text, f"no{NNBSP}7")

    def test_word_without_following_digit_is_unchanged(self) -> None:
        paragraph = Paragraph(
            block_id="p1", text="le numéro de la revue", inlines=[InlineSpan(text="le numéro de la revue")]
        )
        block, transformations = self._apply(paragraph)
        self.assertEqual(block.text, "le numéro de la revue")
        self.assertEqual(transformations, [])

    def test_reprocessing_already_styled_numero_is_idempotent(self) -> None:
        paragraph = Paragraph(block_id="p1", text="n° 5", inlines=[InlineSpan(text="n° 5")])
        block, transformations = self._apply(paragraph)
        self.assertTrue(any(t.rule_id == "R-NO-001" for t in transformations))

        block2, transformations2 = self._apply(block)
        self.assertEqual(transformations2, [])
        self.assertEqual(block2.text, block.text)

    def test_r_no_001_is_marked_style_only_not_a_text_change(self) -> None:
        paragraph = Paragraph(block_id="p1", text="n° 5", inlines=[InlineSpan(text="n° 5")])
        _block, transformations = self._apply(paragraph)
        no_001 = next(t for t in transformations if t.rule_id == "R-NO-001")
        self.assertEqual(no_001.before, no_001.after)
        self.assertTrue(no_001.attributes.get("style_only"))


if __name__ == "__main__":
    unittest.main()
