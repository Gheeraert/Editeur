from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from purh_editorial.model import Document, Transformation
from purh_editorial.rules.engine import CanonicalRuleDecisionEngine
from purh_editorial.rules.model import (
    CompatibilityContext,
    RuleContext,
    RuleDecision,
)
from purh_editorial.rules.orthotypography.etc_rule import (
    PRE_RULE_TEXT_FACT as ETC_PRE_RULE_TEXT_FACT,
    RULE_ID as ETC_RULE_ID,
    EtcAbbreviationRule,
)
from purh_editorial.rules.orthotypography.century_rule import (
    PRE_RULE_TEXT_FACT as CENTURY_PRE_RULE_TEXT_FACT,
    RULE_ID as CENTURY_RULE_ID,
    CenturyAbbreviationRule,
)
from purh_editorial.rules.orthotypography.numero_rule import (
    PRE_RULE_TEXT_FACT as NUMERO_PRE_RULE_TEXT_FACT,
    RULE_ID as NUMERO_RULE_ID,
    NumeroAbbreviationRule,
)
from purh_editorial.rules.orthotypography.ordinal_rule import (
    PRE_RULE_TEXT_FACT as ORDINAL_PRE_RULE_TEXT_FACT,
    RULE_ID as ORDINAL_RULE_ID,
    OrdinalAbbreviationRule,
)
from purh_editorial.rules.orthotypography.pagination_spacing_rule import (
    PRE_RULE_TEXT_FACT as PAGINATION_PRE_RULE_TEXT_FACT,
    RULE_ID as PAGINATION_RULE_ID,
    PaginationSpacingRule,
)
from purh_editorial.rules.orthotypography.redoublement_rule import (
    PRE_RULE_TEXT_FACT as REDOUBLEMENT_PRE_RULE_TEXT_FACT,
    RULE_ID as REDOUBLEMENT_RULE_ID,
    RedoubledAbbreviationRule,
)
from purh_editorial.rules.shadow import (
    CanonicalShadowComparator,
    ShadowComparison,
)
from purh_editorial.rules.thresholds import CanonicalThresholdPolicy
from purh_editorial.services.orthotypo_service import OrthotypoService
from purh_editorial.services.orthotypo_shadow_support import (
    OrthotypoShadowTarget,
    build_legacy_text_observation,
    collect_orthotypo_shadow_targets,
    find_legacy_orthotypo_rule_index,
    reconstruct_pre_rule_text,
)


_COMPATIBILITY_FLAGS = ("legacy_orthotypo_shadow",)


class OrthotypoShadowBatchError(ValueError):
    """Le batch shadow pilote ne peut pas être construit sans ambiguïté."""


@dataclass(frozen=True, slots=True)
class OrthotypoShadowRuleResult:
    rule_id: str
    targets: tuple[OrthotypoShadowTarget, ...]
    native_decisions: tuple[RuleDecision, ...]
    comparisons: tuple[ShadowComparison, ...]


@dataclass(slots=True)
class OrthotypoShadowBatchResult:
    legacy_document: Document
    legacy_transformations: tuple[Transformation, ...]
    rule_results: tuple[OrthotypoShadowRuleResult, ...]

    def for_rule(self, rule_id: str) -> OrthotypoShadowRuleResult:
        for result in self.rule_results:
            if result.rule_id == rule_id:
                return result
        raise KeyError(f"unknown orthotypography shadow pilot rule: {rule_id!r}")


@dataclass(frozen=True, slots=True)
class _OrthotypoShadowRuleSpec:
    rule_id: str
    native_rule: Any
    pre_rule_text_fact: str
    success_justification: str
    failure_justification: str


# Ordre explicite des six transformations textuelles actives dans le legacy.
_PILOT_RULE_SPECS = (
    _OrthotypoShadowRuleSpec(
        rule_id=CENTURY_RULE_ID,
        native_rule=CenturyAbbreviationRule(),
        pre_rule_text_fact=CENTURY_PRE_RULE_TEXT_FACT,
        success_justification=(
            "Conversion exacte des transformations legacy de siècles."
        ),
        failure_justification=(
            "Une transformation legacy de siècles n’a pas pu être convertie."
        ),
    ),
    _OrthotypoShadowRuleSpec(
        rule_id=ORDINAL_RULE_ID,
        native_rule=OrdinalAbbreviationRule(),
        pre_rule_text_fact=ORDINAL_PRE_RULE_TEXT_FACT,
        success_justification=(
            "Conversion exacte des transformations legacy d’ordinaux."
        ),
        failure_justification=(
            "Une transformation legacy d’ordinaux n’a pas pu être convertie."
        ),
    ),
    _OrthotypoShadowRuleSpec(
        rule_id=ETC_RULE_ID,
        native_rule=EtcAbbreviationRule(),
        pre_rule_text_fact=ETC_PRE_RULE_TEXT_FACT,
        success_justification=(
            "Conversion exacte des transformations legacy de la règle etc."
        ),
        failure_justification=(
            "Une transformation legacy etc. n’a pas pu être convertie."
        ),
    ),
    _OrthotypoShadowRuleSpec(
        rule_id=PAGINATION_RULE_ID,
        native_rule=PaginationSpacingRule(),
        pre_rule_text_fact=PAGINATION_PRE_RULE_TEXT_FACT,
        success_justification=(
            "Conversion exacte des transformations legacy de pagination."
        ),
        failure_justification=(
            "Une transformation legacy de pagination n’a pas pu être convertie."
        ),
    ),
    _OrthotypoShadowRuleSpec(
        rule_id=NUMERO_RULE_ID,
        native_rule=NumeroAbbreviationRule(),
        pre_rule_text_fact=NUMERO_PRE_RULE_TEXT_FACT,
        success_justification=(
            "Conversion exacte des transformations legacy de numéro."
        ),
        failure_justification=(
            "Une transformation legacy de numéro n’a pas pu être convertie."
        ),
    ),
    _OrthotypoShadowRuleSpec(
        rule_id=REDOUBLEMENT_RULE_ID,
        native_rule=RedoubledAbbreviationRule(),
        pre_rule_text_fact=REDOUBLEMENT_PRE_RULE_TEXT_FACT,
        success_justification=(
            "Conversion exacte des transformations legacy de redoublement."
        ),
        failure_justification=(
            "Une transformation legacy de redoublement n’a pas pu être "
            "convertie."
        ),
    ),
)


@dataclass(slots=True)
class OrthotypoShadowBatchRunner:
    """Observe les six règles textuelles actives avec une exécution legacy."""

    legacy_service: Any = field(default_factory=OrthotypoService)
    engine: Any = field(
        default_factory=lambda: CanonicalRuleDecisionEngine(
            CanonicalThresholdPolicy()
        )
    )
    comparator: Any = field(default_factory=CanonicalShadowComparator)

    def run(self, document: Document) -> OrthotypoShadowBatchResult:
        if not isinstance(document, Document):
            raise TypeError("document must be a Document")
        if (
            not isinstance(document.document_id, str)
            or not document.document_id.strip()
        ):
            raise OrthotypoShadowBatchError(
                "document_id must be a non-empty string"
            )

        source_snapshot = copy.deepcopy(document)
        try:
            indexed_specs = tuple(
                (find_legacy_orthotypo_rule_index(spec.rule_id), spec)
                for spec in _PILOT_RULE_SPECS
            )
            indexes = tuple(index for index, _spec in indexed_specs)
            if indexes != tuple(sorted(indexes)) or len(set(indexes)) != len(indexes):
                raise OrthotypoShadowBatchError(
                    "pilot rules must be declared in their strict legacy order"
                )
            targets_by_policy = self._collect_targets_by_policy(document)
        except (TypeError, ValueError) as exc:
            if isinstance(exc, OrthotypoShadowBatchError):
                raise
            raise OrthotypoShadowBatchError(str(exc)) from exc

        legacy_document, legacy_transformations_raw = self.legacy_service.apply(
            document
        )
        if document != source_snapshot:
            raise OrthotypoShadowBatchError(
                "legacy service mutated the source document"
            )
        legacy_transformations = tuple(legacy_transformations_raw)
        if any(
            not isinstance(item, Transformation)
            for item in legacy_transformations
        ):
            raise OrthotypoShadowBatchError(
                "legacy service returned a non-Transformation value"
            )

        rule_results = tuple(
            self._evaluate_rule(
                document=document,
                legacy_transformations=legacy_transformations,
                rule_index=rule_index,
                spec=spec,
                targets=targets_by_policy[
                    spec.native_rule.descriptor.protection_policy_id
                ],
            )
            for rule_index, spec in indexed_specs
        )
        return OrthotypoShadowBatchResult(
            legacy_document=legacy_document,
            legacy_transformations=legacy_transformations,
            rule_results=rule_results,
        )

    @staticmethod
    def _collect_targets_by_policy(
        document: Document,
    ) -> dict[str, tuple[OrthotypoShadowTarget, ...]]:
        targets_by_policy: dict[str, tuple[OrthotypoShadowTarget, ...]] = {}
        for spec in _PILOT_RULE_SPECS:
            policy_id = spec.native_rule.descriptor.protection_policy_id
            if policy_id not in targets_by_policy:
                targets_by_policy[policy_id] = collect_orthotypo_shadow_targets(
                    document,
                    protection_policy_id=policy_id,
                )
        return targets_by_policy

    def _evaluate_rule(
        self,
        *,
        document: Document,
        legacy_transformations: tuple[Transformation, ...],
        rule_index: int,
        spec: _OrthotypoShadowRuleSpec,
        targets: tuple[OrthotypoShadowTarget, ...],
    ) -> OrthotypoShadowRuleResult:
        known_target_refs = {target.target_ref for target in targets}
        transformations = tuple(
            transformation
            for transformation in legacy_transformations
            if transformation.rule_id == spec.rule_id
        )
        for transformation in transformations:
            if transformation.target_ref not in known_target_refs:
                raise OrthotypoShadowBatchError(
                    f"legacy {spec.rule_id} transformation targets an unknown "
                    f"source target: {transformation.target_ref!r}"
                )
        grouped: dict[str, list[Transformation]] = {
            target.target_ref: [] for target in targets
        }
        for transformation in transformations:
            grouped[transformation.target_ref].append(transformation)

        decisions: list[RuleDecision] = []
        comparisons: list[ShadowComparison] = []
        for sequence, target in enumerate(targets):
            pre_rule_text = reconstruct_pre_rule_text(
                target.text,
                rule_index=rule_index,
            )
            context = RuleContext(
                document_id=document.document_id,
                target_refs=(target.target_ref,),
                source_facts={spec.pre_rule_text_fact: pre_rule_text},
                canonical_facts={},
                protection=target.protection,
                compatibility=CompatibilityContext(
                    source_config_version=None,
                    flags=_COMPATIBILITY_FLAGS,
                ),
            )
            evaluation = spec.native_rule.evaluate(context)
            decision = self.engine.decide(
                descriptor=spec.native_rule.descriptor,
                evaluation=evaluation,
                protection=target.protection,
                decision_id=(
                    f"native:{spec.rule_id}:{sequence}:{target.target_ref}"
                ),
                sequence=sequence,
                intervention_level=None,
                compatibility_flags=_COMPATIBILITY_FLAGS,
            )
            observation = build_legacy_text_observation(
                rule_id=spec.rule_id,
                target_ref=target.target_ref,
                transformations=tuple(grouped[target.target_ref]),
                sequence=sequence,
                observation_id=(
                    f"legacy:{spec.rule_id}:{sequence}:{target.target_ref}"
                ),
                success_justification=spec.success_justification,
                failure_justification=spec.failure_justification,
            )
            comparison = self.comparator.compare(
                legacy=observation,
                native=decision,
                comparison_id=(
                    f"shadow:{spec.rule_id}:{sequence}:{target.target_ref}"
                ),
                sequence=sequence,
            )
            decisions.append(decision)
            comparisons.append(comparison)
        return OrthotypoShadowRuleResult(
            rule_id=spec.rule_id,
            targets=targets,
            native_decisions=tuple(decisions),
            comparisons=tuple(comparisons),
        )
