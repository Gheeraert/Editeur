from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from purh_editorial.rules.model import (
    DecisionOutcome,
    DeploymentStatus,
    DeterministicResult,
    HeuristicProposal,
    ProtectionDecision,
    RuleDecision,
    RuleDescriptor,
    RuleActionType,
    RuleNature,
)
from purh_editorial.rules.protocols import ThresholdPolicy


class RuleDecisionError(ValueError):
    """Une évaluation ne respecte pas le contrat du moteur natif."""


class DecisionReason(str, Enum):
    RULE_DISABLED = "rule_disabled"
    TARGET_PROTECTED = "target_protected"
    RULE_VETO = "rule_veto"
    NO_MATCH = "no_match"
    EXPLICIT_ABSTENTION = "explicit_abstention"
    DETERMINISTIC_ACTIVE = "deterministic_active"
    DETERMINISTIC_REVIEW_ONLY = "deterministic_review_only"
    HEURISTIC_APPLY_THRESHOLD = "heuristic_apply_threshold"
    HEURISTIC_REVIEW_BAND = "heuristic_review_band"
    HEURISTIC_BELOW_REVIEW = "heuristic_below_review_threshold"
    HEURISTIC_REVIEW_ONLY_REACHED = "heuristic_review_only_reached"
    HEURISTIC_REVIEW_ONLY_BELOW = "heuristic_review_only_below_threshold"


@dataclass(frozen=True, slots=True)
class CanonicalRuleDecisionEngine:
    """Produit une décision traçable sans exécuter l'action proposée.

    Une future intégration devra ordonner les décisions PIPELINE_CONTROL avant
    les actions éditoriales ordinaires. Le présent moteur ne les exécute pas.
    """

    threshold_policy: ThresholdPolicy

    def decide(
        self,
        *,
        descriptor: RuleDescriptor,
        evaluation: DeterministicResult | HeuristicProposal,
        protection: ProtectionDecision,
        decision_id: str,
        sequence: int,
        intervention_level: int | None = None,
        compatibility_flags: tuple[str, ...] = (),
    ) -> RuleDecision:
        self._validate_inputs(
            descriptor=descriptor,
            evaluation=evaluation,
            protection=protection,
            decision_id=decision_id,
            sequence=sequence,
            compatibility_flags=compatibility_flags,
        )

        if descriptor.deployment_status is DeploymentStatus.DISABLED:
            return self._build_decision(
                descriptor=descriptor,
                evaluation=evaluation,
                protection=protection,
                decision_id=decision_id,
                sequence=sequence,
                compatibility_flags=compatibility_flags,
                outcome=DecisionOutcome.IGNORE,
                reason=DecisionReason.RULE_DISABLED,
            )
        if protection.protected:
            return self._build_decision(
                descriptor=descriptor,
                evaluation=evaluation,
                protection=protection,
                decision_id=decision_id,
                sequence=sequence,
                compatibility_flags=compatibility_flags,
                outcome=DecisionOutcome.IGNORE,
                reason=DecisionReason.TARGET_PROTECTED,
            )
        if evaluation.veto_reasons:
            return self._build_decision(
                descriptor=descriptor,
                evaluation=evaluation,
                protection=protection,
                decision_id=decision_id,
                sequence=sequence,
                compatibility_flags=compatibility_flags,
                outcome=DecisionOutcome.IGNORE,
                reason=DecisionReason.RULE_VETO,
            )

        if isinstance(evaluation, DeterministicResult):
            if not evaluation.matched:
                return self._build_decision(
                    descriptor=descriptor,
                    evaluation=evaluation,
                    protection=protection,
                    decision_id=decision_id,
                    sequence=sequence,
                    compatibility_flags=compatibility_flags,
                    outcome=DecisionOutcome.IGNORE,
                    reason=DecisionReason.NO_MATCH,
                )
            if not evaluation.proposed_actions:
                return self._build_decision(
                    descriptor=descriptor,
                    evaluation=evaluation,
                    protection=protection,
                    decision_id=decision_id,
                    sequence=sequence,
                    compatibility_flags=compatibility_flags,
                    outcome=DecisionOutcome.IGNORE,
                    reason=DecisionReason.EXPLICIT_ABSTENTION,
                )
            self._require_primary_action(descriptor, evaluation)
            if descriptor.deployment_status is DeploymentStatus.REVIEW_ONLY:
                outcome = DecisionOutcome.REVIEW
                reason = DecisionReason.DETERMINISTIC_REVIEW_ONLY
            else:
                outcome = DecisionOutcome.APPLY
                reason = DecisionReason.DETERMINISTIC_ACTIVE
            return self._build_decision(
                descriptor=descriptor,
                evaluation=evaluation,
                protection=protection,
                decision_id=decision_id,
                sequence=sequence,
                compatibility_flags=compatibility_flags,
                outcome=outcome,
                reason=reason,
            )

        score_family = descriptor.score_family
        if not score_family:
            raise RuleDecisionError(
                f"heuristic rule {descriptor.rule_id!r} has no native score family"
            )
        if evaluation.score_family != score_family:
            raise RuleDecisionError(
                "heuristic score family differs from the rule descriptor"
            )
        if intervention_level is None:
            raise RuleDecisionError(
                "intervention_level is required for a native heuristic decision"
            )
        self._require_primary_action(descriptor, evaluation)

        thresholds = self.threshold_policy.thresholds(
            score_family=score_family,
            intervention_level=intervention_level,
        )
        if descriptor.deployment_status is DeploymentStatus.REVIEW_ONLY:
            if evaluation.score >= thresholds.review:
                outcome = DecisionOutcome.REVIEW
                reason = DecisionReason.HEURISTIC_REVIEW_ONLY_REACHED
            else:
                outcome = DecisionOutcome.IGNORE
                reason = DecisionReason.HEURISTIC_REVIEW_ONLY_BELOW
        elif evaluation.score >= thresholds.apply:
            outcome = DecisionOutcome.APPLY
            reason = DecisionReason.HEURISTIC_APPLY_THRESHOLD
        elif evaluation.score >= thresholds.review:
            outcome = DecisionOutcome.REVIEW
            reason = DecisionReason.HEURISTIC_REVIEW_BAND
        else:
            outcome = DecisionOutcome.IGNORE
            reason = DecisionReason.HEURISTIC_BELOW_REVIEW

        return self._build_decision(
            descriptor=descriptor,
            evaluation=evaluation,
            protection=protection,
            decision_id=decision_id,
            sequence=sequence,
            compatibility_flags=compatibility_flags,
            outcome=outcome,
            reason=reason,
            review_threshold=thresholds.review,
            apply_threshold=thresholds.apply,
        )

    @staticmethod
    def _validate_inputs(
        *,
        descriptor: RuleDescriptor,
        evaluation: DeterministicResult | HeuristicProposal,
        protection: ProtectionDecision,
        decision_id: str,
        sequence: int,
        compatibility_flags: tuple[str, ...],
    ) -> None:
        if not isinstance(descriptor, RuleDescriptor):
            raise TypeError("descriptor must be a RuleDescriptor")
        if not isinstance(protection, ProtectionDecision):
            raise TypeError("protection must be a ProtectionDecision")
        if not isinstance(decision_id, str) or not decision_id.strip():
            raise RuleDecisionError("decision_id must be a non-empty string")
        if (
            isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence < 0
        ):
            raise RuleDecisionError("sequence must be a non-negative integer")
        if not isinstance(compatibility_flags, tuple):
            raise TypeError("compatibility_flags must be a tuple")
        if any(not isinstance(flag, str) for flag in compatibility_flags):
            raise TypeError("compatibility_flags must contain strings")
        if not isinstance(evaluation, (DeterministicResult, HeuristicProposal)):
            raise TypeError(
                "evaluation must be a DeterministicResult or HeuristicProposal"
            )
        if evaluation.rule_id != descriptor.rule_id:
            raise RuleDecisionError(
                "evaluation rule_id differs from the rule descriptor"
            )
        if descriptor.nature is RuleNature.DETERMINISTIC and not isinstance(
            evaluation, DeterministicResult
        ):
            raise RuleDecisionError(
                "a deterministic descriptor requires DeterministicResult"
            )
        if descriptor.nature is RuleNature.HEURISTIC and not isinstance(
            evaluation, HeuristicProposal
        ):
            raise RuleDecisionError(
                "a heuristic descriptor requires HeuristicProposal"
            )
        if not evaluation.target_refs:
            raise RuleDecisionError("evaluation requires at least one target")
        evaluated_targets = set(evaluation.target_refs)
        for action in evaluation.proposed_actions:
            if action.action_type not in {
                descriptor.action_type,
                RuleActionType.DIAGNOSTIC,
            }:
                raise RuleDecisionError(
                    "proposed action type is not the declared main type or a diagnostic"
                )
            if not set(action.target_refs).issubset(evaluated_targets):
                raise RuleDecisionError(
                    "proposed action targets must belong to evaluation targets"
                )

    @staticmethod
    def _require_primary_action(
        descriptor: RuleDescriptor,
        evaluation: DeterministicResult | HeuristicProposal,
    ) -> None:
        if not any(
            action.action_type is descriptor.action_type
            for action in evaluation.proposed_actions
        ):
            raise RuleDecisionError(
                "the declared main action type is absent from proposed actions"
            )

    @staticmethod
    def _build_decision(
        *,
        descriptor: RuleDescriptor,
        evaluation: DeterministicResult | HeuristicProposal,
        protection: ProtectionDecision,
        decision_id: str,
        sequence: int,
        compatibility_flags: tuple[str, ...],
        outcome: DecisionOutcome,
        reason: DecisionReason,
        review_threshold: float | None = None,
        apply_threshold: float | None = None,
    ) -> RuleDecision:
        if isinstance(evaluation, HeuristicProposal):
            score_family = evaluation.score_family
            score = evaluation.score
            evidence = evaluation.positive_evidence + evaluation.negative_evidence
        else:
            score_family = None
            score = None
            evidence = ()
        return RuleDecision(
            decision_id=decision_id,
            sequence=sequence,
            rule_id=descriptor.rule_id,
            nature=descriptor.nature,
            implementation_state=descriptor.implementation_state,
            deployment_status=descriptor.deployment_status,
            outcome=outcome,
            target_refs=evaluation.target_refs,
            proposed_actions=evaluation.proposed_actions,
            reason_code=reason.value,
            score_family=score_family,
            score=score,
            review_threshold=review_threshold,
            apply_threshold=apply_threshold,
            evidence=evidence,
            veto_reasons=evaluation.veto_reasons,
            protection=protection,
            compatibility_flags=compatibility_flags,
        )
