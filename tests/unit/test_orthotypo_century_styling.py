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

    def test_vie_is_not_converted_to_roman_numeral(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="La vie est belle.",
            inlines=[InlineSpan(text="La vie est belle.")],
        )
        block, transformations = self._apply(paragraph)
        self.assertEqual(block.text, "La vie est belle.")
        self.assertEqual([s.text for s in block.inlines], ["La vie est belle."])

    # ── Priorité 2b : ordinaux romains non-siècle ─────────────────────────────

    def test_iie_republique_est_style(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="la IIe République",
            inlines=[InlineSpan(text="la IIe République")],
        )
        block, _ = self._apply(paragraph)
        small_caps = [s for s in block.inlines if s.style.small_caps]
        superscripts = [s for s in block.inlines if s.style.superscript]
        self.assertEqual([s.text for s in small_caps], ["ii"])
        self.assertEqual([s.text for s in superscripts], ["e"])

    def test_iiie_reich_est_style(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="le IIIe Reich",
            inlines=[InlineSpan(text="le IIIe Reich")],
        )
        block, _ = self._apply(paragraph)
        small_caps = [s for s in block.inlines if s.style.small_caps]
        superscripts = [s for s in block.inlines if s.style.superscript]
        self.assertEqual([s.text for s in small_caps], ["iii"])
        self.assertEqual([s.text for s in superscripts], ["e"])

    def test_ie_empire_est_style(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="le Ie Empire",
            inlines=[InlineSpan(text="le Ie Empire")],
        )
        block, _ = self._apply(paragraph)
        small_caps = [s for s in block.inlines if s.style.small_caps]
        superscripts = [s for s in block.inlines if s.style.superscript]
        self.assertEqual([s.text for s in small_caps], ["i"])
        self.assertEqual([s.text for s in superscripts], ["e"])

    def test_ordinal_romain_sans_contexte_non_style(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="version XIXe",
            inlines=[InlineSpan(text="version XIXe")],
        )
        block, transformations = self._apply(paragraph)
        self.assertFalse(any(s.style.small_caps or s.style.superscript for s in block.inlines))

    # ── Priorité 2c : primo / secundo / tertio (exposant o) ──────────────────

    def test_primo_secundo_tertio_o_en_exposant(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="1o voici, 2o ensuite, 3o enfin.",
            inlines=[InlineSpan(text="1o voici, 2o ensuite, 3o enfin.")],
        )
        block, _ = self._apply(paragraph)
        superscripts = [s for s in block.inlines if s.style.superscript]
        self.assertEqual([s.text for s in superscripts], ["o", "o", "o"])

    def test_primo_chiffre_reste_normal(self) -> None:
        paragraph = Paragraph(
            block_id="p1",
            text="1o voici.",
            inlines=[InlineSpan(text="1o voici.")],
        )
        block, _ = self._apply(paragraph)
        # le chiffre "1" ne doit pas être en petites capitales
        regular = [s for s in block.inlines if not s.style.small_caps and not s.style.superscript]
        self.assertTrue(any("1" in s.text for s in regular))


if __name__ == "__main__":
    unittest.main()
