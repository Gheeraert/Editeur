from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.config import load_settings
from purh_editorial.model import Document, InlineSpan, Paragraph
from purh_editorial.pipeline.step1 import Step1Options, Step1Pipeline


def _pipeline_document(inlines: list[InlineSpan]) -> Document:
    return Document(
        document_id="doc-pipeline-diag",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[
            Paragraph(
                block_id="p1",
                text="".join(span.text for span in inlines),
                inlines=inlines,
            )
        ],
    )


class Step1PipelineDiagnosticsTests(unittest.TestCase):
    def test_pipeline_reports_r_an_002_note_call_after_final_punct(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        document = _pipeline_document(
            [
                InlineSpan(text="mot."),
                InlineSpan(text="1", kind="note_call", note_ref="ftn1"),
            ]
        )

        with patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document):
            result = pipeline.run(Path("dummy.txt"), Step1Options(enable_ai=False, output_path=None))

        diagnostics = result.pipeline_result.report.diagnostics
        self.assertTrue(any(d.rule_id == "R-AN-002" for d in diagnostics))

    def test_pipeline_reports_r_an_003_space_before_note_call(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        document = _pipeline_document(
            [
                InlineSpan(text="mot "),
                InlineSpan(text="1", kind="note_call", note_ref="ftn1"),
            ]
        )

        with patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document):
            result = pipeline.run(Path("dummy.txt"), Step1Options(enable_ai=False, output_path=None))

        diagnostics = result.pipeline_result.report.diagnostics
        self.assertTrue(any(d.rule_id == "R-AN-003" for d in diagnostics))


if __name__ == "__main__":
    unittest.main()
