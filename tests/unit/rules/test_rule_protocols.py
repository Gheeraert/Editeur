from __future__ import annotations

import inspect
import typing

from purh_editorial.rules import protocols


def test_expected_protocols_exist_without_implementations() -> None:
    expected = {
        "DeterministicRule": "evaluate",
        "HeuristicRule": "evaluate",
        "RuleRegistry": "validate",
        "ProtectionResolver": "resolve",
        "ThresholdPolicy": "thresholds",
        "RuleDecisionEngine": "decide",
        "ActionExecutor": "execute",
    }
    for name, method in expected.items():
        protocol = getattr(protocols, name)
        assert getattr(protocol, "_is_protocol", False)
        assert inspect.isfunction(getattr(protocol, method))


def test_protocol_module_has_no_engine_or_executor_implementation() -> None:
    assert not hasattr(protocols, "RuleEngine")
    assert not hasattr(protocols, "DefaultActionExecutor")


def test_rule_decision_engine_annotations_resolve_at_runtime() -> None:
    hints = typing.get_type_hints(protocols.RuleDecisionEngine.decide)
    assert hints["return"].__name__ == "RuleDecision"
