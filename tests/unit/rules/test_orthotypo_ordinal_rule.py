from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest

from purh_editorial.rules.model import (
    CompatibilityContext,
    ProtectionDecision,
    RuleContext,
    to_json_data,
)
from purh_editorial.rules.orthotypography.ordinal_rule import (
    MATCH_CONDITION,
    PRE_RULE_TEXT_FACT,
    RULE_ID,
    OrdinalAbbreviationRule,
)
from purh_editorial.rules.registry import CANONICAL_RULE_REGISTRY


ROOT = Path(__file__).resolve().parents[3]


def _context(
    text: object = "la 1ère partie",
    *,
    targets: tuple[str, ...] = ("p1",),
    include_text: bool = True,
) -> RuleContext:
    source_facts = {PRE_RULE_TEXT_FACT: text} if include_text else {}
    return RuleContext(
        document_id="doc-1",
        target_refs=targets,
        source_facts=source_facts,
        canonical_facts={},
        protection=ProtectionDecision(
            False,
            "legacy.orthotypography",
            (),
            legacy_behavior=True,
        ),
        compatibility=CompatibilityContext(
            source_config_version=None,
            flags=("shadow",),
        ),
    )


@pytest.mark.parametrize(
    ("source", "before", "after"),
    [
        ("la 1ère partie", "1ère", "1re"),
        ("la 1ere partie", "1ere", "1re"),
        ("le 5ème chapitre", "5ème", "5e"),
        ("le 5eme chapitre", "5eme", "5e"),
    ],
)
def test_ordinal_rule_reproduces_the_supported_forms(
    source: str,
    before: str,
    after: str,
) -> None:
    result = OrdinalAbbreviationRule().evaluate(_context(source))
    assert result.matched is True
    assert result.conditions_met == (MATCH_CONDITION,)
    action = result.proposed_actions[0]
    assert (action.before, action.after) == (before, after)
    assert (action.offset_start, action.offset_end) == (
        source.index(before),
        source.index(before) + len(before),
    )


def test_ordinal_rule_preserves_occurrence_order_and_offsets() -> None:
    source = "la 1ère partie, la 1ere annexe, le 5ème chapitre et le 5eme volume"
    result = OrdinalAbbreviationRule().evaluate(_context(source))
    assert tuple(action.before for action in result.proposed_actions) == (
        "1ère",
        "1ere",
        "5ème",
        "5eme",
    )
    assert tuple(action.after for action in result.proposed_actions) == (
        "1re",
        "1re",
        "5e",
        "5e",
    )
    assert tuple(action.offset_start for action in result.proposed_actions) == tuple(
        source.index(value) for value in ("1ère", "1ere", "5ème", "5eme")
    )


@pytest.mark.parametrize(
    "source",
    ["le 1er chapitre", "version 2.0", "Ier", "Ie", "2de", "2nde"],
)
def test_ordinal_rule_keeps_known_guardrails(source: str) -> None:
    result = OrdinalAbbreviationRule().evaluate(_context(source))
    assert result.matched is False
    assert result.proposed_actions == ()
    assert result.conditions_met == ()


@pytest.mark.parametrize("targets", [(), ("p1", "p2")])
def test_ordinal_rule_requires_exactly_one_target(
    targets: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match="exactly one target"):
        OrdinalAbbreviationRule().evaluate(_context(targets=targets))


def test_ordinal_rule_rejects_invalid_context_facts() -> None:
    with pytest.raises(ValueError, match="non-empty target"):
        OrdinalAbbreviationRule().evaluate(_context(targets=("",)))
    with pytest.raises(ValueError, match="pre_rule_text"):
        OrdinalAbbreviationRule().evaluate(_context(include_text=False))
    with pytest.raises(TypeError, match="pre_rule_text"):
        OrdinalAbbreviationRule().evaluate(_context(42))


def test_ordinal_rule_uses_the_canonical_descriptor() -> None:
    assert (
        OrdinalAbbreviationRule.descriptor
        is CANONICAL_RULE_REGISTRY.get(RULE_ID)
    )


def test_ordinal_rule_is_pure_deterministic_and_serializable() -> None:
    context = _context("la 1ère partie et le 5ème chapitre")
    first = OrdinalAbbreviationRule().evaluate(context)
    second = OrdinalAbbreviationRule().evaluate(context)
    assert first == second
    assert context.source_facts[PRE_RULE_TEXT_FACT] == (
        "la 1ère partie et le 5ème chapitre"
    )
    assert json.dumps(to_json_data(first), ensure_ascii=False)
    with pytest.raises(FrozenInstanceError):
        first.matched = False  # type: ignore[misc]


@pytest.mark.parametrize(
    "fixture_name,case_key",
    [
        ("purh_ordinaux.json", "positive_cases"),
        ("purh_ordinaux.json", "negative_cases"),
    ],
)
def test_ordinal_rule_reproduces_characterization_fixture(
    fixture_name: str,
    case_key: str,
) -> None:
    fixture_path = ROOT / "fixtures/orthotypography_characterization" / fixture_name
    raw = fixture_path.read_bytes()
    fixture = json.loads(raw.decode("utf-8"))
    for case in fixture[case_key]:
        source = case["input"]
        result = OrdinalAbbreviationRule().evaluate(_context(source))
        rebuilt = source
        for action in reversed(result.proposed_actions):
            rebuilt = (
                rebuilt[: action.offset_start]
                + action.after
                + rebuilt[action.offset_end :]
            )
        assert rebuilt == case["expected_output"]
    assert fixture_path.read_bytes() == raw


def test_ordinal_rule_reproduces_gold_fixture() -> None:
    fixture_path = ROOT / "fixtures/orthotypography_gold/purh_ordinaux.json"
    raw = fixture_path.read_bytes()
    fixture = json.loads(raw.decode("utf-8"))
    for case in fixture["gold_cases"]:
        source = case["input"]
        result = OrdinalAbbreviationRule().evaluate(_context(source))
        action = result.proposed_actions[0]
        rebuilt = (
            source[: action.offset_start]
            + action.after
            + source[action.offset_end :]
        )
        assert rebuilt == case["expected_output"]
    assert fixture_path.read_bytes() == raw
