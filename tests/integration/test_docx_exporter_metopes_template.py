from __future__ import annotations

import sys
import unittest
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.io.docx_exporter import DocxExporter
from purh_editorial.model import Document, Heading, InlineSpan, InlineStyle, LineatedBlock, Note, Paragraph, QuoteBlock
from purh_editorial.services.metopes_mapper import MetopesMapper
from purh_editorial.services.orthotypo_service import OrthotypoService

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
TEMPLATE_PATH = ROOT / "sources" / "editorial_rules" / "metopes_template_word" / "Commons-publishing-Metopes.dotm"


def _q(local_name: str) -> str:
    return f"{{{W_NS}}}{local_name}"


class DocxExporterMetopesTemplateIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not TEMPLATE_PATH.exists():
            raise unittest.SkipTest(
                f"Gabarit Métopes introuvable: {TEMPLATE_PATH}"
            )

    @staticmethod
    def _runtime_path(filename: str) -> Path:
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        return runtime_dir / filename

    def _export_with_real_template(self, document: Document) -> Path:
        output = self._runtime_path(f"metopes_export_{uuid.uuid4().hex}.docx")
        DocxExporter(template_path=TEMPLATE_PATH).export(document, output)
        return output

    @staticmethod
    def _read_document_xml(output_path: Path) -> ET.Element:
        with zipfile.ZipFile(output_path, "r") as archive:
            xml_bytes = archive.read("word/document.xml")
        return ET.fromstring(xml_bytes)

    @staticmethod
    def _read_footnotes_xml(output_path: Path) -> ET.Element:
        with zipfile.ZipFile(output_path, "r") as archive:
            xml_bytes = archive.read("word/footnotes.xml")
        return ET.fromstring(xml_bytes)

    @staticmethod
    def _runs_with_text(root: ET.Element) -> list[tuple[str, ET.Element]]:
        runs: list[tuple[str, ET.Element]] = []
        for run in root.findall(f".//{_q('r')}"):
            text = "".join((node.text or "") for node in run.findall(_q("t")))
            if text:
                runs.append((text, run))
        return runs

    @staticmethod
    def _paragraphs_with_text(root: ET.Element) -> list[tuple[str, ET.Element]]:
        paragraphs: list[tuple[str, ET.Element]] = []
        for paragraph in root.findall(f".//{_q('p')}"):
            text = "".join((node.text or "") for node in paragraph.findall(f".//{_q('t')}"))
            if text:
                paragraphs.append((text, paragraph))
        return paragraphs

    @staticmethod
    def _first_line_attr(paragraph: ET.Element) -> str | None:
        ind = paragraph.find(f"./{_q('pPr')}/{_q('ind')}")
        if ind is None:
            return None
        return ind.attrib.get(_q("firstLine"))

    @staticmethod
    def _left_indent_attr(paragraph: ET.Element) -> str | None:
        ind = paragraph.find(f"./{_q('pPr')}/{_q('ind')}")
        if ind is None:
            return None
        return ind.attrib.get(_q("left"))

    @staticmethod
    def _justification_attr(paragraph: ET.Element) -> str | None:
        jc = paragraph.find(f"./{_q('pPr')}/{_q('jc')}")
        if jc is None:
            return None
        return jc.attrib.get(_q("val"))

    @staticmethod
    def _line_spacing_attr(paragraph: ET.Element) -> str | None:
        spacing = paragraph.find(f"./{_q('pPr')}/{_q('spacing')}")
        if spacing is None:
            return None
        return spacing.attrib.get(_q("line"))

    @staticmethod
    def _run_font_sizes_half_points(paragraph: ET.Element) -> list[int]:
        values: list[int] = []
        for run in paragraph.findall(f"./{_q('r')}"):
            sz = run.find(f"./{_q('rPr')}/{_q('sz')}")
            if sz is None:
                continue
            val = sz.attrib.get(_q("val"))
            if not val:
                continue
            try:
                values.append(int(val))
            except ValueError:
                continue
        return values

    def test_ooxml_century_styles_with_real_metopes_template(self) -> None:
        source = Document(
            document_id="doc-real-template-1",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="XIXe siècle")],
        )
        styled, _ = OrthotypoService().apply(source)
        output = self._export_with_real_template(styled)
        root = self._read_document_xml(output)
        runs = self._runs_with_text(root)

        roman_run = next((run for text, run in runs if text == "xix"), None)
        self.assertIsNotNone(roman_run, "Run 'xix' introuvable dans word/document.xml")
        self.assertIsNotNone(roman_run.find(f"./{_q('rPr')}/{_q('smallCaps')}"))

        exponent_run = next((run for text, run in runs if text == "e"), None)
        self.assertIsNotNone(exponent_run, "Run 'e' introuvable dans word/document.xml")
        vert_align = exponent_run.find(f"./{_q('rPr')}/{_q('vertAlign')}")
        self.assertIsNotNone(vert_align)
        self.assertEqual(vert_align.attrib.get(_q("val")), "superscript")

        siecle_run = next((run for text, run in runs if "siècle" in text), None)
        self.assertIsNotNone(siecle_run, "Run contenant 'siècle' introuvable")
        self.assertIsNone(siecle_run.find(f"./{_q('rPr')}/{_q('smallCaps')}"))
        self.assertIsNone(siecle_run.find(f"./{_q('rPr')}/{_q('vertAlign')}"))

    def test_ooxml_century_styles_keep_italic_with_real_template(self) -> None:
        source = Document(
            document_id="doc-real-template-2",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                Paragraph(
                    block_id="p1",
                    text="XVIIe siècle",
                    inlines=[InlineSpan(text="XVIIe siècle", style=InlineStyle(italic=True))],
                )
            ],
        )
        styled, _ = OrthotypoService().apply(source)
        output = self._export_with_real_template(styled)
        root = self._read_document_xml(output)
        runs = self._runs_with_text(root)

        roman_run = next((run for text, run in runs if text == "xvii"), None)
        self.assertIsNotNone(roman_run.find(f"./{_q('rPr')}/{_q('i')}"))
        self.assertIsNotNone(roman_run.find(f"./{_q('rPr')}/{_q('smallCaps')}"))

        exponent_run = next((run for text, run in runs if text == "e"), None)
        self.assertIsNotNone(exponent_run.find(f"./{_q('rPr')}/{_q('i')}"))
        vert_align = exponent_run.find(f"./{_q('rPr')}/{_q('vertAlign')}")
        self.assertIsNotNone(vert_align)
        self.assertEqual(vert_align.attrib.get(_q("val")), "superscript")

    def test_docx_package_health_from_real_template(self) -> None:
        source = Document(
            document_id="doc-real-template-3",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="XIXe siècle")],
        )
        styled, _ = OrthotypoService().apply(source)
        output = self._export_with_real_template(styled)

        self.assertTrue(zipfile.is_zipfile(output), "Le DOCX produit n'est pas un zip valide.")
        with zipfile.ZipFile(output, "r") as archive:
            names = set(archive.namelist())
            self.assertIn("[Content_Types].xml", names)
            self.assertIn("word/document.xml", names)
            self.assertIn("word/styles.xml", names)
            self.assertIn("word/_rels/document.xml.rels", names)
            self.assertNotIn("word/vbaProject.bin", names)
            self.assertNotIn("word/vbaData.xml", names)

            content_types = archive.read("[Content_Types].xml").decode("utf-8", errors="ignore")
            self.assertNotIn("macroEnabledTemplate", content_types)
            self.assertNotIn("vbaProject", content_types)

            has_custom_ui = any(name.startswith("customUI/") for name in names)
            # customUI n'est pas supprimé ici: on le suit explicitement pour signaler un risque potentiel.
            self.assertIsInstance(has_custom_ui, bool)


    def test_regular_paragraphs_are_first_line_indented(self) -> None:
        source = Document(
            document_id="doc-indent-1",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                Paragraph(block_id="p1", text="Premier paragraphe."),
                Paragraph(block_id="p2", text="Second paragraphe."),
            ],
        )
        mapped, _ = MetopesMapper().apply(source)
        output = self._export_with_real_template(mapped)
        root = self._read_document_xml(output)
        paragraphs = self._paragraphs_with_text(root)
        self.assertEqual(len(paragraphs), 2)
        self.assertTrue(all(self._first_line_attr(p) is not None for _text, p in paragraphs))

    def test_heading_not_indented_and_following_paragraph_is_indented(self) -> None:
        source = Document(
            document_id="doc-indent-2",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                Heading(block_id="h1", text="Titre"),
                Paragraph(block_id="p1", text="Paragraphe courant."),
            ],
        )
        mapped, _ = MetopesMapper().apply(source)
        output = self._export_with_real_template(mapped)
        root = self._read_document_xml(output)
        paragraphs = self._paragraphs_with_text(root)
        self.assertEqual(len(paragraphs), 2)
        self.assertIsNone(self._first_line_attr(paragraphs[0][1]))
        self.assertIsNotNone(self._first_line_attr(paragraphs[1][1]))

    def test_quote_block_is_not_indented(self) -> None:
        source = Document(
            document_id="doc-indent-quote",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[QuoteBlock(block_id="q1", text="Citation longue.")],
        )
        mapped, _ = MetopesMapper().apply(source)
        output = self._export_with_real_template(mapped)
        root = self._read_document_xml(output)
        paragraphs = self._paragraphs_with_text(root)
        self.assertEqual(len(paragraphs), 1)
        self.assertIsNone(self._first_line_attr(paragraphs[0][1]))

    def test_paragraph_after_quote_block_uses_no_indent_style(self) -> None:
        source = Document(
            document_id="doc-indent-3",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                QuoteBlock(block_id="q1", text="Citation longue."),
                Paragraph(block_id="p1", text="Paragraphe apres citation."),
            ],
        )
        mapped, _ = MetopesMapper().apply(source)
        self.assertEqual(mapped.blocks[1].attributes.get("metopes_style"), "TEI_paragraph_consecutive")

        output = self._export_with_real_template(mapped)
        root = self._read_document_xml(output)
        paragraphs = self._paragraphs_with_text(root)
        self.assertEqual(len(paragraphs), 2)
        self.assertIsNone(self._first_line_attr(paragraphs[1][1]))

    def test_headings_use_limited_font_sizes_for_review_docx(self) -> None:
        source = Document(
            document_id="doc-heading-size",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                Heading(block_id="h1", text="Titre niveau 1", attributes={"heading_level": 1}),
                Heading(block_id="h2", text="Titre niveau 2", attributes={"heading_level": 2}),
                Heading(block_id="h3", text="Titre niveau 3", attributes={"heading_level": 3}),
            ],
        )
        mapped, _ = MetopesMapper().apply(source)
        output = self._export_with_real_template(mapped)
        root = self._read_document_xml(output)
        paragraphs = self._paragraphs_with_text(root)
        self.assertEqual(len(paragraphs), 3)

        sizes_h1 = self._run_font_sizes_half_points(paragraphs[0][1])
        sizes_h2 = self._run_font_sizes_half_points(paragraphs[1][1])
        sizes_h3 = self._run_font_sizes_half_points(paragraphs[2][1])

        self.assertTrue(sizes_h1 and all(v <= 32 for v in sizes_h1), "Heading 1 > 16pt")
        self.assertTrue(sizes_h2 and all(v <= 28 for v in sizes_h2), "Heading 2 > 14pt")
        self.assertTrue(sizes_h3 and all(v <= 26 for v in sizes_h3), "Heading 3 > 13pt")

    def test_quote_blocks_have_review_readability_formatting(self) -> None:
        source = Document(
            document_id="doc-quotes-format",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                QuoteBlock(block_id="q1", text="Citation en prose."),
                LineatedBlock(block_id="q2", text="Vers 1\nVers 2", attributes={
                    "semantic": {"role": "lineated_block", "layout_kind": "lineated_block", "lineation": "lineated", "lines": ["Vers 1", "Vers 2"]},
                }),
            ],
        )
        mapped, _ = MetopesMapper().apply(source)
        output = self._export_with_real_template(mapped)
        root = self._read_document_xml(output)
        paragraphs = self._paragraphs_with_text(root)
        self.assertEqual(len(paragraphs), 2)

        prose_p = paragraphs[0][1]
        poetry_p = paragraphs[1][1]

        self.assertIsNotNone(self._left_indent_attr(prose_p))
        self.assertEqual(self._justification_attr(prose_p), "both")
        self.assertEqual(self._line_spacing_attr(prose_p), "240")
        self.assertTrue(all(v == 22 for v in self._run_font_sizes_half_points(prose_p)))

        self.assertIsNotNone(self._left_indent_attr(poetry_p))
        self.assertEqual(self._justification_attr(poetry_p), "left")
        self.assertEqual(self._line_spacing_attr(poetry_p), "240")
        self.assertTrue(all(v == 22 for v in self._run_font_sizes_half_points(poetry_p)))

    def test_footnotes_runs_use_garamond(self) -> None:
        source = Document(
            document_id="doc-footnote-font",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                Paragraph(
                    block_id="p1",
                    text="Texte avec note.",
                    inlines=[
                        InlineSpan(text="Texte avec note"),
                        InlineSpan(text="", kind="note_call", note_ref="n1"),
                        InlineSpan(text="."),
                    ],
                )
            ],
            notes=[
                Note(note_id="n1", text="Contenu de note."),
            ],
        )
        mapped, _ = MetopesMapper().apply(source)
        output = self._export_with_real_template(mapped)
        root = self._read_footnotes_xml(output)

        garamond_fonts = 0
        for run in root.findall(f".//{_q('r')}"):
            rfonts = run.find(f"./{_q('rPr')}/{_q('rFonts')}")
            if rfonts is None:
                continue
            if rfonts.attrib.get(_q("ascii")) == "Garamond" and rfonts.attrib.get(_q("hAnsi")) == "Garamond":
                garamond_fonts += 1
        self.assertGreater(garamond_fonts, 0, "Aucun run de note en Garamond détecté.")


if __name__ == "__main__":
    unittest.main()
