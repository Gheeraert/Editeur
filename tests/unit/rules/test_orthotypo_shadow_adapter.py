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
from purh_editorial.rules.orthotypography.etc_rule import (
    PRE_RULE_TEXT_FACT,
    RULE_ID,
    EtcAbbreviationRule,
)
from purh_editorial.rules.shadow import (
    ShadowComparisonStatus,
    ShadowDifferenceCode,
)
from purh_editorial.services.orthotypo_service import OrthotypoService
from purh_editorial.services.orthotypo_shadow_adapter import (
    OrthotypoEtcShadowAdapter,
    OrthotypoEtcShadowError,
)


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
    inlines: list[InlineSpan] | None = None,
) -> Note:
    return Note(
        note_id=note_id,
        text=text,
        target_ref=target_ref,
        inlines=inlines or [],
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
        before="etc...",
        after="etc.",
        rule_id=RULE_ID,
        applied=applied,
        attributes=(
            {
                "offset_start": 0,
                "offset_end": 6,
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


class _RecordingEtcRule:
    descriptor = EtcAbbreviationRule.descriptor

    def __init__(self) -> None:
        self.contexts = []
        self.delegate = EtcAbbreviationRule()

    def evaluate(self, context):
        self.contexts.append(context)
        return self.delegate.evaluate(context)


class _FailingThresholdPolicy:
    def thresholds(self, *, score_family: str, intervention_level: int):
        raise AssertionError("deterministic rule consulted thresholds")


@pytest.mark.parametrize(
    ("text", "expected", "outcome"),
    [
        ("etc...", "etc.", DecisionOutcome.APPLY),
        ("etc…", "etc.", DecisionOutcome.APPLY),
        ("Aucun motif.", "Aucun motif.", DecisionOutcome.IGNORE),
        ("etc... puis etc….", "etc. puis etc.", DecisionOutcome.APPLY),
    ],
)
def test_adapter_matches_simple_block_cases(
    text: str,
    expected: str,
    outcome: DecisionOutcome,
) -> None:
    result = OrthotypoEtcShadowAdapter().run(
        _document(blocks=[_block(text)])
    )
    assert result.legacy_document.blocks[0].text == expected
    assert len(result.native_decisions) == 1
    assert result.native_decisions[0].outcome is outcome
    assert result.comparisons[0].status is ShadowComparisonStatus.MATCH


def test_adapter_covers_blocks_then_notes_in_stable_order() -> None:
    result = OrthotypoEtcShadowAdapter().run(
        _document(
            blocks=[
                _block("etc...", block_id="p1"),
                _block("Rien.", block_id="p2"),
            ],
            notes=[_note("etc…", note_id="n1", target_ref="p2")],
        )
    )
    assert tuple(
        decision.target_refs for decision in result.native_decisions
    ) == (("p1",), ("p2",), ("n1",))
    assert tuple(
        decision.sequence for decision in result.native_decisions
    ) == (0, 1, 2)
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
    assert len(result.comparisons) == 3
    assert all(
        comparison.status is ShadowComparisonStatus.MATCH
        for comparison in result.comparisons
    )


@pytest.mark.parametrize(
    "document",
    [
        _document(blocks=[_block("etc...", protected=True)]),
        _document(notes=[_note("etc...", protected=True)]),
        _document(
            blocks=[_block("Bloc protégé.", block_type="quote_block")],
            notes=[_note("etc...", target_ref="p1")],
        ),
    ],
)
def test_protected_targets_propose_natively_but_remain_silent_and_match(
    document: Document,
) -> None:
    result = OrthotypoEtcShadowAdapter().run(document)
    decision = result.native_decisions[-1]
    comparison = result.comparisons[-1]
    assert decision.outcome is DecisionOutcome.IGNORE
    assert len(decision.proposed_actions) == 1
    assert decision.protection.protected is True
    assert decision.protection.legacy_behavior is True
    assert not [
        transformation
        for transformation in result.legacy_transformations
        if transformation.rule_id == RULE_ID
        and transformation.target_ref == decision.target_refs[0]
    ]
    assert comparison.status is ShadowComparisonStatus.MATCH


def test_inherited_note_protection_keeps_its_source_reference() -> None:
    result = OrthotypoEtcShadowAdapter().run(
        _document(
            blocks=[_block("Citation.", block_type="quote_block")],
            notes=[_note("etc...", target_ref="p1")],
        )
    )
    protection = result.native_decisions[1].protection
    assert protection.reasons == ("legacy_protected_note_inherited",)
    assert protection.inherited_from == ("p1",)


def test_explicit_note_protection_uses_its_distinct_reason() -> None:
    result = OrthotypoEtcShadowAdapter().run(
        _document(notes=[_note("etc...", protected=True)])
    )
    protection = result.native_decisions[0].protection
    assert protection.reasons == ("legacy_protected_note",)
    assert protection.inherited_from == ()


def test_inline_text_is_concatenated_like_the_legacy_service() -> None:
    document = _document(
        blocks=[
            _block(
                "stale",
                inlines=[InlineSpan("etc"), InlineSpan("... puis fin.")],
            )
        ]
    )
    result = OrthotypoEtcShadowAdapter().run(document)
    assert result.legacy_document.blocks[0].text == "etc. puis fin."
    assert result.native_decisions[0].proposed_actions[0].before == "etc..."
    assert result.comparisons[0].status is ShadowComparisonStatus.MATCH


@pytest.mark.parametrize(
    "source",
    [
        "xviième siècle, etc...",
        "xviième siècle, etc... et n° 5 ; pp. 12",
    ],
)
def test_pre_rule_text_replays_only_automatic_preceding_rules(
    source: str,
) -> None:
    native = _RecordingEtcRule()
    result = OrthotypoEtcShadowAdapter(native_rule=native).run(
        _document(blocks=[_block(source)])
    )
    pre_rule_text = native.contexts[0].source_facts[PRE_RULE_TEXT_FACT]
    assert pre_rule_text.startswith("XVIIe siècle, etc...")
    native_action = result.native_decisions[0].proposed_actions[0]
    legacy_action = result.comparisons[0].legacy_observation.observed_actions[0]
    assert (
        native_action.offset_start,
        native_action.offset_end,
    ) == (
        legacy_action.offset_start,
        legacy_action.offset_end,
    )
    assert result.comparisons[0].status is ShadowComparisonStatus.MATCH
    assert any(
        transformation.rule_id != RULE_ID
        for transformation in result.legacy_transformations
    )
    etc_transformations = tuple(
        transformation
        for transformation in result.legacy_transformations
        if transformation.rule_id == RULE_ID
    )
    observed_actions = (
        result.comparisons[0].legacy_observation.observed_actions
    )
    assert len(observed_actions) == len(etc_transformations)
    assert all(action.before.startswith("etc") for action in observed_actions)


def test_second_adapter_pass_is_idempotent_for_etc() -> None:
    first = OrthotypoEtcShadowAdapter().run(
        _document(blocks=[_block("etc...")])
    )
    second = OrthotypoEtcShadowAdapter().run(first.legacy_document)
    assert not [
        transformation
        for transformation in second.legacy_transformations
        if transformation.rule_id == RULE_ID
    ]
    assert second.native_decisions[0].outcome is DecisionOutcome.IGNORE
    assert second.comparisons[0].status is ShadowComparisonStatus.MATCH


def test_legacy_is_called_once_source_is_unchanged_and_all_effects_are_returned() -> None:
    source = _document(
        blocks=[_block("xviième siècle, etc... et n° 5 ; pp. 12")]
    )
    source_snapshot = copy.deepcopy(source)
    legacy = _RecordingLegacyService()
    result = OrthotypoEtcShadowAdapter(legacy_service=legacy).run(source)
    direct_document, direct_transformations = OrthotypoService().apply(source)
    assert legacy.calls == 1
    assert source == source_snapshot
    assert result.legacy_document == direct_document
    assert tuple(
        _semantic_transformation(item)
        for item in result.legacy_transformations
    ) == tuple(_semantic_transformation(item) for item in direct_transformations)
    assert {item.rule_id for item in result.legacy_transformations} > {RULE_ID}
    assert {
        action.action_type
        for action in result.comparisons[0].legacy_observation.observed_actions
    } == {RuleActionType.TEXT_TRANSFORM}


def test_native_proposal_is_never_applied_to_the_legacy_document() -> None:
    class DifferentNativeRule:
        descriptor = EtcAbbreviationRule.descriptor

        def evaluate(self, context):
            return DeterministicResult(
                rule_id=RULE_ID,
                matched=True,
                target_refs=context.target_refs,
                proposed_actions=(
                    ProposedAction(
                        RuleActionType.TEXT_TRANSFORM,
                        context.target_refs,
                        before="etc...",
                        after="NATIVE-NON-EXECUTÉ",
                        offset_start=0,
                        offset_end=6,
                    ),
                ),
                conditions_met=("test",),
                veto_reasons=(),
                justification="Proposition de test non exécutée.",
            )

    result = OrthotypoEtcShadowAdapter(
        native_rule=DifferentNativeRule()
    ).run(_document(blocks=[_block("etc...")]))
    assert result.legacy_document.blocks[0].text == "etc."
    assert result.comparisons[0].status is ShadowComparisonStatus.DIVERGENCE
    assert ShadowDifferenceCode.ACTION_CONTENT_MISMATCH in {
        difference.code for difference in result.comparisons[0].differences
    }


def test_deterministic_shadow_never_consults_thresholds() -> None:
    engine = CanonicalRuleDecisionEngine(_FailingThresholdPolicy())
    result = OrthotypoEtcShadowAdapter(engine=engine).run(
        _document(blocks=[_block("etc...")])
    )
    assert result.comparisons[0].status is ShadowComparisonStatus.MATCH


@pytest.mark.parametrize(
    "attributes,applied",
    [
        (
            {
                "offset_end": 6,
                "coordinate_space": "pre_rule_text",
            },
            True,
        ),
        (
            {
                "offset_start": 0,
                "offset_end": 6,
                "coordinate_space": "source_text",
            },
            True,
        ),
        (
            {
                "offset_start": 0,
                "offset_end": 6,
                "coordinate_space": "pre_rule_text",
            },
            False,
        ),
    ],
)
def test_mapping_failures_are_local_and_inconclusive(
    attributes: dict[str, object],
    applied: bool,
) -> None:
    legacy = _StaticLegacyService(
        [_transformation(attributes=attributes, applied=applied)]
    )
    result = OrthotypoEtcShadowAdapter(legacy_service=legacy).run(
        _document(blocks=[_block("etc...")])
    )
    comparison = result.comparisons[0]
    assert legacy.calls == 1
    assert comparison.status is ShadowComparisonStatus.INCONCLUSIVE
    assert (
        comparison.legacy_observation.error_code
        == "legacy_transformation_mapping_failed"
    )


def test_mapping_failure_keeps_actions_converted_before_the_failure() -> None:
    valid = _transformation()
    invalid = _transformation(
        attributes={
            "offset_end": 6,
            "coordinate_space": "pre_rule_text",
        }
    )
    result = OrthotypoEtcShadowAdapter(
        legacy_service=_StaticLegacyService([valid, invalid])
    ).run(_document(blocks=[_block("etc...")]))
    observation = result.comparisons[0].legacy_observation
    assert observation.status.value == "failed"
    assert len(observation.observed_actions) == 1


def test_unknown_legacy_target_is_a_global_adapter_error() -> None:
    legacy = _StaticLegacyService(
        [_transformation(target_ref="unknown")]
    )
    with pytest.raises(OrthotypoEtcShadowError, match="unknown source target"):
        OrthotypoEtcShadowAdapter(legacy_service=legacy).run(
            _document(blocks=[_block("etc...")])
        )


def test_duplicate_or_empty_target_identifiers_are_rejected() -> None:
    with pytest.raises(OrthotypoEtcShadowError, match="unique"):
        OrthotypoEtcShadowAdapter().run(
            _document(
                blocks=[_block("etc...", block_id="same")],
                notes=[_note("etc...", note_id="same")],
            )
        )
    with pytest.raises(OrthotypoEtcShadowError, match="non-empty"):
        OrthotypoEtcShadowAdapter().run(
            _document(blocks=[_block("etc...", block_id="")])
        )


def test_adapter_rejects_non_document_input() -> None:
    with pytest.raises(TypeError, match="Document"):
        OrthotypoEtcShadowAdapter().run("not a document")  # type: ignore[arg-type]
