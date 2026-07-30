from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from purh_editorial.model import Document, Transformation
from purh_editorial.rules.model import (
    ProtectionDecision,
    ProposedAction,
    RuleActionType,
)
from purh_editorial.rules.shadow import (
    LegacyObservationStatus,
    LegacyRuleObservation,
)
from purh_editorial.services.orthotypo_service import TYPO_RULES, TypoRule
from purh_editorial.utils.protection import is_protected_block, is_protected_note


LEGACY_TRANSFORMATION_MAPPING_ERROR = "legacy_transformation_mapping_failed"


@dataclass(frozen=True, slots=True)
class OrthotypoShadowTarget:
    target_ref: str
    text: str
    protection: ProtectionDecision


def collect_orthotypo_shadow_targets(
    document: Document,
    *,
    protection_policy_id: str,
) -> tuple[OrthotypoShadowTarget, ...]:
    """Collecte les cibles exactement dans l'ordre traité par le service legacy."""
    if not isinstance(document, Document):
        raise TypeError("document must be a Document")
    if not isinstance(protection_policy_id, str) or not protection_policy_id.strip():
        raise ValueError("protection_policy_id must be a non-empty string")

    raw_refs = [
        *(block.block_id for block in document.blocks),
        *(note.note_id for note in document.notes),
    ]
    if any(not isinstance(ref, str) or not ref.strip() for ref in raw_refs):
        raise ValueError(
            "all block and note target identifiers must be non-empty strings"
        )
    if len(set(raw_refs)) != len(raw_refs):
        raise ValueError("block and note target identifiers must be unique")

    protected_target_refs = {
        block.block_id
        for block in document.blocks
        if is_protected_block(block)
    }
    targets: list[OrthotypoShadowTarget] = []
    for block in document.blocks:
        protected = is_protected_block(block)
        targets.append(
            OrthotypoShadowTarget(
                target_ref=block.block_id,
                text=_target_text(block),
                protection=ProtectionDecision(
                    protected=protected,
                    policy_id=protection_policy_id,
                    reasons=("legacy_protected_block",) if protected else (),
                    legacy_behavior=True,
                ),
            )
        )
    for note in document.notes:
        explicitly_protected = is_protected_note(
            note,
            protected_target_refs=set(),
        )
        inherited = bool(
            note.target_ref and note.target_ref in protected_target_refs
        )
        protected = is_protected_note(
            note,
            protected_target_refs=protected_target_refs,
        )
        reasons: list[str] = []
        if explicitly_protected:
            reasons.append("legacy_protected_note")
        if inherited:
            reasons.append("legacy_protected_note_inherited")
        targets.append(
            OrthotypoShadowTarget(
                target_ref=note.note_id,
                text=_target_text(note),
                protection=ProtectionDecision(
                    protected=protected,
                    policy_id=protection_policy_id,
                    reasons=tuple(reasons),
                    inherited_from=(
                        (note.target_ref,)
                        if inherited and note.target_ref
                        else ()
                    ),
                    legacy_behavior=True,
                ),
            )
        )
    return tuple(targets)


def find_legacy_orthotypo_rule_index(
    rule_id: str,
    *,
    rules: Sequence[TypoRule] = TYPO_RULES,
) -> int:
    if not isinstance(rule_id, str) or not rule_id.strip():
        raise ValueError("rule_id must be a non-empty string")
    matches = [
        index for index, rule in enumerate(rules) if rule.rule_id == rule_id
    ]
    if len(matches) != 1:
        raise ValueError(f"{rule_id} must occur exactly once in TYPO_RULES")
    index = matches[0]
    if not rules[index].auto:
        raise ValueError(f"{rule_id} must remain auto=True in the legacy service")
    return index


def reconstruct_pre_rule_text(
    source_text: str,
    *,
    rule_index: int,
    rules: Sequence[TypoRule] = TYPO_RULES,
) -> str:
    if not isinstance(source_text, str):
        raise TypeError("source_text must be a string")
    if (
        isinstance(rule_index, bool)
        or not isinstance(rule_index, int)
        or rule_index < 0
        or rule_index >= len(rules)
    ):
        raise ValueError("rule_index must identify a rule in rules")
    text = source_text
    for rule in rules[:rule_index]:
        if rule.auto:
            text = rule.apply(text)
    return text


def convert_legacy_text_transformation(
    transformation: Transformation,
    *,
    expected_rule_id: str,
) -> ProposedAction:
    if not isinstance(transformation, Transformation):
        raise TypeError("transformation must be a Transformation")
    if not isinstance(expected_rule_id, str) or not expected_rule_id.strip():
        raise ValueError("expected_rule_id must be a non-empty string")
    if transformation.rule_id != expected_rule_id:
        raise ValueError("legacy transformation rule_id does not match")
    if transformation.applied is not True:
        raise ValueError("legacy transformation must be applied")
    if transformation.operation != "orthotypo":
        raise ValueError("legacy transformation operation must be orthotypo")
    if (
        not isinstance(transformation.target_ref, str)
        or not transformation.target_ref.strip()
    ):
        raise ValueError("legacy transformation target_ref must be non-empty")
    if not isinstance(transformation.before, str):
        raise TypeError("legacy transformation before must be a string")
    if not isinstance(transformation.after, str):
        raise TypeError("legacy transformation after must be a string")

    attributes = transformation.attributes
    offset_start = attributes["offset_start"]
    offset_end = attributes["offset_end"]
    if (
        isinstance(offset_start, bool)
        or not isinstance(offset_start, int)
        or isinstance(offset_end, bool)
        or not isinstance(offset_end, int)
    ):
        raise TypeError("legacy offsets must be integers")
    if offset_start < 0 or offset_end < offset_start:
        raise ValueError("legacy offsets are invalid")
    if attributes.get("coordinate_space") != "pre_rule_text":
        raise ValueError("legacy coordinate_space must be pre_rule_text")

    return ProposedAction(
        action_type=RuleActionType.TEXT_TRANSFORM,
        target_refs=(transformation.target_ref,),
        before=transformation.before,
        after=transformation.after,
        offset_start=offset_start,
        offset_end=offset_end,
    )


def build_legacy_text_observation(
    *,
    rule_id: str,
    target_ref: str,
    transformations: tuple[Transformation, ...],
    sequence: int,
    observation_id: str,
    success_justification: str | None = None,
    failure_justification: str | None = None,
) -> LegacyRuleObservation:
    if not isinstance(transformations, tuple):
        raise TypeError("transformations must be a tuple")
    if (
        isinstance(sequence, bool)
        or not isinstance(sequence, int)
        or sequence < 0
    ):
        raise ValueError("sequence must be a non-negative integer")
    actions: list[ProposedAction] = []
    mapping_failed = False
    for transformation in transformations:
        try:
            actions.append(
                convert_legacy_text_transformation(
                    transformation,
                    expected_rule_id=rule_id,
                )
            )
        except (TypeError, ValueError, KeyError):
            mapping_failed = True
            break

    status = (
        LegacyObservationStatus.FAILED
        if mapping_failed
        else LegacyObservationStatus.COMPLETE
    )
    if mapping_failed:
        justification = failure_justification or (
            f"Une transformation legacy {rule_id} n'a pas pu être convertie."
        )
    else:
        justification = success_justification or (
            f"Conversion exacte des transformations legacy de {rule_id}."
        )
    return LegacyRuleObservation(
        observation_id=observation_id,
        rule_id=rule_id,
        target_refs=(target_ref,),
        observed_actions=tuple(actions),
        status=status,
        justification=justification,
        error_code=(
            LEGACY_TRANSFORMATION_MAPPING_ERROR if mapping_failed else None
        ),
    )


def _target_text(target: Any) -> str:
    if target.inlines:
        return "".join(span.text for span in target.inlines)
    return target.text
