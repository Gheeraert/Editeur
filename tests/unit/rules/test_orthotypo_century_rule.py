from __future__ import annotations

import json

import pytest

from purh_editorial.model import Block, Document
from purh_editorial.rules.model import (
    CompatibilityContext,
    ProtectionDecision,
    RuleActionType,
    RuleContext,
    to_json_data,
)
from purh_editorial.rules.orthotypography.century_rule import (
    PRE_RULE_TEXT_FACT,
    RULE_ID,
    CenturyAbbreviationRule,
)
from purh_editorial.rules.registry import CANONICAL_RULE_REGISTRY
from purh_editorial.services.orthotypo_service import OrthotypoService


def _context(text: object, targets: tuple[str, ...] = ("p1",)) -> RuleContext:
    return RuleContext(
        document_id="doc-1",
        target_refs=targets,
        source_facts={PRE_RULE_TEXT_FACT: text},
        canonical_facts={},
        protection=ProtectionDecision(
            False, "legacy.orthotypography", (), legacy_behavior=True
        ),
        compatibility=CompatibilityContext(None, ("shadow",)),
    )


@pytest.mark.parametrize(
    ("source", "before", "after"),
    [
        ("XVIIème siècle", "XVIIème", "XVIIe"),
        ("xviiième siècle", "xviiième", "XVIIIe"),
        ("Ie siècle", "Ie", "Ier"),
    ],
)
def test_century_rule_reproduces_legacy_text_transform(
    source: str, before: str, after: str
) -> None:
    result = CenturyAbbreviationRule().evaluate(_context(source))
    action = result.proposed_actions[0]
    assert (action.before, action.after) == (before, after)
    assert (action.offset_start, action.offset_end) == (
        source.index(before),
        source.index(before) + len(before),
    )
    assert action.action_type is RuleActionType.TEXT_TRANSFORM


def test_century_rule_traverses_enumeration_and_preserves_order() -> None:
    source = "XVIème, xviième et XVIIIème siècles"
    result = CenturyAbbreviationRule().evaluate(_context(source))
    assert tuple(action.before for action in result.proposed_actions) == (
        "XVIème",
        "xviième",
        "XVIIIème",
    )
    assert tuple(action.after for action in result.proposed_actions) == (
        "XVIe",
        "XVIIe",
        "XVIIIe",
    )
    assert tuple(action.offset_start for action in result.proposed_actions) == (
        source.index("XVIème"),
        source.index("xviième"),
        source.index("XVIIIème"),
    )


@pytest.mark.parametrize(
    "source",
    [
        "prolonger la vie de l’homme",
        "Maximilien Ier",
        "version XIXe",
        "XXIVème siècle",
        "XVIIe siècle",
    ],
)
def test_century_rule_keeps_legacy_guardrails(source: str) -> None:
    result = CenturyAbbreviationRule().evaluate(_context(source))
    assert result.matched is False
    assert result.proposed_actions == ()


def test_century_rule_matches_legacy_rule_without_century_styling() -> None:
    source = "XVIIème siècle"
    legacy_document, transformations = OrthotypoService().apply(
        Document(
            document_id="doc-1",
            source_path="source.docx",
            source_format="docx",
            blocks=[Block("p1", "paragraph", source)],
        )
    )
    legacy = next(item for item in transformations if item.rule_id == RULE_ID)
    native = CenturyAbbreviationRule().evaluate(_context(source))
    action = native.proposed_actions[0]
    assert (action.before, action.after) == (legacy.before, legacy.after)
    assert (
        action.offset_start,
        action.offset_end,
    ) == (
        legacy.attributes["offset_start"],
        legacy.attributes["offset_end"],
    )
    assert all(action.action_type is RuleActionType.TEXT_TRANSFORM for action in native.proposed_actions)
    assert legacy_document.blocks[0].text == "xviie siècle"
    assert action.after == "XVIIe"


def test_century_rule_is_canonical_pure_and_serializable() -> None:
    context = _context("XVIIème siècle")
    snapshot = to_json_data(context)
    first = CenturyAbbreviationRule().evaluate(context)
    assert first == CenturyAbbreviationRule().evaluate(context)
    assert to_json_data(context) == snapshot
    assert CenturyAbbreviationRule.descriptor is CANONICAL_RULE_REGISTRY.get(RULE_ID)
    assert json.dumps(to_json_data(first), ensure_ascii=False)


def test_century_rule_validates_its_input() -> None:
    with pytest.raises(ValueError, match="exactly one target"):
        CenturyAbbreviationRule().evaluate(_context("XVIIème siècle", ()))
    with pytest.raises(ValueError, match="non-empty target"):
        CenturyAbbreviationRule().evaluate(_context("XVIIème siècle", ("",)))
    with pytest.raises(TypeError, match="pre_rule_text"):
        CenturyAbbreviationRule().evaluate(_context(42))
