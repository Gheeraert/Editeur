from __future__ import annotations

import re

from purh_editorial.rules.model import (
    DeterministicResult,
    ProposedAction,
    RuleActionType,
    RuleContext,
    RuleDescriptor,
)
from purh_editorial.rules.registry import CANONICAL_RULE_REGISTRY


RULE_ID = "purh.pagination.espace"
PRE_RULE_TEXT_FACT = "pre_rule_text"
MATCH_CONDITION = "pagination_spacing_detected"
NNBSP = "\u202f"
_ABBREVIATION = r"\b(pp?|vol|t|f|fol|fig|chap|cat|pl|ms|Ms|n°|N°|col)\."
_PAGINATION_PATTERN = re.compile(
    _ABBREVIATION + r"\s+(?=[\dIVXLCivxlc])"
)


class PaginationSpacingRule:
    """Évalue purement l’espace suivant les abréviations de pagination."""

    descriptor: RuleDescriptor = CANONICAL_RULE_REGISTRY.get(RULE_ID)

    def evaluate(self, context: RuleContext) -> DeterministicResult:
        target_ref, text = _validated_input(context)
        actions: list[ProposedAction] = []
        for match in _PAGINATION_PATTERN.finditer(text):
            replacement = match.group(1) + "." + NNBSP
            if replacement == match.group(0):
                continue
            actions.append(
                ProposedAction(
                    action_type=RuleActionType.TEXT_TRANSFORM,
                    target_refs=(target_ref,),
                    before=match.group(0),
                    after=replacement,
                    offset_start=match.start(),
                    offset_end=match.end(),
                )
            )

        if actions:
            return DeterministicResult(
                rule_id=RULE_ID,
                matched=True,
                target_refs=(target_ref,),
                proposed_actions=tuple(actions),
                conditions_met=(MATCH_CONDITION,),
                veto_reasons=(),
                justification=(
                    "Une espace de pagination à canoniser a été détectée."
                ),
            )
        return DeterministicResult(
            rule_id=RULE_ID,
            matched=False,
            target_refs=(target_ref,),
            proposed_actions=(),
            conditions_met=(),
            veto_reasons=(),
            justification=(
                "Aucune espace de pagination prise en charge n’a été détectée."
            ),
        )


def _validated_input(context: RuleContext) -> tuple[str, str]:
    if not isinstance(context, RuleContext):
        raise TypeError("context must be a RuleContext")
    if len(context.target_refs) != 1:
        raise ValueError("purh.pagination.espace requires exactly one target")
    target_ref = context.target_refs[0]
    if not isinstance(target_ref, str) or not target_ref.strip():
        raise ValueError("purh.pagination.espace requires a non-empty target")
    if PRE_RULE_TEXT_FACT not in context.source_facts:
        raise ValueError("source_facts must contain pre_rule_text")
    text = context.source_facts[PRE_RULE_TEXT_FACT]
    if not isinstance(text, str):
        raise TypeError("pre_rule_text must be a string")
    return target_ref, text
