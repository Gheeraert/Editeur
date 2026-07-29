from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from purh_editorial.rules.engine import (
    CanonicalRuleDecisionEngine,
    DecisionReason,
    RuleDecisionError,
)
from purh_editorial.rules.model import (
    DecisionOutcome,
    DeploymentStatus,
    DeterministicResult,
    HeuristicEvidence,
    HeuristicProposal,
    ImplementationState,
    NormativeStatus,
    ProposedAction,
    ProtectionDecision,
    RuleActionType,
    RuleDescriptor,
    RuleFamily,
    RuleNature,
    ThresholdPair,
    to_json_data,
)
from purh_editorial.rules.thresholds import CanonicalThresholdPolicy


def _descriptor(
    *,
    nature: RuleNature = RuleNature.DETERMINISTIC,
    status: DeploymentStatus = DeploymentStatus.ACTIVE,
    action_type: RuleActionType = RuleActionType.TEXT_TRANSFORM,
    score_family: str | None = None,
    implementation_state: ImplementationState = ImplementationState.LEGACY,
) -> RuleDescriptor:
    return RuleDescriptor(
        rule_id="test.rule",
        owner_module="tests.rules",
        family=RuleFamily.STRUCTURE,
        nature=nature,
        action_type=action_type,
        deployment_status=status,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        normative_sources=(),
        protection_policy_id="test.protection",
        score_family=score_family,
        test_refs=("tests/unit/rules/test_rule_engine.py",),
        implementation_state=implementation_state,
    )


def _action(
    action_type: RuleActionType = RuleActionType.TEXT_TRANSFORM,
    *,
    target: str = "block-1",
) -> ProposedAction:
    kwargs: dict[str, object] = {}
    if action_type is RuleActionType.TEXT_TRANSFORM:
        kwargs.update(before="avant", after="après")
    elif action_type is RuleActionType.DIAGNOSTIC:
        kwargs["diagnostic_payload"] = {"message": "À vérifier"}
    elif action_type is RuleActionType.PIPELINE_CONTROL:
        kwargs["control_payload"] = {"control": "stop_heading_heuristics"}
    elif action_type is RuleActionType.STYLE_TRANSFORM:
        kwargs["style_patch"] = {"italic": True}
    elif action_type is RuleActionType.STRUCTURE_TRANSFORM:
        kwargs["semantic_patch"] = {"role": "heading"}
    return ProposedAction(
        action_type=action_type,
        target_refs=(target,),
        **kwargs,
    )


def _deterministic(
    *,
    matched: bool = True,
    actions: tuple[ProposedAction, ...] | None = None,
    veto_reasons: tuple[str, ...] = (),
    targets: tuple[str, ...] = ("block-1",),
) -> DeterministicResult:
    if actions is None:
        actions = (_action(),) if matched and not veto_reasons else ()
    return DeterministicResult(
        rule_id="test.rule",
        matched=matched,
        target_refs=targets,
        proposed_actions=actions,
        conditions_met=("condition",) if matched else (),
        veto_reasons=veto_reasons,
        justification="résultat déterministe explicite",
    )


def _heuristic(
    score: float,
    *,
    score_family: str = "heading",
    actions: tuple[ProposedAction, ...] | None = None,
    veto_reasons: tuple[str, ...] = (),
) -> HeuristicProposal:
    if actions is None:
        actions = (_action(RuleActionType.STRUCTURE_TRANSFORM),)
    return HeuristicProposal(
        rule_id="test.rule",
        score_family=score_family,
        score=score,
        proposed_actions=actions,
        target_refs=("block-1",),
        positive_evidence=(
            HeuristicEvidence("positive", True, 0.4, "indice positif"),
        ),
        negative_evidence=(
            HeuristicEvidence("negative", False, -0.1, "indice négatif"),
        ),
        veto_reasons=veto_reasons,
        justification="proposition heuristique",
    )


def _protection(protected: bool = False) -> ProtectionDecision:
    return ProtectionDecision(
        protected=protected,
        policy_id="test.protection",
        reasons=("zone protégée",) if protected else (),
    )


def _decide(
    descriptor: RuleDescriptor,
    evaluation: DeterministicResult | HeuristicProposal,
    **overrides: object,
):
    values = {
        "descriptor": descriptor,
        "evaluation": evaluation,
        "protection": _protection(),
        "decision_id": "decision-1",
        "sequence": 3,
        "intervention_level": 50,
        "compatibility_flags": ("legacy-trace",),
    }
    values.update(overrides)
    return CanonicalRuleDecisionEngine(CanonicalThresholdPolicy()).decide(
        **values  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(
    ("action_type", "expected"),
    [
        (RuleActionType.TEXT_TRANSFORM, DecisionOutcome.APPLY),
        (RuleActionType.DIAGNOSTIC, DecisionOutcome.APPLY),
        (RuleActionType.PIPELINE_CONTROL, DecisionOutcome.APPLY),
    ],
)
def test_active_deterministic_actions_are_decided_without_execution(
    action_type: RuleActionType,
    expected: DecisionOutcome,
) -> None:
    action = _action(action_type)
    decision = _decide(
        _descriptor(action_type=action_type),
        _deterministic(actions=(action,)),
    )
    assert decision.outcome is expected
    assert decision.reason_code == DecisionReason.DETERMINISTIC_ACTIVE.value
    assert decision.proposed_actions == (action,)
    assert decision.score is None
    assert decision.review_threshold is None


def test_deterministic_review_only_disabled_protection_veto_and_non_match() -> None:
    review = _decide(
        _descriptor(status=DeploymentStatus.REVIEW_ONLY),
        _deterministic(),
    )
    disabled = _decide(
        _descriptor(status=DeploymentStatus.DISABLED),
        _deterministic(),
    )
    protected = _decide(
        _descriptor(),
        _deterministic(),
        protection=_protection(True),
    )
    vetoed = _decide(
        _descriptor(),
        _deterministic(veto_reasons=("local-veto",)),
    )
    no_match = _decide(_descriptor(), _deterministic(matched=False))
    abstention = _decide(
        _descriptor(),
        _deterministic(actions=()),
    )

    assert (review.outcome, review.reason_code) == (
        DecisionOutcome.REVIEW,
        DecisionReason.DETERMINISTIC_REVIEW_ONLY.value,
    )
    assert (disabled.outcome, disabled.reason_code) == (
        DecisionOutcome.IGNORE,
        DecisionReason.RULE_DISABLED.value,
    )
    assert (protected.outcome, protected.reason_code) == (
        DecisionOutcome.IGNORE,
        DecisionReason.TARGET_PROTECTED.value,
    )
    assert protected.protection == _protection(True)
    assert (vetoed.outcome, vetoed.veto_reasons) == (
        DecisionOutcome.IGNORE,
        ("local-veto",),
    )
    assert no_match.reason_code == DecisionReason.NO_MATCH.value
    assert abstention.reason_code == DecisionReason.EXPLICIT_ABSTENTION.value


@pytest.mark.parametrize("family", ["heading", "poetry"])
def test_active_heuristic_threshold_boundaries(family: str) -> None:
    policy = CanonicalThresholdPolicy()
    thresholds = policy.thresholds(score_family=family, intervention_level=50)
    descriptor = _descriptor(
        nature=RuleNature.HEURISTIC,
        action_type=RuleActionType.STRUCTURE_TRANSFORM,
        score_family=family,
        implementation_state=ImplementationState.NATIVE,
    )

    assert (
        _decide(
            descriptor,
            _heuristic(thresholds.apply, score_family=family),
        ).outcome
        is DecisionOutcome.APPLY
    )
    assert (
        _decide(
            descriptor,
            _heuristic(
                min(1.0, thresholds.apply + 0.01),
                score_family=family,
            ),
        ).outcome
        is DecisionOutcome.APPLY
    )
    assert (
        _decide(
            descriptor,
            _heuristic(thresholds.review, score_family=family),
        ).outcome
        is DecisionOutcome.REVIEW
    )
    assert (
        _decide(
            descriptor,
            _heuristic(
                (thresholds.review + thresholds.apply) / 2,
                score_family=family,
            ),
        ).outcome
        is DecisionOutcome.REVIEW
    )
    assert (
        _decide(
            descriptor,
            _heuristic(thresholds.review - 0.01, score_family=family),
        ).outcome
        is DecisionOutcome.IGNORE
    )


@pytest.mark.parametrize("family", ["heading", "poetry"])
def test_review_only_heuristic_is_never_applied(family: str) -> None:
    thresholds = CanonicalThresholdPolicy().thresholds(
        score_family=family,
        intervention_level=50,
    )
    descriptor = _descriptor(
        nature=RuleNature.HEURISTIC,
        status=DeploymentStatus.REVIEW_ONLY,
        action_type=RuleActionType.STRUCTURE_TRANSFORM,
        score_family=family,
        implementation_state=ImplementationState.NATIVE,
    )
    assert _decide(descriptor, _heuristic(thresholds.review - 0.01, score_family=family)).outcome is DecisionOutcome.IGNORE
    for score in (
        thresholds.review,
        (thresholds.review + thresholds.apply) / 2,
        thresholds.apply,
        1.0,
    ):
        decision = _decide(
            descriptor,
            _heuristic(score, score_family=family),
            intervention_level=100,
        )
        assert decision.outcome is DecisionOutcome.REVIEW
        assert decision.reason_code == DecisionReason.HEURISTIC_REVIEW_ONLY_REACHED.value


class _FailIfCalledPolicy:
    def thresholds(self, *, score_family: str, intervention_level: int) -> ThresholdPair:
        raise AssertionError("thresholds must not be consulted")


@pytest.mark.parametrize(
    ("status", "protected", "veto"),
    [
        (DeploymentStatus.DISABLED, False, False),
        (DeploymentStatus.ACTIVE, True, False),
        (DeploymentStatus.ACTIVE, False, True),
    ],
)
def test_priority_decisions_do_not_consult_thresholds(
    status: DeploymentStatus,
    protected: bool,
    veto: bool,
) -> None:
    descriptor = _descriptor(
        nature=RuleNature.HEURISTIC,
        status=status,
        action_type=RuleActionType.STRUCTURE_TRANSFORM,
        score_family=None if status is DeploymentStatus.DISABLED else "heading",
    )
    proposal = _heuristic(
        1.0,
        actions=() if veto else None,
        veto_reasons=("veto",) if veto else (),
    )
    decision = CanonicalRuleDecisionEngine(_FailIfCalledPolicy()).decide(
        descriptor=descriptor,
        evaluation=proposal,
        protection=_protection(protected),
        decision_id="priority",
        sequence=0,
    )
    assert decision.outcome is DecisionOutcome.IGNORE
    assert decision.review_threshold is None
    assert decision.score == 1.0


@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (lambda d, e: (d, HeuristicProposal(
            rule_id="other", score_family="heading", score=0.8,
            proposed_actions=e.proposed_actions, target_refs=e.target_refs,
            positive_evidence=e.positive_evidence,
            negative_evidence=e.negative_evidence, veto_reasons=(),
            justification="mismatch",
        )), "rule_id"),
        (lambda d, e: (_descriptor(nature=RuleNature.HEURISTIC), _deterministic()), "heuristic descriptor"),
        (lambda d, e: (d, _heuristic(0.8, score_family="poetry")), "score family"),
    ],
)
def test_incoherent_evaluations_are_rejected(mutator, error: str) -> None:
    descriptor = _descriptor(
        nature=RuleNature.HEURISTIC,
        action_type=RuleActionType.STRUCTURE_TRANSFORM,
        score_family="heading",
    )
    evaluation = _heuristic(0.8)
    bad_descriptor, bad_evaluation = mutator(descriptor, evaluation)
    with pytest.raises(RuleDecisionError, match=error):
        _decide(bad_descriptor, bad_evaluation)


def test_deterministic_descriptor_rejects_heuristic_evaluation() -> None:
    with pytest.raises(RuleDecisionError, match="deterministic descriptor"):
        _decide(_descriptor(), _heuristic(0.8))


def test_native_heuristic_requires_family_level_and_coherent_targets() -> None:
    legacy_without_family = _descriptor(
        nature=RuleNature.HEURISTIC,
        action_type=RuleActionType.STRUCTURE_TRANSFORM,
    )
    with pytest.raises(RuleDecisionError, match="no native score family"):
        _decide(legacy_without_family, _heuristic(0.8))

    native = _descriptor(
        nature=RuleNature.HEURISTIC,
        action_type=RuleActionType.STRUCTURE_TRANSFORM,
        score_family="heading",
        implementation_state=ImplementationState.NATIVE,
    )
    with pytest.raises(RuleDecisionError, match="intervention_level"):
        _decide(native, _heuristic(0.8), intervention_level=None)
    incoherent_action = _action(RuleActionType.STRUCTURE_TRANSFORM, target="other")
    with pytest.raises(RuleDecisionError, match="action targets"):
        _decide(native, _heuristic(0.8, actions=(incoherent_action,)))
    wrong_type = _action(RuleActionType.TEXT_TRANSFORM)
    with pytest.raises(RuleDecisionError, match="action type"):
        _decide(native, _heuristic(0.8, actions=(wrong_type,)))


def test_deterministic_evaluation_requires_a_target() -> None:
    with pytest.raises(RuleDecisionError, match="at least one target"):
        _decide(
            _descriptor(),
            _deterministic(matched=False, targets=()),
        )


@pytest.mark.parametrize(
    ("override", "error"),
    [
        ({"decision_id": ""}, "decision_id"),
        ({"sequence": -1}, "sequence"),
        ({"sequence": True}, "sequence"),
        ({"compatibility_flags": ["legacy"]}, "compatibility_flags"),
    ],
)
def test_call_metadata_is_strict(override: dict[str, object], error: str) -> None:
    with pytest.raises((RuleDecisionError, TypeError), match=error):
        _decide(_descriptor(), _deterministic(), **override)


def test_trace_is_complete_stable_serializable_and_deterministic() -> None:
    descriptor = _descriptor(
        nature=RuleNature.HEURISTIC,
        action_type=RuleActionType.STRUCTURE_TRANSFORM,
        score_family="heading",
        implementation_state=ImplementationState.NATIVE,
    )
    evaluation = _heuristic(0.85)
    protection = _protection()
    first = _decide(descriptor, evaluation, protection=protection)
    second = _decide(descriptor, evaluation, protection=protection)

    assert first == second
    assert first.decision_id == "decision-1"
    assert first.sequence == 3
    assert first.rule_id == descriptor.rule_id
    assert first.implementation_state is ImplementationState.NATIVE
    assert first.deployment_status is DeploymentStatus.ACTIVE
    assert first.target_refs == ("block-1",)
    assert first.proposed_actions == evaluation.proposed_actions
    assert first.evidence == evaluation.positive_evidence + evaluation.negative_evidence
    assert first.compatibility_flags == ("legacy-trace",)
    assert first.review_threshold == 0.60
    assert first.apply_threshold == 0.85
    json.dumps(to_json_data(first))
    with pytest.raises(FrozenInstanceError):
        first.sequence = 4  # type: ignore[misc]
    assert evaluation.score == 0.85
    assert descriptor.score_family == "heading"
