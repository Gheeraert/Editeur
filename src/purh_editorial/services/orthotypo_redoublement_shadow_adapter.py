from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from purh_editorial.model import Document, Transformation
from purh_editorial.rules.engine import CanonicalRuleDecisionEngine
from purh_editorial.rules.model import (
    CompatibilityContext,
    RuleContext,
    RuleDecision,
)
from purh_editorial.rules.orthotypography.redoublement_rule import (
    PRE_RULE_TEXT_FACT,
    RULE_ID,
    RedoubledAbbreviationRule,
)
from purh_editorial.rules.shadow import (
    CanonicalShadowComparator,
    ShadowComparison,
)
from purh_editorial.rules.thresholds import CanonicalThresholdPolicy
from purh_editorial.services.orthotypo_service import OrthotypoService
from purh_editorial.services.orthotypo_shadow_support import (
    build_legacy_text_observation,
    collect_orthotypo_shadow_targets,
    find_legacy_orthotypo_rule_index,
    reconstruct_pre_rule_text,
)


_COMPATIBILITY_FLAGS = ("legacy_orthotypo_shadow",)


class OrthotypoRedoublementShadowError(ValueError):
    """Le parcours shadow du redoublement ne peut pas être construit."""


@dataclass(slots=True)
class OrthotypoRedoublementShadowResult:
    rule_id: str
    legacy_document: Document
    legacy_transformations: tuple[Transformation, ...]
    native_decisions: tuple[RuleDecision, ...]
    comparisons: tuple[ShadowComparison, ...]


@dataclass(slots=True)
class OrthotypoRedoublementShadowAdapter:
    """Observe le redoublement sans exécuter l'action native."""

    legacy_service: Any = field(default_factory=OrthotypoService)
    native_rule: Any = field(default_factory=RedoubledAbbreviationRule)
    engine: Any = field(
        default_factory=lambda: CanonicalRuleDecisionEngine(
            CanonicalThresholdPolicy()
        )
    )
    comparator: Any = field(default_factory=CanonicalShadowComparator)

    def run(self, document: Document) -> OrthotypoRedoublementShadowResult:
        if not isinstance(document, Document):
            raise TypeError("document must be a Document")
        if (
            not isinstance(document.document_id, str)
            or not document.document_id.strip()
        ):
            raise OrthotypoRedoublementShadowError(
                "document_id must be a non-empty string"
            )

        try:
            targets = collect_orthotypo_shadow_targets(
                document,
                protection_policy_id=(
                    self.native_rule.descriptor.protection_policy_id
                ),
            )
            legacy_rule_index = find_legacy_orthotypo_rule_index(RULE_ID)
        except (TypeError, ValueError) as exc:
            raise OrthotypoRedoublementShadowError(str(exc)) from exc
        known_target_refs = {target.target_ref for target in targets}

        legacy_document, legacy_transformations_raw = self.legacy_service.apply(
            document
        )
        legacy_transformations = tuple(legacy_transformations_raw)
        if any(
            not isinstance(item, Transformation)
            for item in legacy_transformations
        ):
            raise OrthotypoRedoublementShadowError(
                "legacy service returned a non-Transformation value"
            )

        filtered_transformations = tuple(
            transformation
            for transformation in legacy_transformations
            if transformation.rule_id == RULE_ID
        )
        for transformation in filtered_transformations:
            if transformation.target_ref not in known_target_refs:
                raise OrthotypoRedoublementShadowError(
                    "legacy redoublement transformation targets an unknown "
                    f"source target: {transformation.target_ref!r}"
                )

        grouped: dict[str, list[Transformation]] = {
            target.target_ref: [] for target in targets
        }
        for transformation in filtered_transformations:
            grouped[transformation.target_ref].append(transformation)

        decisions: list[RuleDecision] = []
        comparisons: list[ShadowComparison] = []
        for sequence, target in enumerate(targets):
            pre_rule_text = reconstruct_pre_rule_text(
                target.text,
                rule_index=legacy_rule_index,
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
            observation = build_legacy_text_observation(
                rule_id=RULE_ID,
                target_ref=target.target_ref,
                transformations=tuple(grouped[target.target_ref]),
                sequence=sequence,
                observation_id=(
                    f"legacy:{RULE_ID}:{sequence}:{target.target_ref}"
                ),
                success_justification=(
                    "Conversion exacte des transformations legacy de "
                    "redoublement."
                ),
                failure_justification=(
                    "Une transformation legacy de redoublement n’a pas pu "
                    "être convertie."
                ),
            )
            comparison = self.comparator.compare(
                legacy=observation,
                native=decision,
                comparison_id=f"shadow:{RULE_ID}:{sequence}:{target.target_ref}",
                sequence=sequence,
            )
            decisions.append(decision)
            comparisons.append(comparison)

        return OrthotypoRedoublementShadowResult(
            rule_id=RULE_ID,
            legacy_document=legacy_document,
            legacy_transformations=legacy_transformations,
            native_decisions=tuple(decisions),
            comparisons=tuple(comparisons),
        )
