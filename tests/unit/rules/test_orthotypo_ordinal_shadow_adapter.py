from __future__ import annotations

import copy

import pytest

from purh_editorial.model import Block, Document, Note, Transformation
from purh_editorial.rules.engine import CanonicalRuleDecisionEngine
from purh_editorial.rules.model import (
    DecisionOutcome,
    DeterministicResult,
    ProposedAction,
    RuleActionType,
)
from purh_editorial.rules.orthotypography.ordinal_rule import (
    PRE_RULE_TEXT_FACT,
    RULE_ID,
    OrdinalAbbreviationRule,
)
from purh_editorial.rules.shadow import (
    LegacyObservationStatus,
    ShadowComparisonStatus,
)
from purh_editorial.services.orthotypo_ordinal_shadow_adapter import (
    OrthotypoOrdinalShadowAdapter,
)
from purh_editorial.services.orthotypo_service import OrthotypoService


def _document(
    *,
    blocks: list[Block] | None = None,
    notes: list[Note] | None = None,
) -> Document:
    return Document(
        document_id="doc-1",
        source_path="source.docx",
        source_format="docx",
        blocks=blocks or [],
        notes=notes or [],
    )


def _block(
    text: str,
    *,
    block_id: str = "p1",
    block_type: str = "paragraph",
    protected: bool = False,
) -> Block:
    return Block(
        block_id=block_id,
        block_type=block_type,
        text=text,
        attributes={"protected": True} if protected else {},
    )


def _note(
    text: str,
    *,
    note_id: str = "n1",
    target_ref: str | None = None,
    protected: bool = False,
) -> Note:
    return Note(
        note_id=note_id,
        text=text,
        target_ref=target_ref,
        attributes={"protected": True} if protected else {},
    )


class _RecordingLegacyService:
    def __init__(self) -> None:
        self.calls = 0
        self.delegate = OrthotypoService()

    def apply(
        self,
        document: Document,
    ) -> tuple[Document, list[Transformation]]:
        self.calls += 1
        return self.delegate.apply(document)


class _RecordingOrdinalRule:
    descriptor = OrdinalAbbreviationRule.descriptor

    def __init__(self) -> None:
        self.contexts = []
        self.delegate = OrdinalAbbreviationRule()

    def evaluate(self, context):
        self.contexts.append(context)
        return self.delegate.evaluate(context)


class _StaticLegacyService:
    def __init__(self, transformation: Transformation) -> None:
        self.transformation = transformation

    def apply(
        self,
        document: Document,
    ) -> tuple[Document, list[Transformation]]:
        return copy.deepcopy(document), [self.transformation]


class _FailingThresholdPolicy:
    def thresholds(self, *, score_family: str, intervention_level: int):
        raise AssertionError("deterministic rule consulted thresholds")


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("la 1ère partie", "la 1re partie"),
        ("la 1ere partie", "la 1re partie"),
        ("le 5ème chapitre", "le 5e chapitre"),
        ("le 5eme chapitre", "le 5e chapitre"),
    ],
)
def test_adapter_matches_the_supported_ordinal_forms(
    source: str,
    expected: str,
) -> None:
    result = OrthotypoOrdinalShadowAdapter().run(
        _document(blocks=[_block(source)])
    )
    assert result.legacy_document.blocks[0].text == expected
    assert result.native_decisions[0].outcome is DecisionOutcome.APPLY
    assert result.comparisons[0].status is ShadowComparisonStatus.MATCH


def test_adapter_matches_multiple_actions_and_a_note() -> None:
    result = OrthotypoOrdinalShadowAdapter().run(
        _document(
            blocks=[
                _block("la 1ère partie et le 5ème chapitre", block_id="p1"),
            ],
            notes=[_note("la 1ere annexe", note_id="n1")],
        )
    )
    assert tuple(
        action.before for action in result.native_decisions[0].proposed_actions
    ) == ("1ère", "5ème")
    assert result.legacy_document.blocks[0].text == (
        "la 1re partie et le 5e chapitre"
    )
    assert result.legacy_document.notes[0].text == "la 1re annexe"
    assert all(
        comparison.status is ShadowComparisonStatus.MATCH
        for comparison in result.comparisons
    )


def test_guardrails_have_no_proposal_and_match_legacy_silence() -> None:
    result = OrthotypoOrdinalShadowAdapter().run(
        _document(
            blocks=[
                _block("le 1er chapitre", block_id="p1"),
                _block("version 2.0", block_id="p2"),
                _block("Ier, Ie, 2de et 2nde", block_id="p3"),
            ]
        )
    )
    assert all(
        decision.outcome is DecisionOutcome.IGNORE
        and not decision.proposed_actions
        for decision in result.native_decisions
    )
    assert all(
        comparison.status is ShadowComparisonStatus.MATCH
        for comparison in result.comparisons
    )


def test_pre_rule_text_is_reconstructed_before_ordinal_evaluation() -> None:
    native = _RecordingOrdinalRule()
    result = OrthotypoOrdinalShadowAdapter(native_rule=native).run(
        _document(blocks=[_block("xviième siècle, la 1ère partie")])
    )
    assert native.contexts[0].source_facts[PRE_RULE_TEXT_FACT] == (
        "XVIIe siècle, la 1ère partie"
    )
    assert result.comparisons[0].status is ShadowComparisonStatus.MATCH


def test_neighboring_rule_effects_are_not_observed_as_ordinals() -> None:
    result = OrthotypoOrdinalShadowAdapter().run(
        _document(blocks=[_block("xviième siècle, la 1ère partie, etc...")])
    )
    assert {item.rule_id for item in result.legacy_transformations} > {RULE_ID}
    observed = result.comparisons[0].legacy_observation.observed_actions
    assert len(observed) == 1
    assert observed[0].before == "1ère"
    assert result.comparisons[0].status is ShadowComparisonStatus.MATCH


@pytest.mark.parametrize(
    "document",
    [
        _document(blocks=[_block("la 1ère partie", protected=True)]),
        _document(notes=[_note("la 1ère partie", protected=True)]),
        _document(
            blocks=[_block("Citation.", block_type="quote_block")],
            notes=[_note("la 1ère partie", target_ref="p1")],
        ),
    ],
)
def test_protected_targets_propose_but_match_legacy_silence(
    document: Document,
) -> None:
    result = OrthotypoOrdinalShadowAdapter().run(document)
    decision = result.native_decisions[-1]
    comparison = result.comparisons[-1]
    assert decision.outcome is DecisionOutcome.IGNORE
    assert decision.proposed_actions[0].before == "1ère"
    assert comparison.legacy_observation.observed_actions == ()
    assert comparison.status is ShadowComparisonStatus.MATCH


def test_legacy_is_called_once_source_is_unchanged_and_second_pass_is_quiet() -> None:
    source = _document(blocks=[_block("la 1ère partie")])
    snapshot = copy.deepcopy(source)
    legacy = _RecordingLegacyService()
    first = OrthotypoOrdinalShadowAdapter(legacy_service=legacy).run(source)
    second = OrthotypoOrdinalShadowAdapter().run(first.legacy_document)
    assert legacy.calls == 1
    assert source == snapshot
    assert not [
        transformation
        for transformation in second.legacy_transformations
        if transformation.rule_id == RULE_ID
    ]
    assert second.native_decisions[0].outcome is DecisionOutcome.IGNORE
    assert second.comparisons[0].status is ShadowComparisonStatus.MATCH


def test_native_divergence_is_visible_but_not_executed() -> None:
    class DifferentNativeRule:
        descriptor = OrdinalAbbreviationRule.descriptor

        def evaluate(self, context):
            return DeterministicResult(
                rule_id=RULE_ID,
                matched=True,
                target_refs=context.target_refs,
                proposed_actions=(
                    ProposedAction(
                        RuleActionType.TEXT_TRANSFORM,
                        context.target_refs,
                        before="1ère",
                        after="NATIVE-NON-EXECUTÉ",
                        offset_start=3,
                        offset_end=7,
                    ),
                ),
                conditions_met=("test",),
                veto_reasons=(),
                justification="Proposition de test non exécutée.",
            )

    result = OrthotypoOrdinalShadowAdapter(
        native_rule=DifferentNativeRule()
    ).run(_document(blocks=[_block("la 1ère partie")]))
    assert result.legacy_document.blocks[0].text == "la 1re partie"
    assert result.comparisons[0].status is ShadowComparisonStatus.DIVERGENCE


def test_mapping_failure_is_inconclusive() -> None:
    malformed = Transformation(
        transformation_id="tr-test",
        module="orthotypo",
        target_ref="p1",
        operation="orthotypo",
        before="1ère",
        after="1re",
        rule_id=RULE_ID,
        applied=True,
        attributes={"offset_end": 7, "coordinate_space": "pre_rule_text"},
    )
    result = OrthotypoOrdinalShadowAdapter(
        legacy_service=_StaticLegacyService(malformed)
    ).run(_document(blocks=[_block("la 1ère partie")]))
    assert (
        result.comparisons[0].legacy_observation.status
        is LegacyObservationStatus.FAILED
    )
    assert result.comparisons[0].status is ShadowComparisonStatus.INCONCLUSIVE


def test_deterministic_vertical_never_consults_thresholds() -> None:
    engine = CanonicalRuleDecisionEngine(_FailingThresholdPolicy())
    result = OrthotypoOrdinalShadowAdapter(engine=engine).run(
        _document(blocks=[_block("la 1ère partie")])
    )
    assert result.comparisons[0].status is ShadowComparisonStatus.MATCH
