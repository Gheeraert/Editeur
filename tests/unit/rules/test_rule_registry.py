from __future__ import annotations

from collections import Counter
from dataclasses import FrozenInstanceError, replace

import pytest

from purh_editorial.rules.model import (
    DeploymentStatus,
    ImplementationState,
    NormativeStatus,
    RuleActionType,
    RuleDescriptor,
    RuleFamily,
    RuleNature,
)
from purh_editorial.rules.registry import (
    CANONICAL_RULE_REGISTRY,
    CanonicalRuleRegistry,
)


EXPECTED_RULE_IDS = (
    "purh.apostrophe", "purh.points_suspension", "purh.guillemets.droits",
    "purh.ligature.oe", "purh.guillemets.espace_apres_ouvrant",
    "purh.guillemets.espace_avant_fermant", "purh.espaces.avant_ponct_forte",
    "purh.espaces.avant_ponct_faible", "purh.espaces.double", "purh.civilite",
    "purh.numeral_dynastique",
    "purh.siecles", "purh.siecles.style", "purh.ordinaux", "purh.ordinaux.style",
    "purh.civilite.style", "purh.tiret.double",
    "purh.abreviations.etc", "purh.pagination.espace", "purh.numero", "purh.numero.style",
    "purh.abreviations.redoublement", "purh.nombres.milliers",
    "purh.ecriture_inclusive.point_median", "purh.date.jour_mois", "purh.tiret.incise",
    "purh.tiret.incise.diagnostic", "purh.guillemets.ponctuation_fermante", "purh.note.espace_initiale",
    "purh.note.majuscule_initiale", "purh.note.abreviation_latine",
    "purh.note.espace_op_cit", "purh.note.espace_sans_lieu_date",
    "purh.note.ponctuation_finale", "purh.note.appel.placement", "purh.note.appel.espace_avant",
    "purh.note.diagnostic.debut_minuscule", "purh.note.diagnostic.ponctuation_finale_ambigue",
    "purh.note.italique_latin",
    "structure.bibliography.section.start", "structure.bibliography.section.end",
    "structure.bibliography.item.promote", "bibliography.entry.detect",
    "purh.biblio.pagination_nnbsp", "purh.biblio.numero_nnbsp",
    "purh.biblio.ponctuation_finale", "purh.biblio.casse_auteur",
    "structure.frontmatter.abstract",
    "structure.frontmatter.keywords", "structure.frontmatter.acknowledgment",
    "structure.frontmatter.circuit_breaker", "structure.source_style.heading",
    "structure.allcaps.heading", "structure.bold.heading", "structure.italic.author",
    "structure.italic.heading", "structure.epigraph.heuristic",
    "structure.bibliography.section", "structure.bibliography.heuristic",
    "structure.indent.quote", "structure.quote.guillemets", "structure.heading.heuristic",
    "structure.heading.diagnostic", "structure.lineated.blank_bounded.merge",
    "structure.lineated.short_sequence.merge", "structure.poetry.heuristique",
    "structure.lineated.group.annotate", "structure.lineated.stanza.merge",
)


EXPECTED_COUNTS = {
    "family": {
        RuleFamily.ORTHOTYPOGRAPHY: 28,
        RuleFamily.FOOTNOTE: 11,
        RuleFamily.BIBLIOGRAPHY: 8,
        RuleFamily.STRUCTURE: 21,
    },
    "nature": {
        RuleNature.DETERMINISTIC: 37,
        RuleNature.HEURISTIC: 31,
    },
    "action": {
        RuleActionType.TEXT_TRANSFORM: 30,
        RuleActionType.STYLE_TRANSFORM: 5,
        RuleActionType.STRUCTURE_TRANSFORM: 21,
        RuleActionType.DIAGNOSTIC: 8,
        RuleActionType.PIPELINE_CONTROL: 4,
    },
    "status": {
        DeploymentStatus.ACTIVE: 47,
        DeploymentStatus.REVIEW_ONLY: 18,
        DeploymentStatus.DISABLED: 3,
    },
    "state": {
        ImplementationState.LEGACY: 62,
        ImplementationState.PLANNED: 4,
        ImplementationState.DORMANT: 2,
    },
}


def _descriptor(rule_id: str, *, aliases: tuple[str, ...] = ()) -> RuleDescriptor:
    return RuleDescriptor(
        rule_id=rule_id,
        owner_module="tests.owner",
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action_type=RuleActionType.TEXT_TRANSFORM,
        deployment_status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        normative_sources=(),
        protection_policy_id="legacy.orthotypography",
        legacy_aliases=aliases,
        test_refs=("tests/unit/rules/test_rule_registry.py",),
    )


def test_canonical_registry_is_complete_valid_and_stably_ordered() -> None:
    descriptors = CANONICAL_RULE_REGISTRY.all()
    actual_ids = tuple(descriptor.rule_id for descriptor in descriptors)
    assert actual_ids == EXPECTED_RULE_IDS
    assert CANONICAL_RULE_REGISTRY.validate() == ()
    assert len({item.rule_id for item in descriptors}) == len(descriptors)


def test_registry_counts_match_the_pass_3_migration_table() -> None:
    descriptors = CANONICAL_RULE_REGISTRY.all()
    assert Counter(item.family for item in descriptors) == EXPECTED_COUNTS["family"]
    assert Counter(item.nature for item in descriptors) == EXPECTED_COUNTS["nature"]
    assert Counter(item.action_type for item in descriptors) == EXPECTED_COUNTS["action"]
    assert Counter(item.deployment_status for item in descriptors) == EXPECTED_COUNTS["status"]
    assert Counter(item.implementation_state for item in descriptors) == EXPECTED_COUNTS["state"]


def test_registry_access_filters_and_immutability() -> None:
    registry = CANONICAL_RULE_REGISTRY
    assert registry.get("purh.siecles").family is RuleFamily.ORTHOTYPOGRAPHY
    assert len(registry.by_family(RuleFamily.FOOTNOTE)) == 11
    assert len(registry.by_nature(RuleNature.HEURISTIC)) == 31
    assert len(registry.by_action(RuleActionType.STYLE_TRANSFORM)) == 5
    assert len(registry.by_status(DeploymentStatus.DISABLED)) == 3
    assert len(registry.by_implementation_state(ImplementationState.PLANNED)) == 4
    with pytest.raises(FrozenInstanceError):
        registry.descriptors = ()  # type: ignore[misc]
    with pytest.raises(KeyError):
        registry.get("missing.rule")


def test_registry_supports_aliases_and_detects_alias_conflicts() -> None:
    first = _descriptor("one", aliases=("legacy.one",))
    second = _descriptor("two")
    registry = CanonicalRuleRegistry((first, second))
    assert registry.get("legacy.one") is first
    assert registry.validate() == ()

    duplicate_alias = replace(second, legacy_aliases=("legacy.one",))
    errors = CanonicalRuleRegistry((first, duplicate_alias)).validate()
    assert any("duplicate alias" in error for error in errors)

    primary_conflict = replace(second, rule_id="legacy.one")
    errors = CanonicalRuleRegistry((first, primary_conflict)).validate()
    assert any("conflicts with a primary" in error for error in errors)


def test_registry_detects_duplicate_rule_ids() -> None:
    first = _descriptor("one")
    duplicate = replace(first)
    registry = CanonicalRuleRegistry((first, duplicate))
    errors = registry.validate()
    assert any("duplicate rule_id" in error for error in errors)


def test_four_families_statuses_and_implementation_states_are_present() -> None:
    descriptors = CANONICAL_RULE_REGISTRY.all()
    assert {item.family for item in descriptors} == set(RuleFamily)
    assert {item.deployment_status for item in descriptors} == set(DeploymentStatus)
    assert {item.implementation_state for item in descriptors} == {
        ImplementationState.LEGACY,
        ImplementationState.PLANNED,
        ImplementationState.DORMANT,
    }
    assert CANONICAL_RULE_REGISTRY.get("bibliography.entry.detect").implementation_state is ImplementationState.DORMANT
    assert CANONICAL_RULE_REGISTRY.get("structure.frontmatter.circuit_breaker").action_type is RuleActionType.PIPELINE_CONTROL
    assert (
        CANONICAL_RULE_REGISTRY.get("purh.note.ponctuation_finale").normative_status
        is NormativeStatus.INTERNAL_UNSOURCED
    )


def test_descriptors_contain_metadata_only() -> None:
    for descriptor in CANONICAL_RULE_REGISTRY.all():
        assert not callable(descriptor)
        for value in descriptor.__dataclass_fields__:
            field_value = getattr(descriptor, value)
            assert not callable(field_value)
