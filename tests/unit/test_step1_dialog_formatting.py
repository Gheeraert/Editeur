from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Diagnostic, Document, Evidence, ModuleRun, Paragraph, PipelineResult, ProcessingReport
from purh_editorial.pipeline.step1 import Step1Result
from purh_editorial.ui.step1_dialog import (
    build_result_text,
    format_diagnostics,
    format_module_runs,
    format_outputs,
    format_warnings,
)


class Step1DialogFormattingTests(unittest.TestCase):
    def _build_result(self) -> Step1Result:
        doc = Document(
            document_id="doc-ui",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="Texte")],
        )
        report = ProcessingReport(report_id="r1", document_id="doc-ui")
        report.transformations = []
        report.diagnostics = [
            Diagnostic(
                diagnostic_id="d1",
                module="footnote_normalizer",
                severity="warning",
                category="footnote_call_placement",
                message="Diagnostic test.",
                target_ref="p1",
                evidence=Evidence(excerpt="mot.1"),
                rule_id="R-AN-002",
            )
        ]
        report.warnings = ["TEI export skipped: test warning"]
        report.module_runs = [
            ModuleRun(
                module_name="orthotypo",
                version="2.0.0",
                started_at="2026-01-01T00:00:00+00:00",
                finished_at="2026-01-01T00:00:01+00:00",
                summary={"corrections": 3},
            )
        ]
        pipeline_result = PipelineResult(
            source_document=doc,
            styled_document=doc,
            report=report,
            tei_xml="<TEI/>",
        )
        return Step1Result(pipeline_result=pipeline_result, output_docx=Path("out.docx"))

    def test_format_diagnostics_includes_expected_fields(self) -> None:
        result = self._build_result()
        text = format_diagnostics(result.pipeline_result.report.diagnostics)
        self.assertIn("rule_id=R-AN-002", text)
        self.assertIn("severity=warning", text)
        self.assertIn("category=footnote_call_placement", text)
        self.assertIn("message=Diagnostic test.", text)
        self.assertIn("excerpt=mot.1", text)
        self.assertIn("target_ref=p1", text)

    def test_format_warnings_and_module_runs(self) -> None:
        result = self._build_result()
        warnings_text = format_warnings(result.pipeline_result.report.warnings)
        modules_text = format_module_runs(result.pipeline_result.report.module_runs)
        self.assertIn("TEI export skipped: test warning", warnings_text)
        self.assertIn("orthotypo", modules_text)
        self.assertIn("status=success", modules_text)

    def test_format_outputs_and_full_report(self) -> None:
        result = self._build_result()
        outputs_text = format_outputs(result)
        report_text = build_result_text(result)
        self.assertIn("DOCX de relecture", outputs_text)
        self.assertIn("XML-TEI", outputs_text)
        self.assertIn("Corrections appliquees", report_text)
        self.assertIn("Diagnostics a verifier", report_text)
        self.assertIn("Warnings techniques", report_text)
        self.assertIn("Resume modules", report_text)

    def test_empty_collections_have_safe_messages(self) -> None:
        self.assertEqual(format_diagnostics([]), "Aucun diagnostic.")
        self.assertEqual(format_warnings([]), "Aucun warning.")
        self.assertEqual(format_module_runs([]), "Aucun module execute.")


if __name__ == "__main__":
    unittest.main()
