from __future__ import annotations

from dataclasses import FrozenInstanceError
import json

import pytest

from purh_editorial.model import Diagnostic, Transformation
from purh_editorial.rules.model import (
    DecisionOutcome,
    DeploymentStatus,
    ImplementationState,
    ProposedAction,
    ProtectionDecision,
    RuleActionType,
    RuleDecision,
    RuleNature,
    to_json_data,
)
from purh_editorial.rules.shadow import (
    CanonicalShadowComparator,
    LegacyObservationStatus,
    LegacyRuleObservation,
    ShadowComparison,
    ShadowComparisonError,
    ShadowComparisonStatus,
    ShadowDifference,
    ShadowDifferenceCode,
    _canonical_action_signature,
)


def _action(
    action_type: RuleActionType = RuleActionType.TEXT_TRANSFORM,
    *,
    target: str = "p1",
    variant: str = "default",
) -> ProposedAction:
    if action_type is RuleActionType.TEXT_TRANSFORM:
        return ProposedAction(
            action_type,
            (target,),
            before="avant",
            after="après" if variant == "default" else variant,
        )
    if action_type is RuleActionType.STYLE_TRANSFORM:
        return ProposedAction(
            action_type,
            (target,),
            style_patch={"small_caps": True, "variant": variant},
        )
    if action_type is RuleActionType.STRUCTURE_TRANSFORM:
        return ProposedAction(
            action_type,
            (target,),
            semantic_patch={
                "role": "heading" if variant == "default" else variant
            },
            created_refs=(target,),
            deleted_refs=("deleted",) if variant == "refs" else (),
            merged_refs=(target, "deleted") if variant == "refs" else (),
        )
    if action_type is RuleActionType.DIAGNOSTIC:
        return ProposedAction(
            action_type,
            (target,),
            diagnostic_payload={
                "message": "À vérifier" if variant == "default" else variant
            },
        )
    return ProposedAction(
        action_type,
        (target,),
        control_payload={
            "control": "stop" if variant == "default" else variant
        },
    )


def _observation(
    *,
    status: LegacyObservationStatus = LegacyObservationStatus.COMPLETE,
    targets: tuple[str, ...] = ("p1",),
    actions: tuple[ProposedAction, ...] = (),
    error_code: str | None = None,
) -> LegacyRuleObservation:
    return LegacyRuleObservation(
        observation_id="legacy-1",
        rule_id="test.rule",
        target_refs=targets,
        observed_actions=actions,
        status=status,
        justification="Observation canonique du comportement legacy.",
        error_code=error_code,
    )


def _decision(
    outcome: DecisionOutcome,
    *,
    targets: tuple[str, ...] = ("p1",),
    actions: tuple[ProposedAction, ...] = (),
    reason_code: str = "test_reason",
    nature: RuleNature = RuleNature.DETERMINISTIC,
    deployment_status: DeploymentStatus | None = None,
) -> RuleDecision:
    if outcome in {DecisionOutcome.APPLY, DecisionOutcome.REVIEW} and not actions:
        actions = (_action(),)
    heuristic = nature is RuleNature.HEURISTIC
    return RuleDecision(
        decision_id="native-1",
        sequence=4,
        rule_id="test.rule",
        nature=nature,
        implementation_state=(
            ImplementationState.NATIVE
            if heuristic
            else ImplementationState.LEGACY
        ),
        deployment_status=(
            deployment_status
            if deployment_status is not None
            else (
                DeploymentStatus.REVIEW_ONLY
                if outcome is DecisionOutcome.REVIEW
                else DeploymentStatus.ACTIVE
            )
        ),
        outcome=outcome,
        target_refs=targets,
        proposed_actions=actions,
        reason_code=reason_code,
        score_family="heading" if heuristic else None,
        score=0.7 if heuristic else None,
        review_threshold=0.6 if heuristic else None,
        apply_threshold=0.85 if heuristic else None,
        evidence=(),
        veto_reasons=(),
        protection=ProtectionDecision(False, "test.policy", ()),
    )


def _compare(
    legacy: LegacyRuleObservation,
    native: RuleDecision,
) -> ShadowComparison:
    return CanonicalShadowComparator().compare(
        legacy=legacy,
        native=native,
        comparison_id="comparison-1",
        sequence=7,
    )


def _codes(comparison: ShadowComparison) -> tuple[ShadowDifferenceCode, ...]:
    return tuple(difference.code for difference in comparison.differences)


def test_legacy_observation_accepts_complete_partial_unavailable_and_failed() -> None:
    action = _action()
    complete = _observation(actions=(action,))
    silent = _observation()
    partial = _observation(
        status=LegacyObservationStatus.PARTIAL,
        actions=(action,),
    )
    unavailable = _observation(status=LegacyObservationStatus.UNAVAILABLE)
    failed = _observation(
        status=LegacyObservationStatus.FAILED,
        actions=(action,),
        error_code="legacy_capture_failed",
    )
    assert complete.observed_actions == (action,)
    assert silent.observed_actions == ()
    assert partial.observed_actions == (action,)
    assert unavailable.observed_actions == ()
    assert failed.error_code == "legacy_capture_failed"
    json.dumps(to_json_data((complete, partial, unavailable, failed)))
    with pytest.raises(FrozenInstanceError):
        complete.status = LegacyObservationStatus.PARTIAL  # type: ignore[misc]


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"observation_id": ""}, "observation_id"),
        ({"rule_id": ""}, "rule_id"),
        ({"justification": ""}, "justification"),
        ({"target_refs": ["p1"]}, "target_refs"),
        ({"observed_actions": []}, "observed_actions"),
        (
            {
                "status": LegacyObservationStatus.UNAVAILABLE,
                "observed_actions": (_action(),),
            },
            "unavailable",
        ),
        (
            {"status": LegacyObservationStatus.FAILED, "error_code": None},
            "error_code",
        ),
        (
            {
                "status": LegacyObservationStatus.COMPLETE,
                "error_code": "unexpected",
            },
            "complete",
        ),
        ({"error_code": " "}, "error_code"),
    ],
)
def test_legacy_observation_rejects_invalid_contracts(
    overrides: dict[str, object],
    error: str,
) -> None:
    values: dict[str, object] = {
        "observation_id": "legacy-1",
        "rule_id": "test.rule",
        "target_refs": ("p1",),
        "observed_actions": (),
        "status": LegacyObservationStatus.COMPLETE,
        "justification": "Observation.",
        "error_code": None,
    }
    values.update(overrides)
    with pytest.raises((TypeError, ValueError), match=error):
        LegacyRuleObservation(**values)  # type: ignore[arg-type]


def test_legacy_observation_rejects_action_outside_its_targets() -> None:
    with pytest.raises(ValueError, match="action targets"):
        _observation(actions=(_action(target="other"),))


def test_shadow_difference_validates_indices_and_signatures() -> None:
    difference = ShadowDifference(
        ShadowDifferenceCode.ACTION_CONTENT_MISMATCH,
        legacy_index=0,
        native_index=0,
        legacy_signature="legacy",
        native_signature="native",
    )
    assert difference.legacy_index == 0
    for index in (-1, True):
        with pytest.raises(ValueError, match="legacy_index"):
            ShadowDifference(
                ShadowDifferenceCode.ACTION_CONTENT_MISMATCH,
                legacy_index=index,  # type: ignore[arg-type]
            )
    with pytest.raises(ValueError, match="signature"):
        ShadowDifference(
            ShadowDifferenceCode.ACTION_CONTENT_MISMATCH,
            legacy_signature="",
        )


@pytest.mark.parametrize(
    ("legacy", "native", "kwargs", "error"),
    [
        ("bad", _decision(DecisionOutcome.IGNORE), {}, "legacy"),
        (_observation(), "bad", {}, "native"),
        (
            _observation(),
            _decision(DecisionOutcome.IGNORE),
            {"comparison_id": ""},
            "comparison_id",
        ),
        (
            _observation(),
            _decision(DecisionOutcome.IGNORE),
            {"sequence": -1},
            "sequence",
        ),
        (
            _observation(),
            _decision(DecisionOutcome.IGNORE),
            {"sequence": True},
            "sequence",
        ),
    ],
)
def test_comparator_rejects_invalid_inputs(
    legacy: object,
    native: object,
    kwargs: dict[str, object],
    error: str,
) -> None:
    values = {"comparison_id": "comparison", "sequence": 0}
    values.update(kwargs)
    with pytest.raises((TypeError, ShadowComparisonError), match=error):
        CanonicalShadowComparator().compare(
            legacy=legacy,  # type: ignore[arg-type]
            native=native,  # type: ignore[arg-type]
            **values,  # type: ignore[arg-type]
        )


def test_comparator_rejects_different_rule_identifiers() -> None:
    native = _decision(DecisionOutcome.IGNORE)
    mismatched = LegacyRuleObservation(
        "legacy",
        "other.rule",
        ("p1",),
        (),
        LegacyObservationStatus.COMPLETE,
        "Observation.",
    )
    with pytest.raises(ShadowComparisonError, match="identifiers"):
        _compare(mismatched, native)


@pytest.mark.parametrize(
    ("status", "error_code", "expected_code"),
    [
        (
            LegacyObservationStatus.PARTIAL,
            None,
            ShadowDifferenceCode.LEGACY_OBSERVATION_PARTIAL,
        ),
        (
            LegacyObservationStatus.UNAVAILABLE,
            None,
            ShadowDifferenceCode.LEGACY_OBSERVATION_UNAVAILABLE,
        ),
        (
            LegacyObservationStatus.FAILED,
            "capture_failed",
            ShadowDifferenceCode.LEGACY_OBSERVATION_FAILED,
        ),
    ],
)
def test_incomplete_observations_are_strictly_inconclusive(
    status: LegacyObservationStatus,
    error_code: str | None,
    expected_code: ShadowDifferenceCode,
) -> None:
    actions = () if status is LegacyObservationStatus.UNAVAILABLE else (_action(),)
    legacy = _observation(
        status=status,
        actions=actions,
        error_code=error_code,
    )
    comparison = _compare(legacy, _decision(DecisionOutcome.APPLY))
    assert comparison.status is ShadowComparisonStatus.INCONCLUSIVE
    assert comparison.policy_equivalent is None
    assert comparison.targets_equivalent is None
    assert comparison.actions_equivalent is None
    assert _codes(comparison) == (expected_code,)
    assert comparison.legacy_observation.observed_actions == actions


@pytest.mark.parametrize(
    ("legacy_targets", "native_targets", "equivalent", "code"),
    [
        (("p1", "p2"), ("p1", "p2"), True, None),
        (
            ("p2", "p1"),
            ("p1", "p2"),
            False,
            ShadowDifferenceCode.TARGET_ORDER_MISMATCH,
        ),
        (
            ("p1",),
            ("p1", "p2"),
            False,
            ShadowDifferenceCode.TARGET_SET_MISMATCH,
        ),
        (
            ("p1", "p2", "p3"),
            ("p1", "p2"),
            False,
            ShadowDifferenceCode.TARGET_SET_MISMATCH,
        ),
        (
            ("p1", "p1"),
            ("p1",),
            False,
            ShadowDifferenceCode.TARGET_SET_MISMATCH,
        ),
        (
            ("p1", "p2", "p1"),
            ("p1", "p1", "p2"),
            False,
            ShadowDifferenceCode.TARGET_ORDER_MISMATCH,
        ),
    ],
)
def test_target_comparison_preserves_order(
    legacy_targets: tuple[str, ...],
    native_targets: tuple[str, ...],
    equivalent: bool,
    code: ShadowDifferenceCode | None,
) -> None:
    legacy = _observation(targets=legacy_targets)
    native = _decision(DecisionOutcome.IGNORE, targets=native_targets)
    comparison = _compare(legacy, native)
    assert comparison.targets_equivalent is equivalent
    assert comparison.legacy_observation.target_refs == legacy_targets
    if code is None:
        assert comparison.status is ShadowComparisonStatus.MATCH
    else:
        assert code in _codes(comparison)


def test_apply_matches_exact_actions_including_complementary_diagnostic() -> None:
    actions = (_action(), _action(RuleActionType.DIAGNOSTIC))
    comparison = _compare(
        _observation(actions=actions),
        _decision(DecisionOutcome.APPLY, actions=actions),
    )
    assert comparison.status is ShadowComparisonStatus.MATCH
    assert comparison.policy_equivalent is True
    assert comparison.targets_equivalent is True
    assert comparison.actions_equivalent is True
    assert comparison.differences == ()


def test_apply_diverges_when_legacy_is_silent() -> None:
    comparison = _compare(
        _observation(),
        _decision(DecisionOutcome.APPLY, actions=(_action(),)),
    )
    assert comparison.status is ShadowComparisonStatus.DIVERGENCE
    assert comparison.policy_equivalent is False
    assert comparison.actions_equivalent is False
    assert ShadowDifferenceCode.NATIVE_APPLY_LEGACY_SILENT in _codes(comparison)
    assert ShadowDifferenceCode.ACTION_COUNT_MISMATCH in _codes(comparison)


def test_apply_detects_action_count_and_order() -> None:
    text = _action()
    diagnostic = _action(RuleActionType.DIAGNOSTIC)
    count = _compare(
        _observation(actions=(text,)),
        _decision(DecisionOutcome.APPLY, actions=(text, diagnostic)),
    )
    order = _compare(
        _observation(actions=(diagnostic, text)),
        _decision(DecisionOutcome.APPLY, actions=(text, diagnostic)),
    )
    assert ShadowDifferenceCode.ACTION_COUNT_MISMATCH in _codes(count)
    assert _codes(order) == (ShadowDifferenceCode.ACTION_ORDER_MISMATCH,)
    assert order.differences[0].legacy_signature is not None
    assert order.differences[0].native_signature is not None


@pytest.mark.parametrize(
    ("legacy_action", "native_action", "expected_code"),
    [
        (
            _action(RuleActionType.TEXT_TRANSFORM),
            _action(RuleActionType.STYLE_TRANSFORM),
            ShadowDifferenceCode.ACTION_TYPE_MISMATCH,
        ),
        (
            _action(target="p1"),
            _action(target="p2"),
            ShadowDifferenceCode.ACTION_TARGET_MISMATCH,
        ),
        (
            _action(variant="legacy-after"),
            _action(variant="native-after"),
            ShadowDifferenceCode.ACTION_CONTENT_MISMATCH,
        ),
        (
            _action(RuleActionType.DIAGNOSTIC, variant="legacy"),
            _action(RuleActionType.DIAGNOSTIC, variant="native"),
            ShadowDifferenceCode.ACTION_CONTENT_MISMATCH,
        ),
        (
            _action(RuleActionType.STYLE_TRANSFORM, variant="legacy"),
            _action(RuleActionType.STYLE_TRANSFORM, variant="native"),
            ShadowDifferenceCode.ACTION_CONTENT_MISMATCH,
        ),
        (
            _action(RuleActionType.STRUCTURE_TRANSFORM, variant="legacy"),
            _action(RuleActionType.STRUCTURE_TRANSFORM, variant="native"),
            ShadowDifferenceCode.ACTION_CONTENT_MISMATCH,
        ),
        (
            _action(RuleActionType.PIPELINE_CONTROL, variant="legacy"),
            _action(RuleActionType.PIPELINE_CONTROL, variant="native"),
            ShadowDifferenceCode.ACTION_CONTENT_MISMATCH,
        ),
        (
            _action(RuleActionType.STRUCTURE_TRANSFORM, variant="refs"),
            _action(RuleActionType.STRUCTURE_TRANSFORM),
            ShadowDifferenceCode.ACTION_CONTENT_MISMATCH,
        ),
    ],
)
def test_apply_distinguishes_action_difference_kinds(
    legacy_action: ProposedAction,
    native_action: ProposedAction,
    expected_code: ShadowDifferenceCode,
) -> None:
    targets = tuple(
        dict.fromkeys(legacy_action.target_refs + native_action.target_refs)
    )
    comparison = _compare(
        _observation(targets=targets, actions=(legacy_action,)),
        _decision(
            DecisionOutcome.APPLY,
            targets=targets,
            actions=(native_action,),
        ),
    )
    assert comparison.status is ShadowComparisonStatus.DIVERGENCE
    assert comparison.policy_equivalent is True
    assert comparison.actions_equivalent is False
    assert _codes(comparison) == (expected_code,)


@pytest.mark.parametrize("diagnostic_count", [1, 2])
def test_review_matches_one_or_more_legacy_diagnostics(
    diagnostic_count: int,
) -> None:
    diagnostics = tuple(
        _action(RuleActionType.DIAGNOSTIC)
        for _ in range(diagnostic_count)
    )
    native_action = _action(RuleActionType.STRUCTURE_TRANSFORM)
    comparison = _compare(
        _observation(actions=diagnostics),
        _decision(
            DecisionOutcome.REVIEW,
            actions=(native_action,),
            nature=RuleNature.HEURISTIC,
        ),
    )
    assert comparison.status is ShadowComparisonStatus.MATCH
    assert comparison.policy_equivalent is True
    assert comparison.actions_equivalent is None


def test_review_matches_for_active_heuristic_in_review_band() -> None:
    diagnostic = _action(RuleActionType.DIAGNOSTIC)
    comparison = _compare(
        _observation(actions=(diagnostic,)),
        _decision(
            DecisionOutcome.REVIEW,
            actions=(_action(RuleActionType.STRUCTURE_TRANSFORM),),
            nature=RuleNature.HEURISTIC,
            deployment_status=DeploymentStatus.ACTIVE,
            reason_code="heuristic_review_band",
        ),
    )
    assert comparison.status is ShadowComparisonStatus.MATCH
    assert comparison.native_decision.deployment_status is DeploymentStatus.ACTIVE
    assert comparison.actions_equivalent is None


@pytest.mark.parametrize(
    ("legacy_actions", "expected_codes"),
    [
        ((), (ShadowDifferenceCode.NATIVE_REVIEW_LEGACY_SILENT,)),
        (
            (_action(),),
            (ShadowDifferenceCode.LEGACY_MUTATION_NATIVE_REVIEW,),
        ),
        (
            (_action(), _action(RuleActionType.DIAGNOSTIC)),
            (ShadowDifferenceCode.LEGACY_MUTATION_NATIVE_REVIEW,),
        ),
        (
            (_action(RuleActionType.PIPELINE_CONTROL),),
            (ShadowDifferenceCode.LEGACY_CONTROL_NATIVE_REVIEW,),
        ),
        (
            (
                _action(RuleActionType.PIPELINE_CONTROL),
                _action(RuleActionType.DIAGNOSTIC),
            ),
            (ShadowDifferenceCode.LEGACY_CONTROL_NATIVE_REVIEW,),
        ),
    ],
)
def test_review_divergences_follow_operational_effects(
    legacy_actions: tuple[ProposedAction, ...],
    expected_codes: tuple[ShadowDifferenceCode, ...],
) -> None:
    comparison = _compare(
        _observation(actions=legacy_actions),
        _decision(
            DecisionOutcome.REVIEW,
            actions=(_action(),),
            nature=RuleNature.HEURISTIC,
        ),
    )
    assert comparison.status is ShadowComparisonStatus.DIVERGENCE
    assert comparison.policy_equivalent is False
    assert comparison.actions_equivalent is None
    assert _codes(comparison) == expected_codes


@pytest.mark.parametrize(
    "reason_code",
    [
        "rule_disabled",
        "target_protected",
        "rule_veto",
        "no_match",
        "heuristic_below_review_threshold",
    ],
)
def test_ignore_matches_legacy_silence_regardless_of_native_reason(
    reason_code: str,
) -> None:
    comparison = _compare(
        _observation(),
        _decision(DecisionOutcome.IGNORE, reason_code=reason_code),
    )
    assert comparison.status is ShadowComparisonStatus.MATCH
    assert comparison.policy_equivalent is True
    assert comparison.actions_equivalent is None


@pytest.mark.parametrize(
    "legacy_actions",
    [
        (_action(),),
        (_action(RuleActionType.DIAGNOSTIC),),
        (_action(RuleActionType.PIPELINE_CONTROL),),
        (_action(), _action(RuleActionType.DIAGNOSTIC)),
    ],
)
def test_ignore_diverges_for_every_legacy_effect(
    legacy_actions: tuple[ProposedAction, ...],
) -> None:
    comparison = _compare(
        _observation(actions=legacy_actions),
        _decision(DecisionOutcome.IGNORE),
    )
    assert comparison.status is ShadowComparisonStatus.DIVERGENCE
    assert comparison.policy_equivalent is False
    assert comparison.actions_equivalent is None
    assert _codes(comparison) == (
        ShadowDifferenceCode.LEGACY_EFFECT_NATIVE_IGNORE,
    )


def test_action_signatures_are_canonical_stable_and_address_independent() -> None:
    first = _action(RuleActionType.DIAGNOSTIC)
    second = _action(RuleActionType.DIAGNOSTIC)
    first_signature = _canonical_action_signature(first)
    assert first_signature == _canonical_action_signature(first)
    assert first_signature == _canonical_action_signature(second)
    assert first_signature.startswith('{"action_type":')
    assert "0x" not in first_signature
    assert first_signature == json.dumps(
        to_json_data(first),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


@pytest.mark.parametrize(
    "comparison",
    [
        _compare(_observation(), _decision(DecisionOutcome.IGNORE)),
        _compare(
            _observation(actions=(_action(),)),
            _decision(
                DecisionOutcome.APPLY,
                actions=(_action(variant="different"),),
            ),
        ),
        _compare(
            _observation(status=LegacyObservationStatus.UNAVAILABLE),
            _decision(DecisionOutcome.IGNORE),
        ),
    ],
)
def test_match_divergence_and_inconclusive_are_json_serializable(
    comparison: ShadowComparison,
) -> None:
    payload = to_json_data(comparison)
    json.dumps(payload, ensure_ascii=False)

    def assert_native(value: object) -> None:
        assert not isinstance(value, tuple)
        if isinstance(value, dict):
            for item in value.values():
                assert_native(item)
        elif isinstance(value, list):
            for item in value:
                assert_native(item)

    assert_native(payload)
    assert isinstance(payload["status"], str)


def test_comparator_is_pure_deterministic_and_does_not_execute_actions() -> None:
    actions = (_action(), _action(RuleActionType.DIAGNOSTIC))
    legacy = _observation(actions=actions)
    native = _decision(DecisionOutcome.APPLY, actions=actions)
    comparator = CanonicalShadowComparator()
    first = comparator.compare(
        legacy=legacy,
        native=native,
        comparison_id="stable",
        sequence=0,
    )
    second = comparator.compare(
        legacy=legacy,
        native=native,
        comparison_id="stable",
        sequence=0,
    )
    assert first == second
    assert legacy.observed_actions == actions
    assert native.proposed_actions == actions
    assert all(
        not isinstance(item, (Transformation, Diagnostic))
        for item in (first, *first.differences)
    )
