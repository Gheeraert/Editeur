from __future__ import annotations

from collections import Counter
import copy
from dataclasses import replace

import pytest

from purh_editorial.model import (
    Block,
    Document,
    InlineSpan,
    InlineStyle,
    Note,
    Transformation,
)
from purh_editorial.rules.engine import CanonicalRuleDecisionEngine
from purh_editorial.rules.model import ProposedAction, RuleActionType
from purh_editorial.rules.orthotypography.century_rule import (
    RULE_ID as CENTURY_RULE_ID,
    CenturyAbbreviationRule,
)
from purh_editorial.rules.orthotypography.etc_rule import RULE_ID as ETC_RULE_ID
from purh_editorial.rules.orthotypography.numero_rule import (
    RULE_ID as NUMERO_RULE_ID,
    NumeroAbbreviationRule,
)
from purh_editorial.rules.orthotypography.ordinal_rule import (
    RULE_ID as ORDINAL_RULE_ID,
    OrdinalAbbreviationRule,
)
from purh_editorial.rules.orthotypography.redoublement_rule import (
    RULE_ID as REDOUBLEMENT_RULE_ID,
    RedoubledAbbreviationRule,
)
from purh_editorial.rules.orthotypography.pagination_spacing_rule import (
    RULE_ID as PAGINATION_RULE_ID,
    PaginationSpacingRule,
)
from purh_editorial.rules.orthotypography.etc_rule import EtcAbbreviationRule
from purh_editorial.rules.shadow import (
    LegacyObservationStatus,
    ShadowComparisonStatus,
)
import purh_editorial.services.orthotypo_shadow_batch as batch_module
from purh_editorial.services.orthotypo_ordinal_shadow_adapter import (
    OrthotypoOrdinalShadowAdapter,
)
from purh_editorial.services.orthotypo_redoublement_shadow_adapter import (
    OrthotypoRedoublementShadowAdapter,
)
from purh_editorial.services.orthotypo_service import OrthotypoService
from purh_editorial.services.orthotypo_shadow_adapter import (
    OrthotypoEtcShadowAdapter,
)
from purh_editorial.services.orthotypo_shadow_batch import (
    OrthotypoShadowBatchError,
    OrthotypoShadowBatchRunner,
)


def _document() -> Document:
    return Document(
        document_id="doc-1",
        source_path="source.docx",
        source_format="docx",
        blocks=[
            Block(
                block_id="p1",
                block_type="paragraph",
                text=(
                    "XVIIème siècle, etc... Voir pp. 12-14, n° 5, "
                    "la 1ère partie et le 5ème chapitre. "
                    "Formes canoniques : XVIIe siècle, p.\u202f9, no\u202f8. "
                    "La vie demeure."
                ),
                inlines=[
                    InlineSpan(
                        text=(
                            "XVIIème siècle, etc... Voir pp. 12-14, n° 5, "
                            "la 1ère partie et le 5ème chapitre. "
                            "Formes canoniques : XVIIe siècle, p.\u202f9, "
                            "no\u202f8. La vie demeure."
                        )
                    )
                ],
            ),
            Block(
                block_id="p2",
                block_type="paragraph",
                text="Sans proposition.",
            ),
            Block(
                block_id="p3",
                block_type="paragraph",
                text="etc... dans la 1ère annexe.",
                attributes={"protected": True},
            ),
        ],
        notes=[
            Note(
                note_id="n1",
                text="Au xviiième siècle, voir p. 2, n° 3 et etc...",
                target_ref="p1",
            )
        ],
    )


def _century_document(inlines: list[InlineSpan]) -> Document:
    text = "".join(span.text for span in inlines)
    return Document(
        document_id="century-doc",
        source_path="source.docx",
        source_format="docx",
        blocks=[
            Block(
                block_id="p1",
                block_type="paragraph",
                text=text,
                inlines=inlines,
            )
        ],
    )


def _styled_xviie_spans(*, roman_small_caps: bool = True, e_sup: bool = True):
    return [
        InlineSpan(text="au "),
        InlineSpan(text="xv", style=InlineStyle(small_caps=roman_small_caps)),
        InlineSpan(text="ii", style=InlineStyle(small_caps=roman_small_caps)),
        InlineSpan(text="e", style=InlineStyle(superscript=e_sup)),
        InlineSpan(text=" siècle"),
    ]


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

    def apply(
        self,
        document: Document,
    ) -> tuple[Document, list[Transformation]]:
        return copy.deepcopy(document), self.transformations


class _FailingThresholdPolicy:
    def thresholds(self, *, score_family: str, intervention_level: int):
        raise AssertionError("deterministic rule consulted thresholds")


def _ordinal_transformation(
    *,
    target_ref: str = "p1",
    attributes: dict[str, object] | None = None,
) -> Transformation:
    return Transformation(
        transformation_id="tr-test",
        module="orthotypo",
        target_ref=target_ref,
        operation="orthotypo",
        before="1ère",
        after="1re",
        rule_id=ORDINAL_RULE_ID,
        applied=True,
        attributes=(
            {
                "offset_start": 3,
                "offset_end": 7,
                "coordinate_space": "pre_rule_text",
            }
            if attributes is None
            else attributes
        ),
    )


def test_batch_calls_legacy_once_and_does_not_mutate_source() -> None:
    document = _document()
    snapshot = copy.deepcopy(document)
    legacy = _RecordingLegacyService()
    result = OrthotypoShadowBatchRunner(legacy_service=legacy).run(document)
    assert legacy.calls == 1
    assert document == snapshot
    assert result.legacy_document != document
    assert result.legacy_transformations


def test_batch_matches_all_three_individual_adapters_exactly() -> None:
    document = _document()
    batch = OrthotypoShadowBatchRunner().run(document)
    individual_results = {
        ETC_RULE_ID: OrthotypoEtcShadowAdapter().run(document),
        REDOUBLEMENT_RULE_ID: OrthotypoRedoublementShadowAdapter().run(document),
        ORDINAL_RULE_ID: OrthotypoOrdinalShadowAdapter().run(document),
    }
    for rule_id, individual in individual_results.items():
        grouped = batch.for_rule(rule_id)
        assert grouped.native_decisions == individual.native_decisions
        assert grouped.comparisons == individual.comparisons


def test_batch_results_follow_legacy_order_and_keep_rule_effects_separate() -> None:
    result = OrthotypoShadowBatchRunner().run(_document())
    assert tuple(item.rule_id for item in result.rule_results) == (
        CENTURY_RULE_ID,
        ORDINAL_RULE_ID,
        ETC_RULE_ID,
        PAGINATION_RULE_ID,
        NUMERO_RULE_ID,
        REDOUBLEMENT_RULE_ID,
    )
    expected_before = {
        CENTURY_RULE_ID: {"XVIIème", "xviiième"},
        ORDINAL_RULE_ID: {"1ère", "5ème"},
        ETC_RULE_ID: {"etc..."},
        PAGINATION_RULE_ID: {"pp. ", "p. "},
        NUMERO_RULE_ID: {"n° "},
        REDOUBLEMENT_RULE_ID: {"pp."},
    }
    for rule_result in result.rule_results:
        observed_before = {
            action.before
            for comparison in rule_result.comparisons
            for action in comparison.legacy_observation.observed_actions
        }
        assert observed_before == expected_before[rule_result.rule_id]
        assert all(
            comparison.status is ShadowComparisonStatus.MATCH
            for comparison in rule_result.comparisons
        )
    assert any(
        item.rule_id == "R-SO-001" for item in result.legacy_transformations
    )
    assert any(
        item.rule_id == "R-NO-001" for item in result.legacy_transformations
    )
    for rule_id in (CENTURY_RULE_ID, NUMERO_RULE_ID):
        assert all(
            action.action_type.value == "text_transform"
            for comparison in result.for_rule(rule_id).comparisons
            for action in comparison.legacy_observation.observed_actions
        )


def test_batch_reconciles_a_fully_styled_century_without_a_false_divergence() -> None:
    document = _century_document(_styled_xviie_spans())
    snapshot = copy.deepcopy(document)
    result = OrthotypoShadowBatchRunner().run(document)
    century = result.for_rule(CENTURY_RULE_ID)
    assert document == snapshot
    assert not [item for item in result.legacy_transformations if item.rule_id == CENTURY_RULE_ID]
    assert century.native_decisions[0].proposed_actions == ()
    assert century.native_decisions[0].outcome.value == "ignore"
    assert century.comparisons[0].status is ShadowComparisonStatus.MATCH


def test_batch_keeps_unstyled_and_incompletely_styled_century_actions() -> None:
    variants = (
        [InlineSpan(text="au xviie siècle")],
        _styled_xviie_spans(roman_small_caps=False),
        _styled_xviie_spans(e_sup=False),
    )
    for inlines in variants:
        result = OrthotypoShadowBatchRunner().run(_century_document(inlines))
        century = result.for_rule(CENTURY_RULE_ID)
        assert len(century.native_decisions[0].proposed_actions) == 1
        assert century.native_decisions[0].proposed_actions[0].before == "xviie"
        assert any(
            item.rule_id == CENTURY_RULE_ID
            for item in result.legacy_transformations
        )
        assert century.comparisons[0].status is ShadowComparisonStatus.MATCH


def test_batch_filters_only_the_fully_styled_century_in_a_mixed_target() -> None:
    inlines = [
        InlineSpan(text="au "),
        InlineSpan(text="xvii", style=InlineStyle(small_caps=True)),
        InlineSpan(text="e", style=InlineStyle(superscript=True)),
        InlineSpan(text=" et xviie siècles"),
    ]
    result = OrthotypoShadowBatchRunner().run(_century_document(inlines))
    century = result.for_rule(CENTURY_RULE_ID)
    assert tuple(action.before for action in century.native_decisions[0].proposed_actions) == (
        "xviie",
    )
    assert century.native_decisions[0].proposed_actions[0].offset_start == 12
    assert tuple(
        action.offset_start
        for action in century.native_decisions[0].proposed_actions
    ) == (12,)


def test_batch_reconciles_a_fully_styled_century_in_a_note() -> None:
    note_inlines = _styled_xviie_spans()
    document = Document(
        document_id="note-doc",
        source_path="source.docx",
        source_format="docx",
        blocks=[Block(block_id="p1", block_type="paragraph", text="Corps.")],
        notes=[
            Note(
                note_id="n1",
                text="".join(span.text for span in note_inlines),
                inlines=note_inlines,
                target_ref="p1",
            )
        ],
    )
    century = OrthotypoShadowBatchRunner().run(document).for_rule(CENTURY_RULE_ID)
    note_decision = next(
        decision for decision in century.native_decisions if decision.target_refs == ("n1",)
    )
    note_comparison = next(
        comparison for comparison in century.comparisons if comparison.rule_id == CENTURY_RULE_ID and comparison.sequence == 1
    )
    assert note_decision.proposed_actions == ()
    assert note_comparison.status is ShadowComparisonStatus.MATCH


def test_century_reconciliation_rejects_unsafe_inline_mappings() -> None:
    action = ProposedAction(
        action_type=RuleActionType.TEXT_TRANSFORM,
        target_refs=("p1",),
        before="xviie",
        after="XVIIe",
        offset_start=3,
        offset_end=8,
    )
    document = _century_document(_styled_xviie_spans())
    assert not batch_module._is_century_action_already_satisfied_by_style(
        action=action,
        document=document,
        target_ref="p1",
        target_text="mismatch",
    )
    assert not batch_module._is_century_action_already_satisfied_by_style(
        action=replace(action, offset_end=7),
        document=document,
        target_ref="p1",
        target_text="au xviie siècle",
    )
    no_inlines = Document(
        document_id="flat-century",
        source_path="source.docx",
        source_format="docx",
        blocks=[Block(block_id="p1", block_type="paragraph", text="au xviie siècle")],
    )
    assert not batch_module._is_century_action_already_satisfied_by_style(
        action=action,
        document=no_inlines,
        target_ref="p1",
        target_text="au xviie siècle",
    )
    document.blocks[0].inlines[1].kind = "field"
    assert not batch_module._is_century_action_already_satisfied_by_style(
        action=action,
        document=document,
        target_ref="p1",
        target_text="au xviie siècle",
    )


def test_batch_keeps_author_capital_century_out_of_the_text_rule() -> None:
    inlines = [
        InlineSpan(text="au XVII", style=InlineStyle(superscript=False)),
        InlineSpan(text="e", style=InlineStyle(superscript=True)),
        InlineSpan(text=" siècle"),
    ]
    result = OrthotypoShadowBatchRunner().run(_century_document(inlines))
    century = result.for_rule(CENTURY_RULE_ID)
    assert century.native_decisions[0].proposed_actions == ()
    assert not [item for item in result.legacy_transformations if item.rule_id == CENTURY_RULE_ID]
    assert century.comparisons[0].status is ShadowComparisonStatus.MATCH


def test_batch_refuses_unknown_rule_lookup_and_out_of_order_declaration(
    monkeypatch,
) -> None:
    result = OrthotypoShadowBatchRunner().run(_document())
    with pytest.raises(KeyError, match="unknown orthotypography shadow pilot"):
        result.for_rule("purh.unknown")
    monkeypatch.setattr(
        batch_module,
        "_PILOT_RULE_SPECS",
        tuple(reversed(batch_module._PILOT_RULE_SPECS)),
    )
    with pytest.raises(OrthotypoShadowBatchError, match="strict legacy order"):
        OrthotypoShadowBatchRunner().run(_document())


def test_batch_rejects_unknown_legacy_target() -> None:
    transformation = _ordinal_transformation(target_ref="unknown")
    with pytest.raises(OrthotypoShadowBatchError, match="unknown source target"):
        OrthotypoShadowBatchRunner(
            legacy_service=_StaticLegacyService([transformation])
        ).run(_document())


def test_mapping_failure_matches_individual_adapter_inconclusive_result() -> None:
    malformed = _ordinal_transformation(
        attributes={
            "offset_end": 7,
            "coordinate_space": "pre_rule_text",
        }
    )
    document = Document(
        document_id="doc-1",
        source_path="source.docx",
        source_format="docx",
        blocks=[
            Block(
                block_id="p1",
                block_type="paragraph",
                text="la 1ère partie",
            )
        ],
    )
    batch = OrthotypoShadowBatchRunner(
        legacy_service=_StaticLegacyService([malformed])
    ).run(document)
    individual = OrthotypoOrdinalShadowAdapter(
        legacy_service=_StaticLegacyService([malformed])
    ).run(document)
    grouped = batch.for_rule(ORDINAL_RULE_ID)
    assert grouped.comparisons == individual.comparisons
    assert (
        grouped.comparisons[0].legacy_observation.status
        is LegacyObservationStatus.FAILED
    )
    assert grouped.comparisons[0].status is ShadowComparisonStatus.INCONCLUSIVE


def test_target_collection_occurs_once_per_distinct_protection_policy(
    monkeypatch,
) -> None:
    original = batch_module.collect_orthotypo_shadow_targets
    calls: list[str] = []

    def recording_collection(document, *, protection_policy_id):
        calls.append(protection_policy_id)
        return original(
            document,
            protection_policy_id=protection_policy_id,
        )

    monkeypatch.setattr(
        batch_module,
        "collect_orthotypo_shadow_targets",
        recording_collection,
    )
    OrthotypoShadowBatchRunner().run(_document())
    expected_policies = {
        CenturyAbbreviationRule.descriptor.protection_policy_id,
        EtcAbbreviationRule.descriptor.protection_policy_id,
        PaginationSpacingRule.descriptor.protection_policy_id,
        NumeroAbbreviationRule.descriptor.protection_policy_id,
        RedoubledAbbreviationRule.descriptor.protection_policy_id,
        OrdinalAbbreviationRule.descriptor.protection_policy_id,
    }
    assert Counter(calls) == Counter({policy: 1 for policy in expected_policies})


def test_batch_deterministic_rules_never_consult_thresholds() -> None:
    engine = CanonicalRuleDecisionEngine(_FailingThresholdPolicy())
    result = OrthotypoShadowBatchRunner(engine=engine).run(_document())
    assert all(
        comparison.status is ShadowComparisonStatus.MATCH
        for rule_result in result.rule_results
        for comparison in rule_result.comparisons
    )


@pytest.mark.parametrize(
    "document",
    [None, "not-a-document"],
)
def test_batch_requires_document(document: object) -> None:
    with pytest.raises(TypeError, match="Document"):
        OrthotypoShadowBatchRunner().run(document)  # type: ignore[arg-type]
