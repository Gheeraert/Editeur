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


RULE_ID = "purh.abreviations.etc"
PRE_RULE_TEXT_FACT = "pre_rule_text"
MATCH_CONDITION = "etc_redundant_ellipsis"
_ETC_PATTERN = re.compile(r"etc(?:…\.*|\.{2,})")


class EtcAbbreviationRule:
    """Évalue purement la normalisation legacy ``etc…``/``etc...``."""

    descriptor: RuleDescriptor = CANONICAL_RULE_REGISTRY.get(RULE_ID)

    def evaluate(self, context: RuleContext) -> DeterministicResult:
        if not isinstance(context, RuleContext):
            raise TypeError("context must be a RuleContext")
        if len(context.target_refs) != 1:
            raise ValueError("purh.abreviations.etc requires exactly one target")

        target_ref = context.target_refs[0]
        if not isinstance(target_ref, str) or not target_ref.strip():
            raise ValueError("purh.abreviations.etc requires a non-empty target")
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
                after="etc.",
                offset_start=match.start(),
                offset_end=match.end(),
            )
            for match in _ETC_PATTERN.finditer(text)
        )
        if actions:
            return DeterministicResult(
                rule_id=RULE_ID,
                matched=True,
                target_refs=(target_ref,),
                proposed_actions=actions,
                conditions_met=(MATCH_CONDITION,),
                veto_reasons=(),
                justification=(
                    "Une forme « etc. » suivie de points redondants a été détectée."
                ),
            )
        return DeterministicResult(
            rule_id=RULE_ID,
            matched=False,
            target_refs=(target_ref,),
            proposed_actions=(),
            conditions_met=(),
            veto_reasons=(),
            justification="Aucune forme « etc. » à normaliser n’a été détectée.",
        )
