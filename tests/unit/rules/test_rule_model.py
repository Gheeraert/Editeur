from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import typing

import pytest

from purh_editorial.rules.model import (
    CompatibilityContext,
    DecisionOutcome,
    DeploymentStatus,
    DeterministicResult,
    EvidencePolarity,
    ExecutionResult,
    HeuristicEvidence,
    HeuristicProposal,
    ImplementationState,
    NormativeStatus,
    NormativeSource,
    ProposedAction,
    ProtectionDecision,
    RuleActionType,
    RuleDecision,
    RuleDescriptor,
    RuleFamily,
    RuleNature,
    ThresholdPair,
)


def _descriptor(**overrides: object) -> RuleDescriptor:
    values = {
        "rule_id": "test.rule",
        "owner_module": "tests.owner",
        "family": RuleFamily.ORTHOTYPOGRAPHY,
        "nature": RuleNature.DETERMINISTIC,
        "action_type": RuleActionType.TEXT_TRANSFORM,
        "deployment_status": DeploymentStatus.ACTIVE,
        "normative_status": NormativeStatus.INTERNAL_UNSOURCED,
        "normative_sources": (),
        "protection_policy_id": "test.policy",
        "test_refs": ("tests/unit/rules/test_rule_model.py",),
    }
    values.update(overrides)
    return RuleDescriptor(**values)  # type: ignore[arg-type]


def _protection() -> ProtectionDecision:
    return ProtectionDecision(False, "test.policy", ())


def _source(status: NormativeStatus) -> NormativeSource:
    return NormativeSource(
        source_id=f"test.{status.value}",
        authority="Tests",
        title="Source de test",
        status=status,
    )


def test_enum_values_are_stable_and_abstain_is_not_an_action() -> None:
    assert RuleFamily.ORTHOTYPOGRAPHY.value == "orthotypography"
    assert RuleNature.HEURISTIC.value == "heuristic"
    assert RuleActionType.PIPELINE_CONTROL.value == "pipeline_control"
    assert DecisionOutcome.REVIEW.value == "review"
    assert "ABSTAIN" not in RuleActionType.__members__


def test_dataclasses_are_frozen_and_descriptor_collections_are_tuples() -> None:
    descriptor = _descriptor()
    with pytest.raises(FrozenInstanceError):
        descriptor.rule_id = "other"  # type: ignore[misc]
    with pytest.raises(TypeError, match="test_refs must be a tuple"):
        _descriptor(test_refs=["tests/unit/rules/test_rule_model.py"])


def test_descriptor_validates_nature_score_and_aliases() -> None:
    with pytest.raises(ValueError, match="rule_id"):
        _descriptor(rule_id="")
    with pytest.raises(ValueError, match="owner_module"):
        _descriptor(owner_module="")
    with pytest.raises(ValueError, match="deterministic"):
        _descriptor(score_family="heading")
    with pytest.raises(ValueError, match="native heuristic"):
        _descriptor(
            nature=RuleNature.HEURISTIC,
            implementation_state=ImplementationState.NATIVE,
        )
    legacy = _descriptor(
        nature=RuleNature.HEURISTIC,
        implementation_state=ImplementationState.LEGACY,
    )
    assert legacy.score_family is None
    with pytest.raises(ValueError, match="cannot contain rule_id"):
        _descriptor(legacy_aliases=("test.rule",))


def test_normative_source_and_rule_statuses_are_typed_and_coherent() -> None:
    purh_source = _source(NormativeStatus.PURH_VALIDATED)
    assert purh_source.status is NormativeStatus.PURH_VALIDATED
    assert _descriptor(
        normative_status=NormativeStatus.PURH_VALIDATED,
        normative_sources=(purh_source,),
    ).normative_sources == (purh_source,)
    for status in (
        NormativeStatus.DOCUMENTED_GENERAL,
        NormativeStatus.CORPUS_OBSERVED,
    ):
        assert _descriptor(
            normative_status=status,
            normative_sources=(_source(status),),
        ).normative_status is status
    with pytest.raises(TypeError, match="NormativeStatus"):
        NormativeSource(
            source_id="test.invalid",
            authority="Tests",
            title="Source invalide",
            status="purh_validated",  # type: ignore[arg-type]
        )

    for rule_status, source_status in (
        (NormativeStatus.PURH_VALIDATED, NormativeStatus.DOCUMENTED_GENERAL),
        (NormativeStatus.DOCUMENTED_GENERAL, NormativeStatus.PURH_VALIDATED),
        (NormativeStatus.CORPUS_OBSERVED, NormativeStatus.DOCUMENTED_GENERAL),
    ):
        with pytest.raises(ValueError, match="matching source status"):
            _descriptor(
                normative_status=rule_status,
                normative_sources=(_source(source_status),),
            )

    assert _descriptor(
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        normative_sources=(),
    ).normative_sources == ()
    with pytest.raises(ValueError, match="cannot claim"):
        _descriptor(
            normative_status=NormativeStatus.INTERNAL_UNSOURCED,
            normative_sources=(_source(NormativeStatus.DOCUMENTED_GENERAL),),
        )
    assert _descriptor(
        normative_status=NormativeStatus.NOT_APPLICABLE,
        normative_sources=(),
    ).normative_status is NormativeStatus.NOT_APPLICABLE


def test_text_action_validates_targets_and_offsets() -> None:
    action = ProposedAction(
        RuleActionType.TEXT_TRANSFORM,
        ("p1",),
        before="a",
        after="b",
        offset_start=0,
        offset_end=1,
    )
    assert action.offset_start == 0
    with pytest.raises(ValueError, match="at least one target"):
        ProposedAction(RuleActionType.TEXT_TRANSFORM, ())
    with pytest.raises(ValueError, match="provided together"):
        ProposedAction(
            RuleActionType.TEXT_TRANSFORM,
            ("p1",),
            offset_start=0,
        )
    with pytest.raises(ValueError, match="greater than"):
        ProposedAction(
            RuleActionType.TEXT_TRANSFORM,
            ("p1",),
            offset_start=2,
            offset_end=1,
        )


def test_action_payloads_are_typed_and_incompatible_fields_are_rejected() -> None:
    diagnostic = ProposedAction(
        RuleActionType.DIAGNOSTIC,
        ("p1",),
        diagnostic_payload={"message": "À vérifier"},
    )
    assert diagnostic.diagnostic_payload == {"message": "À vérifier"}
    with pytest.raises(ValueError, match="require diagnostic_payload"):
        ProposedAction(RuleActionType.DIAGNOSTIC, ("p1",))

    style = ProposedAction(
        RuleActionType.STYLE_TRANSFORM,
        ("p1",),
        before="xvii",
        after="xvii",
        style_patch={"small_caps": True},
    )
    assert style.before == style.after
    with pytest.raises(TypeError):
        style.style_patch["small_caps"] = False  # type: ignore[index]

    control = ProposedAction(
        RuleActionType.PIPELINE_CONTROL,
        ("p1",),
        control_payload={"control": "circuit_breaker"},
    )
    assert control.control_payload == {"control": "circuit_breaker"}
    with pytest.raises(ValueError, match="require control_payload"):
        ProposedAction(RuleActionType.PIPELINE_CONTROL, ("p1",))


def test_deterministic_result_covers_transform_diagnostic_non_match_and_veto() -> None:
    transform = ProposedAction(
        RuleActionType.TEXT_TRANSFORM,
        ("p1",),
        before="XVIIème",
        after="XVIIe",
    )
    result = DeterministicResult(
        "purh.siecles",
        True,
        ("p1",),
        (transform,),
        ("century_context",),
        (),
        "Forme canonique reconnue.",
    )
    assert result.proposed_actions == (transform,)

    diagnostic = ProposedAction(
        RuleActionType.DIAGNOSTIC,
        ("p1",),
        diagnostic_payload={"message": "Espace avant appel de note."},
    )
    assert DeterministicResult(
        "R-AN-003",
        True,
        ("p1",),
        (diagnostic,),
        ("space_before_note_call",),
        (),
        "Placement certain, déplacement non automatisé.",
    ).matched

    non_match = DeterministicResult(
        "purh.siecles",
        False,
        ("p1",),
        (),
        (),
        (),
        "Motif absent.",
    )
    assert non_match.proposed_actions == ()
    with pytest.raises(ValueError, match="non-match"):
        DeterministicResult(
            "purh.siecles",
            False,
            ("p1",),
            (transform,),
            (),
            (),
            "Motif absent.",
        )
    with pytest.raises(ValueError, match="veto"):
        DeterministicResult(
            "purh.siecles",
            True,
            ("p1",),
            (transform,),
            ("century_context",),
            ("protected",),
            "Zone protégée.",
        )


def test_abstention_is_an_actionless_explained_result() -> None:
    result = DeterministicResult(
        "purh.tiret.incise",
        True,
        ("p1",),
        (),
        ("dash_candidate",),
        (),
        "Convention non tranchée : abstention explicite.",
    )
    assert result.proposed_actions == ()


def test_heuristic_proposal_validates_score_evidence_veto_and_fusion() -> None:
    positive = HeuristicEvidence(
        "short_lines",
        EvidencePolarity.POSITIVE,
        4,
        0.3,
        "Quatre lignes courtes.",
    )
    negative = HeuristicEvidence(
        "sentence_like",
        EvidencePolarity.NEGATIVE,
        False,
        -0.1,
        "Pas de phrase.",
    )
    fusion = ProposedAction(
        RuleActionType.STRUCTURE_TRANSFORM,
        ("v1", "v2", "v3"),
        before={"block_type": "paragraph"},
        after={"block_type": "lineated_block"},
        semantic_patch={"role": "quote", "lineation": "verse"},
        created_refs=("v1",),
        deleted_refs=("v2", "v3"),
        merged_refs=("v1", "v2", "v3"),
    )
    proposal = HeuristicProposal(
        "R-CI-POETRY-001",
        "poetry",
        0.82,
        (fusion,),
        ("v1", "v2", "v3"),
        (positive,),
        (negative,),
        (),
        "Séquence poétique probable.",
    )
    assert proposal.proposed_actions[0].merged_refs == ("v1", "v2", "v3")

    with pytest.raises(ValueError, match="between 0 and 1"):
        HeuristicProposal(
            "R-CI-POETRY-001",
            "poetry",
            1.1,
            (fusion,),
            ("v1",),
            (),
            (),
            (),
            "Score invalide.",
        )
    with pytest.raises(ValueError, match="distinct"):
        HeuristicProposal(
            "R-CI-POETRY-001",
            "poetry",
            0.5,
            (fusion,),
            ("v1",),
            (positive,),
            (
                HeuristicEvidence(
                    "short_lines",
                    EvidencePolarity.NEGATIVE,
                    False,
                    None,
                    "Conflit.",
                ),
            ),
            (),
            "Indices contradictoires.",
        )

    veto = HeuristicProposal(
        "R-CI-POETRY-001",
        "poetry",
        0.7,
        (),
        ("v1",),
        (),
        (),
        ("bibliography",),
        "Veto bibliographique.",
    )
    assert veto.proposed_actions == ()


def test_heuristic_evidence_requires_explicit_polarity_and_is_immutable() -> None:
    positive = HeuristicEvidence(
        "capital_letters",
        EvidencePolarity.POSITIVE,
        True,
        None,
        "Capitales observées.",
    )
    negative = HeuristicEvidence(
        "final_punctuation",
        EvidencePolarity.NEGATIVE,
        True,
        None,
        "Ponctuation de phrase observée.",
    )
    assert positive.polarity is EvidencePolarity.POSITIVE
    assert negative.polarity is EvidencePolarity.NEGATIVE
    assert positive.contribution is None
    with pytest.raises(FrozenInstanceError):
        positive.polarity = EvidencePolarity.NEGATIVE  # type: ignore[misc]
    with pytest.raises(TypeError, match="EvidencePolarity"):
        HeuristicEvidence(
            "invalid",
            "positive",  # type: ignore[arg-type]
            True,
            0.1,
            "Polarité invalide.",
        )


def test_heuristic_proposal_rejects_evidence_in_the_wrong_collection() -> None:
    positive = HeuristicEvidence(
        "short",
        EvidencePolarity.POSITIVE,
        True,
        0.2,
        "Indice positif.",
    )
    negative = HeuristicEvidence(
        "punctuation",
        EvidencePolarity.NEGATIVE,
        True,
        -0.1,
        "Indice négatif.",
    )
    action = ProposedAction(
        RuleActionType.STRUCTURE_TRANSFORM,
        ("p1",),
        semantic_patch={"role": "heading"},
    )
    for positives, negatives, message in (
        ((negative,), (), "positive_evidence"),
        ((), (positive,), "negative_evidence"),
    ):
        with pytest.raises(ValueError, match=message):
            HeuristicProposal(
                "test.heuristic",
                "heading",
                0.7,
                (action,),
                ("p1",),
                positives,
                negatives,
                (),
                "Collections incohérentes.",
            )


@pytest.mark.parametrize(
    ("review", "apply"),
    [(-0.1, 0.5), (0.6, 0.5), (0.5, 1.1)],
)
def test_threshold_pair_rejects_invalid_bounds(review: float, apply: float) -> None:
    with pytest.raises(ValueError):
        ThresholdPair(review, apply)


def test_rule_decision_has_only_minimal_coherence_validation() -> None:
    action = ProposedAction(
        RuleActionType.TEXT_TRANSFORM,
        ("p1",),
        before="a",
        after="b",
    )
    decision = RuleDecision(
        decision_id="decision-1",
        sequence=0,
        rule_id="test.rule",
        nature=RuleNature.DETERMINISTIC,
        implementation_state=ImplementationState.LEGACY,
        deployment_status=DeploymentStatus.ACTIVE,
        outcome=DecisionOutcome.APPLY,
        target_refs=("p1",),
        proposed_actions=(action,),
        reason_code="matched",
        score_family=None,
        score=None,
        review_threshold=None,
        apply_threshold=None,
        evidence=(),
        veto_reasons=(),
        protection=_protection(),
        compatibility_flags=(),
    )
    assert decision.sequence == 0
    with pytest.raises(ValueError, match="review_only"):
        replace(decision, deployment_status=DeploymentStatus.REVIEW_ONLY)
    with pytest.raises(ValueError, match="disabled"):
        replace(decision, deployment_status=DeploymentStatus.DISABLED)
    with pytest.raises(ValueError, match="veto"):
        replace(decision, veto_reasons=("protected",))


def test_native_heuristic_decision_requires_score_and_score_family() -> None:
    action = ProposedAction(
        RuleActionType.STRUCTURE_TRANSFORM,
        ("p1",),
        before={"block_type": "paragraph"},
        after={"block_type": "heading"},
    )
    with pytest.raises(ValueError, match="require score"):
        RuleDecision(
            decision_id="decision-heuristic",
            sequence=1,
            rule_id="R-STRUCT-HEADING-001",
            nature=RuleNature.HEURISTIC,
            implementation_state=ImplementationState.NATIVE,
            deployment_status=DeploymentStatus.ACTIVE,
            outcome=DecisionOutcome.REVIEW,
            target_refs=("p1",),
            proposed_actions=(action,),
            reason_code="review_band",
            score_family=None,
            score=None,
            review_threshold=None,
            apply_threshold=None,
            evidence=(),
            veto_reasons=(),
            protection=_protection(),
        )


def test_compatibility_context_requires_tuple_flags() -> None:
    assert CompatibilityContext(None).flags == ()
    with pytest.raises(TypeError):
        CompatibilityContext(None, flags=["legacy"])  # type: ignore[arg-type]


def test_execution_result_type_hints_resolve_at_runtime() -> None:
    hints = typing.get_type_hints(ExecutionResult)
    assert str(hints["transformations"]).startswith("tuple[")
    assert str(hints["diagnostics"]).startswith("tuple[")
