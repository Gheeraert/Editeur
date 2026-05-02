from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.config import load_settings
from purh_editorial.pipeline.step1 import Step1Options, Step1Pipeline
from tests.helpers.docx_factory import create_table_docx

TEI_NS = "http://www.tei-c.org/ns/1.0"


class Step1PipelineTeiExportTests(unittest.TestCase):
    def test_pipeline_exposes_well_formed_tei_xml(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        source_path = ROOT / "tests" / "fixtures" / "minimal_source.txt"

        result = pipeline.run(source_path, Step1Options(enable_ai=False, output_path=None))
        tei_xml = result.pipeline_result.tei_xml

        self.assertIsNotNone(tei_xml)
        root = ET.fromstring(tei_xml)
        self.assertEqual(root.tag, f"{{{TEI_NS}}}TEI")
        body = root.find(f"./{{{TEI_NS}}}text/{{{TEI_NS}}}body")
        self.assertIsNotNone(body)

    def test_pipeline_writes_tei_xml_file_when_output_path_is_provided(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        source_path = ROOT / "tests" / "fixtures" / "minimal_source.txt"
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        tei_output_path = runtime_dir / f"pipeline_tei_{uuid.uuid4().hex}.xml"

        result = pipeline.run(
            source_path,
            Step1Options(
                enable_ai=False,
                output_path=None,
                tei_output_path=tei_output_path,
            ),
        )

        self.assertIsNotNone(result.pipeline_result.tei_xml)
        self.assertTrue(tei_output_path.exists())
        xml_text = tei_output_path.read_text(encoding="utf-8")
        root = ET.fromstring(xml_text)
        self.assertEqual(root.tag, f"{{{TEI_NS}}}TEI")

    def test_pipeline_reports_r_gq_004_quote_punctuation_diagnostic(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        source_path = runtime_dir / f"quote_diag_{uuid.uuid4().hex}.txt"
        source_path.write_text("Il écrit : « La question est ouverte ».", encoding="utf-8")

        result = pipeline.run(source_path, Step1Options(enable_ai=False, output_path=None))
        diagnostics = result.pipeline_result.report.diagnostics

        self.assertTrue(any(d.rule_id == "R-GQ-004" for d in diagnostics))

    def test_pipeline_exports_docx_table_to_tei_in_order(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        source_path = runtime_dir / f"table_src_{uuid.uuid4().hex}.docx"
        create_table_docx(source_path)

        result = pipeline.run(source_path, Step1Options(enable_ai=False, output_path=None))
        tei_xml = result.pipeline_result.tei_xml
        self.assertIsNotNone(tei_xml)
        root = ET.fromstring(tei_xml)
        body = root.find(f"./{{{TEI_NS}}}text/{{{TEI_NS}}}body")
        self.assertIsNotNone(body)

        table = body.find(f".//{{{TEI_NS}}}table")
        self.assertIsNotNone(table)
        rows = table.findall(f"{{{TEI_NS}}}row")
        self.assertEqual(len(rows), 1)
        cells = rows[0].findall(f"{{{TEI_NS}}}cell")
        self.assertEqual(len(cells), 2)
        self.assertIn("VIII,Pr.,", cells[0].text or "")
        self.assertIn("VIII;Pr.,18", cells[1].text or "")

        # Vérifie l'ordre logique avant/table/après dans le flux TEI
        ordered_texts: list[str] = []
        for node in body.iter():
            if node.tag in {f"{{{TEI_NS}}}p", f"{{{TEI_NS}}}head", f"{{{TEI_NS}}}cell"}:
                if node.text and node.text.strip():
                    ordered_texts.append(node.text.strip())
            elif node.tag == f"{{{TEI_NS}}}table":
                ordered_texts.append("[TABLE]")
        self.assertIn("Avant tableau", ordered_texts)
        self.assertIn("Après tableau", ordered_texts)
        self.assertIn("[TABLE]", ordered_texts)
        self.assertLess(ordered_texts.index("Avant tableau"), ordered_texts.index("[TABLE]"))
        self.assertLess(ordered_texts.index("[TABLE]"), ordered_texts.index("Après tableau"))

        source_doc = result.pipeline_result.source_document
        table_block_count = sum(1 for b in source_doc.blocks if b.block_type == "table")
        table_diags = source_doc.annotations.get("tei_table_diagnostics", [])
        self.assertEqual(len(table_diags), table_block_count)
        self.assertTrue(all(d.get("code") == "table_exported_to_tei" for d in table_diags))


if __name__ == "__main__":
    unittest.main()
