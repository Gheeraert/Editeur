from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest

from purh_editorial.rules.model import (
    CompatibilityContext,
    DeterministicResult,
    ProtectionDecision,
    RuleContext,
    to_json_data,
)
from purh_editorial.rules.orthotypography.etc_rule import (
    MATCH_CONDITION,
    PRE_RULE_TEXT_FACT,
    RULE_ID,
    EtcAbbreviationRule,
)
from purh_editorial.rules.registry import CANONICAL_RULE_REGISTRY


ROOT = Path(__file__).resolve().parents[3]


def _context(
    text: object = "etc...",
    *,
    targets: tuple[str, ...] = ("p1",),
    include_text: bool = True,
    protected: bool = False,
) -> RuleContext:
    source_facts = {PRE_RULE_TEXT_FACT: text} if include_text else {}
    return RuleContext(
        document_id="doc-1",
        target_refs=targets,
        source_facts=source_facts,
        canonical_facts={},
        protection=ProtectionDecision(
            protected,
            "legacy.orthotypography",
            ("protected",) if protected else (),
            legacy_behavior=True,
        ),
        compatibility=CompatibilityContext(
            source_config_version=None,
            flags=("shadow",),
        ),
    )


@pytest.mark.parametrize(
    ("source", "before"),
    [
        ("etc...", "etc..."),
        ("etc....", "etc...."),
        ("etc…", "etc…"),
        ("etc….", "etc…."),
    ],
)
def test_etc_rule_reproduces_the_legacy_positive_forms(
    source: str,
    before: str,
) -> None:
    result = EtcAbbreviationRule().evaluate(_context(source))
    assert result.matched is True
    assert result.conditions_met == (MATCH_CONDITION,)
    assert len(result.proposed_actions) == 1
    action = result.proposed_actions[0]
    assert action.before == before
    assert action.after == "etc."
    assert (action.offset_start, action.offset_end) == (0, len(source))


def test_etc_rule_preserves_occurrence_order_and_exact_offsets() -> None:
    source = "Avant etc... puis etc…. Fin."
    result = EtcAbbreviationRule().evaluate(_context(source))
    assert tuple(action.before for action in result.proposed_actions) == (
        "etc...",
        "etc….",
    )
    assert tuple(
        (action.offset_start, action.offset_end)
        for action in result.proposed_actions
    ) == (
        (source.index("etc..."), source.index("etc...") + len("etc...")),
        (source.index("etc…."), source.index("etc….") + len("etc….")),
    )


@pytest.mark.parametrize("source", ["etc.", "Sans abréviation.", "Etc...", "ETC…"])
def test_etc_rule_reports_a_stable_non_match(source: str) -> None:
    result = EtcAbbreviationRule().evaluate(_context(source))
    assert result == DeterministicResult(
        rule_id=RULE_ID,
        matched=False,
        target_refs=("p1",),
        proposed_actions=(),
        conditions_met=(),
        veto_reasons=(),
        justification="Aucune forme « etc. » à normaliser n’a été détectée.",
    )


@pytest.mark.parametrize("targets", [(), ("p1", "p2")])
def test_etc_rule_requires_exactly_one_target(
    targets: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match="exactly one target"):
        EtcAbbreviationRule().evaluate(_context(targets=targets))


def test_etc_rule_rejects_missing_or_non_string_pre_rule_text() -> None:
    with pytest.raises(ValueError, match="pre_rule_text"):
        EtcAbbreviationRule().evaluate(_context(include_text=False))
    with pytest.raises(TypeError, match="pre_rule_text"):
        EtcAbbreviationRule().evaluate(_context(42))


def test_etc_rule_uses_the_exact_canonical_descriptor() -> None:
    assert (
        EtcAbbreviationRule.descriptor
        is CANONICAL_RULE_REGISTRY.get(RULE_ID)
    )


def test_etc_rule_is_pure_deterministic_and_serializable() -> None:
    context = _context("etc... et etc…", protected=True)
    first = EtcAbbreviationRule().evaluate(context)
    second = EtcAbbreviationRule().evaluate(context)
    assert first == second
    assert first.matched is True
    assert context.source_facts[PRE_RULE_TEXT_FACT] == "etc... et etc…"
    assert json.dumps(to_json_data(first), ensure_ascii=False)
    with pytest.raises(FrozenInstanceError):
        first.matched = False  # type: ignore[misc]


def test_fixture_cases_are_reproduced_without_modifying_the_fixture() -> None:
    fixture_path = (
        ROOT
        / "fixtures/orthotypography_characterization/purh_abreviations_etc.json"
    )
    raw = fixture_path.read_bytes()
    fixture = json.loads(raw.decode("utf-8"))
    for case in fixture["positive_cases"]:
        result = EtcAbbreviationRule().evaluate(_context(case["input"]))
        rebuilt = case["input"]
        for action in reversed(result.proposed_actions):
            rebuilt = (
                rebuilt[: action.offset_start]
                + action.after
                + rebuilt[action.offset_end :]
            )
        assert rebuilt == case["expected_output"]
    for case in fixture["negative_cases"]:
        assert EtcAbbreviationRule().evaluate(
            _context(case["input"])
        ).matched is False
    assert fixture_path.read_bytes() == raw
