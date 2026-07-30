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


RULE_ID = "purh.ordinaux"
PRE_RULE_TEXT_FACT = "pre_rule_text"
MATCH_CONDITION = "ordinal_abbreviation_detected"
_ORDINAL_PATTERN = re.compile(r"\b(\d+)(ère|ere|ème|eme)\b")


class OrdinalAbbreviationRule:
    """Évalue purement les ordinaux simples pris en charge par le legacy."""

    descriptor: RuleDescriptor = CANONICAL_RULE_REGISTRY.get(RULE_ID)

    def evaluate(self, context: RuleContext) -> DeterministicResult:
        if not isinstance(context, RuleContext):
            raise TypeError("context must be a RuleContext")
        if len(context.target_refs) != 1:
            raise ValueError("purh.ordinaux requires exactly one target")

        target_ref = context.target_refs[0]
        if not isinstance(target_ref, str) or not target_ref.strip():
            raise ValueError("purh.ordinaux requires a non-empty target")
        if PRE_RULE_TEXT_FACT not in context.source_facts:
            raise ValueError("source_facts must contain pre_rule_text")
        text = context.source_facts[PRE_RULE_TEXT_FACT]
        if not isinstance(text, str):
            raise TypeError("pre_rule_text must be a string")

        actions: list[ProposedAction] = []
        for match in _ORDINAL_PATTERN.finditer(text):
            replacement = _replacement(match)
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
                justification="Un ordinal simple à abréger a été détecté.",
            )
        return DeterministicResult(
            rule_id=RULE_ID,
            matched=False,
            target_refs=(target_ref,),
            proposed_actions=(),
            conditions_met=(),
            veto_reasons=(),
            justification="Aucun ordinal simple pris en charge n’a été détecté.",
        )


def _replacement(match: re.Match[str]) -> str:
    number = match.group(1)
    suffix = match.group(2).lower()
    if suffix in {"ère", "ere"} and number == "1":
        return "1re"
    if suffix in {"ème", "eme"}:
        return f"{number}e"
    return match.group(0)
