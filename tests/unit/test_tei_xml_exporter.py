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
from purh_editorial.model import Document, Heading, InlineSpan, InlineStyle, Note, Paragraph, QuoteBlock


def _q(local_name: str) -> str:
    return f"{{{TEI_NS}}}{local_name}"


class TeiXmlExporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.exporter = TeiXmlExporter()

    def test_export_simple_paragraph(self) -> None:
        document = Document(
            document_id="doc1",
            source_path="source.docx",
            source_format="docx",
            blocks=[Paragraph(block_id="p1", text="Texte simple.")],
        )

        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        body = root.find(f"./{_q('text')}/{_q('body')}")
        self.assertIsNotNone(body)
        p = body.find(_q("p"))
        self.assertIsNotNone(p)
        self.assertEqual(p.text, "Texte simple.")

    def test_export_heading_as_head(self) -> None:
        document = Document(
            document_id="doc2",
            source_path="source.docx",
            source_format="docx",
            blocks=[Heading(block_id="h1", text="Titre section")],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        body = root.find(f"./{_q('text')}/{_q('body')}")
        head = body.find(_q("head"))
        self.assertIsNotNone(head)
        self.assertEqual(head.text, "Titre section")

    def test_export_quote_block(self) -> None:
        document = Document(
            document_id="doc3",
            source_path="source.docx",
            source_format="docx",
            blocks=[QuoteBlock(block_id="q1", text="Citation longue.")],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        body = root.find(f"./{_q('text')}/{_q('body')}")
        quote = body.find(_q("quote"))
        self.assertIsNotNone(quote)
        p = quote.find(_q("p"))
        self.assertIsNotNone(p)
        self.assertEqual(p.text, "Citation longue.")

    def test_export_inline_styles(self) -> None:
        document = Document(
            document_id="doc4",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Paragraph(
                    block_id="p1",
                    text="",
                    inlines=[
                        InlineSpan(text="A"),
                        InlineSpan(text="B", style=InlineStyle(italic=True)),
                        InlineSpan(text="C", style=InlineStyle(small_caps=True)),
                        InlineSpan(text="D", style=InlineStyle(superscript=True)),
                    ],
                )
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        body = root.find(f"./{_q('text')}/{_q('body')}")
        p = body.find(_q("p"))
        his = p.findall(_q("hi"))
        self.assertEqual([h.attrib.get("rend") for h in his], ["italic", "small-caps", "sup"])
        self.assertEqual(p.text, "A")
        self.assertEqual(his[0].text, "B")
        self.assertEqual(his[1].text, "C")
        self.assertEqual(his[2].text, "D")

    def test_export_note_inline_with_italic_content(self) -> None:
        document = Document(
            document_id="doc5",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Paragraph(
                    block_id="p1",
                    text="",
                    inlines=[
                        InlineSpan(text="Texte "),
                        InlineSpan(text="[1]", kind="note_call", note_ref="ftn1"),
                        InlineSpan(text=" suite"),
                    ],
                )
            ],
            notes=[
                Note(
                    note_id="ftn1",
                    text="",
                    inlines=[
                        InlineSpan(text="note "),
                        InlineSpan(text="italique", style=InlineStyle(italic=True)),
                    ],
                )
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        body = root.find(f"./{_q('text')}/{_q('body')}")
        p = body.find(_q("p"))
        note = p.find(_q("note"))
        self.assertIsNotNone(note)
        self.assertEqual(note.attrib.get("place"), "foot")
        hi = note.find(_q("hi"))
        self.assertIsNotNone(hi)
        self.assertEqual(hi.attrib.get("rend"), "italic")
        self.assertEqual(hi.text, "italique")

    def test_export_produces_well_formed_xml(self) -> None:
        document = Document(
            document_id="doc6",
            source_path="source.docx",
            source_format="docx",
            blocks=[Paragraph(block_id="p1", text="Texte")],
        )
        xml_text = self.exporter.export_document(document)
        parsed = ET.fromstring(xml_text)
        self.assertEqual(parsed.tag, _q("TEI"))


if __name__ == "__main__":
    unittest.main()

