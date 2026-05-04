from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Diagnostic, Document, Evidence, Paragraph
from purh_editorial.services.structure_ai_arbitrator import (
    StructureAiArbitrator,
    settings_for_ai_aggressiveness,
    parse_structure_ai_json,
)


class _FakeProvider:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        return self.response


class _RaisingProvider:
    def __init__(self, message: str = "provider_error") -> None:
        self.message = message
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        raise RuntimeError(self.message)


class _SequenceProvider:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    def complete(self, prompt: str) -> str:
        self.calls += 1
        if self.calls <= len(self.responses):
            return self.responses[self.calls - 1]
        return self.responses[-1]


def _doc() -> Document:
    return Document(
        document_id="doc-ai-arbitration",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[
            Paragraph(block_id="p1", text="Contexte avant."),
            Paragraph(block_id="p2", text="Cadre theorique"),
            Paragraph(block_id="p3", text="Contexte apres."),
        ],
    )


def _candidate_diag(
    *,
    rule_id: str,
    target_ref: str = "p2",
    ai_candidate: bool = True,
    veto_reasons: list[str] | None = None,
) -> Diagnostic:
    return Diagnostic(
        diagnostic_id="diag1",
        module="structure",
        severity="info",
        category="heading_candidate" if rule_id == "R-STRUCT-HEADING-001" else "poetry_quote_candidate",
        message="candidate",
        target_ref=target_ref,
        evidence=Evidence(excerpt="Cadre theorique"),
        rule_id=rule_id,
        attributes={
            "score": 0.72,
            "decision": "diagnostic",
            "evidence": {"excerpt": "Cadre theorique"},
            "veto_reasons": veto_reasons or [],
            "ai_candidate": ai_candidate,
            "target_refs": [target_ref],
        },
    )


class StructureAiArbitratorTests(unittest.TestCase):
    def test_heading_grey_candidate_calls_provider(self) -> None:
        provider = _FakeProvider(
            '{"classification":"heading","confidence":0.91,"reason":"nominal","recommended_action":"diagnostic"}'
        )
        arbitrator = StructureAiArbitrator(provider=provider)
        diags, warnings, calls = arbitrator.arbitrate_from_diagnostics(
            document=_doc(),
            diagnostics=[_candidate_diag(rule_id="R-STRUCT-HEADING-001")],
            enable_ai=True,
        )
        self.assertEqual(calls, 1)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(len(warnings), 0)
        self.assertEqual(len(diags), 1)

    def test_poetry_grey_candidate_calls_provider(self) -> None:
        provider = _FakeProvider(
            '{"classification":"poetry_quote","confidence":0.88,"reason":"metrics","recommended_action":"diagnostic"}'
        )
        arbitrator = StructureAiArbitrator(provider=provider)
        diags, _, calls = arbitrator.arbitrate_from_diagnostics(
            document=_doc(),
            diagnostics=[_candidate_diag(rule_id="R-CI-POETRY-001")],
            enable_ai=True,
        )
        self.assertEqual(calls, 1)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(len(diags), 1)

    def test_veto_candidate_does_not_call_provider(self) -> None:
        provider = _FakeProvider(
            '{"classification":"heading","confidence":0.91,"reason":"x","recommended_action":"diagnostic"}'
        )
        arbitrator = StructureAiArbitrator(provider=provider)
        _, _, calls = arbitrator.arbitrate_from_diagnostics(
            document=_doc(),
            diagnostics=[_candidate_diag(rule_id="R-STRUCT-HEADING-001", veto_reasons=["list_like"])],
            enable_ai=True,
        )
        self.assertEqual(calls, 0)
        self.assertEqual(provider.calls, 0)

    def test_non_ai_candidate_does_not_call_provider(self) -> None:
        provider = _FakeProvider(
            '{"classification":"heading","confidence":0.91,"reason":"x","recommended_action":"diagnostic"}'
        )
        arbitrator = StructureAiArbitrator(provider=provider)
        _, _, calls = arbitrator.arbitrate_from_diagnostics(
            document=_doc(),
            diagnostics=[_candidate_diag(rule_id="R-STRUCT-HEADING-001", ai_candidate=False)],
            enable_ai=True,
        )
        self.assertEqual(calls, 0)
        self.assertEqual(provider.calls, 0)

    def test_enable_ai_false_does_not_call_provider(self) -> None:
        provider = _FakeProvider(
            '{"classification":"heading","confidence":0.91,"reason":"x","recommended_action":"diagnostic"}'
        )
        arbitrator = StructureAiArbitrator(provider=provider)
        _, _, calls = arbitrator.arbitrate_from_diagnostics(
            document=_doc(),
            diagnostics=[_candidate_diag(rule_id="R-STRUCT-HEADING-001")],
            enable_ai=False,
        )
        self.assertEqual(calls, 0)
        self.assertEqual(provider.calls, 0)

    def test_valid_json_is_parsed(self) -> None:
        result = parse_structure_ai_json(
            '{"classification":"paragraph","confidence":0.5,"reason":"ok","recommended_action":"diagnostic"}'
        )
        self.assertEqual(result.classification, "paragraph")
        self.assertEqual(result.confidence, 0.5)

    def test_non_json_response_produces_warning_diagnostic(self) -> None:
        provider = _FakeProvider("not-json")
        arbitrator = StructureAiArbitrator(provider=provider)
        diags, _, calls = arbitrator.arbitrate_from_diagnostics(
            document=_doc(),
            diagnostics=[_candidate_diag(rule_id="R-STRUCT-HEADING-001")],
            enable_ai=True,
        )
        self.assertEqual(calls, 1)
        self.assertEqual(len(diags), 1)
        self.assertEqual(diags[0].rule_id, "R-STRUCT-AI-LOCAL-001")
        self.assertEqual(diags[0].severity, "warning")

    def test_unknown_classification_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_structure_ai_json(
                '{"classification":"weird","confidence":0.5,"reason":"x","recommended_action":"diagnostic"}'
            )

    def test_confidence_out_of_bounds_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_structure_ai_json(
                '{"classification":"heading","confidence":1.2,"reason":"x","recommended_action":"diagnostic"}'
            )

    def test_arbitration_does_not_modify_document_text(self) -> None:
        provider = _FakeProvider(
            '{"classification":"heading","confidence":0.91,"reason":"x","recommended_action":"diagnostic"}'
        )
        arbitrator = StructureAiArbitrator(provider=provider)
        document = _doc()
        before = [b.text for b in document.blocks]
        arbitrator.arbitrate_from_diagnostics(
            document=document,
            diagnostics=[_candidate_diag(rule_id="R-STRUCT-HEADING-001")],
            enable_ai=True,
        )
        after = [b.text for b in document.blocks]
        self.assertEqual(before, after)

    def test_max_calls_cap_is_respected(self) -> None:
        provider = _FakeProvider(
            '{"classification":"heading","confidence":0.91,"reason":"x","recommended_action":"diagnostic"}'
        )
        arbitrator = StructureAiArbitrator(provider=provider)
        diags = [
            _candidate_diag(rule_id="R-STRUCT-HEADING-001", target_ref="p1"),
            _candidate_diag(rule_id="R-STRUCT-HEADING-001", target_ref="p2"),
        ]
        _, _, calls = arbitrator.arbitrate_from_diagnostics(
            document=_doc(),
            diagnostics=diags,
            enable_ai=True,
            max_calls=1,
        )
        self.assertEqual(calls, 1)
        self.assertEqual(provider.calls, 1)

    def test_non_json_with_max_calls_1_counts_attempt(self) -> None:
        provider = _FakeProvider("not-json")
        arbitrator = StructureAiArbitrator(provider=provider)
        diags, _, calls = arbitrator.arbitrate_from_diagnostics(
            document=_doc(),
            diagnostics=[_candidate_diag(rule_id="R-STRUCT-HEADING-001")],
            enable_ai=True,
            max_calls=1,
        )
        self.assertEqual(provider.calls, 1)
        self.assertEqual(calls, 1)
        self.assertEqual(len(diags), 1)
        self.assertEqual(diags[0].severity, "warning")
        self.assertEqual(diags[0].rule_id, "R-STRUCT-AI-LOCAL-001")

    def test_provider_exception_with_two_candidates_max_calls_1_counts_one_attempt(self) -> None:
        provider = _RaisingProvider()
        arbitrator = StructureAiArbitrator(provider=provider)
        diags = [
            _candidate_diag(rule_id="R-STRUCT-HEADING-001", target_ref="p1"),
            _candidate_diag(rule_id="R-STRUCT-HEADING-001", target_ref="p2"),
        ]
        out_diags, _, calls = arbitrator.arbitrate_from_diagnostics(
            document=_doc(),
            diagnostics=diags,
            enable_ai=True,
            max_calls=1,
        )
        self.assertEqual(provider.calls, 1)
        self.assertEqual(calls, 1)
        self.assertEqual(len(out_diags), 1)
        self.assertEqual(out_diags[0].severity, "warning")

    def test_first_invalid_second_valid_max_calls_1_only_first_attempted(self) -> None:
        provider = _SequenceProvider(
            [
                "not-json",
                '{"classification":"heading","confidence":0.91,"reason":"ok","recommended_action":"diagnostic"}',
            ]
        )
        arbitrator = StructureAiArbitrator(provider=provider)
        diags = [
            _candidate_diag(rule_id="R-STRUCT-HEADING-001", target_ref="p1"),
            _candidate_diag(rule_id="R-STRUCT-HEADING-001", target_ref="p2"),
        ]
        out_diags, _, calls = arbitrator.arbitrate_from_diagnostics(
            document=_doc(),
            diagnostics=diags,
            enable_ai=True,
            max_calls=1,
        )
        self.assertEqual(provider.calls, 1)
        self.assertEqual(calls, 1)
        self.assertEqual(len(out_diags), 1)
        self.assertEqual(out_diags[0].severity, "warning")

    def test_ai_aggressiveness_profiles(self) -> None:
        conservative_settings, conservative_calls = settings_for_ai_aggressiveness(
            "conservative",
            base_max_structure_ai_calls=6,
        )
        balanced_settings, balanced_calls = settings_for_ai_aggressiveness(
            "balanced",
            base_max_structure_ai_calls=6,
        )
        aggressive_settings, aggressive_calls = settings_for_ai_aggressiveness(
            "aggressive",
            base_max_structure_ai_calls=6,
        )

        self.assertEqual(conservative_settings.confidence_threshold, 0.90)
        self.assertEqual(balanced_settings.confidence_threshold, 0.85)
        self.assertEqual(aggressive_settings.confidence_threshold, 0.75)
        self.assertEqual(conservative_calls, 3)
        self.assertEqual(balanced_calls, 6)
        self.assertEqual(aggressive_calls, 6)

    def test_apply_cluster_transforms_poetry_quote_blocks(self) -> None:
        document = Document(
            document_id="doc-cluster-poetry",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                Paragraph(block_id="p1", text="Ligne une"),
                Paragraph(block_id="p2", text="Ligne deux"),
                Paragraph(block_id="p3", text="Ligne trois"),
            ],
        )
        cluster_diag = Diagnostic(
            diagnostic_id="diag_cluster_poetry",
            module="structure_ai_arbitration",
            severity="info",
            category="paragraph_cluster_candidate",
            message="cluster",
            target_ref="p1",
            rule_id="R-STRUCT-CLUSTER-001",
            evidence=Evidence(excerpt="Ligne une\nLigne deux\nLigne trois"),
            attributes={
                "classification": "poetry_quote",
                "recommended_action": "transform",
                "confidence": 0.93,
                "reason": "vers courts homogènes",
                "block_ids": ["p1", "p2", "p3"],
            },
        )
        arbitrator = StructureAiArbitrator(provider=None)

        transformations, diagnostics, summary = arbitrator.apply_cluster_transformations(
            document=document,
            diagnostics=[cluster_diag],
            enable_ai_transform=True,
            confidence_threshold=0.85,
        )

        self.assertEqual(summary["candidates"], 1)
        self.assertEqual(summary["applied"], 1)
        self.assertEqual(summary["refused"], 0)
        self.assertEqual(len(transformations), 1)
        self.assertEqual(len(document.blocks), 1)
        merged = document.blocks[0]
        self.assertEqual(merged.block_type, "lineated_block")
        self.assertEqual(merged.attributes.get("highlight_color"), "ai_structure")
        self.assertEqual(merged.attributes.get("merged_from"), ["p1", "p2", "p3"])
        semantic = merged.attributes.get("semantic", {})
        self.assertEqual(semantic.get("lineation"), "lineated")
        self.assertEqual(semantic.get("lines"), ["Ligne une", "Ligne deux", "Ligne trois"])
        self.assertTrue(any(d.attributes.get("status") == "applied" for d in diagnostics))

    def test_apply_cluster_refuses_list_item_without_block_type_change(self) -> None:
        document = Document(
            document_id="doc-cluster-list",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[
                Paragraph(block_id="p1", text="Item A"),
                Paragraph(block_id="p2", text="Item B"),
                Paragraph(block_id="p3", text="Item C"),
            ],
        )
        cluster_diag = Diagnostic(
            diagnostic_id="diag_cluster_list",
            module="structure_ai_arbitration",
            severity="info",
            category="paragraph_cluster_candidate",
            message="cluster",
            target_ref="p1",
            rule_id="R-STRUCT-CLUSTER-001",
            evidence=Evidence(excerpt="Item A\nItem B\nItem C"),
            attributes={
                "classification": "list_item",
                "recommended_action": "transform",
                "confidence": 0.94,
                "reason": "items parallèles",
                "block_ids": ["p1", "p2", "p3"],
            },
        )
        arbitrator = StructureAiArbitrator(provider=None)

        transformations, diagnostics, summary = arbitrator.apply_cluster_transformations(
            document=document,
            diagnostics=[cluster_diag],
            enable_ai_transform=True,
            confidence_threshold=0.85,
        )

        self.assertEqual(summary["candidates"], 1)
        self.assertEqual(summary["applied"], 0)
        self.assertEqual(summary["refused"], 1)
        self.assertEqual(summary["refusal_reasons"].get("list_not_supported"), 1)
        self.assertEqual(len(transformations), 0)
        self.assertTrue(
            any(
                d.message == "transformation refusée : type liste non encore supporté par cette passe"
                for d in diagnostics
            )
        )
        self.assertTrue(all(block.block_type == "paragraph" for block in document.blocks))


if __name__ == "__main__":
    unittest.main()
