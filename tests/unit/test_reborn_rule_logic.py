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
    find_incise_dash_diagnostics,
    find_numero_style_matches,
    find_quote_punctuation_diagnostics,
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
from purh_editorial.corrector.word_document import _apply_text_edits


EXPECTED_DETERMINISTIC_IDS = {
    "purh.apostrophe",
    "purh.points_suspension",
    "purh.ligature.oe",
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
        (find_initial_space_edits, "  Note", "Note", "Note", "Note"),
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


def test_note_abbreviation_variants() -> None:
    assert normalize_op_cit_spacing("Voir art.  cit.") == f"Voir art.{NNBSP}cit."
    normalized = f"Voir loc.{NNBSP}cit."
    assert normalize_op_cit_spacing(normalized) == normalized
    assert apply_text_edits(
        "\x02\tNote",
        find_initial_space_edits("\x02\tNote"),
    ) == "\x02Note"
    marker_edit = find_initial_space_edits("\x02\tNote")[0]
    assert marker_edit.replacement == "N"
    assert marker_edit.end - marker_edit.start == 2


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
            'Il dit "bonjour".',
            'print("bonjour")',
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
    assert finder(positive) == diagnostics


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
    assert len(DETERMINISTIC_RULE_IDS) == 36
    assert len(set(DETERMINISTIC_RULE_IDS)) == 36
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
    assert len(RULE_IDS) == 46
    assert len(set(RULE_IDS)) == 46


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
