from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from purh_editorial.model import Document, Transformation
from purh_editorial.rules.engine import CanonicalRuleDecisionEngine
from purh_editorial.rules.model import (
    CompatibilityContext,
    ProtectionDecision,
    ProposedAction,
    RuleActionType,
    RuleContext,
    RuleDecision,
)
from purh_editorial.rules.orthotypography.etc_rule import (
    PRE_RULE_TEXT_FACT,
    RULE_ID,
    EtcAbbreviationRule,
)
from purh_editorial.rules.shadow import (
    CanonicalShadowComparator,
    LegacyObservationStatus,
    LegacyRuleObservation,
    ShadowComparison,
)
from purh_editorial.rules.thresholds import CanonicalThresholdPolicy
from purh_editorial.services.orthotypo_service import OrthotypoService, TYPO_RULES
from purh_editorial.utils.protection import is_protected_block, is_protected_note


_COMPATIBILITY_FLAGS = ("legacy_orthotypo_shadow",)
_MAPPING_ERROR = "legacy_transformation_mapping_failed"


class OrthotypoEtcShadowError(ValueError):
    """Le parcours shadow ``etc.`` ne peut pas être construit sans ambiguïté."""


@dataclass(slots=True)
class OrthotypoEtcShadowResult:
    rule_id: str
    legacy_document: Document
    legacy_transformations: tuple[Transformation, ...]
    native_decisions: tuple[RuleDecision, ...]
    comparisons: tuple[ShadowComparison, ...]


@dataclass(frozen=True, slots=True)
class _ShadowTarget:
    target_ref: str
    text: str
    protection: ProtectionDecision


@dataclass(slots=True)
class OrthotypoEtcShadowAdapter:
    """Observe une seule verticale sans exécuter l'action native."""

    legacy_service: Any = field(default_factory=OrthotypoService)
    native_rule: Any = field(default_factory=EtcAbbreviationRule)
    engine: Any = field(
        default_factory=lambda: CanonicalRuleDecisionEngine(
            CanonicalThresholdPolicy()
        )
    )
    comparator: Any = field(default_factory=CanonicalShadowComparator)

    def run(self, document: Document) -> OrthotypoEtcShadowResult:
        if not isinstance(document, Document):
            raise TypeError("document must be a Document")
        if not isinstance(document.document_id, str) or not document.document_id.strip():
            raise OrthotypoEtcShadowError("document_id must be a non-empty string")

        targets = self._collect_targets(document)
        known_target_refs = {target.target_ref for target in targets}
        etc_rule_index = self._find_legacy_rule_index()

        legacy_document, legacy_transformations_raw = self.legacy_service.apply(
            document
        )
        legacy_transformations = tuple(legacy_transformations_raw)
        if any(
            not isinstance(item, Transformation)
            for item in legacy_transformations
        ):
            raise OrthotypoEtcShadowError(
                "legacy service returned a non-Transformation value"
            )

        etc_transformations = tuple(
            transformation
            for transformation in legacy_transformations
            if transformation.rule_id == RULE_ID
        )
        for transformation in etc_transformations:
            if transformation.target_ref not in known_target_refs:
                raise OrthotypoEtcShadowError(
                    "legacy etc. transformation targets an unknown source target: "
                    f"{transformation.target_ref!r}"
                )

        grouped: dict[str, list[Transformation]] = {
            target.target_ref: [] for target in targets
        }
        for transformation in etc_transformations:
            grouped[transformation.target_ref].append(transformation)

        decisions: list[RuleDecision] = []
        comparisons: list[ShadowComparison] = []
        for sequence, target in enumerate(targets):
            pre_rule_text = self._reconstruct_pre_rule_text(
                target.text,
                etc_rule_index=etc_rule_index,
            )
            context = RuleContext(
                document_id=document.document_id,
                target_refs=(target.target_ref,),
                source_facts={PRE_RULE_TEXT_FACT: pre_rule_text},
                canonical_facts={},
                protection=target.protection,
                compatibility=CompatibilityContext(
                    source_config_version=None,
                    flags=_COMPATIBILITY_FLAGS,
                ),
            )
            evaluation = self.native_rule.evaluate(context)
            decision = self.engine.decide(
                descriptor=self.native_rule.descriptor,
                evaluation=evaluation,
                protection=target.protection,
                decision_id=f"native:{RULE_ID}:{sequence}:{target.target_ref}",
                sequence=sequence,
                intervention_level=None,
                compatibility_flags=_COMPATIBILITY_FLAGS,
            )
            observation = self._build_observation(
                target_ref=target.target_ref,
                transformations=tuple(grouped[target.target_ref]),
                sequence=sequence,
            )
            comparison = self.comparator.compare(
                legacy=observation,
                native=decision,
                comparison_id=f"shadow:{RULE_ID}:{sequence}:{target.target_ref}",
                sequence=sequence,
            )
            decisions.append(decision)
            comparisons.append(comparison)

        return OrthotypoEtcShadowResult(
            rule_id=RULE_ID,
            legacy_document=legacy_document,
            legacy_transformations=legacy_transformations,
            native_decisions=tuple(decisions),
            comparisons=tuple(comparisons),
        )

    def _collect_targets(self, document: Document) -> tuple[_ShadowTarget, ...]:
        raw_refs = [
            *(block.block_id for block in document.blocks),
            *(note.note_id for note in document.notes),
        ]
        if any(not isinstance(ref, str) or not ref.strip() for ref in raw_refs):
            raise OrthotypoEtcShadowError(
                "all block and note target identifiers must be non-empty strings"
            )
        if len(set(raw_refs)) != len(raw_refs):
            raise OrthotypoEtcShadowError(
                "block and note target identifiers must be unique"
            )

        descriptor = self.native_rule.descriptor
        protected_target_refs = {
            block.block_id
            for block in document.blocks
            if is_protected_block(block)
        }
        targets: list[_ShadowTarget] = []
        for block in document.blocks:
            protected = is_protected_block(block)
            targets.append(
                _ShadowTarget(
                    target_ref=block.block_id,
                    text=self._target_text(block),
                    protection=ProtectionDecision(
                        protected=protected,
                        policy_id=descriptor.protection_policy_id,
                        reasons=(
                            ("legacy_protected_block",) if protected else ()
                        ),
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
                note.target_ref
                and note.target_ref in protected_target_refs
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
                _ShadowTarget(
                    target_ref=note.note_id,
                    text=self._target_text(note),
                    protection=ProtectionDecision(
                        protected=protected,
                        policy_id=descriptor.protection_policy_id,
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

    @staticmethod
    def _target_text(target: Any) -> str:
        inlines = target.inlines
        if inlines:
            return "".join(span.text for span in inlines)
        return target.text

    @staticmethod
    def _find_legacy_rule_index() -> int:
        matches = [
            index
            for index, rule in enumerate(TYPO_RULES)
            if rule.rule_id == RULE_ID
        ]
        if len(matches) != 1:
            raise OrthotypoEtcShadowError(
                f"{RULE_ID} must occur exactly once in TYPO_RULES"
            )
        index = matches[0]
        if not TYPO_RULES[index].auto:
            raise OrthotypoEtcShadowError(
                f"{RULE_ID} must remain auto=True in the legacy service"
            )
        return index

    @staticmethod
    def _reconstruct_pre_rule_text(
        source_text: str,
        *,
        etc_rule_index: int,
    ) -> str:
        text = source_text
        for rule in TYPO_RULES[:etc_rule_index]:
            if rule.auto:
                text = rule.apply(text)
        return text

    @staticmethod
    def _build_observation(
        *,
        target_ref: str,
        transformations: tuple[Transformation, ...],
        sequence: int,
    ) -> LegacyRuleObservation:
        actions: list[ProposedAction] = []
        mapping_failed = False
        for transformation in transformations:
            try:
                actions.append(
                    OrthotypoEtcShadowAdapter._convert_transformation(
                        transformation
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
        return LegacyRuleObservation(
            observation_id=f"legacy:{RULE_ID}:{sequence}:{target_ref}",
            rule_id=RULE_ID,
            target_refs=(target_ref,),
            observed_actions=tuple(actions),
            status=status,
            justification=(
                "Conversion exacte des transformations legacy de la règle etc."
                if not mapping_failed
                else "Une transformation legacy etc. n’a pas pu être convertie."
            ),
            error_code=_MAPPING_ERROR if mapping_failed else None,
        )

    @staticmethod
    def _convert_transformation(
        transformation: Transformation,
    ) -> ProposedAction:
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
