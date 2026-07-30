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


RULE_ID = "purh.siecles"
PRE_RULE_TEXT_FACT = "pre_rule_text"
MATCH_CONDITION = "century_abbreviation_detected"
_CENTURY_PATTERN = re.compile(
    r"\b([IVXLCDMivxlcdm]{1,8})[eè][rm]?[eé]?\b",
    re.UNICODE,
)
_VALID_CENTURIES = frozenset(
    {
        "i",
        "ii",
        "iii",
        "iv",
        "v",
        "vi",
        "vii",
        "viii",
        "ix",
        "x",
        "xi",
        "xii",
        "xiii",
        "xiv",
        "xv",
        "xvi",
        "xvii",
        "xviii",
        "xix",
        "xx",
        "xxi",
        "xxii",
        "xxiii",
    }
)
_CENTURY_CONTEXT_RE = re.compile(
    r"^\s*(si[eè]cles?|s\.)\b",
    re.IGNORECASE | re.UNICODE,
)
_CENTURY_ENUM_CONNECTOR_RE = re.compile(
    r"^(?:[,\-]\s*|\s*(?:et|ou|au|à)\s+)"
    r"([IVXLCDMivxlcdm]{1,8}[eè][rm]?[eé]?)\b",
    re.IGNORECASE | re.UNICODE,
)


class CenturyAbbreviationRule:
    """Évalue purement la transformation textuelle legacy des siècles."""

    descriptor: RuleDescriptor = CANONICAL_RULE_REGISTRY.get(RULE_ID)

    def evaluate(self, context: RuleContext) -> DeterministicResult:
        target_ref, text = _validated_input(context)
        actions: list[ProposedAction] = []
        for match in _CENTURY_PATTERN.finditer(text):
            roman = match.group(1)
            if roman.lower() not in _VALID_CENTURIES:
                continue
            lookahead = text[match.end() : match.end() + 64]
            if not _has_century_context(lookahead):
                continue
            replacement = "Ier" if roman.lower() == "i" else roman.upper() + "e"
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
                    "Une forme textuelle de siècle à canoniser a été détectée."
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
                "Aucune forme textuelle de siècle prise en charge n’a été détectée."
            ),
        )


def _validated_input(context: RuleContext) -> tuple[str, str]:
    if not isinstance(context, RuleContext):
        raise TypeError("context must be a RuleContext")
    if len(context.target_refs) != 1:
        raise ValueError("purh.siecles requires exactly one target")
    target_ref = context.target_refs[0]
    if not isinstance(target_ref, str) or not target_ref.strip():
        raise ValueError("purh.siecles requires a non-empty target")
    if PRE_RULE_TEXT_FACT not in context.source_facts:
        raise ValueError("source_facts must contain pre_rule_text")
    text = context.source_facts[PRE_RULE_TEXT_FACT]
    if not isinstance(text, str):
        raise TypeError("pre_rule_text must be a string")
    return target_ref, text


def _has_century_context(lookahead: str) -> bool:
    remaining = lookahead
    for _ in range(6):
        if _CENTURY_CONTEXT_RE.match(remaining):
            return True
        connector = _CENTURY_ENUM_CONNECTOR_RE.match(remaining)
        if connector is None:
            return False
        remaining = remaining[connector.end() :]
    return False
