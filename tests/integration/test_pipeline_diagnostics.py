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
    def test_structure_ai_provider_created_from_session_api_key(self) -> None:
        settings = load_settings()
        settings.ai.api_key = None
        pipeline = Step1Pipeline(settings=settings, structure_ai_provider=None)
        document = Document(
            document_id="doc-create-provider",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="Texte simple")],
        )
        structure_diag = Diagnostic(
            diagnostic_id="diag-structure",
            module="structure",
            severity="info",
            category="heading_candidate",
            message="candidate",
            target_ref="p1",
            evidence=Evidence(excerpt="Texte simple"),
            rule_id="R-STRUCT-HEADING-001",
            attributes={
                "score": 0.7,
                "decision": "diagnostic",
                "evidence": {"excerpt": "Texte simple"},
                "veto_reasons": [],
                "ai_candidate": True,
                "target_refs": ["p1"],
            },
        )
        with (
            patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document),
            patch.object(pipeline.structure, "process", return_value=([structure_diag], [])),
            patch.object(pipeline.structure_ai, "arbitrate_from_diagnostics", return_value=([], [], 0)) as arb_mock,
        ):
            pipeline.run(
                Path("dummy.txt"),
                Step1Options(
                    decision_mode="heuristic_ai_local",
                    ai_api_key="session-key",
                    output_path=None,
                ),
            )
        self.assertIsNotNone(pipeline.structure_ai.provider)
        self.assertTrue(arb_mock.call_args.kwargs.get("enable_ai"))

    def test_structure_ai_without_key_and_provider_keeps_warning(self) -> None:
        settings = load_settings()
        settings.ai.api_key = None
        pipeline = Step1Pipeline(settings=settings, structure_ai_provider=None)
        document = Document(
            document_id="doc-no-provider",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="Texte simple")],
        )
        structure_diag = Diagnostic(
            diagnostic_id="diag-structure",
            module="structure",
            severity="info",
            category="heading_candidate",
            message="candidate",
            target_ref="p1",
            evidence=Evidence(excerpt="Texte simple"),
            rule_id="R-STRUCT-HEADING-001",
            attributes={
                "score": 0.7,
                "decision": "diagnostic",
                "evidence": {"excerpt": "Texte simple"},
                "veto_reasons": [],
                "ai_candidate": True,
                "target_refs": ["p1"],
            },
        )
        with (
            patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document),
            patch.object(pipeline.structure, "process", return_value=([structure_diag], [])),
        ):
            result = pipeline.run(
                Path("dummy.txt"),
                Step1Options(decision_mode="heuristic_ai_local", output_path=None),
            )
        self.assertTrue(
            any("no provider configured" in warning.lower() for warning in result.pipeline_result.report.warnings)
        )

    def test_injected_structure_ai_provider_is_not_overridden_by_session_key(self) -> None:
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
        settings.ai.api_key = None
        provider = FakeProvider()
        pipeline = Step1Pipeline(settings=settings, structure_ai_provider=provider)
        document = Document(
            document_id="doc-injected-provider",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="Texte simple")],
        )
        structure_diag = Diagnostic(
            diagnostic_id="diag-structure",
            module="structure",
            severity="info",
            category="heading_candidate",
            message="candidate",
            target_ref="p1",
            evidence=Evidence(excerpt="Texte simple"),
            rule_id="R-STRUCT-HEADING-001",
            attributes={
                "score": 0.7,
                "decision": "diagnostic",
                "evidence": {"excerpt": "Texte simple"},
                "veto_reasons": [],
                "ai_candidate": True,
                "target_refs": ["p1"],
            },
        )
        with (
            patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document),
            patch.object(pipeline.structure, "process", return_value=([structure_diag], [])),
        ):
            pipeline.run(
                Path("dummy.txt"),
                Step1Options(
                    decision_mode="heuristic_ai_local",
                    ai_api_key="session-key",
                    output_path=None,
                ),
            )
        self.assertIs(pipeline.structure_ai.provider, provider)
        self.assertEqual(provider.calls, 1)

    def test_unsupported_ai_provider_warns_without_runtime_provider_creation(self) -> None:
        settings = load_settings()
        settings.ai.api_key = None
        pipeline = Step1Pipeline(settings=settings, structure_ai_provider=None)
        document = Document(
            document_id="doc-unsupported-provider",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="Texte simple")],
        )
        structure_diag = Diagnostic(
            diagnostic_id="diag-structure",
            module="structure",
            severity="info",
            category="heading_candidate",
            message="candidate",
            target_ref="p1",
            evidence=Evidence(excerpt="Texte simple"),
            rule_id="R-STRUCT-HEADING-001",
            attributes={
                "score": 0.7,
                "decision": "diagnostic",
                "evidence": {"excerpt": "Texte simple"},
                "veto_reasons": [],
                "ai_candidate": True,
                "target_refs": ["p1"],
            },
        )
        with (
            patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document),
            patch.object(pipeline.structure, "process", return_value=([structure_diag], [])),
        ):
            result = pipeline.run(
                Path("dummy.txt"),
                Step1Options(
                    decision_mode="heuristic_ai_local",
                    ai_provider="openai",
                    ai_api_key="session-key",
                    output_path=None,
                ),
            )
        self.assertTrue(
            any("unsupported ai_provider" in warning.lower() for warning in result.pipeline_result.report.warnings)
        )

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

    def test_pipeline_deterministic_mode_disables_structure_heuristics(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        document = Document(
            document_id="doc-deterministic-structure",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                Paragraph(block_id="p1", text="La reception du modele tragique", attributes={"all_runs_bold": True}),
                Paragraph(block_id="p2", text="« " + ("texte " * 40).strip() + " »"),
            ],
        )
        with patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document):
            result = pipeline.run(Path("dummy.txt"), Step1Options(decision_mode="deterministic", output_path=None))

        report = result.pipeline_result.report
        self.assertEqual(document.blocks[0].block_type, "paragraph")
        self.assertEqual(document.blocks[1].block_type, "paragraph")
        self.assertFalse(any(d.rule_id == "R-STRUCT-HEADING-001" for d in report.diagnostics))
        self.assertFalse(any(d.rule_id == "R-CI-POETRY-001" for d in report.diagnostics))
        structure_run = next(m for m in report.module_runs if m.module_name == "structure")
        self.assertEqual(structure_run.summary.get("structure_mode"), "deterministic")
        self.assertEqual(structure_run.summary.get("heuristics_enabled"), False)

    def test_pipeline_heuristic_mode_keeps_structure_heuristics(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        document = Document(
            document_id="doc-heuristic-structure",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                Paragraph(block_id="h1", text="Titre", block_type="heading"),
                Paragraph(block_id="p1", text="La reception du modele tragique", attributes={"all_runs_bold": True}),
                Paragraph(block_id="p2", text="« " + ("texte " * 40).strip() + " »"),
            ],
        )
        with patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document):
            result = pipeline.run(
                Path("dummy.txt"),
                Step1Options(decision_mode="heuristic", heuristic_profile="balanced", output_path=None),
            )

        report = result.pipeline_result.report
        structure_run = next(m for m in report.module_runs if m.module_name == "structure")
        self.assertEqual(structure_run.summary.get("structure_mode"), "heuristic")
        self.assertEqual(structure_run.summary.get("heuristics_enabled"), True)


if __name__ == "__main__":
    unittest.main()
