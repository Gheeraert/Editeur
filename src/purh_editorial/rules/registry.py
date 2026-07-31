from __future__ import annotations

from dataclasses import dataclass

from purh_editorial.rules.model import (
    DeploymentStatus,
    ImplementationState,
    NormativeSource,
    NormativeStatus,
    RuleActionType,
    RuleDescriptor,
    RuleFamily,
    RuleNature,
)


ORTHO_OWNER = "purh_editorial.services.orthotypo_service"
FOOTNOTE_OWNER = "purh_editorial.services.footnote_normalizer"
BIBLIO_OWNER = "purh_editorial.services.bibliography_normalizer"
STRUCTURE_OWNER = "purh_editorial.services.structure_service"

ORTHO_TEST = "tests/unit/test_orthotypo_deployment_characterization.py"
FOOTNOTE_TEST = "tests/unit/test_footnote_characterization_matrix.py"
BIBLIO_TEST = "tests/unit/test_bibliography_characterization_boundaries.py"
STRUCTURE_TEST = "tests/unit/test_structure_characterization_modes_and_protection.py"
PROTECTION_TEST = "tests/unit/test_protection_asymmetry_characterization.py"

PURH_P10 = NormativeSource(
    source_id="purh.guide.p10",
    authority="PURH",
    title="Guide de préparation éditoriale",
    locator="p. 10",
    status=NormativeStatus.PURH_VALIDATED,
)
PURH_P11 = NormativeSource(
    source_id="purh.guide.p11",
    authority="PURH",
    title="Guide de préparation éditoriale",
    locator="p. 11",
    status=NormativeStatus.PURH_VALIDATED,
)
PURH_P11_12 = NormativeSource(
    source_id="purh.guide.p11-12",
    authority="PURH",
    title="Guide de préparation éditoriale",
    locator="p. 11-12",
    status=NormativeStatus.PURH_VALIDATED,
)
PURH_P12 = NormativeSource(
    source_id="purh.guide.p12",
    authority="PURH",
    title="Guide de préparation éditoriale",
    locator="p. 12",
    status=NormativeStatus.PURH_VALIDATED,
)
GENERAL_TYPOGRAPHY = NormativeSource(
    source_id="typography.general",
    authority="Référence typographique générale",
    title="Convention typographique générale à confirmer pour les PURH",
    status=NormativeStatus.DOCUMENTED_GENERAL,
)
OBSERVED_CORPUS = NormativeSource(
    source_id="purh.corpus.observed",
    authority="PURH",
    title="Comportements observés dans le corpus de caractérisation",
    status=NormativeStatus.CORPUS_OBSERVED,
)


def _rule(
    rule_id: str,
    *,
    owner: str,
    family: RuleFamily,
    nature: RuleNature,
    action: RuleActionType,
    status: DeploymentStatus,
    normative_status: NormativeStatus,
    sources: tuple[NormativeSource, ...] = (),
    score_family: str | None = None,
    state: ImplementationState = ImplementationState.LEGACY,
    aliases: tuple[str, ...] = (),
    tests: tuple[str, ...],
) -> RuleDescriptor:
    return RuleDescriptor(
        rule_id=rule_id,
        owner_module=owner,
        family=family,
        nature=nature,
        action_type=action,
        deployment_status=status,
        normative_status=normative_status,
        normative_sources=sources,
        protection_policy_id=f"legacy.{family.value}",
        score_family=score_family,
        test_refs=tests,
        implementation_state=state,
        legacy_aliases=aliases,
    )


ORTHOTYPOGRAPHY_RULES = (
    _rule(
        "purh.apostrophe",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.DOCUMENTED_GENERAL,
        sources=(GENERAL_TYPOGRAPHY,),
        tests=(ORTHO_TEST, PROTECTION_TEST),
    ),
    _rule(
        "purh.points_suspension",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.DOCUMENTED_GENERAL,
        sources=(GENERAL_TYPOGRAPHY,),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.guillemets.droits",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.DIAGNOSTIC,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.PURH_VALIDATED,
        sources=(PURH_P12,),
        score_family="quote_structure",
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.ligature.oe",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.DOCUMENTED_GENERAL,
        sources=(GENERAL_TYPOGRAPHY,),
        aliases=("R-ORTHO-LIGATURE-OE-001",),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.guillemets.espace_apres_ouvrant",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.DOCUMENTED_GENERAL,
        sources=(GENERAL_TYPOGRAPHY,),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.guillemets.espace_avant_fermant",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.DOCUMENTED_GENERAL,
        sources=(GENERAL_TYPOGRAPHY,),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.espaces.avant_ponct_forte",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.CORPUS_OBSERVED,
        sources=(OBSERVED_CORPUS,),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.espaces.avant_ponct_faible",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.DOCUMENTED_GENERAL,
        sources=(GENERAL_TYPOGRAPHY,),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.espaces.double",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.DOCUMENTED_GENERAL,
        sources=(GENERAL_TYPOGRAPHY,),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.civilite",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.DOCUMENTED_GENERAL,
        sources=(GENERAL_TYPOGRAPHY,),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.siecles",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.PURH_VALIDATED,
        sources=(PURH_P10,),
        tests=(ORTHO_TEST, "tests/unit/test_orthotypo_century_styling.py"),
    ),
    _rule(
        "purh.siecles.style",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.STYLE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.PURH_VALIDATED,
        sources=(PURH_P10,),
        aliases=("R-SO-001",),
        tests=(ORTHO_TEST, "tests/unit/test_orthotypo_century_styling.py"),
    ),
    _rule(
        "purh.ordinaux",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.PURH_VALIDATED,
        sources=(PURH_P10,),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.tiret.double",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.DIAGNOSTIC,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.DOCUMENTED_GENERAL,
        sources=(GENERAL_TYPOGRAPHY,),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.abreviations.etc",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.PURH_VALIDATED,
        sources=(PURH_P10,),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.pagination.espace",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.PURH_VALIDATED,
        sources=(PURH_P11_12,),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.numero",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.PURH_VALIDATED,
        sources=(PURH_P12,),
        tests=(ORTHO_TEST, "tests/unit/test_orthotypo_numero_styling.py"),
    ),
    _rule(
        "purh.numero.style",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.STYLE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.PURH_VALIDATED,
        sources=(PURH_P12,),
        aliases=("R-NO-001",),
        tests=(ORTHO_TEST, "tests/unit/test_orthotypo_numero_styling.py"),
    ),
    _rule(
        "purh.abreviations.redoublement",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.PURH_VALIDATED,
        sources=(PURH_P11,),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.nombres.milliers",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.DOCUMENTED_GENERAL,
        sources=(GENERAL_TYPOGRAPHY,),
        tests=(ORTHO_TEST,),
    ),
    _rule(
        "purh.tiret.incise",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.DISABLED,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        tests=(ORTHO_TEST, "tests/unit/test_orthotypo_incise_dash_abstention.py"),
    ),
    _rule(
        "purh.tiret.incise.diagnostic",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.DIAGNOSTIC,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.CORPUS_OBSERVED,
        sources=(OBSERVED_CORPUS,),
        aliases=("R-TI-001",),
        tests=("tests/unit/test_orthotypo_incise_dash_abstention.py",),
    ),
    _rule(
        "purh.guillemets.ponctuation_fermante",
        owner=ORTHO_OWNER,
        family=RuleFamily.ORTHOTYPOGRAPHY,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.DIAGNOSTIC,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.PURH_VALIDATED,
        aliases=("R-GQ-004",),
        sources=(PURH_P12,),
        score_family="quote_structure",
        tests=("tests/unit/test_quote_punctuation_diagnostics.py",),
    ),
)


FOOTNOTE_RULES = (
    _rule(
        "purh.note.espace_initiale",
        owner=FOOTNOTE_OWNER,
        family=RuleFamily.FOOTNOTE,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        tests=(FOOTNOTE_TEST, PROTECTION_TEST),
    ),
    _rule(
        "purh.note.majuscule_initiale",
        owner=FOOTNOTE_OWNER,
        family=RuleFamily.FOOTNOTE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="footnote_form",
        tests=(FOOTNOTE_TEST,),
    ),
    _rule(
        "purh.note.abreviation_latine",
        owner=FOOTNOTE_OWNER,
        family=RuleFamily.FOOTNOTE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="footnote_form",
        tests=(FOOTNOTE_TEST,),
    ),
    _rule(
        "purh.note.espace_op_cit",
        owner=FOOTNOTE_OWNER,
        family=RuleFamily.FOOTNOTE,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.PURH_VALIDATED,
        sources=(PURH_P11_12,),
        tests=(FOOTNOTE_TEST,),
    ),
    _rule(
        "purh.note.espace_sans_lieu_date",
        owner=FOOTNOTE_OWNER,
        family=RuleFamily.FOOTNOTE,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.PURH_VALIDATED,
        sources=(PURH_P11_12,),
        tests=(FOOTNOTE_TEST,),
    ),
    _rule(
        "purh.note.ponctuation_finale",
        owner=FOOTNOTE_OWNER,
        family=RuleFamily.FOOTNOTE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="footnote_form",
        tests=(FOOTNOTE_TEST,),
    ),
    _rule(
        "purh.note.appel.placement",
        owner=FOOTNOTE_OWNER,
        family=RuleFamily.FOOTNOTE,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.DIAGNOSTIC,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.PURH_VALIDATED,
        sources=(PURH_P11,),
        aliases=("R-AN-002",),
        tests=(FOOTNOTE_TEST, "tests/unit/test_footnote_note_call_diagnostics.py"),
    ),
    _rule(
        "purh.note.appel.espace_avant",
        owner=FOOTNOTE_OWNER,
        family=RuleFamily.FOOTNOTE,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.DIAGNOSTIC,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.PURH_VALIDATED,
        sources=(PURH_P11,),
        aliases=("R-AN-003",),
        tests=(FOOTNOTE_TEST, "tests/unit/test_footnote_note_call_diagnostics.py"),
    ),
    _rule(
        "purh.note.diagnostic.debut_minuscule",
        owner=FOOTNOTE_OWNER,
        family=RuleFamily.FOOTNOTE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.DIAGNOSTIC,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="footnote_form",
        aliases=("R-AN-004",),
        tests=(FOOTNOTE_TEST,),
    ),
    _rule(
        "purh.note.diagnostic.ponctuation_finale_ambigue",
        owner=FOOTNOTE_OWNER,
        family=RuleFamily.FOOTNOTE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.DIAGNOSTIC,
        status=DeploymentStatus.REVIEW_ONLY,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="footnote_form",
        aliases=("R-AN-005",),
        tests=(FOOTNOTE_TEST,),
    ),
)


BIBLIOGRAPHY_RULES = (
    _rule(
        "structure.bibliography.section.start",
        owner=BIBLIO_OWNER,
        family=RuleFamily.BIBLIOGRAPHY,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.PIPELINE_CONTROL,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="bibliography_structure",
        state=ImplementationState.PLANNED,
        tests=(BIBLIO_TEST,),
    ),
    _rule(
        "structure.bibliography.section.end",
        owner=BIBLIO_OWNER,
        family=RuleFamily.BIBLIOGRAPHY,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.PIPELINE_CONTROL,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="bibliography_structure",
        state=ImplementationState.PLANNED,
        tests=(BIBLIO_TEST,),
    ),
    _rule(
        "structure.bibliography.item.promote",
        owner=BIBLIO_OWNER,
        family=RuleFamily.BIBLIOGRAPHY,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="bibliography_structure",
        state=ImplementationState.PLANNED,
        tests=(BIBLIO_TEST,),
    ),
    _rule(
        "bibliography.entry.detect",
        owner=BIBLIO_OWNER,
        family=RuleFamily.BIBLIOGRAPHY,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.DISABLED,
        normative_status=NormativeStatus.NOT_APPLICABLE,
        score_family="bibliography_structure",
        state=ImplementationState.DORMANT,
        tests=(BIBLIO_TEST,),
    ),
    _rule(
        "purh.biblio.pagination_nnbsp",
        owner=BIBLIO_OWNER,
        family=RuleFamily.BIBLIOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        tests=(BIBLIO_TEST, PROTECTION_TEST),
    ),
    _rule(
        "purh.biblio.numero_nnbsp",
        owner=BIBLIO_OWNER,
        family=RuleFamily.BIBLIOGRAPHY,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        tests=(BIBLIO_TEST,),
    ),
    _rule(
        "purh.biblio.ponctuation_finale",
        owner=BIBLIO_OWNER,
        family=RuleFamily.BIBLIOGRAPHY,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.TEXT_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="bibliography_form",
        tests=(BIBLIO_TEST,),
    ),
)


STRUCTURE_RULES = (
    _rule(
        "structure.frontmatter.abstract",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.CORPUS_OBSERVED,
        sources=(OBSERVED_CORPUS,),
        tests=("tests/unit/test_frontmatter_semantics.py", STRUCTURE_TEST),
    ),
    _rule(
        "structure.frontmatter.keywords",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.CORPUS_OBSERVED,
        sources=(OBSERVED_CORPUS,),
        tests=("tests/unit/test_frontmatter_semantics.py",),
    ),
    _rule(
        "structure.frontmatter.acknowledgment",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.CORPUS_OBSERVED,
        sources=(OBSERVED_CORPUS,),
        tests=("tests/unit/test_frontmatter_semantics.py",),
    ),
    _rule(
        "structure.frontmatter.circuit_breaker",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.DETERMINISTIC,
        action=RuleActionType.PIPELINE_CONTROL,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.CORPUS_OBSERVED,
        sources=(OBSERVED_CORPUS,),
        state=ImplementationState.PLANNED,
        tests=("tests/unit/test_frontmatter_semantics.py",),
    ),
    _rule(
        "structure.source_style.heading",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="heading",
        tests=(STRUCTURE_TEST,),
    ),
    _rule(
        "structure.allcaps.heading",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="heading",
        tests=(STRUCTURE_TEST, "tests/unit/test_heading_heuristic_scoring.py"),
    ),
    _rule(
        "structure.bold.heading",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="heading",
        tests=(STRUCTURE_TEST, "tests/unit/test_heading_heuristic_scoring.py"),
    ),
    _rule(
        "structure.italic.author",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        tests=(STRUCTURE_TEST,),
    ),
    _rule(
        "structure.italic.heading",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="heading",
        tests=(STRUCTURE_TEST,),
    ),
    _rule(
        "structure.epigraph.heuristic",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        tests=(STRUCTURE_TEST,),
    ),
    _rule(
        "structure.bibliography.section",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.PIPELINE_CONTROL,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="bibliography_structure",
        tests=(STRUCTURE_TEST,),
    ),
    _rule(
        "structure.bibliography.heuristic",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="bibliography_structure",
        tests=(STRUCTURE_TEST,),
    ),
    _rule(
        "structure.indent.quote",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="quote_structure",
        tests=(STRUCTURE_TEST,),
    ),
    _rule(
        "structure.quote.guillemets",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="quote_structure",
        tests=(STRUCTURE_TEST,),
    ),
    _rule(
        "structure.heading.heuristic",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="heading",
        tests=("tests/unit/test_heading_heuristic_scoring.py",),
    ),
    _rule(
        "structure.heading.diagnostic",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="heading",
        aliases=("R-STRUCT-HEADING-001",),
        tests=("tests/unit/test_heading_heuristic_scoring.py",),
    ),
    _rule(
        "structure.lineated.blank_bounded.merge",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="poetry",
        tests=(STRUCTURE_TEST, "tests/unit/test_structure_service_poetry_detection.py"),
    ),
    _rule(
        "structure.lineated.short_sequence.merge",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.DISABLED,
        normative_status=NormativeStatus.NOT_APPLICABLE,
        score_family="poetry",
        state=ImplementationState.DORMANT,
        tests=("tests/unit/test_structure_service_poetry_detection.py",),
    ),
    _rule(
        "structure.poetry.heuristique",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="poetry",
        aliases=("R-CI-POETRY-001",),
        tests=("tests/unit/test_poetry_heuristic_scoring.py",),
    ),
    _rule(
        "structure.lineated.group.annotate",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="poetry",
        tests=("tests/unit/test_poetry_heuristic_scoring.py",),
    ),
    _rule(
        "structure.lineated.stanza.merge",
        owner=STRUCTURE_OWNER,
        family=RuleFamily.STRUCTURE,
        nature=RuleNature.HEURISTIC,
        action=RuleActionType.STRUCTURE_TRANSFORM,
        status=DeploymentStatus.ACTIVE,
        normative_status=NormativeStatus.INTERNAL_UNSOURCED,
        score_family="poetry",
        tests=("tests/unit/test_poetry_heuristic_scoring.py",),
    ),
)


CANONICAL_RULE_DESCRIPTORS = (
    *ORTHOTYPOGRAPHY_RULES,
    *FOOTNOTE_RULES,
    *BIBLIOGRAPHY_RULES,
    *STRUCTURE_RULES,
)


@dataclass(frozen=True, slots=True)
class CanonicalRuleRegistry:
    descriptors: tuple[RuleDescriptor, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.descriptors, tuple):
            raise TypeError("descriptors must be a tuple")

    def get(self, rule_id: str) -> RuleDescriptor:
        for descriptor in self.descriptors:
            if descriptor.rule_id == rule_id or rule_id in descriptor.legacy_aliases:
                return descriptor
        raise KeyError(rule_id)

    def all(self) -> tuple[RuleDescriptor, ...]:
        return self.descriptors

    def by_family(self, family: RuleFamily) -> tuple[RuleDescriptor, ...]:
        return tuple(item for item in self.descriptors if item.family is family)

    def by_nature(self, nature: RuleNature) -> tuple[RuleDescriptor, ...]:
        return tuple(item for item in self.descriptors if item.nature is nature)

    def by_action(self, action: RuleActionType) -> tuple[RuleDescriptor, ...]:
        return tuple(item for item in self.descriptors if item.action_type is action)

    def by_status(self, status: DeploymentStatus) -> tuple[RuleDescriptor, ...]:
        return tuple(
            item for item in self.descriptors if item.deployment_status is status
        )

    def by_implementation_state(
        self,
        state: ImplementationState,
    ) -> tuple[RuleDescriptor, ...]:
        return tuple(
            item for item in self.descriptors if item.implementation_state is state
        )

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        primary_ids: dict[str, int] = {}
        aliases: dict[str, str] = {}

        for index, descriptor in enumerate(self.descriptors):
            if not isinstance(descriptor, RuleDescriptor):
                errors.append(f"descriptor at index {index} is not a RuleDescriptor")
                continue
            if not descriptor.rule_id.strip():
                errors.append(f"descriptor at index {index} has an empty rule_id")
            if not descriptor.owner_module.strip():
                errors.append(f"{descriptor.rule_id}: empty owner_module")
            if descriptor.rule_id in primary_ids:
                errors.append(f"duplicate rule_id: {descriptor.rule_id}")
            else:
                primary_ids[descriptor.rule_id] = index
            if (
                descriptor.nature is RuleNature.DETERMINISTIC
                and descriptor.score_family is not None
            ):
                errors.append(
                    f"{descriptor.rule_id}: deterministic rule has score_family"
                )
            if (
                descriptor.nature is RuleNature.HEURISTIC
                and descriptor.implementation_state is ImplementationState.NATIVE
                and not descriptor.score_family
            ):
                errors.append(
                    f"{descriptor.rule_id}: native heuristic has no score_family"
                )
            if not isinstance(descriptor.implementation_state, ImplementationState):
                errors.append(
                    f"{descriptor.rule_id}: unknown implementation_state "
                    f"{descriptor.implementation_state!r}"
                )
            for test_ref in descriptor.test_refs:
                if not test_ref.startswith("tests/"):
                    errors.append(
                        f"{descriptor.rule_id}: malformed test reference {test_ref!r}"
                    )
            for alias in descriptor.legacy_aliases:
                previous = aliases.get(alias)
                if previous is not None:
                    errors.append(
                        f"duplicate alias {alias!r}: {previous} and "
                        f"{descriptor.rule_id}"
                    )
                else:
                    aliases[alias] = descriptor.rule_id

        primary_set = set(primary_ids)
        for alias, owner in aliases.items():
            if alias in primary_set:
                errors.append(
                    f"alias {alias!r} for {owner} conflicts with a primary rule_id"
                )

        return tuple(errors)


CANONICAL_RULE_REGISTRY = CanonicalRuleRegistry(
    descriptors=CANONICAL_RULE_DESCRIPTORS,
)
