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
from purh_editorial.ui.step1_dialog import Step1Dialog


class Step1DialogFormattingTests(unittest.TestCase):
    def test_build_result_summary_includes_required_sections(self) -> None:
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
        result = Step1Result(pipeline_result=pipeline_result, output_docx=Path("out.docx"))

        summary = Step1Dialog._build_result_summary(result)
        self.assertIn("Corrections appliquees", summary)
        self.assertIn("Diagnostics a verifier", summary)
        self.assertIn("Warnings techniques", summary)
        self.assertIn("R-AN-002", summary)
        self.assertIn("mot.1", summary)
        self.assertIn("DOCX:", summary)
        self.assertIn("XML-TEI: genere", summary)


if __name__ == "__main__":
    unittest.main()
