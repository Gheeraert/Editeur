from __future__ import annotations

import copy

import pytest

from purh_editorial.model import Block, Document, InlineSpan, Note, Transformation
from purh_editorial.rules.engine import CanonicalRuleDecisionEngine
from purh_editorial.rules.model import (
    DecisionOutcome,
    DeterministicResult,
    ProposedAction,
    RuleActionType,
)
from purh_editorial.rules.orthotypography.redoublement_rule import (
    PRE_RULE_TEXT_FACT,
    RULE_ID,
    RedoubledAbbreviationRule,
)
from purh_editorial.rules.shadow import (
    LegacyObservationStatus,
    ShadowComparisonStatus,
    ShadowDifferenceCode,
)
from purh_editorial.services.orthotypo_redoublement_shadow_adapter import (
    OrthotypoRedoublementShadowAdapter,
    OrthotypoRedoublementShadowError,
)
from purh_editorial.services.orthotypo_service import OrthotypoService


NNBSP = "\u202f"


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
    inlines: list[InlineSpan] | None = None,
) -> Block:
    return Block(
        block_id=block_id,
        block_type=block_type,
        text=text,
        inlines=inlines or [],
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


def _transformation(
    *,
    target_ref: str = "p1",
    applied: bool = True,
    attributes: dict[str, object] | None = None,
) -> Transformation:
    return Transformation(
        transformation_id="tr-test",
        module="orthotypo",
        target_ref=target_ref,
        operation="orthotypo",
        before="pp.",
        after="p.",
        rule_id=RULE_ID,
        applied=applied,
        attributes=(
            {
                "offset_start": 0,
                "offset_end": 3,
                "coordinate_space": "pre_rule_text",
            }
            if attributes is None
            else attributes
        ),
    )


def _semantic_transformation(transformation: Transformation) -> tuple[object, ...]:
    return (
        transformation.module,
        transformation.target_ref,
        transformation.operation,
        transformation.before,
        transformation.after,
        transformation.rule_id,
        transformation.applied,
        transformation.validated_by_human,
        transformation.attributes,
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


class _StaticLegacyService:
    def __init__(self, transformations: list[Transformation]) -> None:
        self.transformations = transformations
        self.calls = 0

    def apply(
        self,
        document: Document,
    ) -> tuple[Document, list[Transformation]]:
        self.calls += 1
        return copy.deepcopy(document), self.transformations


class _RecordingRedoublementRule:
    descriptor = RedoubledAbbreviationRule.descriptor

    def __init__(self) -> None:
        self.contexts = []
        self.delegate = RedoubledAbbreviationRule()

    def evaluate(self, context):
        self.contexts.append(context)
        return self.delegate.evaluate(context)


class _FailingThresholdPolicy:
    def thresholds(self, *, score_family: str, intervention_level: int):
        raise AssertionError("deterministic rule consulted thresholds")


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("pp. 53-84", f"p.{NNBSP}53-84"),
        ("vv. 122-128", "v. 122-128"),
        ("ll. 5 et 12", "l. 5 et 12"),
        ("§§ 5-9", "§ 5-9"),
    ],
)
def test_adapter_matches_each_positive_form(
    source: str,
    expected: str,
) -> None:
    result = OrthotypoRedoublementShadowAdapter().run(
        _document(blocks=[_block(source)])
    )
    assert result.legacy_document.blocks[0].text == expected
    assert result.native_decisions[0].outcome is DecisionOutcome.APPLY
    assert result.comparisons[0].status is ShadowComparisonStatus.MATCH


def test_adapter_handles_multiple_occurrences_and_inlines() -> None:
    result = OrthotypoRedoublementShadowAdapter().run(
        _document(
            blocks=[
                _block(
                    "stale",
                    inlines=[
                        InlineSpan("pp. 1, "),
                        InlineSpan("vv. 2 et §§ 3"),
                    ],
                )
            ]
        )
    )
    assert result.legacy_document.blocks[0].text == (
        f"p.{NNBSP}1, v. 2 et § 3"
    )
    assert tuple(
        action.before
        for action in result.native_decisions[0].proposed_actions
    ) == ("pp.", "vv.", "§§")
    assert result.comparisons[0].status is ShadowComparisonStatus.MATCH


def test_mixed_document_has_one_decision_and_comparison_per_target() -> None:
    result = OrthotypoRedoublementShadowAdapter().run(
        _document(
            blocks=[
                _block("pp. 1", block_id="p1"),
                _block("Sans motif.", block_id="p2"),
            ],
            notes=[_note("vv. 2", note_id="n1", target_ref="p2")],
        )
    )
    assert len(result.native_decisions) == 3
    assert len(result.comparisons) == 3
    assert tuple(
        decision.decision_id for decision in result.native_decisions
    ) == (
        f"native:{RULE_ID}:0:p1",
        f"native:{RULE_ID}:1:p2",
        f"native:{RULE_ID}:2:n1",
    )
    assert tuple(
        comparison.comparison_id for comparison in result.comparisons
    ) == (
        f"shadow:{RULE_ID}:0:p1",
        f"shadow:{RULE_ID}:1:p2",
        f"shadow:{RULE_ID}:2:n1",
    )
    assert all(
        comparison.status is ShadowComparisonStatus.MATCH
        for comparison in result.comparisons
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("voir p. 12", f"voir p.{NNBSP}12"),
        ("supp. cit.", "supp. cit."),
    ],
)
def test_negative_redoublement_cases_match_legacy_silence(
    source: str,
    expected: str,
) -> None:
    result = OrthotypoRedoublementShadowAdapter().run(
        _document(blocks=[_block(source)])
    )
    assert result.legacy_document.blocks[0].text == expected
    assert result.native_decisions[0].outcome is DecisionOutcome.IGNORE
    assert not result.comparisons[0].legacy_observation.observed_actions
    assert result.comparisons[0].status is ShadowComparisonStatus.MATCH


def test_pp_is_evaluated_after_legacy_pagination_spacing() -> None:
    native = _RecordingRedoublementRule()
    result = OrthotypoRedoublementShadowAdapter(native_rule=native).run(
        _document(blocks=[_block("pp. 53-84")])
    )
    pre_rule_text = native.contexts[0].source_facts[PRE_RULE_TEXT_FACT]
    assert pre_rule_text == f"pp.{NNBSP}53-84"
    native_action = result.native_decisions[0].proposed_actions[0]
    legacy_action = result.comparisons[0].legacy_observation.observed_actions[0]
    assert (native_action.before, native_action.after) == ("pp.", "p.")
    assert (
        native_action.offset_start,
        native_action.offset_end,
    ) == (
        legacy_action.offset_start,
        legacy_action.offset_end,
    ) == (0, 3)
    assert result.legacy_document.blocks[0].text == f"p.{NNBSP}53-84"


def test_neighboring_rules_remain_outside_the_redoublement_observation() -> None:
    source = "xviième siècle, pp. 53-84, etc... et n° 5"
    native = _RecordingRedoublementRule()
    result = OrthotypoRedoublementShadowAdapter(native_rule=native).run(
        _document(blocks=[_block(source)])
    )
    pre_rule_text = native.contexts[0].source_facts[PRE_RULE_TEXT_FACT]
    assert pre_rule_text.startswith(f"XVIIe siècle, pp.{NNBSP}53-84, etc.")
    assert {item.rule_id for item in result.legacy_transformations} > {RULE_ID}
    filtered = tuple(
        item for item in result.legacy_transformations
        if item.rule_id == RULE_ID
    )
    observed = result.comparisons[0].legacy_observation.observed_actions
    assert len(observed) == len(filtered) == 1
    assert observed[0].before == "pp."
    assert result.comparisons[0].status is ShadowComparisonStatus.MATCH


@pytest.mark.parametrize(
    "document",
    [
        _document(blocks=[_block("pp. 12", protected=True)]),
        _document(notes=[_note("pp. 12", protected=True)]),
        _document(
            blocks=[_block("Citation.", block_type="quote_block")],
            notes=[_note("pp. 12", target_ref="p1")],
        ),
    ],
)
def test_protected_targets_propose_but_remain_silent_and_match(
    document: Document,
) -> None:
    result = OrthotypoRedoublementShadowAdapter().run(document)
    decision = result.native_decisions[-1]
    comparison = result.comparisons[-1]
    assert decision.outcome is DecisionOutcome.IGNORE
    assert decision.proposed_actions[0].before == "pp."
    assert decision.protection.protected is True
    assert comparison.legacy_observation.observed_actions == ()
    assert comparison.status is ShadowComparisonStatus.MATCH


def test_second_pass_is_idempotent_for_redoublement() -> None:
    first = OrthotypoRedoublementShadowAdapter().run(
        _document(blocks=[_block("pp. 12")])
    )
    second = OrthotypoRedoublementShadowAdapter().run(first.legacy_document)
    assert not [
        item for item in second.legacy_transformations
        if item.rule_id == RULE_ID
    ]
    assert second.native_decisions[0].outcome is DecisionOutcome.IGNORE
    assert second.comparisons[0].status is ShadowComparisonStatus.MATCH


def test_legacy_is_called_once_and_remains_the_only_source_of_effects() -> None:
    source = _document(
        blocks=[_block("xviième siècle, pp. 53-84, etc... et n° 5")]
    )
    source_snapshot = copy.deepcopy(source)
    legacy = _RecordingLegacyService()
    result = OrthotypoRedoublementShadowAdapter(
        legacy_service=legacy
    ).run(source)
    direct_document, direct_transformations = OrthotypoService().apply(source)
    assert legacy.calls == 1
    assert source == source_snapshot
    assert result.legacy_document == direct_document
    assert tuple(
        _semantic_transformation(item)
        for item in result.legacy_transformations
    ) == tuple(_semantic_transformation(item) for item in direct_transformations)


def test_native_divergence_is_reported_but_never_executed() -> None:
    class DifferentNativeRule:
        descriptor = RedoubledAbbreviationRule.descriptor

        def evaluate(self, context):
            return DeterministicResult(
                rule_id=RULE_ID,
                matched=True,
                target_refs=context.target_refs,
                proposed_actions=(
                    ProposedAction(
                        RuleActionType.TEXT_TRANSFORM,
                        context.target_refs,
                        before="pp.",
                        after="NATIVE-NON-EXECUTÉ",
                        offset_start=0,
                        offset_end=3,
                    ),
                ),
                conditions_met=("test",),
                veto_reasons=(),
                justification="Proposition de test non exécutée.",
            )

    result = OrthotypoRedoublementShadowAdapter(
        native_rule=DifferentNativeRule()
    ).run(_document(blocks=[_block("pp. 12")]))
    assert result.legacy_document.blocks[0].text == f"p.{NNBSP}12"
    assert result.comparisons[0].status is ShadowComparisonStatus.DIVERGENCE
    assert ShadowDifferenceCode.ACTION_CONTENT_MISMATCH in {
        difference.code for difference in result.comparisons[0].differences
    }


@pytest.mark.parametrize(
    "attributes,applied",
    [
        (
            {
                "offset_end": 3,
                "coordinate_space": "pre_rule_text",
            },
            True,
        ),
        (
            {
                "offset_start": 0,
                "offset_end": 3,
                "coordinate_space": "source_text",
            },
            True,
        ),
        (
            {
                "offset_start": 0,
                "offset_end": 3,
                "coordinate_space": "pre_rule_text",
            },
            False,
        ),
    ],
)
def test_mapping_defects_are_failed_and_inconclusive(
    attributes: dict[str, object],
    applied: bool,
) -> None:
    legacy = _StaticLegacyService(
        [_transformation(attributes=attributes, applied=applied)]
    )
    result = OrthotypoRedoublementShadowAdapter(
        legacy_service=legacy
    ).run(_document(blocks=[_block("pp. 12")]))
    observation = result.comparisons[0].legacy_observation
    assert observation.status is LegacyObservationStatus.FAILED
    assert result.comparisons[0].status is ShadowComparisonStatus.INCONCLUSIVE


def test_unknown_legacy_target_is_rejected() -> None:
    legacy = _StaticLegacyService(
        [_transformation(target_ref="unknown")]
    )
    with pytest.raises(
        OrthotypoRedoublementShadowError,
        match="unknown source target",
    ):
        OrthotypoRedoublementShadowAdapter(legacy_service=legacy).run(
            _document(blocks=[_block("pp. 12")])
        )


def test_deterministic_vertical_never_consults_thresholds() -> None:
    engine = CanonicalRuleDecisionEngine(_FailingThresholdPolicy())
    result = OrthotypoRedoublementShadowAdapter(engine=engine).run(
        _document(blocks=[_block("pp. 12")])
    )
    assert result.comparisons[0].status is ShadowComparisonStatus.MATCH
