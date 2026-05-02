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

XML_NS = "http://www.w3.org/XML/1998/namespace"


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
        div = body.find(_q("div"))
        self.assertIsNotNone(div)
        self.assertEqual(div.attrib.get("type"), "section1")
        head = div.find(_q("head"))
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
        cit = body.find(_q("cit"))
        self.assertIsNotNone(cit)
        quote = cit.find(_q("quote"))
        self.assertIsNotNone(quote)
        self.assertEqual(quote.text, "Citation longue.")

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
                    label="1",
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
        self.assertEqual(note.attrib.get("n"), "1")
        self.assertEqual(note.attrib.get(f"{{{XML_NS}}}id"), "ftn1")
        hi = note.find(_q("hi"))
        self.assertIsNotNone(hi)
        self.assertEqual(hi.attrib.get("rend"), "italic")
        self.assertEqual(hi.text, "italique")

    def test_note_consecutive_plain_runs_preserve_order(self) -> None:
        """Régression: runs bruts consécutifs après une italique ne doivent pas
        remonter dans note.text (avant les enfants <hi>) mais rester dans hi.tail."""
        document = Document(
            document_id="doc_reg",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Paragraph(
                    block_id="p1",
                    text="",
                    inlines=[InlineSpan(text="[1]", kind="note_call", note_ref="ftn1")],
                )
            ],
            notes=[
                Note(
                    note_id="ftn1",
                    label="1",
                    text="",
                    inlines=[
                        InlineSpan(text="Le Mercure galant", style=InlineStyle(italic=True)),
                        InlineSpan(text=", janvier-mars 1677, Paris, Barbin, 1677, p."),
                        InlineSpan(text=" 47 ; voir aussi Corneille, "),
                        InlineSpan(text="Œuvres complètes", style=InlineStyle(italic=True)),
                        InlineSpan(text=", éd. Georges Couton, Paris, Gallimard, t."),
                        InlineSpan(text=" III, 1987, p. 1313."),
                    ],
                )
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        body = root.find(f"./{_q('text')}/{_q('body')}")
        note = body.find(f".//{_q('note')}")
        self.assertIsNotNone(note)
        # note.text doit être vide/None: le premier contenu est un <hi>
        self.assertFalse(note.text and note.text.strip(), f"note.text ne doit pas contenir de texte: {note.text!r}")
        his = note.findall(_q("hi"))
        self.assertEqual(len(his), 2)
        self.assertEqual(his[0].text, "Le Mercure galant")
        self.assertIn("47", his[0].tail or "")
        self.assertEqual(his[1].text, "Œuvres complètes")
        self.assertIn("1313", his[1].tail or "")

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

    def test_export_combined_italic_small_caps_in_single_hi(self) -> None:
        document = Document(
            document_id="doc7",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Paragraph(
                    block_id="p1",
                    text="",
                    inlines=[
                        InlineSpan(
                            text="texte",
                            style=InlineStyle(italic=True, small_caps=True),
                        )
                    ],
                )
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        hi = root.find(f"./{_q('text')}/{_q('body')}/{_q('p')}/{_q('hi')}")
        self.assertIsNotNone(hi)
        self.assertEqual(hi.attrib.get("rend"), "italic small-caps")
        self.assertEqual(hi.text, "texte")

    def test_export_combined_bold_superscript_in_single_hi(self) -> None:
        document = Document(
            document_id="doc8",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Paragraph(
                    block_id="p1",
                    text="",
                    inlines=[
                        InlineSpan(
                            text="x",
                            style=InlineStyle(bold=True, superscript=True),
                        )
                    ],
                )
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        hi = root.find(f"./{_q('text')}/{_q('body')}/{_q('p')}/{_q('hi')}")
        self.assertIsNotNone(hi)
        self.assertEqual(hi.attrib.get("rend"), "bold sup")
        self.assertEqual(hi.text, "x")

    def test_heading_level_1_opens_section1_div(self) -> None:
        document = Document(
            document_id="doc9",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Heading(block_id="h1", text="Titre 1"),
                Paragraph(block_id="p1", text="Paragraphe."),
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        body = root.find(f"./{_q('text')}/{_q('body')}")
        div = body.find(_q("div"))
        self.assertIsNotNone(div)
        self.assertEqual(div.attrib.get("type"), "section1")
        self.assertEqual(div.find(_q("head")).text, "Titre 1")
        self.assertEqual(div.find(_q("p")).text, "Paragraphe.")

    def test_heading_level_1_then_2_nests_section2(self) -> None:
        document = Document(
            document_id="doc10",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Heading(block_id="h1", text="Titre 1", attributes={"heading_level": 1}),
                Paragraph(block_id="p1", text="Texte 1"),
                Heading(block_id="h2", text="Titre 2", attributes={"heading_level": 2}),
                Paragraph(block_id="p2", text="Texte 2"),
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        body = root.find(f"./{_q('text')}/{_q('body')}")
        div1 = body.find(_q("div"))
        self.assertIsNotNone(div1)
        div2 = div1.find(_q("div"))
        self.assertIsNotNone(div2)
        self.assertEqual(div1.attrib.get("type"), "section1")
        self.assertEqual(div2.attrib.get("type"), "section2")
        self.assertEqual(div2.find(_q("head")).text, "Titre 2")

    def test_two_headings_same_level_create_two_sibling_divs(self) -> None:
        document = Document(
            document_id="doc11",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Heading(block_id="h1", text="Titre A", attributes={"heading_level": 1}),
                Paragraph(block_id="p1", text="Texte A"),
                Heading(block_id="h2", text="Titre B", attributes={"heading_level": 1}),
                Paragraph(block_id="p2", text="Texte B"),
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        body = root.find(f"./{_q('text')}/{_q('body')}")
        divs = body.findall(_q("div"))
        self.assertEqual(len(divs), 2)
        self.assertEqual(divs[0].find(_q("head")).text, "Titre A")
        self.assertEqual(divs[1].find(_q("head")).text, "Titre B")

    def test_paragraph_before_first_heading_stays_directly_under_body(self) -> None:
        document = Document(
            document_id="doc12",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Paragraph(block_id="p0", text="Avant titre"),
                Heading(block_id="h1", text="Titre"),
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        body = root.find(f"./{_q('text')}/{_q('body')}")
        children = list(body)
        self.assertGreaterEqual(len(children), 2)
        self.assertEqual(children[0].tag, _q("p"))
        self.assertEqual(children[0].text, "Avant titre")
        self.assertEqual(children[1].tag, _q("div"))


if __name__ == "__main__":
    unittest.main()
