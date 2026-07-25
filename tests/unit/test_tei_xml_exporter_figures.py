from __future__ import annotations

import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.io.tei_xml_exporter import TEI_NS, TeiXmlExporter, media_filename_for_asset
from purh_editorial.model import Document, ImageAsset, ImageOccurrence, Paragraph


def _q(local: str) -> str:
    return f"{{{TEI_NS}}}{local}"


class TeiXmlExporterFiguresTests(unittest.TestCase):
    def _document_with_image(self, *, alt_text="", title="", caption=None) -> Document:
        block = Paragraph(block_id="b1", text="Texte avec figure.")
        asset = ImageAsset(
            asset_id="img-1", filename="image1.png", content_type="image/png",
            data=b"\x89PNG", sha256="abc",
        )
        occ = ImageOccurrence(
            occurrence_id="imgocc-1", asset_ref="img-1", placement="inline",
            target_ref="b1", order=1, alt_text=alt_text, title=title, caption=caption,
        )
        return Document(
            document_id="doc-1", source_path="p", source_format="docx",
            blocks=[block], image_assets={"img-1": asset}, image_occurrences=[occ],
        )

    def test_figure_element_is_emitted_with_graphic_url(self) -> None:
        document = self._document_with_image(alt_text="Une description", title="Un titre")
        xml_str = TeiXmlExporter().export_document(document)
        root = ET.fromstring(xml_str)
        figures = root.findall(f".//{_q('figure')}")
        self.assertEqual(len(figures), 1)
        graphic = figures[0].find(_q("graphic"))
        self.assertIsNotNone(graphic)
        self.assertEqual(graphic.get("url"), f"media/{media_filename_for_asset(document.image_assets['img-1'])}")

    def test_fig_desc_uses_alt_text(self) -> None:
        document = self._document_with_image(alt_text="Texte alternatif")
        xml_str = TeiXmlExporter().export_document(document)
        root = ET.fromstring(xml_str)
        fig_desc = root.find(f".//{_q('figDesc')}")
        self.assertIsNotNone(fig_desc)
        self.assertEqual(fig_desc.text, "Texte alternatif")

    def test_head_uses_caption_over_title(self) -> None:
        document = self._document_with_image(title="Titre", caption="Légende réelle")
        xml_str = TeiXmlExporter().export_document(document)
        root = ET.fromstring(xml_str)
        head = root.find(f".//{_q('figure')}/{_q('head')}")
        self.assertIsNotNone(head)
        self.assertEqual(head.text, "Légende réelle")

    def test_external_link_image_is_not_emitted_as_figure(self) -> None:
        block = Paragraph(block_id="b1", text="Texte.")
        occ = ImageOccurrence(
            occurrence_id="imgocc-1", asset_ref="", placement="inline",
            target_ref="b1", order=1, external_link="https://example.org/x.png",
        )
        document = Document(
            document_id="doc-1", source_path="p", source_format="docx",
            blocks=[block], image_occurrences=[occ],
        )
        xml_str = TeiXmlExporter().export_document(document)
        root = ET.fromstring(xml_str)
        self.assertEqual(root.findall(f".//{_q('figure')}"), [])

    def test_note_placement_image_is_not_emitted_as_body_figure(self) -> None:
        block = Paragraph(block_id="b1", text="Texte.")
        asset = ImageAsset(
            asset_id="img-1", filename="image1.png", content_type="image/png",
            data=b"\x89PNG", sha256="abc",
        )
        occ = ImageOccurrence(
            occurrence_id="imgocc-1", asset_ref="img-1", placement="note",
            target_ref="ftn1", order=1,
        )
        document = Document(
            document_id="doc-1", source_path="p", source_format="docx",
            blocks=[block], image_assets={"img-1": asset}, image_occurrences=[occ],
        )
        xml_str = TeiXmlExporter().export_document(document)
        root = ET.fromstring(xml_str)
        self.assertEqual(root.findall(f".//{_q('figure')}"), [])


if __name__ == "__main__":
    unittest.main()
