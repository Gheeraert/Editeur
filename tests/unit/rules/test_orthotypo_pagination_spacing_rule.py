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
from purh_editorial.rules.orthotypography.pagination_spacing_rule import (
    NNBSP,
    PRE_RULE_TEXT_FACT,
    RULE_ID,
    PaginationSpacingRule,
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
    "abbreviation",
    ["p", "pp", "vol", "t", "f", "fol", "fig", "chap", "cat", "pl", "ms", "Ms", "n°", "N°", "col"],
)
def test_pagination_rule_covers_exact_legacy_abbreviations(
    abbreviation: str,
) -> None:
    source = f"{abbreviation}. 12"
    result = PaginationSpacingRule().evaluate(_context(source))
    action = result.proposed_actions[0]
    assert (action.before, action.after) == (
        f"{abbreviation}. ",
        f"{abbreviation}.{NNBSP}",
    )
    assert action.offset_end == len(action.before)


def test_pagination_rule_handles_roman_numbers_whitespace_and_order() -> None:
    source = "p.\tX puis vol.  II et pp.\n12"
    result = PaginationSpacingRule().evaluate(_context(source))
    assert tuple(action.before for action in result.proposed_actions) == (
        "p.\t",
        "vol.  ",
        "pp.\n",
    )
    assert tuple(action.after for action in result.proposed_actions) == (
        f"p.{NNBSP}",
        f"vol.{NNBSP}",
        f"pp.{NNBSP}",
    )
    assert tuple(action.offset_start for action in result.proposed_actions) == (
        source.index("p.\t"),
        source.index("vol.  "),
        source.index("pp.\n"),
    )


@pytest.mark.parametrize(
    "source",
    [f"voir p.{NNBSP}12", "voir p. texte", "supp. 12", "p."],
)
def test_pagination_rule_keeps_negative_and_canonical_forms(source: str) -> None:
    assert PaginationSpacingRule().evaluate(_context(source)).proposed_actions == ()


def test_pagination_rule_matches_the_same_legacy_transformation() -> None:
    source = "Voir pp. 12-14"
    _document, transformations = OrthotypoService().apply(
        Document(
            document_id="doc-1",
            source_path="source.docx",
            source_format="docx",
            blocks=[Block("p1", "paragraph", source)],
        )
    )
    legacy = next(item for item in transformations if item.rule_id == RULE_ID)
    action = PaginationSpacingRule().evaluate(_context(source)).proposed_actions[0]
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
    assert action.action_type is RuleActionType.TEXT_TRANSFORM
    assert action.after == f"pp.{NNBSP}"


def test_pagination_rule_is_canonical_pure_and_serializable() -> None:
    context = _context("p. 12 et vol. II")
    snapshot = to_json_data(context)
    first = PaginationSpacingRule().evaluate(context)
    assert first == PaginationSpacingRule().evaluate(context)
    assert to_json_data(context) == snapshot
    assert PaginationSpacingRule.descriptor is CANONICAL_RULE_REGISTRY.get(RULE_ID)
    assert json.dumps(to_json_data(first), ensure_ascii=False)


def test_pagination_rule_validates_its_input() -> None:
    with pytest.raises(ValueError, match="exactly one target"):
        PaginationSpacingRule().evaluate(_context("p. 12", ()))
    with pytest.raises(ValueError, match="non-empty target"):
        PaginationSpacingRule().evaluate(_context("p. 12", ("",)))
    with pytest.raises(TypeError, match="pre_rule_text"):
        PaginationSpacingRule().evaluate(_context(12))
