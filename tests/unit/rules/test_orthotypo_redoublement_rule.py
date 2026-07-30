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
from purh_editorial.rules.orthotypography.redoublement_rule import (
    MATCH_CONDITION,
    PRE_RULE_TEXT_FACT,
    RULE_ID,
    RedoubledAbbreviationRule,
)
from purh_editorial.rules.registry import CANONICAL_RULE_REGISTRY


ROOT = Path(__file__).resolve().parents[3]
NNBSP = "\u202f"


def _context(
    text: object = "pp. 53-84",
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
        (f"pp.{NNBSP}53-84", "pp.", "p."),
        ("vv. 122-128", "vv.", "v."),
        ("ll. 5 et 12", "ll.", "l."),
        ("§§ 5-9", "§§", "§"),
    ],
)
def test_redoublement_rule_reproduces_each_positive_form(
    source: str,
    before: str,
    after: str,
) -> None:
    result = RedoubledAbbreviationRule().evaluate(_context(source))
    assert result.matched is True
    assert result.conditions_met == (MATCH_CONDITION,)
    assert len(result.proposed_actions) == 1
    action = result.proposed_actions[0]
    assert (action.before, action.after) == (before, after)
    assert (action.offset_start, action.offset_end) == (
        source.index(before),
        source.index(before) + len(before),
    )


def test_redoublement_rule_preserves_order_and_offsets() -> None:
    source = "pp. 1, vv. 2, ll. 3 et §§ 4"
    result = RedoubledAbbreviationRule().evaluate(_context(source))
    assert tuple(action.before for action in result.proposed_actions) == (
        "pp.",
        "vv.",
        "ll.",
        "§§",
    )
    assert tuple(action.after for action in result.proposed_actions) == (
        "p.",
        "v.",
        "l.",
        "§",
    )
    assert tuple(action.offset_start for action in result.proposed_actions) == (
        source.index("pp."),
        source.index("vv."),
        source.index("ll."),
        source.index("§§"),
    )


@pytest.mark.parametrize(
    "source",
    ["voir p. 12", "supp. cit.", "PP. 12", "Vv. 3", "§ 5"],
)
def test_redoublement_rule_keeps_negative_forms(source: str) -> None:
    result = RedoubledAbbreviationRule().evaluate(_context(source))
    assert result.matched is False
    assert result.proposed_actions == ()
    assert result.conditions_met == ()
    assert result.veto_reasons == ()


@pytest.mark.parametrize("targets", [(), ("p1", "p2")])
def test_redoublement_rule_requires_exactly_one_target(
    targets: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match="exactly one target"):
        RedoubledAbbreviationRule().evaluate(_context(targets=targets))


def test_redoublement_rule_rejects_empty_target_and_invalid_text_fact() -> None:
    with pytest.raises(ValueError, match="non-empty target"):
        RedoubledAbbreviationRule().evaluate(_context(targets=("",)))
    with pytest.raises(ValueError, match="pre_rule_text"):
        RedoubledAbbreviationRule().evaluate(_context(include_text=False))
    with pytest.raises(TypeError, match="pre_rule_text"):
        RedoubledAbbreviationRule().evaluate(_context(42))


def test_redoublement_rule_uses_the_canonical_descriptor() -> None:
    assert (
        RedoubledAbbreviationRule.descriptor
        is CANONICAL_RULE_REGISTRY.get(RULE_ID)
    )


def test_redoublement_rule_is_pure_deterministic_and_serializable() -> None:
    context = _context("pp. 1 et §§ 2")
    first = RedoubledAbbreviationRule().evaluate(context)
    second = RedoubledAbbreviationRule().evaluate(context)
    assert first == second
    assert context.source_facts[PRE_RULE_TEXT_FACT] == "pp. 1 et §§ 2"
    assert json.dumps(to_json_data(first), ensure_ascii=False)
    with pytest.raises(FrozenInstanceError):
        first.matched = False  # type: ignore[misc]


def test_fixture_is_reproduced_from_the_actual_pre_rule_text() -> None:
    fixture_path = (
        ROOT
        / "fixtures/orthotypography_characterization/"
        "purh_abreviations_redoublement.json"
    )
    raw = fixture_path.read_bytes()
    fixture = json.loads(raw.decode("utf-8"))
    for case in fixture["positive_cases"]:
        pre_rule_text = case["input"]
        if pre_rule_text.startswith("pp. "):
            pre_rule_text = pre_rule_text.replace("pp. ", f"pp.{NNBSP}", 1)
        result = RedoubledAbbreviationRule().evaluate(
            _context(pre_rule_text)
        )
        rebuilt = pre_rule_text
        for action in reversed(result.proposed_actions):
            rebuilt = (
                rebuilt[: action.offset_start]
                + action.after
                + rebuilt[action.offset_end :]
            )
        assert rebuilt == case["expected_output"]
    for case in fixture["negative_cases"]:
        pre_rule_text = case["input"]
        if pre_rule_text.startswith("voir p. "):
            pre_rule_text = pre_rule_text.replace("p. ", f"p.{NNBSP}", 1)
        assert RedoubledAbbreviationRule().evaluate(
            _context(pre_rule_text)
        ).matched is False
    assert fixture_path.read_bytes() == raw
