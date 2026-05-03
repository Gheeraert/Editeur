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
from purh_editorial.model import Block, Document, Heading, InlineSpan, InlineStyle, LineatedBlock, Note, Paragraph, QuoteBlock

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

    def test_export_poetry_group_as_lg_l(self) -> None:
        document = Document(
            document_id="doc-poetry-group",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                LineatedBlock(
                    block_id="p1",
                    text="Vers 1",
                    attributes={
                        "semantic": {
                            "role": "lineated_block",
                            "layout_kind": "lineated_block",
                            "lineation": "lineated",
                            "lines": ["Vers 1"],
                            "poetry_group_id": "poetry_group_001",
                            "poetry_line_index": 1,
                        },
                    },
                ),
                LineatedBlock(
                    block_id="p2",
                    text="Vers 2",
                    attributes={
                        "semantic": {
                            "role": "lineated_block",
                            "layout_kind": "lineated_block",
                            "lineation": "lineated",
                            "lines": ["Vers 2"],
                            "poetry_group_id": "poetry_group_001",
                            "poetry_line_index": 2,
                        },
                    },
                ),
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        body = root.find(f"./{_q('text')}/{_q('body')}")
        lg = body.find(f"./{_q('lg')}")
        self.assertIsNotNone(lg)
        self.assertIsNone(body.find(_q("cit")))
        lines = lg.findall(_q("l"))
        self.assertEqual([line.text for line in lines], ["Vers 1", "Vers 2"])

    def test_lineated_quote_still_renders_inside_cit_quote(self) -> None:
        document = Document(
            document_id="doc-lineated-quote",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                QuoteBlock(
                    block_id="q1",
                    text="Vers 1\nVers 2",
                    attributes={
                        "semantic": {
                            "role": "quote",
                            "layout_kind": "lineated_block",
                            "lineation": "lineated",
                            "lines": ["Vers 1", "Vers 2"],
                        }
                    },
                )
            ],
        )

        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        lg = root.find(f".//{_q('cit')}/{_q('quote')}/{_q('lg')}")
        self.assertIsNotNone(lg)
        lines = lg.findall(_q("l"))
        self.assertEqual([line.text for line in lines], ["Vers 1", "Vers 2"])

    def test_poetry_l_preserves_italic_inline(self) -> None:
        document = Document(
            document_id="doc-poetry-italic",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                LineatedBlock(
                    block_id="q1",
                    text="",
                    inlines=[
                        InlineSpan(text="Je vois "),
                        InlineSpan(text="Phedre", style=InlineStyle(italic=True)),
                        InlineSpan(text="", kind="line_break"),
                        InlineSpan(text="Deuxieme vers"),
                    ],
                    attributes={
                        "semantic": {
                            "role": "lineated_block",
                            "layout_kind": "lineated_block",
                            "lineation": "lineated",
                            "lines": ["Je vois Phedre", "Deuxieme vers"],
                        }
                    },
                )
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        lines = root.findall(f".//{_q('lg')}/{_q('l')}")
        self.assertEqual(len(lines), 2)
        hi = lines[0].find(_q("hi"))
        self.assertIsNotNone(hi)
        self.assertEqual(hi.attrib.get("rend"), "italic")
        self.assertEqual(hi.text, "Phedre")
        self.assertEqual(lines[1].text, "Deuxieme vers")

    def test_poetry_l_preserves_multiple_inline_styles(self) -> None:
        document = Document(
            document_id="doc-poetry-styles",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                LineatedBlock(
                    block_id="q1",
                    text="",
                    inlines=[
                        InlineSpan(text="gras", style=InlineStyle(bold=True)),
                        InlineSpan(text="", kind="line_break"),
                        InlineSpan(text="petites", style=InlineStyle(small_caps=True)),
                        InlineSpan(text="", kind="line_break"),
                        InlineSpan(text="x", style=InlineStyle(superscript=True)),
                        InlineSpan(text="", kind="line_break"),
                        InlineSpan(text="y", style=InlineStyle(subscript=True)),
                    ],
                    attributes={
                        "semantic": {
                            "role": "lineated_block",
                            "layout_kind": "lineated_block",
                            "lineation": "lineated",
                            "lines": ["gras", "petites", "x", "y"],
                        }
                    },
                )
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        lines = root.findall(f".//{_q('lg')}/{_q('l')}")
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0].find(_q("hi")).attrib.get("rend"), "bold")
        self.assertEqual(lines[1].find(_q("hi")).attrib.get("rend"), "small-caps")
        self.assertEqual(lines[2].find(_q("hi")).attrib.get("rend"), "sup")
        self.assertEqual(lines[3].find(_q("hi")).attrib.get("rend"), "sub")

    def test_poetry_l_preserves_note_call(self) -> None:
        document = Document(
            document_id="doc-poetry-note",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                LineatedBlock(
                    block_id="q1",
                    text="",
                    inlines=[
                        InlineSpan(text="Vers avec note"),
                        InlineSpan(text="[1]", kind="note_call", note_ref="n1"),
                    ],
                    attributes={
                        "semantic": {
                            "role": "lineated_block",
                            "layout_kind": "lineated_block",
                            "lineation": "lineated",
                            "lines": ["Vers avec note"],
                        }
                    },
                )
            ],
            notes=[Note(note_id="n1", label="1", text="Texte de note")],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        line = root.find(f".//{_q('lg')}/{_q('l')}")
        self.assertIsNotNone(line)
        note = line.find(_q("note"))
        self.assertIsNotNone(note)
        self.assertEqual(note.attrib.get("place"), "foot")
        self.assertEqual(note.attrib.get(f"{{{XML_NS}}}id"), "n1")

    def test_poetry_l_splits_on_inline_line_breaks(self) -> None:
        document = Document(
            document_id="doc-poetry-breaks",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                LineatedBlock(
                    block_id="q1",
                    text="",
                    inlines=[
                        InlineSpan(text="Ligne 1"),
                        InlineSpan(text="", kind="line_break"),
                        InlineSpan(text="Ligne 2"),
                        InlineSpan(text="", kind="line_break"),
                        InlineSpan(text="Ligne 3"),
                    ],
                    attributes={
                        "semantic": {
                            "role": "lineated_block",
                            "layout_kind": "lineated_block",
                            "lineation": "lineated",
                            "lines": ["Ligne 1", "Ligne 2", "Ligne 3"],
                        }
                    },
                )
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        lines = root.findall(f".//{_q('lg')}/{_q('l')}")
        self.assertEqual(len(lines), 3)

    def test_poetry_plain_text_fallback_still_works(self) -> None:
        document = Document(
            document_id="doc-poetry-fallback",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                LineatedBlock(
                    block_id="q1",
                    text="Vers 1\nVers 2",
                    attributes={
                        "semantic": {
                            "role": "lineated_block",
                            "layout_kind": "lineated_block",
                            "lineation": "lineated",
                            "lines": ["Vers 1", "Vers 2"],
                        }
                    },
                )
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        lines = root.findall(f".//{_q('lg')}/{_q('l')}")
        self.assertEqual([line.text for line in lines], ["Vers 1", "Vers 2"])

    def test_non_poetry_quote_inline_behavior_unchanged(self) -> None:
        document = Document(
            document_id="doc-prose-quote-inline",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                QuoteBlock(
                    block_id="q1",
                    text="",
                    inlines=[
                        InlineSpan(text="Une citation "),
                        InlineSpan(text="italique", style=InlineStyle(italic=True)),
                    ],
                    attributes={
                        "semantic": {
                            "role": "quote",
                            "quote_kind": "prose",
                            "lineation": "prose",
                        }
                    },
                )
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        self.assertEqual(len(root.findall(f".//{_q('lg')}")), 0)
        quote = root.find(f".//{_q('cit')}/{_q('quote')}")
        self.assertIsNotNone(quote)
        hi = quote.find(_q("hi"))
        self.assertIsNotNone(hi)
        self.assertEqual(hi.attrib.get("rend"), "italic")
        self.assertEqual(hi.text, "italique")

    def test_poetry_l_preserves_tail_after_inline_style(self) -> None:
        document = Document(
            document_id="doc-poetry-tail-style",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                LineatedBlock(
                    block_id="q1",
                    text="",
                    inlines=[
                        InlineSpan(text="Je vois "),
                        InlineSpan(text="Phedre", style=InlineStyle(italic=True)),
                        InlineSpan(text=" venir"),
                        InlineSpan(text="", kind="line_break"),
                        InlineSpan(text="Deuxieme vers"),
                    ],
                    attributes={
                        "semantic": {
                            "role": "lineated_block",
                            "layout_kind": "lineated_block",
                            "lineation": "lineated",
                            "lines": ["Je vois Phedre venir", "Deuxieme vers"],
                        }
                    },
                )
            ],
        )

        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        lines = root.findall(f".//{_q('lg')}/{_q('l')}")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].text, "Je vois ")
        hi = lines[0].find(_q("hi"))
        self.assertIsNotNone(hi)
        self.assertEqual(hi.attrib.get("rend"), "italic")
        self.assertEqual(hi.text, "Phedre")
        self.assertEqual(hi.tail, " venir")
        self.assertEqual(lines[1].text, "Deuxieme vers")

    def test_poetry_l_preserves_tail_after_note_call(self) -> None:
        document = Document(
            document_id="doc-poetry-tail-note",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                LineatedBlock(
                    block_id="q1",
                    text="",
                    inlines=[
                        InlineSpan(text="Vers"),
                        InlineSpan(text="[1]", kind="note_call", note_ref="n1"),
                        InlineSpan(text=" suite"),
                    ],
                    attributes={
                        "semantic": {
                            "role": "lineated_block",
                            "layout_kind": "lineated_block",
                            "lineation": "lineated",
                            "lines": ["Vers suite"],
                        }
                    },
                )
            ],
            notes=[Note(note_id="n1", label="1", text="Note")],
        )

        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        line = root.find(f".//{_q('lg')}/{_q('l')}")
        self.assertIsNotNone(line)
        self.assertEqual(line.text, "Vers")
        note = line.find(_q("note"))
        self.assertIsNotNone(note)
        self.assertEqual(note.tail, " suite")

    def test_poetry_l_preserves_style_note_style_sequence_order(self) -> None:
        document = Document(
            document_id="doc-poetry-mixed-order",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                LineatedBlock(
                    block_id="q1",
                    text="",
                    inlines=[
                        InlineSpan(text="A "),
                        InlineSpan(text="B", style=InlineStyle(italic=True)),
                        InlineSpan(text=" C "),
                        InlineSpan(text="[1]", kind="note_call", note_ref="n1"),
                        InlineSpan(text=" D "),
                        InlineSpan(text="E", style=InlineStyle(small_caps=True)),
                        InlineSpan(text=" F"),
                    ],
                    attributes={
                        "semantic": {
                            "role": "lineated_block",
                            "layout_kind": "lineated_block",
                            "lineation": "lineated",
                            "lines": ["A B C D E F"],
                        }
                    },
                )
            ],
            notes=[Note(note_id="n1", label="1", text="Note")],
        )

        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        line = root.find(f".//{_q('lg')}/{_q('l')}")
        self.assertIsNotNone(line)
        self.assertEqual(line.text, "A ")
        his = line.findall(_q("hi"))
        self.assertEqual(len(his), 2)
        self.assertEqual(his[0].text, "B")
        self.assertEqual(his[0].tail, " C ")
        note = line.find(_q("note"))
        self.assertIsNotNone(note)
        self.assertEqual(note.tail, " D ")
        self.assertEqual(his[1].text, "E")
        self.assertEqual(his[1].tail, " F")

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

    def test_export_table_between_paragraphs_preserves_order(self) -> None:
        table_ooxml = (
            '<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:tr>"
            "<w:tc><w:p><w:r><w:t>A1</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>B1</w:t></w:r></w:p></w:tc>"
            "</w:tr>"
            "</w:tbl>"
        )
        document = Document(
            document_id="doc_table_order",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Paragraph(block_id="p1", text="avant"),
                Block(
                    block_id="t1",
                    block_type="table",
                    attributes={"table_ooxml": table_ooxml, "protected_zone": "table"},
                ),
                Paragraph(block_id="p2", text="apres"),
            ],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        body = root.find(f"./{_q('text')}/{_q('body')}")
        self.assertIsNotNone(body)
        children = list(body)
        self.assertEqual(children[0].tag, _q("p"))
        self.assertEqual(children[0].text, "avant")
        self.assertEqual(children[1].tag, _q("table"))
        self.assertEqual(children[2].tag, _q("p"))
        self.assertEqual(children[2].text, "apres")

    def test_export_table_2x2_to_tei_rows_and_cells(self) -> None:
        table_ooxml = (
            '<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:tr>"
            "<w:tc><w:p><w:r><w:t>c11</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>c12</w:t></w:r></w:p></w:tc>"
            "</w:tr>"
            "<w:tr>"
            "<w:tc><w:p><w:r><w:t>c21</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>c22</w:t></w:r></w:p></w:tc>"
            "</w:tr>"
            "</w:tbl>"
        )
        document = Document(
            document_id="doc_table_2x2",
            source_path="source.docx",
            source_format="docx",
            blocks=[Block(block_id="t1", block_type="table", attributes={"table_ooxml": table_ooxml})],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        table = root.find(f"./{_q('text')}/{_q('body')}/{_q('table')}")
        self.assertIsNotNone(table)
        rows = table.findall(_q("row"))
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0].findall(_q("cell"))), 2)
        self.assertEqual(len(rows[1].findall(_q("cell"))), 2)
        self.assertEqual(rows[0].findall(_q("cell"))[0].text, "c11")
        self.assertEqual(rows[0].findall(_q("cell"))[1].text, "c12")
        self.assertEqual(rows[1].findall(_q("cell"))[0].text, "c21")
        self.assertEqual(rows[1].findall(_q("cell"))[1].text, "c22")

    def test_export_table_records_success_diagnostic(self) -> None:
        table_ooxml = (
            '<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:tr><w:tc><w:p><w:r><w:t>x</w:t></w:r></w:p></w:tc></w:tr>"
            "</w:tbl>"
        )
        document = Document(
            document_id="doc_table_diag",
            source_path="source.docx",
            source_format="docx",
            blocks=[Block(block_id="t1", block_type="table", attributes={"table_ooxml": table_ooxml})],
        )
        self.exporter.export_document(document)
        diags = document.annotations.get("tei_table_diagnostics", [])
        self.assertEqual(len(diags), 1)
        self.assertEqual(diags[0].get("code"), "table_exported_to_tei")
        self.assertEqual(diags[0].get("rows"), 1)
        self.assertEqual(diags[0].get("cells"), 1)

    def test_export_table_never_silent_when_missing_ooxml(self) -> None:
        document = Document(
            document_id="doc_table_missing",
            source_path="source.docx",
            source_format="docx",
            blocks=[Block(block_id="t1", block_type="table", attributes={})],
        )
        xml_text = self.exporter.export_document(document)
        root = ET.fromstring(xml_text)
        body = root.find(f"./{_q('text')}/{_q('body')}")
        self.assertIsNotNone(body)
        p = body.find(_q("p"))
        self.assertIsNotNone(p)
        self.assertIn("Table not exported", p.text or "")
        diags = document.annotations.get("tei_table_diagnostics", [])
        self.assertEqual(len(diags), 1)
        self.assertEqual(diags[0].get("code"), "table_not_exported_to_tei")


if __name__ == "__main__":
    unittest.main()



