from __future__ import annotations

import pytest

from purh_editorial.corrector.rules.bibliography import (
    BIBLIOGRAPHY_SECTION_HEADING_RE,
    find_bibliography_author_casing_edits,
    find_bibliography_final_punctuation_edits,
    find_bibliography_numero_edits,
    find_bibliography_pagination_edits,
)
from purh_editorial.corrector.rules.footnotes import (
    NNBSP,
    find_ambiguous_final_punctuation_diagnostics,
    find_final_punctuation_edits,
    find_initial_space_edits,
    find_initial_capital_edits,
    find_latin_abbreviation_edits,
    find_latin_abbreviation_ranges,
    find_lowercase_start_diagnostics,
    find_op_cit_edits,
    find_sans_lieu_date_edits,
    normalize_op_cit_spacing,
    note_call_diagnostic_ids,
)
from purh_editorial.corrector.rules.orthotypography import (
    ORTHOTYPOGRAPHY_TEXT_RULES,
    apply_text_edits,
    find_centuries,
    find_double_dash_diagnostics,
    find_english_quote_conversion_edits,
    find_folio_style_matches,
    find_incise_dash_diagnostics,
    find_numero_style_matches,
    find_quote_punctuation_diagnostics,
    find_recto_verso_edits,
    find_recto_verso_style_matches,
    find_straight_quote_diagnostics,
    normalize_points_suspension,
)
from purh_editorial.corrector.rules.structure import (
    detect_frontmatter_rule,
    is_allcaps_heading,
)
from purh_editorial.corrector.runner import (
    DETERMINISTIC_RULE_IDS,
    HEURISTIC_RULE_IDS,
    RULE_IDS,
)
from purh_editorial.corrector.word_document import (
    FOOTNOTE_QUOTE_TEXT_RULES,
    FOOTNOTE_REMAINING_TEXT_RULES,
    _apply_text_edits,
)


EXPECTED_DETERMINISTIC_IDS = {
    "purh.apostrophe",
    "purh.points_suspension",
    "purh.ligature.oe",
    "purh.guillemets.anglais_vers_chevrons",
    "purh.guillemets.espace_apres_ouvrant",
    "purh.guillemets.espace_avant_fermant",
    "purh.espaces.avant_ponct_forte",
    "purh.espaces.avant_ponct_faible",
    "purh.espaces.double",
    "purh.civilite",
    "purh.numeral_dynastique",
    "purh.siecles",
    "purh.ordinaux",
    "purh.abreviations.etc",
    "purh.pagination.espace",
    "purh.numero",
    "purh.folio",
    "purh.recto_verso",
    "purh.abreviations.redoublement",
    "purh.nombres.milliers",
    "purh.ecriture_inclusive.point_median",
    "purh.date.jour_mois",
    "purh.note.espace_initiale",
    "purh.note.espace_op_cit",
    "purh.note.espace_sans_lieu_date",
    "purh.biblio.pagination_nnbsp",
    "purh.biblio.numero_nnbsp",
    "purh.siecles.style",
    "purh.numero.style",
    "purh.folio.style",
    "purh.recto_verso.style",
    "purh.ordinaux.style",
    "purh.civilite.style",
    "purh.note.italique_latin",
    "purh.tiret.incise.diagnostic",
    "purh.note.appel.placement",
    "purh.note.appel.espace_avant",
    "structure.frontmatter.abstract",
    "structure.frontmatter.keywords",
    "structure.frontmatter.acknowledgment",
    "structure.allcaps.heading",
    "purh.style.titre",
    "purh.style.citation",
    "purh.style.citation_intense",
    "purh.style.normal",
    "purh.style.corps_de_texte",
    "purh.style.note_bas_de_page",
    "purh.style.appel_de_note",
    "purh.style.normal_refresh",
    "structure.poetry.heuristique",
}

EXPECTED_HEURISTIC_IDS = {
    "purh.guillemets.droits",
    "purh.tiret.double",
    "purh.guillemets.ponctuation_fermante",
    "purh.note.majuscule_initiale",
    "purh.note.abreviation_latine",
    "purh.note.ponctuation_finale",
    "purh.note.diagnostic.debut_minuscule",
    "purh.note.diagnostic.ponctuation_finale_ambigue",
    "purh.biblio.ponctuation_finale",
    "purh.biblio.casse_auteur",
}


def _orthotypography_finder(rule_id: str):
    return dict(ORTHOTYPOGRAPHY_TEXT_RULES)[rule_id]


@pytest.mark.parametrize(
    ("rule_id", "source", "expected", "negative", "conform"),
    [
        ("purh.apostrophe", "L'auteur", "L’auteur", "'début", "L’auteur"),
        (
            "purh.points_suspension",
            "Texte... Suite",
            "Texte… Suite",
            "Texte.... Suite",
            "Texte… Suite",
        ),
        (
            "purh.ligature.oe",
            "une soeur",
            "une sœur",
            "coelacanthe",
            "une sœur",
        ),
        (
            "purh.guillemets.espace_apres_ouvrant",
            "« Bonjour",
            f"«{NNBSP}Bonjour",
            "Bonjour",
            f"«{NNBSP}Bonjour",
        ),
        (
            "purh.guillemets.espace_avant_fermant",
            "Bonjour »",
            f"Bonjour{NNBSP}»",
            "Bonjour",
            f"Bonjour{NNBSP}»",
        ),
        (
            "purh.espaces.avant_ponct_forte",
            "Voici:",
            f"Voici{NNBSP}:",
            "10:30",
            f"Voici{NNBSP}:",
        ),
        (
            "purh.espaces.avant_ponct_faible",
            "mot , suite",
            "mot, suite",
            "valeur ,14",
            "mot, suite",
        ),
        (
            "purh.espaces.double",
            "deux  espaces",
            "deux espaces",
            f"deux{NNBSP} espaces",
            "deux espaces",
        ),
        (
            "purh.civilite",
            "M. Dupont",
            f"M.{chr(0x00A0)}Dupont",
            "M. dupont",
            f"M.{chr(0x00A0)}Dupont",
        ),
        (
            "purh.numeral_dynastique",
            "Louis XIV régna",
            f"Louis{chr(0x00A0)}XIV régna",
            "au XVIe siècle",
            f"Louis{chr(0x00A0)}XIV régna",
        ),
        (
            "purh.siecles",
            "XVIème siècle",
            "xvie siècle",
            "XVIème chapitre",
            "xvie siècle",
        ),
        ("purh.ordinaux", "1ère partie", "1re partie", "1er", "1re partie"),
        ("purh.abreviations.etc", "etc…", "etc.", "etc", "etc."),
        (
            "purh.pagination.espace",
            "p. 12",
            f"p.{NNBSP}12",
            "p. texte",
            f"p.{NNBSP}12",
        ),
        (
            "purh.numero",
            "n° 5",
            f"no{NNBSP}5",
            "numéro cinq",
            f"no{NNBSP}5",
        ),
        (
            "purh.folio",
            "fol. 12",
            f"fo{NNBSP}12",
            "le folio de la reliure",
            f"fo{NNBSP}12",
        ),
        (
            "purh.recto_verso",
            "recto 12",
            f"ro{NNBSP}12",
            "le recto de la lettre",
            f"ro{NNBSP}12",
        ),
        (
            "purh.abreviations.redoublement",
            "pp. 53",
            "p. 53",
            "supp. cit.",
            "p. 53",
        ),
        (
            "purh.nombres.milliers",
            "1 500 000",
            f"1{NNBSP}500{NNBSP}000",
            "2025",
            f"1{NNBSP}500{NNBSP}000",
        ),
        (
            # Extrait reel, Ethnographes_originaux.docx vs
            # ethnographes-engages-styles/*.docx.
            "purh.ecriture_inclusive.point_median",
            "chercheur.e.s",
            "chercheur·e·s",
            "c.q.f.d.",
            "chercheur·e·s",
        ),
        (
            "purh.date.jour_mois",
            "le 24 décembre 1968",
            f"le 24{NNBSP}décembre 1968",
            "le 32 décembre",
            f"le 24{NNBSP}décembre 1968",
        ),
    ],
)
def test_orthotypography_text_rules_are_guarded_and_idempotent(
    rule_id: str,
    source: str,
    expected: str,
    negative: str,
    conform: str,
) -> None:
    finder = _orthotypography_finder(rule_id)
    corrected = apply_text_edits(source, finder(source))
    assert corrected == expected
    assert finder(negative) == []
    assert finder(conform) == []
    assert apply_text_edits(corrected, finder(corrected)) == corrected


def test_points_suspension_and_century_guardrails() -> None:
    assert normalize_points_suspension("Texte….") == "Texte…."
    assert normalize_points_suspension("Texte… Suite") == "Texte… Suite"
    for text in ("XVIème siècle", "xvie siècle", "VIe siècle", "Ier siècle"):
        assert len(find_centuries(text)) == 1
    for text in (
        "la vie continue",
        "une vie entière",
        "VIe",
        "XVIème chapitre",
        "XLIVe siècle",
    ):
        assert find_centuries(text) == []


@pytest.mark.parametrize(
    ("finder", "source", "expected", "negative", "conform"),
    [
        (
            find_op_cit_edits,
            "Voir op. cit.",
            f"Voir op.{NNBSP}cit.",
            "Voir loc.",
            f"Voir op.{NNBSP}cit.",
        ),
        (
            find_sans_lieu_date_edits,
            "Voir s. l.",
            f"Voir s.{NNBSP}l.",
            "Voir s.",
            f"Voir s.{NNBSP}l.",
        ),
    ],
)
def test_footnote_text_rules_are_guarded_and_idempotent(
    finder,
    source: str,
    expected: str,
    negative: str,
    conform: str,
) -> None:
    corrected = apply_text_edits(source, finder(source))
    assert corrected == expected
    assert finder(negative) == []
    assert finder(conform) == []
    assert apply_text_edits(corrected, finder(corrected)) == corrected


@pytest.mark.parametrize(
    "source",
    [
        "Note",  # aucun séparateur : le numéro de note colle au texte
        "\tNote",  # tabulation résiduelle
        "  Note",  # espaces multiples
        " Note",  # espace insécable
    ],
)
def test_footnote_initial_space_is_normalized_to_a_single_space(
    source: str,
) -> None:
    corrected = apply_text_edits(source, find_initial_space_edits(source))
    assert corrected == " Note"
    # Le premier caractère de contenu réel ("N") ne doit jamais être inclus
    # dans la plage remplacée : Word applique à un Range.Text réécrit la mise
    # en forme du début de la plage d'origine, pas celle du caractère
    # remplacé, donc l'englober perdrait sa mise en forme (italique, gras...).
    for edit in find_initial_space_edits(source):
        assert edit.end <= source.index("N")
    assert find_initial_space_edits(" Note") == []
    assert apply_text_edits(corrected, find_initial_space_edits(corrected)) == corrected


def test_footnote_initial_space_respects_leading_marker() -> None:
    assert apply_text_edits(
        "\x02\tNote",
        find_initial_space_edits("\x02\tNote"),
    ) == "\x02 Note"
    assert apply_text_edits(
        "\x02Note",
        find_initial_space_edits("\x02Note"),
    ) == "\x02 Note"
    marker_edit = find_initial_space_edits("\x02\tNote")[0]
    assert marker_edit.replacement == " "
    assert (marker_edit.start, marker_edit.end) == (1, 2)


def test_note_abbreviation_variants() -> None:
    assert normalize_op_cit_spacing("Voir art.  cit.") == f"Voir art.{NNBSP}cit."
    normalized = f"Voir loc.{NNBSP}cit."
    assert normalize_op_cit_spacing(normalized) == normalized


@pytest.mark.parametrize(
    "source",
    [
        "Corneille et le mystère de l’identité",
        "Cette idée est reprise plus loin",
        "Une identité plurielle, une idéologie affirmée",
    ],
)
def test_latin_italic_ranges_do_not_match_id_inside_a_word(source: str) -> None:
    # "id" (abreviation latine de "idem") ne doit matcher qu'en tant que mot
    # complet - un mot ordinaire commencant par "id" (identite, idee...) n'a
    # rien a voir avec l'abreviation et ne doit jamais etre mis en italique.
    assert find_latin_abbreviation_ranges(source) == []


def test_footnotes_apply_every_orthotypography_text_rule() -> None:
    # Les notes de bas de page doivent recevoir l'integralite de
    # ORTHOTYPOGRAPHY_TEXT_RULES (guillemets + le reste), pas seulement un
    # sous-ensemble choisi au fil des ajouts : sinon des familles entieres
    # (siecles, espacement de la ponctuation forte/faible, civilites...)
    # restent silencieusement non appliquees dans les notes alors que leur
    # stylage associe (petites capitales, superscript) l'est deja.
    footnote_rule_ids = {rule_id for rule_id, _ in FOOTNOTE_QUOTE_TEXT_RULES} | {
        rule_id for rule_id, _ in FOOTNOTE_REMAINING_TEXT_RULES
    }
    assert footnote_rule_ids == {rule_id for rule_id, _ in ORTHOTYPOGRAPHY_TEXT_RULES}
    assert not (
        {rule_id for rule_id, _ in FOOTNOTE_QUOTE_TEXT_RULES}
        & {rule_id for rule_id, _ in FOOTNOTE_REMAINING_TEXT_RULES}
    )


def test_latin_italic_ranges_still_match_real_abbreviations() -> None:
    assert [
        edit.replacement for edit in find_latin_abbreviation_ranges("Voir Id., p. 4")
    ] == ["Id."]
    assert [
        edit.replacement for edit in find_latin_abbreviation_ranges("Voir Idem, p. 4")
    ] == ["Idem"]


@pytest.mark.parametrize(
    ("finder", "source", "expected", "negative", "conform"),
    [
        (
            find_bibliography_pagination_edits,
            "p. 12",
            f"p.{NNBSP}12",
            "p. texte",
            f"p.{NNBSP}12",
        ),
        (
            find_bibliography_numero_edits,
            "n° 7",
            f"n°{NNBSP}7",
            "n° sept",
            f"n°{NNBSP}7",
        ),
    ],
)
def test_bibliography_text_logic_is_exact_and_idempotent(
    finder,
    source: str,
    expected: str,
    negative: str,
    conform: str,
) -> None:
    corrected = apply_text_edits(source, finder(source))
    assert corrected == expected
    assert finder(negative) == []
    assert finder(conform) == []
    assert apply_text_edits(corrected, finder(corrected)) == corrected


def test_bibliography_final_punctuation_adds_missing_period() -> None:
    source = "Dupont Jean, Essai critique, Paris, Gallimard, 2020"
    edits = find_bibliography_final_punctuation_edits(source)
    assert apply_text_edits(source, edits) == source + "."
    assert find_bibliography_final_punctuation_edits(source + ".") == []


@pytest.mark.parametrize(
    "source",
    [
        "Entrée déjà ponctuée.",
        "Entrée entre guillemets »",
        "- élément de liste sans point final",
        "Voir https://exemple.org/reference-sans-point",
        "",
    ],
)
def test_bibliography_final_punctuation_guards(source: str) -> None:
    assert find_bibliography_final_punctuation_edits(source) == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        # Extraits réels comparés brut/corrigé, Ch14_Source_bibliographie.docx
        # (sources/manuscripts_styled/heraldique_styles) :
        (
            "FERRARI Matteo, « Stemmi esposti… »",
            "Ferrari Matteo, « Stemmi esposti… »",
        ),
        (
            "GALLAVOTTI CAVALLERO Daniela, « L’iconografia… »",
            "Gallavotti Cavallero Daniela, « L’iconografia… »",
        ),
        (
            "HERMANN-FIORE Kristina, « La salle clémentine… »",
            "Hermann-Fiore Kristina, « La salle clémentine… »",
        ),
        (
            "LAURENTIIS Elena de, « Preparatio ad missam… »",
            "Laurentiis Elena de, « Preparatio ad missam… »",
        ),
    ],
)
def test_bibliography_author_casing_matches_real_corpus(
    source: str, expected: str
) -> None:
    edits = find_bibliography_author_casing_edits(source)
    assert apply_text_edits(source, edits) == expected
    assert apply_text_edits(expected, find_bibliography_author_casing_edits(expected)) == expected


@pytest.mark.parametrize(
    "source",
    [
        "Ferrari Matteo, « déjà correct »",
        "UNESCO, rapport annuel 2020.",
        "Ceci est une phrase normale, pas une bibliographie.",
        "",
    ],
)
def test_bibliography_author_casing_guards(source: str) -> None:
    assert find_bibliography_author_casing_edits(source) == []


@pytest.mark.parametrize(
    "text",
    [
        "Bibliographie",
        "Sources",
        "Références bibliographiques",
        "Bibliography",
        "Works cited",
    ],
)
def test_bibliography_section_heading_detection(text: str) -> None:
    assert BIBLIOGRAPHY_SECTION_HEADING_RE.match(text)


def test_bibliography_section_heading_rejects_ordinary_titles() -> None:
    assert BIBLIOGRAPHY_SECTION_HEADING_RE.match("Introduction") is None
    assert BIBLIOGRAPHY_SECTION_HEADING_RE.match("Chapitre 3") is None


def test_style_detectors_are_closed_and_idempotence_ready() -> None:
    assert find_centuries("xvie siècle")[0].roman == "xvi"
    assert find_numero_style_matches(f"no{NNBSP}5")[0].group(1) == "o"
    assert find_numero_style_matches("nombre cinq") == []
    assert find_folio_style_matches(f"fo{NNBSP}12")[0].group(1) == "o"
    assert find_folio_style_matches("folio") == []
    assert find_recto_verso_style_matches(f"ro{NNBSP}3")[0].group(1) == "o"
    assert find_recto_verso_style_matches(f"vo{NNBSP}4")[0].group(1) == "o"
    assert find_recto_verso_style_matches("rose") == []


def test_recto_verso_handles_both_forms_in_order() -> None:
    text = f"voir ro{NNBSP}3 et vo{NNBSP}4"
    # Deja au format cible : aucune modification supplementaire attendue.
    assert find_recto_verso_edits(text) == []
    corrected = apply_text_edits(
        "voir recto 3 et verso 4", find_recto_verso_edits("voir recto 3 et verso 4")
    )
    assert corrected == text


def test_diagnostic_detectors_do_not_change_text() -> None:
    text = "mot - mot"
    diagnostics = find_incise_dash_diagnostics(text)
    assert len(diagnostics) == 1
    assert apply_text_edits(text, diagnostics) == text
    assert find_incise_dash_diagnostics("mot-mot") == []
    assert note_call_diagnostic_ids(".") == ("purh.note.appel.placement",)
    assert note_call_diagnostic_ids(" ") == ("purh.note.appel.espace_avant",)
    assert note_call_diagnostic_ids("t") == ()


@pytest.mark.parametrize(
    ("finder", "positive", "negative", "conform"),
    [
        (
            find_straight_quote_diagnostics,
            'class="bonjour"',
            'Il dit "bonjour".',
            "Il dit « bonjour ».",
        ),
        (
            find_double_dash_diagnostics,
            "avant--après",
            "avant-après",
            "avant–après",
        ),
        (
            find_quote_punctuation_diagnostics,
            "« Que faire ? ».",
            "Il parle de « réforme ».",
            "« Que faire ? »",
        ),
    ],
)
def test_heuristic_orthotypography_diagnostics_are_non_mutating(
    finder,
    positive: str,
    negative: str,
    conform: str,
) -> None:
    diagnostics = finder(positive)
    assert len(diagnostics) == 1
    assert apply_text_edits(positive, diagnostics) == positive
    assert finder(negative) == []
    assert finder(conform) == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('Il dit "bonjour".', "Il dit «bonjour»."),
        ("Il dit “bonjour”.", "Il dit «bonjour»."),
        # Guillemets droits fermant un guillemet anglais ouvrant : melange de
        # styles toleré pour la paire de premier niveau.
        ('Il dit “bonjour".', "Il dit «bonjour»."),
    ],
)
def test_english_quotes_become_chevrons(source: str, expected: str) -> None:
    corrected = apply_text_edits(source, find_english_quote_conversion_edits(source))
    assert corrected == expected
    assert find_english_quote_conversion_edits(corrected) == []


def test_nested_english_quotes_are_left_untouched() -> None:
    # Guillemets dans les guillemets : seule la paire de premier niveau
    # devient des chevrons, la paire imbriquee reste en guillemets anglais.
    # Un guillemet anglais courbe ("“"/"”") est directionnel et permet de
    # detecter l'imbrication sans ambiguite, y compris quand le niveau
    # exterieur est en guillemets droits (melange de styles courant).
    source = 'Il a dit "Elle a dit “bonjour” hier" ce matin.'
    corrected = apply_text_edits(source, find_english_quote_conversion_edits(source))
    assert corrected == "Il a dit «Elle a dit “bonjour” hier» ce matin."
    assert find_english_quote_conversion_edits(corrected) == []

    curly_source = "Il a dit “Elle a dit “bonjour” hier” ce matin."
    curly_corrected = apply_text_edits(
        curly_source, find_english_quote_conversion_edits(curly_source)
    )
    assert curly_corrected == "Il a dit «Elle a dit “bonjour” hier» ce matin."


def test_english_quote_conversion_skips_technical_context() -> None:
    assert find_english_quote_conversion_edits('class="bonjour"') == []
    assert find_english_quote_conversion_edits("«déjà correct»") == []
    # Guillemet non apparie (nombre impair) : laisse en l'etat, rien a
    # convertir avec certitude.
    assert find_english_quote_conversion_edits('Il dit "bonjour.') == []


@pytest.mark.parametrize(
    "source",
    [
        # Virgule, point-virgule ou deux-points juste apres la citation :
        # ponctuation de prose ordinaire, pas un indice de contexte
        # technique - ne doit pas empecher la conversion en chevrons.
        "Mais elle est surtout une “tragédie de combat”, qui emporte le spectateur.",
        "Nous frissonnons devant cette “tragédie de combat”; une œuvre marquante.",
        "Les auteurs “classiques”: Corneille, Racine.",
    ],
)
def test_english_quote_conversion_is_not_blocked_by_following_prose_punctuation(
    source: str,
) -> None:
    edits = find_english_quote_conversion_edits(source)
    corrected = apply_text_edits(source, edits)
    assert "“" not in corrected and "”" not in corrected
    assert "«" in corrected and "»" in corrected
    assert find_straight_quote_diagnostics(corrected) == []


@pytest.mark.parametrize(
    ("finder", "source", "expected", "negative", "conform"),
    [
        (
            find_initial_capital_edits,
            "fragment sans point",
            "Fragment sans point",
            "van Gogh",
            "Fragment sans point",
        ),
        (
            find_latin_abbreviation_edits,
            "Voir Ibid., p. 2",
            "Voir ibid., p. 2",
            "Ibid., p. 2",
            "Voir ibid., p. 2",
        ),
        (
            find_final_punctuation_edits,
            "Fragment sans point",
            "Fragment sans point.",
            "https://example.org",
            "Fragment sans point.",
        ),
    ],
)
def test_heuristic_footnote_transformations_are_guarded_and_idempotent(
    finder,
    source: str,
    expected: str,
    negative: str,
    conform: str,
) -> None:
    corrected = apply_text_edits(source, finder(source))
    assert corrected == expected
    assert finder(negative) == []
    assert finder(conform) == []
    assert apply_text_edits(corrected, finder(corrected)) == corrected


@pytest.mark.parametrize(
    ("finder", "positive", "negative"),
    [
        (
            find_lowercase_start_diagnostics,
            "https://example.org",
            "Fragment normal.",
        ),
        (
            find_ambiguous_final_punctuation_diagnostics,
            "- élément de liste",
            "Élément de liste.",
        ),
    ],
)
def test_heuristic_footnote_diagnostics_are_non_mutating(
    finder,
    positive: str,
    negative: str,
) -> None:
    diagnostics = finder(positive)
    assert len(diagnostics) == 1
    assert apply_text_edits(positive, diagnostics) == positive
    assert finder(negative) == []
    assert finder(positive) == diagnostics


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        ("Résumé :", "structure.frontmatter.abstract"),
        ("Keywords:", "structure.frontmatter.keywords"),
        ("Acknowledgments", "structure.frontmatter.acknowledgment"),
    ],
)
def test_frontmatter_detection_is_exact(text: str, rule_id: str) -> None:
    assert detect_frontmatter_rule(text) == rule_id
    assert detect_frontmatter_rule("Texte ordinaire.") is None


@pytest.mark.parametrize(
    "text",
    [
        # Extraits reels courts (titres de section generiques), voir
        # docs/journal/ANALYSE_CORPUS_HP2.md et
        # docs/journal/OBSERVATIONS_CORPUS_2026-07-31.md.
        "SOURCES ET BIBLIOGRAPHIE",
        "BIBLIOGRAPHIE SÉLECTIVE",
        "MANUSCRITS ET DOCUMENTS D'ARCHIVES",
        "TABLE DES FIGURES",
        "CHAPITRE 3",
    ],
)
def test_allcaps_heading_detects_real_patterns(text: str) -> None:
    assert is_allcaps_heading(text)


@pytest.mark.parametrize(
    "text",
    [
        "I",
        "A",
        "IV",
        "Introduction",
        "Chapitre 3",
        "Table des figures",
        "",
        "12",
        "M. Dupont",
    ],
)
def test_allcaps_heading_guards_short_and_mixed_case(text: str) -> None:
    assert not is_allcaps_heading(text)


def test_exact_deterministic_identifier_set() -> None:
    # 34 des 34 règles déterministes du catalogue restant hors
    # NOT_YET_IMPLEMENTED_RULE_IDS : seule structure.frontmatter.circuit_breaker
    # reste à concevoir (cf. runner.py — `planned`, jamais fonctionnelle même
    # dans la voie legacy). structure.allcaps.heading complète cette liste :
    # implémentée en diagnostic (surlignage), condition déterministe (style de
    # titre Word + texte tout capitales), pas de transformation automatique de
    # casse (risque de perdre la casse d'un nom propre dans le titre).
    # purh.guillemets.anglais_vers_chevrons (nouvelle) convertit les guillemets
    # droits/anglais de premier niveau en chevrons français ; une paire
    # imbriquée dans une autre reste en l'état (convention citation dans
    # citation).
    # structure.poetry.heuristique (branche "heuristique") fusionne les blocs
    # de paragraphes consecutifs stylés "Citation intense" en un paragraphe
    # unique par saut de ligne manuel : condition déterministe (style Word
    # natif), pas le moteur de score legacy `poetry`.
    # purh.style.normal_refresh (branche "heuristique") réapplique
    # silencieusement le style "Normal" à chaque paragraphe qui le porte déjà
    # (contournement d'un artefact de rendu Word), sans toucher au texte.
    assert len(DETERMINISTIC_RULE_IDS) == 50
    assert len(set(DETERMINISTIC_RULE_IDS)) == 50
    assert set(DETERMINISTIC_RULE_IDS) == EXPECTED_DETERMINISTIC_IDS


def test_exact_heuristic_and_complete_identifier_sets() -> None:
    # 10 des 32 règles heuristiques du catalogue : les 17 règles de
    # heading/poésie/citation/section bibliographique restent à concevoir
    # (moteur de score legacy exclu par docs/REBORN_ARCHITECTURE.md §7), ainsi
    # que les règles bibliographie explicitement `planned`/`dormant` et
    # `purh.tiret.incise` (`disabled` au catalogue, aucun détecteur dans
    # corrector/rules/) — cf. NOT_YET_IMPLEMENTED_RULE_IDS dans runner.py.
    # purh.biblio.casse_auteur (nouvelle) ramène la casse d'un nom d'auteur
    # tout capitales en tête d'entrée bibliographique, grounded sur 15
    # entrées réelles comparées brut/corrigé (Ch14_Source_bibliographie).
    assert len(HEURISTIC_RULE_IDS) == 10
    assert len(set(HEURISTIC_RULE_IDS)) == 10
    assert set(HEURISTIC_RULE_IDS) == EXPECTED_HEURISTIC_IDS
    assert len(RULE_IDS) == 60
    assert len(set(RULE_IDS)) == 60


class _IgnoringRange:
    def __init__(self, text: str, start: int = 0, end: int | None = None) -> None:
        self._buffer = text
        self.Start = start
        self.End = len(text) if end is None else end
        self.HighlightColorIndex = 0

    @property
    def Text(self) -> str:
        return self._buffer[self.Start : self.End]

    @Text.setter
    def Text(self, _replacement: str) -> None:
        pass

    @property
    def Duplicate(self):
        duplicate = _IgnoringRange(self._buffer, self.Start, self.End)
        return duplicate

    def SetRange(self, start: int, end: int) -> None:
        self.Start = start
        self.End = end


class _IgnoringParagraph:
    def __init__(self, text: str) -> None:
        self.Range = _IgnoringRange(text)


class _RefusingRange(_IgnoringRange):
    @property
    def Duplicate(self):
        return _RefusingRange(self._buffer, self.Start, self.End)

    @_IgnoringRange.Text.setter
    def Text(self, _replacement: str) -> None:
        raise RuntimeError("Impossible de supprimer la plage.")


def test_word_backend_counts_only_a_change_applied_by_word() -> None:
    paragraph = _IgnoringParagraph("Texte:")
    assert _apply_text_edits(
        paragraph,
        lambda _text: [type("Edit", (), {
            "start": 5,
            "end": 6,
            "replacement": "\u202f:",
        })()],
    ) == 0


def test_word_backend_skips_only_a_range_word_declares_unmodifiable() -> None:
    paragraph = _IgnoringParagraph("«Texte")
    paragraph.Range = _RefusingRange("«Texte")
    assert _apply_text_edits(
        paragraph,
        lambda _text: [type("Edit", (), {
            "start": 0,
            "end": 1,
            "replacement": "«\u202f",
        })()],
    ) == 0
