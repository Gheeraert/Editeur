from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
import json

from purh_editorial.rules.model import (
    DecisionOutcome,
    ProposedAction,
    RuleActionType,
    RuleDecision,
    to_json_data,
)


class LegacyObservationStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class ShadowComparisonStatus(str, Enum):
    MATCH = "match"
    DIVERGENCE = "divergence"
    INCONCLUSIVE = "inconclusive"


class ShadowDifferenceCode(str, Enum):
    LEGACY_OBSERVATION_PARTIAL = "legacy_observation_partial"
    LEGACY_OBSERVATION_UNAVAILABLE = "legacy_observation_unavailable"
    LEGACY_OBSERVATION_FAILED = "legacy_observation_failed"
    TARGET_SET_MISMATCH = "target_set_mismatch"
    TARGET_ORDER_MISMATCH = "target_order_mismatch"
    NATIVE_APPLY_LEGACY_SILENT = "native_apply_legacy_silent"
    NATIVE_REVIEW_LEGACY_SILENT = "native_review_legacy_silent"
    LEGACY_MUTATION_NATIVE_REVIEW = "legacy_mutation_native_review"
    LEGACY_CONTROL_NATIVE_REVIEW = "legacy_control_native_review"
    LEGACY_EFFECT_NATIVE_IGNORE = "legacy_effect_native_ignore"
    ACTION_COUNT_MISMATCH = "action_count_mismatch"
    ACTION_ORDER_MISMATCH = "action_order_mismatch"
    ACTION_TYPE_MISMATCH = "action_type_mismatch"
    ACTION_TARGET_MISMATCH = "action_target_mismatch"
    ACTION_CONTENT_MISMATCH = "action_content_mismatch"


class ShadowComparisonError(ValueError):
    """Les entrées du comparateur shadow sont incohérentes."""


def _require_non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_optional_non_empty(value: str | None, field_name: str) -> None:
    if value is not None:
        _require_non_empty(value, field_name)


@dataclass(frozen=True, slots=True)
class LegacyRuleObservation:
    observation_id: str
    rule_id: str
    target_refs: tuple[str, ...]
    observed_actions: tuple[ProposedAction, ...]
    status: LegacyObservationStatus
    justification: str
    error_code: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.observation_id, "observation_id")
        _require_non_empty(self.rule_id, "rule_id")
        _require_non_empty(self.justification, "justification")
        if not isinstance(self.target_refs, tuple):
            raise TypeError("target_refs must be a tuple")
        if not isinstance(self.observed_actions, tuple):
            raise TypeError("observed_actions must be a tuple")
        if not isinstance(self.status, LegacyObservationStatus):
            raise TypeError("status must be a LegacyObservationStatus")
        if any(
            not isinstance(action, ProposedAction)
            for action in self.observed_actions
        ):
            raise TypeError("observed_actions must contain ProposedAction values")
        observed_targets = set(self.target_refs)
        if any(
            not set(action.target_refs).issubset(observed_targets)
            for action in self.observed_actions
        ):
            raise ValueError(
                "observed action targets must belong to observation target_refs"
            )
        _require_optional_non_empty(self.error_code, "error_code")
        if (
            self.status is LegacyObservationStatus.UNAVAILABLE
            and self.observed_actions
        ):
            raise ValueError("unavailable observations cannot contain actions")
        if (
            self.status is LegacyObservationStatus.FAILED
            and self.error_code is None
        ):
            raise ValueError("failed observations require error_code")
        if (
            self.status is LegacyObservationStatus.COMPLETE
            and self.error_code is not None
        ):
            raise ValueError("complete observations cannot define error_code")


@dataclass(frozen=True, slots=True)
class ShadowDifference:
    code: ShadowDifferenceCode
    legacy_index: int | None = None
    native_index: int | None = None
    legacy_signature: str | None = None
    native_signature: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, ShadowDifferenceCode):
            raise TypeError("code must be a ShadowDifferenceCode")
        for name in ("legacy_index", "native_index"):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(f"{name} must be a non-negative integer or None")
        _require_optional_non_empty(self.legacy_signature, "legacy_signature")
        _require_optional_non_empty(self.native_signature, "native_signature")


_INCONCLUSIVE_CODES = {
    ShadowDifferenceCode.LEGACY_OBSERVATION_PARTIAL,
    ShadowDifferenceCode.LEGACY_OBSERVATION_UNAVAILABLE,
    ShadowDifferenceCode.LEGACY_OBSERVATION_FAILED,
}


@dataclass(frozen=True, slots=True)
class ShadowComparison:
    comparison_id: str
    sequence: int
    rule_id: str
    status: ShadowComparisonStatus
    policy_equivalent: bool | None
    targets_equivalent: bool | None
    actions_equivalent: bool | None
    differences: tuple[ShadowDifference, ...]
    legacy_observation: LegacyRuleObservation
    native_decision: RuleDecision

    def __post_init__(self) -> None:
        _require_non_empty(self.comparison_id, "comparison_id")
        _require_non_empty(self.rule_id, "rule_id")
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
        ):
            raise ValueError("sequence must be a non-negative integer")
        if not isinstance(self.status, ShadowComparisonStatus):
            raise TypeError("status must be a ShadowComparisonStatus")
        for name in (
            "policy_equivalent",
            "targets_equivalent",
            "actions_equivalent",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, bool):
                raise TypeError(f"{name} must be a bool or None")
        if not isinstance(self.differences, tuple):
            raise TypeError("differences must be a tuple")
        if any(
            not isinstance(difference, ShadowDifference)
            for difference in self.differences
        ):
            raise TypeError("differences must contain ShadowDifference values")
        if not isinstance(self.legacy_observation, LegacyRuleObservation):
            raise TypeError(
                "legacy_observation must be a LegacyRuleObservation"
            )
        if not isinstance(self.native_decision, RuleDecision):
            raise TypeError("native_decision must be a RuleDecision")
        if not (
            self.rule_id
            == self.legacy_observation.rule_id
            == self.native_decision.rule_id
        ):
            raise ValueError("comparison rule identifiers must agree")
        if self.status is ShadowComparisonStatus.MATCH:
            if (
                self.policy_equivalent is not True
                or self.targets_equivalent is not True
                or self.actions_equivalent not in (True, None)
                or self.differences
            ):
                raise ValueError("match comparison has inconsistent axes")
        elif self.status is ShadowComparisonStatus.DIVERGENCE:
            if not self.differences:
                raise ValueError("divergence requires at least one difference")
        elif self.status is ShadowComparisonStatus.INCONCLUSIVE:
            if not any(
                difference.code in _INCONCLUSIVE_CODES
                for difference in self.differences
            ):
                raise ValueError(
                    "inconclusive comparison requires an observation status code"
                )
            if any(
                value is not None
                for value in (
                    self.policy_equivalent,
                    self.targets_equivalent,
                    self.actions_equivalent,
                )
            ):
                raise ValueError("inconclusive comparison axes must be None")


def _canonical_action_signature(action: ProposedAction) -> str:
    return json.dumps(
        to_json_data(action),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _difference_for_incomplete_status(
    status: LegacyObservationStatus,
) -> ShadowDifference:
    code = {
        LegacyObservationStatus.PARTIAL:
            ShadowDifferenceCode.LEGACY_OBSERVATION_PARTIAL,
        LegacyObservationStatus.UNAVAILABLE:
            ShadowDifferenceCode.LEGACY_OBSERVATION_UNAVAILABLE,
        LegacyObservationStatus.FAILED:
            ShadowDifferenceCode.LEGACY_OBSERVATION_FAILED,
    }[status]
    return ShadowDifference(code)


def _compare_targets(
    legacy_targets: tuple[str, ...],
    native_targets: tuple[str, ...],
) -> tuple[bool, tuple[ShadowDifference, ...]]:
    if legacy_targets == native_targets:
        return True, ()
    if set(legacy_targets) == set(native_targets):
        return False, (
            ShadowDifference(ShadowDifferenceCode.TARGET_ORDER_MISMATCH),
        )
    return False, (
        ShadowDifference(ShadowDifferenceCode.TARGET_SET_MISMATCH),
    )


def _compare_actions_exactly(
    legacy_actions: tuple[ProposedAction, ...],
    native_actions: tuple[ProposedAction, ...],
) -> tuple[bool, tuple[ShadowDifference, ...]]:
    if legacy_actions == native_actions:
        return True, ()

    legacy_signatures = tuple(
        _canonical_action_signature(action) for action in legacy_actions
    )
    native_signatures = tuple(
        _canonical_action_signature(action) for action in native_actions
    )
    if (
        len(legacy_signatures) == len(native_signatures)
        and Counter(legacy_signatures) == Counter(native_signatures)
    ):
        differing_index = next(
            index
            for index, (legacy_signature, native_signature) in enumerate(
                zip(legacy_signatures, native_signatures)
            )
            if legacy_signature != native_signature
        )
        return False, (
            ShadowDifference(
                ShadowDifferenceCode.ACTION_ORDER_MISMATCH,
                legacy_index=differing_index,
                native_index=differing_index,
                legacy_signature=legacy_signatures[differing_index],
                native_signature=native_signatures[differing_index],
            ),
        )

    differences: list[ShadowDifference] = []
    if len(legacy_actions) != len(native_actions):
        differences.append(
            ShadowDifference(ShadowDifferenceCode.ACTION_COUNT_MISMATCH)
        )

    for index, (legacy_action, native_action) in enumerate(
        zip(legacy_actions, native_actions)
    ):
        if legacy_action == native_action:
            continue
        if legacy_action.action_type is not native_action.action_type:
            code = ShadowDifferenceCode.ACTION_TYPE_MISMATCH
        elif legacy_action.target_refs != native_action.target_refs:
            code = ShadowDifferenceCode.ACTION_TARGET_MISMATCH
        else:
            code = ShadowDifferenceCode.ACTION_CONTENT_MISMATCH
        differences.append(
            ShadowDifference(
                code,
                legacy_index=index,
                native_index=index,
                legacy_signature=legacy_signatures[index],
                native_signature=native_signatures[index],
            )
        )
    return False, tuple(differences)


_MUTATING_ACTION_TYPES = {
    RuleActionType.TEXT_TRANSFORM,
    RuleActionType.STYLE_TRANSFORM,
    RuleActionType.STRUCTURE_TRANSFORM,
}


@dataclass(frozen=True, slots=True)
class CanonicalShadowComparator:
    def compare(
        self,
        *,
        legacy: LegacyRuleObservation,
        native: RuleDecision,
        comparison_id: str,
        sequence: int,
    ) -> ShadowComparison:
        self._validate_inputs(
            legacy=legacy,
            native=native,
            comparison_id=comparison_id,
            sequence=sequence,
        )
        if legacy.status is not LegacyObservationStatus.COMPLETE:
            return ShadowComparison(
                comparison_id=comparison_id,
                sequence=sequence,
                rule_id=legacy.rule_id,
                status=ShadowComparisonStatus.INCONCLUSIVE,
                policy_equivalent=None,
                targets_equivalent=None,
                actions_equivalent=None,
                differences=(
                    _difference_for_incomplete_status(legacy.status),
                ),
                legacy_observation=legacy,
                native_decision=native,
            )

        targets_equivalent, target_differences = _compare_targets(
            legacy.target_refs,
            native.target_refs,
        )
        differences = list(target_differences)
        legacy_actions = legacy.observed_actions

        if native.outcome is DecisionOutcome.APPLY:
            policy_equivalent = bool(legacy_actions)
            if not legacy_actions:
                differences.append(
                    ShadowDifference(
                        ShadowDifferenceCode.NATIVE_APPLY_LEGACY_SILENT
                    )
                )
            actions_equivalent, action_differences = _compare_actions_exactly(
                legacy_actions,
                native.proposed_actions,
            )
            differences.extend(action_differences)
        elif native.outcome is DecisionOutcome.REVIEW:
            actions_equivalent = None
            has_mutation = any(
                action.action_type in _MUTATING_ACTION_TYPES
                for action in legacy_actions
            )
            has_diagnostic = any(
                action.action_type is RuleActionType.DIAGNOSTIC
                for action in legacy_actions
            )
            has_control = any(
                action.action_type is RuleActionType.PIPELINE_CONTROL
                for action in legacy_actions
            )
            policy_equivalent = (
                has_diagnostic and not has_mutation and not has_control
            )
            if not legacy_actions:
                differences.append(
                    ShadowDifference(
                        ShadowDifferenceCode.NATIVE_REVIEW_LEGACY_SILENT
                    )
                )
            if has_mutation:
                differences.append(
                    ShadowDifference(
                        ShadowDifferenceCode.LEGACY_MUTATION_NATIVE_REVIEW
                    )
                )
            if has_control:
                differences.append(
                    ShadowDifference(
                        ShadowDifferenceCode.LEGACY_CONTROL_NATIVE_REVIEW
                    )
                )
        else:
            actions_equivalent = None
            policy_equivalent = not legacy_actions
            if legacy_actions:
                differences.append(
                    ShadowDifference(
                        ShadowDifferenceCode.LEGACY_EFFECT_NATIVE_IGNORE
                    )
                )

        status = (
            ShadowComparisonStatus.MATCH
            if (
                policy_equivalent
                and targets_equivalent
                and actions_equivalent in (True, None)
                and not differences
            )
            else ShadowComparisonStatus.DIVERGENCE
        )
        return ShadowComparison(
            comparison_id=comparison_id,
            sequence=sequence,
            rule_id=legacy.rule_id,
            status=status,
            policy_equivalent=policy_equivalent,
            targets_equivalent=targets_equivalent,
            actions_equivalent=actions_equivalent,
            differences=tuple(differences),
            legacy_observation=legacy,
            native_decision=native,
        )

    @staticmethod
    def _validate_inputs(
        *,
        legacy: LegacyRuleObservation,
        native: RuleDecision,
        comparison_id: str,
        sequence: int,
    ) -> None:
        if not isinstance(legacy, LegacyRuleObservation):
            raise TypeError("legacy must be a LegacyRuleObservation")
        if not isinstance(native, RuleDecision):
            raise TypeError("native must be a RuleDecision")
        if not isinstance(comparison_id, str) or not comparison_id.strip():
            raise ShadowComparisonError(
                "comparison_id must be a non-empty string"
            )
        if (
            isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence < 0
        ):
            raise ShadowComparisonError(
                "sequence must be a non-negative integer"
            )
        if legacy.rule_id != native.rule_id:
            raise ShadowComparisonError(
                "legacy and native rule identifiers must agree"
            )
