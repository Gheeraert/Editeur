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
from purh_editorial.model import Diagnostic, Document, Evidence, InlineSpan, Paragraph
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
            result = pipeline.run(Path("dummy.txt"), Step1Options(output_path=None))

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
            result = pipeline.run(Path("dummy.txt"), Step1Options(output_path=None))

        diagnostics = result.pipeline_result.report.diagnostics
        self.assertTrue(any(d.rule_id == "R-AN-003" for d in diagnostics))

    def test_pipeline_reports_structure_ai_local_arbitration(self) -> None:
        class FakeProvider:
            def __init__(self) -> None:
                self.calls = 0

            def complete(self, prompt: str) -> str:
                self.calls += 1
                return (
                    '{"classification":"heading","confidence":0.9,'
                    '"reason":"nominal","recommended_action":"diagnostic"}'
                )

        settings = load_settings()
        settings.ai.api_key = "dummy-key"
        provider = FakeProvider()
        pipeline = Step1Pipeline(settings=settings, structure_ai_provider=provider)
        document = Document(
            document_id="doc-structure-ai",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="Cadre theorique")],
        )
        structure_diag = Diagnostic(
            diagnostic_id="diag-structure",
            module="structure",
            severity="info",
            category="heading_candidate",
            message="candidate",
            target_ref="p1",
            evidence=Evidence(excerpt="Cadre theorique"),
            rule_id="R-STRUCT-HEADING-001",
            attributes={
                "score": 0.7,
                "decision": "diagnostic",
                "evidence": {"excerpt": "Cadre theorique"},
                "veto_reasons": [],
                "ai_candidate": True,
                "target_refs": ["p1"],
            },
        )

        with (
            patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document),
            patch.object(pipeline.structure, "process", return_value=([structure_diag], [])),
            patch.object(pipeline.ai, "apply", return_value=(document, [])),
        ):
            result = pipeline.run(
                Path("dummy.txt"),
                Step1Options(enable_structure_ai=True, output_path=None),
            )

        diagnostics = result.pipeline_result.report.diagnostics
        self.assertTrue(any(d.rule_id == "R-STRUCT-AI-LOCAL-001" for d in diagnostics))
        self.assertEqual(provider.calls, 1)

    def test_structure_ai_enabled_does_not_call_editorial_ai(self) -> None:
        class FakeProvider:
            def __init__(self) -> None:
                self.calls = 0

            def complete(self, prompt: str) -> str:
                self.calls += 1
                return (
                    '{"classification":"heading","confidence":0.9,'
                    '"reason":"nominal","recommended_action":"diagnostic"}'
                )

        settings = load_settings()
        settings.ai.api_key = "dummy-key"
        provider = FakeProvider()
        pipeline = Step1Pipeline(settings=settings, structure_ai_provider=provider)
        document = Document(
            document_id="doc-structure-only",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="Cadre theorique")],
        )
        structure_diag = Diagnostic(
            diagnostic_id="diag-structure",
            module="structure",
            severity="info",
            category="heading_candidate",
            message="candidate",
            target_ref="p1",
            evidence=Evidence(excerpt="Cadre theorique"),
            rule_id="R-STRUCT-HEADING-001",
            attributes={
                "score": 0.7,
                "decision": "diagnostic",
                "evidence": {"excerpt": "Cadre theorique"},
                "veto_reasons": [],
                "ai_candidate": True,
                "target_refs": ["p1"],
            },
        )

        with (
            patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document),
            patch.object(pipeline.structure, "process", return_value=([structure_diag], [])),
            patch.object(pipeline.ai, "apply", return_value=(document, [])) as ai_apply_mock,
        ):
            pipeline.run(Path("dummy.txt"), Step1Options(enable_structure_ai=True, output_path=None))

        self.assertEqual(provider.calls, 1)
        ai_apply_mock.assert_not_called()

    def test_editorial_ai_enabled_does_not_call_structure_ai_when_disabled(self) -> None:
        class FakeProvider:
            def __init__(self) -> None:
                self.calls = 0

            def complete(self, prompt: str) -> str:
                self.calls += 1
                return "{}"

        settings = load_settings()
        settings.ai.api_key = "dummy-key"
        provider = FakeProvider()
        pipeline = Step1Pipeline(settings=settings, structure_ai_provider=provider)
        document = Document(
            document_id="doc-editorial-only",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="Texte long " * 40)],
        )
        with (
            patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document),
            patch.object(pipeline.ai, "apply", return_value=(document, [])) as ai_apply_mock,
        ):
            pipeline.run(Path("dummy.txt"), Step1Options(enable_editorial_ai=True, output_path=None))

        ai_apply_mock.assert_called_once()
        self.assertEqual(provider.calls, 0)

    def test_both_ai_disabled_by_default(self) -> None:
        settings = load_settings()
        settings.ai.api_key = "dummy-key"
        pipeline = Step1Pipeline(settings=settings)
        document = Document(
            document_id="doc-no-ai-default",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="Texte long " * 40)],
        )
        with (
            patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document),
            patch.object(pipeline.structure_ai, "arbitrate_from_diagnostics", return_value=([], [], 0)) as arb_mock,
            patch.object(pipeline.ai, "apply", return_value=(document, [])) as ai_apply_mock,
        ):
            pipeline.run(Path("dummy.txt"), Step1Options(output_path=None))

        arb_mock.assert_called_once()
        # Called with enable_ai=False in arbitrator contract
        self.assertFalse(arb_mock.call_args.kwargs.get("enable_ai"))
        ai_apply_mock.assert_not_called()

    def test_structure_ai_call_cap_is_respected(self) -> None:
        class FakeProvider:
            def __init__(self) -> None:
                self.calls = 0

            def complete(self, prompt: str) -> str:
                self.calls += 1
                return (
                    '{"classification":"heading","confidence":0.9,'
                    '"reason":"nominal","recommended_action":"diagnostic"}'
                )

        settings = load_settings()
        settings.ai.api_key = "dummy-key"
        provider = FakeProvider()
        pipeline = Step1Pipeline(settings=settings, structure_ai_provider=provider)
        document = Document(
            document_id="doc-structure-cap",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="a"), Paragraph(block_id="p2", text="b")],
        )
        structure_diags = [
            Diagnostic(
                diagnostic_id="diag-1",
                module="structure",
                severity="info",
                category="heading_candidate",
                message="candidate",
                target_ref="p1",
                evidence=Evidence(excerpt="a"),
                rule_id="R-STRUCT-HEADING-001",
                attributes={
                    "score": 0.7,
                    "decision": "diagnostic",
                    "evidence": {"excerpt": "a"},
                    "veto_reasons": [],
                    "ai_candidate": True,
                    "target_refs": ["p1"],
                },
            ),
            Diagnostic(
                diagnostic_id="diag-2",
                module="structure",
                severity="info",
                category="heading_candidate",
                message="candidate",
                target_ref="p2",
                evidence=Evidence(excerpt="b"),
                rule_id="R-STRUCT-HEADING-001",
                attributes={
                    "score": 0.7,
                    "decision": "diagnostic",
                    "evidence": {"excerpt": "b"},
                    "veto_reasons": [],
                    "ai_candidate": True,
                    "target_refs": ["p2"],
                },
            ),
        ]
        with (
            patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document),
            patch.object(pipeline.structure, "process", return_value=(structure_diags, [])),
        ):
            pipeline.run(
                Path("dummy.txt"),
                Step1Options(enable_structure_ai=True, max_structure_ai_calls=1, output_path=None),
            )
        self.assertEqual(provider.calls, 1)


if __name__ == "__main__":
    unittest.main()
