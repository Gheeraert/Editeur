from __future__ import annotations

import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.io.tei_xml_exporter import TEI_NS, TeiXmlExporter
from purh_editorial.model import Document, InlineSpan, InlineStyle, Paragraph
from purh_editorial.services.orthotypo_service import OrthotypoService


def _q(local_name: str) -> str:
    return f"{{{TEI_NS}}}{local_name}"


class OrthotypoCenturyStylingTests(unittest.TestCase):
    def _apply(self, paragraph: Paragraph) -> tuple[Paragraph, list]:
        document = Document(
            document_id="doc-century",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[paragraph],
        )
        service = OrthotypoService()
        corrected, transformations = service.apply(document)
        return corrected.blocks[0], transformations

    def test_xixe_siecle_is_split_and_styled(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="XIXe siècle",
            inlines=[InlineSpan(text="XIXe siècle")],
        )
        block, _ = self._apply(paragraph)
        self.assertEqual([s.text for s in block.inlines], ["xix", "e", " siècle"])
        self.assertTrue(block.inlines[0].style.small_caps)
        self.assertTrue(block.inlines[1].style.superscript)
        self.assertFalse(block.inlines[2].style.small_caps)
        self.assertFalse(block.inlines[2].style.superscript)

    def test_xviiieme_siecle_is_split_and_styled(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="XVIIIème siècle",
            inlines=[InlineSpan(text="XVIIIème siècle")],
        )
        block, _ = self._apply(paragraph)
        self.assertEqual([s.text for s in block.inlines], ["xviii", "e", " siècle"])
        self.assertTrue(block.inlines[0].style.small_caps)
        self.assertTrue(block.inlines[1].style.superscript)

    def test_lowercase_xixe_siecle_is_split_and_styled(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="xixe siècle",
            inlines=[InlineSpan(text="xixe siècle")],
        )
        block, _ = self._apply(paragraph)
        self.assertEqual([s.text for s in block.inlines], ["xix", "e", " siècle"])
        self.assertTrue(block.inlines[0].style.small_caps)
        self.assertTrue(block.inlines[1].style.superscript)

    def test_existing_italic_style_is_preserved_on_century_parts(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="XVIIe siècle",
            inlines=[InlineSpan(text="XVIIe siècle", style=InlineStyle(italic=True))],
        )
        block, _ = self._apply(paragraph)
        self.assertEqual([s.text for s in block.inlines], ["xvii", "e", " siècle"])
        self.assertTrue(block.inlines[0].style.italic)
        self.assertTrue(block.inlines[0].style.small_caps)
        self.assertTrue(block.inlines[1].style.italic)
        self.assertTrue(block.inlines[1].style.superscript)

    def test_two_centuries_are_both_styled(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="XIXe siècle et XXIe siècle",
            inlines=[InlineSpan(text="XIXe siècle et XXIe siècle")],
        )
        block, _ = self._apply(paragraph)
        small_caps = [s for s in block.inlines if s.style.small_caps]
        superscripts = [s for s in block.inlines if s.style.superscript]
        self.assertEqual([s.text for s in small_caps], ["xix", "xxi"])
        self.assertEqual([s.text for s in superscripts], ["e", "e"])

    def test_three_centuries_enumeration_with_et_are_all_styled(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="XVIe, XVIIe et XVIIIe siècles",
            inlines=[InlineSpan(text="XVIe, XVIIe et XVIIIe siècles")],
        )
        block, _ = self._apply(paragraph)
        small_caps = [s.text for s in block.inlines if s.style.small_caps]
        self.assertEqual(small_caps, ["xvi", "xvii", "xviii"])

    def test_du_au_enumeration_is_styled(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="du XVIe au XVIIIe siècle",
            inlines=[InlineSpan(text="du XVIe au XVIIIe siècle")],
        )
        block, _ = self._apply(paragraph)
        small_caps = [s.text for s in block.inlines if s.style.small_caps]
        self.assertEqual(small_caps, ["xvi", "xviii"])

    def test_aux_et_enumeration_is_styled(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="aux XVIIe et XVIIIe siècles",
            inlines=[InlineSpan(text="aux XVIIe et XVIIIe siècles")],
        )
        block, _ = self._apply(paragraph)
        small_caps = [s.text for s in block.inlines if s.style.small_caps]
        self.assertEqual(small_caps, ["xvii", "xviii"])

    def test_hyphenated_range_enumeration_is_styled(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="XVIe-XVIIIe siècles",
            inlines=[InlineSpan(text="XVIe-XVIIIe siècles")],
        )
        block, _ = self._apply(paragraph)
        small_caps = [s.text for s in block.inlines if s.style.small_caps]
        self.assertEqual(small_caps, ["xvi", "xviii"])

    def test_arrondissement_without_siecle_context_is_untouched(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="Il habite dans le XVIe arrondissement de Paris.",
            inlines=[InlineSpan(text="Il habite dans le XVIe arrondissement de Paris.")],
        )
        block, _ = self._apply(paragraph)
        self.assertFalse(any(s.style.small_caps for s in block.inlines))

    def test_flat_block_can_create_styled_inlines_for_century(self) -> None:
        paragraph = Paragraph(block_id="p1", text="XIXe siècle")
        block, _ = self._apply(paragraph)
        self.assertEqual([s.text for s in block.inlines], ["xix", "e", " siècle"])
        self.assertTrue(block.inlines[0].style.small_caps)
        self.assertTrue(block.inlines[1].style.superscript)

    def test_tei_export_contains_small_caps_and_sup_after_orthotypo(self) -> None:
        paragraph = Paragraph(block_id="p1", text="XIXe siècle")
        block, _ = self._apply(paragraph)
        document = Document(
            document_id="doc-tei-century",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[block],
        )
        xml_text = TeiXmlExporter().export_document(document)
        root = ET.fromstring(xml_text)
        his = root.findall(f".//{_q('hi')}")
        rend_values = [hi.attrib.get("rend") for hi in his]
        self.assertIn("small-caps", rend_values)
        self.assertIn("sup", rend_values)
        self.assertIn("xix", [hi.text for hi in his if hi.attrib.get("rend") == "small-caps"])
        self.assertIn("e", [hi.text for hi in his if hi.attrib.get("rend") == "sup"])

    def test_version_xixe_without_century_context_is_unchanged(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="version XIXe",
            inlines=[InlineSpan(text="version XIXe")],
        )
        block, _ = self._apply(paragraph)
        self.assertEqual(block.text, "version XIXe")
        self.assertEqual([s.text for s in block.inlines], ["version XIXe"])
        self.assertFalse(any(s.style.small_caps or s.style.superscript for s in block.inlines))

    def test_out_of_whitelist_roman_is_unchanged(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="XLIVe siècle",
            inlines=[InlineSpan(text="XLIVe siècle")],
        )
        block, _ = self._apply(paragraph)
        self.assertEqual(block.text, "XLIVe siècle")
        self.assertEqual([s.text for s in block.inlines], ["XLIVe siècle"])

    def test_text_without_century_is_unchanged(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="Texte sans siecle.",
            inlines=[InlineSpan(text="Texte sans siecle.")],
        )
        block, transformations = self._apply(paragraph)
        self.assertEqual(block.text, "Texte sans siecle.")
        self.assertEqual([s.text for s in block.inlines], ["Texte sans siecle."])
        self.assertEqual(transformations, [])

    def test_regnal_ordinal_ier_is_not_corrupted_to_ie(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="l’empereur Maximilien Ier (1459-1519) et François Ier",
            inlines=[InlineSpan(text="l’empereur Maximilien Ier (1459-1519) et François Ier")],
        )
        block, _ = self._apply(paragraph)
        self.assertEqual(
            block.text,
            "l’empereur Maximilien Ier (1459-1519) et François Ier",
        )

    def test_common_word_vie_is_not_treated_as_century(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="prolonger la vie de l’homme",
            inlines=[InlineSpan(text="prolonger la vie de l’homme")],
        )
        block, _ = self._apply(paragraph)
        self.assertEqual(block.text, "prolonger la vie de l’homme")

    def test_ier_siecle_is_not_corrupted_to_ie_siecle(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="au Ier siècle",
            inlines=[InlineSpan(text="au Ier siècle")],
        )
        block, _ = self._apply(paragraph)
        self.assertEqual(block.text, "au Ier siècle")

    def test_reprocessing_already_styled_enumeration_is_a_no_op(self) -> None:
        # "xviie" n'est pas immediatement suivi de "siecle" (seul "xixe" l'est) : sur
        # une reprise, purh.siecles remet "xixe" en majuscules puis le stylage le
        # reconvertit en minuscules stylees, un aller-retour qui ne change rien au
        # texte final. Avant correction, ce cas produisait une fausse transformation
        # "century_styling" (before == after) a chaque nouveau passage du pipeline sur
        # un document deja traite (voir docs/PHASE1_FIABILITE_PIPELINE.md, defaut 2).
        paragraph = Paragraph(
            block_id="p1",
            text="du xviie au xixe siècles",
            inlines=[InlineSpan(text="du xviie au xixe siècles")],
        )
        block, transformations = self._apply(paragraph)
        self.assertTrue(any(t.attributes.get("century_styling") for t in transformations))

        block2, transformations2 = self._apply(block)
        self.assertEqual(transformations2, [])
        self.assertEqual(block2.text, block.text)


if __name__ == "__main__":
    unittest.main()
