from __future__ import annotations

import json
import re

import pytest

from purh_editorial.rules.model import (
    DeploymentStatus,
    DeterministicResult,
    HeuristicEvidence,
    HeuristicProposal,
    ProposedAction,
    RuleActionType,
    to_json_data,
)
from purh_editorial.rules.registry import CANONICAL_RULE_REGISTRY


def test_registry_descriptors_serialize_to_json_native_values() -> None:
    payload = to_json_data(CANONICAL_RULE_REGISTRY.all())
    encoded = json.dumps(payload, ensure_ascii=False)
    assert '"orthotypography"' in encoded
    assert isinstance(payload, list)
    assert isinstance(payload[0]["test_refs"], list)
    assert payload[0]["deployment_status"] == DeploymentStatus.REVIEW_ONLY.value


def test_text_style_diagnostic_and_structure_actions_serialize() -> None:
    actions = (
        ProposedAction(
            RuleActionType.TEXT_TRANSFORM,
            ("p1",),
            before="etc...",
            after="etc.",
        ),
        ProposedAction(
            RuleActionType.STYLE_TRANSFORM,
            ("p1",),
            before="xvii",
            after="xvii",
            style_patch={"small_caps": True},
        ),
        ProposedAction(
            RuleActionType.DIAGNOSTIC,
            ("p2",),
            diagnostic_payload={"message": "À vérifier", "severity": "warning"},
        ),
        ProposedAction(
            RuleActionType.STRUCTURE_TRANSFORM,
            ("v1", "v2"),
            semantic_patch={"role": "quote", "lineation": "verse"},
            deleted_refs=("v2",),
            merged_refs=("v1", "v2"),
        ),
    )
    payload = to_json_data(actions)
    json.dumps(payload, ensure_ascii=False)
    assert payload[1]["style_patch"] == {"small_caps": True}
    assert payload[2]["diagnostic_payload"]["message"] == "À vérifier"
    assert payload[3]["merged_refs"] == ["v1", "v2"]


def test_results_and_heuristic_evidence_serialize_without_enum_or_tuple() -> None:
    action = ProposedAction(
        RuleActionType.TEXT_TRANSFORM,
        ("p1",),
        before="a",
        after="b",
    )
    deterministic = DeterministicResult(
        "test.rule",
        True,
        ("p1",),
        (action,),
        ("exact_match",),
        (),
        "Correspondance exacte.",
    )
    heuristic = HeuristicProposal(
        "test.heuristic",
        "heading",
        0.7,
        (action,),
        ("p1",),
        (HeuristicEvidence("short", True, 0.2, "Bloc court."),),
        (),
        (),
        "Titre possible.",
    )
    payload = to_json_data({"deterministic": deterministic, "heuristic": heuristic})
    json.dumps(payload, ensure_ascii=False)

    def assert_native(value: object) -> None:
        assert not isinstance(value, tuple)
        if isinstance(value, dict):
            for item in value.values():
                assert_native(item)
        elif isinstance(value, list):
            for item in value:
                assert_native(item)

    assert_native(payload)


def test_serializer_rejects_non_json_objects() -> None:
    with pytest.raises(TypeError, match="Unsupported JSON value"):
        to_json_data(re.compile("x"))

