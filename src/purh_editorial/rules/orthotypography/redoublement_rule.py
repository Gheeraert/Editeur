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


RULE_ID = "purh.abreviations.redoublement"
PRE_RULE_TEXT_FACT = "pre_rule_text"
MATCH_CONDITION = "abbreviation_reduplication_detected"
_REDOUBLEMENT_PATTERN = re.compile(r"\b(pp|vv|ll)\.|§§")


class RedoubledAbbreviationRule:
    """Évalue purement les abréviations françaises redoublées."""

    descriptor: RuleDescriptor = CANONICAL_RULE_REGISTRY.get(RULE_ID)

    def evaluate(self, context: RuleContext) -> DeterministicResult:
        if not isinstance(context, RuleContext):
            raise TypeError("context must be a RuleContext")
        if len(context.target_refs) != 1:
            raise ValueError(
                "purh.abreviations.redoublement requires exactly one target"
            )

        target_ref = context.target_refs[0]
        if not isinstance(target_ref, str) or not target_ref.strip():
            raise ValueError(
                "purh.abreviations.redoublement requires a non-empty target"
            )
        if PRE_RULE_TEXT_FACT not in context.source_facts:
            raise ValueError("source_facts must contain pre_rule_text")
        text = context.source_facts[PRE_RULE_TEXT_FACT]
        if not isinstance(text, str):
            raise TypeError("pre_rule_text must be a string")

        actions = tuple(
            ProposedAction(
                action_type=RuleActionType.TEXT_TRANSFORM,
                target_refs=(target_ref,),
                before=match.group(0),
                after=(
                    match.group(1)[0] + "."
                    if match.group(1)
                    else "§"
                ),
                offset_start=match.start(),
                offset_end=match.end(),
            )
            for match in _REDOUBLEMENT_PATTERN.finditer(text)
        )
        if actions:
            return DeterministicResult(
                rule_id=RULE_ID,
                matched=True,
                target_refs=(target_ref,),
                proposed_actions=actions,
                conditions_met=(MATCH_CONDITION,),
                veto_reasons=(),
                justification="Une abréviation française redoublée a été détectée.",
            )
        return DeterministicResult(
            rule_id=RULE_ID,
            matched=False,
            target_refs=(target_ref,),
            proposed_actions=(),
            conditions_met=(),
            veto_reasons=(),
            justification="Aucune abréviation française redoublée n’a été détectée.",
        )
