from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
import re

import pytest

from purh_editorial.model import Block, Document, InlineSpan, Note, Transformation
from purh_editorial.rules.model import RuleActionType, to_json_data
from purh_editorial.rules.shadow import LegacyObservationStatus
from purh_editorial.services.orthotypo_service import TypoRule
from purh_editorial.services.orthotypo_shadow_support import (
    LEGACY_TRANSFORMATION_MAPPING_ERROR,
    build_legacy_text_observation,
    collect_orthotypo_shadow_targets,
    convert_legacy_text_transformation,
    find_legacy_orthotypo_rule_index,
    reconstruct_pre_rule_text,
)


RULE_ID = "test.text.rule"
POLICY_ID = "legacy.orthotypography"


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
    rule_id: str = RULE_ID,
    target_ref: str = "p1",
    before: object = "etc...",
    after: object = "etc.",
    applied: bool = True,
    operation: str = "orthotypo",
    attributes: dict[str, object] | None = None,
) -> Transformation:
    return Transformation(
        transformation_id="tr-1",
        module="orthotypo",
        target_ref=target_ref,
        operation=operation,
        before=before,  # type: ignore[arg-type]
        after=after,  # type: ignore[arg-type]
        rule_id=rule_id,
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


def _rule(
    rule_id: str,
    pattern: str,
    replacement: str,
    *,
    auto: bool = True,
) -> TypoRule:
    return TypoRule(
        rule_id=rule_id,
        pattern=re.compile(pattern),
        replacement=replacement,
        description=rule_id,
        auto=auto,
    )


def test_collects_blocks_then_notes_and_uses_inline_text() -> None:
    targets = collect_orthotypo_shadow_targets(
        _document(
            blocks=[
                _block(
                    "stale",
                    block_id="p1",
                    inlines=[InlineSpan("Texte "), InlineSpan("inline")],
                ),
                _block("Second", block_id="p2"),
            ],
            notes=[_note("Note", note_id="n1", target_ref="p2")],
        ),
        protection_policy_id=POLICY_ID,
    )
    assert tuple(target.target_ref for target in targets) == ("p1", "p2", "n1")
    assert tuple(target.text for target in targets) == (
        "Texte inline",
        "Second",
        "Note",
    )
    assert all(target.protection.legacy_behavior for target in targets)
    with pytest.raises(FrozenInstanceError):
        targets[0].text = "mutation"  # type: ignore[misc]


def test_collects_block_and_explicit_note_protections() -> None:
    targets = collect_orthotypo_shadow_targets(
        _document(
            blocks=[_block("Bloc", protected=True)],
            notes=[_note("Note", protected=True)],
        ),
        protection_policy_id=POLICY_ID,
    )
    assert targets[0].protection.reasons == ("legacy_protected_block",)
    assert targets[1].protection.reasons == ("legacy_protected_note",)
    assert targets[1].protection.inherited_from == ()


def test_collects_inherited_note_protection() -> None:
    targets = collect_orthotypo_shadow_targets(
        _document(
            blocks=[_block("Citation", block_type="quote_block")],
            notes=[_note("Note", target_ref="p1")],
        ),
        protection_policy_id=POLICY_ID,
    )
    assert targets[1].protection.reasons == (
        "legacy_protected_note_inherited",
    )
    assert targets[1].protection.inherited_from == ("p1",)


def test_collection_rejects_empty_or_duplicate_identifiers() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        collect_orthotypo_shadow_targets(
            _document(blocks=[_block("Texte", block_id="")]),
            protection_policy_id=POLICY_ID,
        )
    with pytest.raises(ValueError, match="unique"):
        collect_orthotypo_shadow_targets(
            _document(
                blocks=[_block("Texte", block_id="same")],
                notes=[_note("Note", note_id="same")],
            ),
            protection_policy_id=POLICY_ID,
        )


def test_finds_one_active_legacy_rule() -> None:
    rules = (
        _rule("before", "a", "b"),
        _rule(RULE_ID, "b", "c"),
        _rule("after", "c", "d"),
    )
    assert find_legacy_orthotypo_rule_index(RULE_ID, rules=rules) == 1


def test_find_rejects_missing_duplicate_and_inactive_rules() -> None:
    with pytest.raises(ValueError, match="exactly once"):
        find_legacy_orthotypo_rule_index(
            RULE_ID,
            rules=(_rule("other", "a", "b"),),
        )
    with pytest.raises(ValueError, match="exactly once"):
        find_legacy_orthotypo_rule_index(
            RULE_ID,
            rules=(
                _rule(RULE_ID, "a", "b"),
                _rule(RULE_ID, "b", "c"),
            ),
        )
    with pytest.raises(ValueError, match="auto=True"):
        find_legacy_orthotypo_rule_index(
            RULE_ID,
            rules=(_rule(RULE_ID, "a", "b", auto=False),),
        )


def test_reconstructs_only_automatic_rules_before_the_target() -> None:
    rules = (
        _rule("automatic-before", "a", "A"),
        _rule("inactive-before", "A", "X", auto=False),
        _rule(RULE_ID, "A", "TARGET"),
        _rule("automatic-after", "A", "AFTER"),
    )
    source = "a"
    reconstructed = reconstruct_pre_rule_text(
        source,
        rule_index=2,
        rules=rules,
    )
    assert reconstructed == "A"
    assert source == "a"


def test_converts_a_valid_text_transformation_exactly() -> None:
    action = convert_legacy_text_transformation(
        _transformation(),
        expected_rule_id=RULE_ID,
    )
    assert action.action_type is RuleActionType.TEXT_TRANSFORM
    assert action.target_refs == ("p1",)
    assert (action.before, action.after) == ("etc...", "etc.")
    assert (action.offset_start, action.offset_end) == (0, 6)


@pytest.mark.parametrize(
    ("transformation", "error"),
    [
        (_transformation(rule_id="other"), "rule_id"),
        (_transformation(applied=False), "applied"),
        (_transformation(operation="other"), "operation"),
        (_transformation(target_ref=""), "target_ref"),
        (_transformation(before=1), "before"),
        (_transformation(after=1), "after"),
        (
            _transformation(
                attributes={
                    "offset_end": 6,
                    "coordinate_space": "pre_rule_text",
                }
            ),
            "offset_start",
        ),
        (
            _transformation(
                attributes={
                    "offset_start": True,
                    "offset_end": 6,
                    "coordinate_space": "pre_rule_text",
                }
            ),
            "integers",
        ),
        (
            _transformation(
                attributes={
                    "offset_start": -1,
                    "offset_end": 6,
                    "coordinate_space": "pre_rule_text",
                }
            ),
            "invalid",
        ),
        (
            _transformation(
                attributes={
                    "offset_start": 7,
                    "offset_end": 6,
                    "coordinate_space": "pre_rule_text",
                }
            ),
            "invalid",
        ),
        (
            _transformation(
                attributes={
                    "offset_start": 0,
                    "offset_end": 6,
                    "coordinate_space": "source_text",
                }
            ),
            "coordinate_space",
        ),
    ],
)
def test_rejects_invalid_legacy_text_transformations(
    transformation: Transformation,
    error: str,
) -> None:
    with pytest.raises((KeyError, TypeError, ValueError), match=error):
        convert_legacy_text_transformation(
            transformation,
            expected_rule_id=RULE_ID,
        )


def test_builds_complete_silent_and_ordered_observations() -> None:
    silent = build_legacy_text_observation(
        rule_id=RULE_ID,
        target_ref="p1",
        transformations=(),
        sequence=0,
        observation_id="legacy:0:p1",
    )
    transformations = (
        _transformation(
            before="etc...",
            attributes={
                "offset_start": 0,
                "offset_end": 6,
                "coordinate_space": "pre_rule_text",
            },
        ),
        _transformation(
            before="etc…",
            attributes={
                "offset_start": 10,
                "offset_end": 14,
                "coordinate_space": "pre_rule_text",
            },
        ),
    )
    observed = build_legacy_text_observation(
        rule_id=RULE_ID,
        target_ref="p1",
        transformations=transformations,
        sequence=0,
        observation_id="legacy:0:p1",
    )
    assert silent.status is LegacyObservationStatus.COMPLETE
    assert silent.observed_actions == ()
    assert observed.status is LegacyObservationStatus.COMPLETE
    assert tuple(action.before for action in observed.observed_actions) == (
        "etc...",
        "etc…",
    )
    assert json.dumps(to_json_data(observed), ensure_ascii=False)


def test_failed_observation_stops_at_first_invalid_mapping() -> None:
    first_invalid = build_legacy_text_observation(
        rule_id=RULE_ID,
        target_ref="p1",
        transformations=(
            _transformation(rule_id="other"),
            _transformation(),
        ),
        sequence=0,
        observation_id="legacy:0:p1",
    )
    after_valid = build_legacy_text_observation(
        rule_id=RULE_ID,
        target_ref="p1",
        transformations=(
            _transformation(),
            _transformation(rule_id="other"),
            _transformation(),
        ),
        sequence=0,
        observation_id="legacy:0:p1",
    )
    assert first_invalid.status is LegacyObservationStatus.FAILED
    assert first_invalid.observed_actions == ()
    assert after_valid.status is LegacyObservationStatus.FAILED
    assert len(after_valid.observed_actions) == 1
    assert after_valid.error_code == LEGACY_TRANSFORMATION_MAPPING_ERROR
