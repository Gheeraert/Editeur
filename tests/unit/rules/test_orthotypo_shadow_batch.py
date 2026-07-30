from __future__ import annotations

from collections import Counter
import copy

import pytest

from purh_editorial.model import Block, Document, Note, Transformation
from purh_editorial.rules.engine import CanonicalRuleDecisionEngine
from purh_editorial.rules.orthotypography.etc_rule import RULE_ID as ETC_RULE_ID
from purh_editorial.rules.orthotypography.ordinal_rule import (
    RULE_ID as ORDINAL_RULE_ID,
    OrdinalAbbreviationRule,
)
from purh_editorial.rules.orthotypography.redoublement_rule import (
    RULE_ID as REDOUBLEMENT_RULE_ID,
    RedoubledAbbreviationRule,
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
                    "etc... Voir pp. 12-14, la 1ère partie et "
                    "le 5ème chapitre."
                ),
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
                text="Voir pp. 2 et etc...",
                target_ref="p1",
            )
        ],
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
        ORDINAL_RULE_ID,
        ETC_RULE_ID,
        REDOUBLEMENT_RULE_ID,
    )
    expected_before = {
        ORDINAL_RULE_ID: {"1ère", "5ème"},
        ETC_RULE_ID: {"etc..."},
        REDOUBLEMENT_RULE_ID: {"pp."},
    }
    for rule_result in result.rule_results:
        observed_before = {
            action.before
            for comparison in rule_result.comparisons
            for action in comparison.legacy_observation.observed_actions
        }
        assert observed_before == expected_before[rule_result.rule_id]


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
        EtcAbbreviationRule.descriptor.protection_policy_id,
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
