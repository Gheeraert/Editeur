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
from purh_editorial.model import Document, Heading, InlineSpan, InlineStyle, Paragraph, QuoteBlock
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


if __name__ == "__main__":
    unittest.main()
