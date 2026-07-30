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
from purh_editorial.rules.orthotypography.numero_rule import (
    NNBSP,
    PRE_RULE_TEXT_FACT,
    RULE_ID,
    NumeroAbbreviationRule,
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
        ("n° 5", "n° ", f"no{NNBSP}"),
        ("N°5", "N°", f"No{NNBSP}"),
        ("nº 12", "nº ", f"no{NNBSP}"),
        ("No. 7", "No. ", f"No{NNBSP}"),
    ],
)
def test_numero_rule_reproduces_legacy_text_transform(
    source: str, before: str, after: str
) -> None:
    action = NumeroAbbreviationRule().evaluate(_context(source)).proposed_actions[0]
    assert (action.before, action.after) == (before, after)
    assert (action.offset_start, action.offset_end) == (0, len(before))
    assert action.action_type is RuleActionType.TEXT_TRANSFORM


def test_numero_rule_preserves_order_offsets_and_excludes_digits() -> None:
    source = "n° 5 puis No. 12"
    result = NumeroAbbreviationRule().evaluate(_context(source))
    assert tuple(action.before for action in result.proposed_actions) == (
        "n° ",
        "No. ",
    )
    assert tuple(action.offset_start for action in result.proposed_actions) == (
        0,
        source.index("No."),
    )
    assert all(action.before[-1] != "5" for action in result.proposed_actions)


@pytest.mark.parametrize(
    "source",
    [f"no{NNBSP}5", "n° sans chiffre", "le numéro de la revue", "o 5"],
)
def test_numero_rule_keeps_negative_and_canonical_forms(source: str) -> None:
    assert NumeroAbbreviationRule().evaluate(_context(source)).proposed_actions == ()


def test_numero_rule_matches_legacy_without_superscript_style() -> None:
    source = "n° 5"
    _document, transformations = OrthotypoService().apply(
        Document(
            document_id="doc-1",
            source_path="source.docx",
            source_format="docx",
            blocks=[Block("p1", "paragraph", source)],
        )
    )
    legacy = next(item for item in transformations if item.rule_id == RULE_ID)
    native = NumeroAbbreviationRule().evaluate(_context(source))
    action = native.proposed_actions[0]
    assert (
        action.before,
        action.after,
        action.offset_start,
        action.offset_end,
    ) == (
        legacy.before,
        legacy.after,
        legacy.attributes["offset_start"],
        legacy.attributes["offset_end"],
    )
    assert all(action.action_type is RuleActionType.TEXT_TRANSFORM for action in native.proposed_actions)
    assert action.after == f"no{NNBSP}"


def test_numero_rule_is_canonical_pure_and_serializable() -> None:
    context = _context("n° 5 et N°12")
    snapshot = to_json_data(context)
    first = NumeroAbbreviationRule().evaluate(context)
    assert first == NumeroAbbreviationRule().evaluate(context)
    assert to_json_data(context) == snapshot
    assert NumeroAbbreviationRule.descriptor is CANONICAL_RULE_REGISTRY.get(RULE_ID)
    assert json.dumps(to_json_data(first), ensure_ascii=False)


def test_numero_rule_validates_its_input() -> None:
    with pytest.raises(ValueError, match="exactly one target"):
        NumeroAbbreviationRule().evaluate(_context("n° 5", ()))
    with pytest.raises(ValueError, match="non-empty target"):
        NumeroAbbreviationRule().evaluate(_context("n° 5", ("",)))
    with pytest.raises(TypeError, match="pre_rule_text"):
        NumeroAbbreviationRule().evaluate(_context(5))
