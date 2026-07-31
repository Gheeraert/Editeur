from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

NBSP = "\u00a0"
# Nommee historiquement "NNBSP" (espace fine insecable, U+202F), mais la
# valeur a ete corrigee vers l'espace insecable normale U+00A0 : verification
# sur le corpus reel corrige par les editrices PURH (Ch14_Source_bibliographie,
# heraldique_styles/*, dissimuler_styles/*, ~3000 espaces insecables comptees
# au niveau XML brut) - 0 occurrence de U+202F, 100% en U+00A0, aussi bien
# pour les guillemets que la pagination/numero/milliers. Le nom est conserve
# pour ne pas renommer tous les appels existants.
NNBSP = NBSP


@dataclass(frozen=True)
class TextEdit:
    start: int
    end: int
    replacement: str


@dataclass(frozen=True)
class CenturyMatch:
    start: int
    end: int
    text: str
    roman: str
    suffix: str
    normalized: str


Replacement = str | Callable[[re.Match[str]], str]


def _regex_edits(
    text: str,
    pattern: re.Pattern[str],
    replacement: Replacement,
) -> list[TextEdit]:
    edits: list[TextEdit] = []
    for match in pattern.finditer(text):
        after = replacement(match) if callable(replacement) else match.expand(replacement)
        if after != match.group(0):
            edits.append(TextEdit(match.start(), match.end(), after))
    return edits


_APOSTROPHE_RE = re.compile(r"(?<=[A-Za-zÀ-ɏ])'")
_POINTS_SUSPENSION_RE = re.compile(r"(?<!\.)\.\.\.(?!\.)")

_OE_LIGATURE_FORMS = {
    "boeuf": "bœuf",
    "boeufs": "bœufs",
    "oeuf": "œuf",
    "oeufs": "œufs",
    "soeur": "sœur",
    "soeurs": "sœurs",
    "coeur": "cœur",
    "coeurs": "cœurs",
    "oeuvre": "œuvre",
    "oeuvres": "œuvres",
    "oeil": "œil",
    "voeu": "vœu",
    "voeux": "vœux",
    "noeud": "nœud",
    "noeuds": "nœuds",
    "moeurs": "mœurs",
}
_OE_RE = re.compile(
    r"\b(" + "|".join(sorted(_OE_LIGATURE_FORMS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

_OPEN_QUOTE_SPACE_RE = re.compile(r"«[ \t\u00a0\u202f]*")
_CLOSE_QUOTE_SPACE_RE = re.compile(r"[ \t\u00a0\u202f]*»")
_STRONG_PUNCT_RE = re.compile(r"[ \t\u00a0\u202f]*([:;?!])")
_WEAK_PUNCT_RE = re.compile(r"[ \t\u00a0\u202f]+([,.])(?!\d)")
_DOUBLE_SPACE_RE = re.compile(r"[ \t]{2,}")
_CIVILITY_RE = re.compile(
    r"\b(M\.|Mme[s]?|Dr?|Pr?|Prof\.) (?=[A-ZÀ-ÖØ-Þ])",
    re.UNICODE,
)
# Ecriture inclusive au point median : liste fermee de morphemes de genre/
# nombre courants (cf. purh.ligature.oe pour le meme principe de liste
# fermee plutot que regle generale). Verifie sur corpus reel
# (Ethnographes_originaux.docx vs ethnographes-engages-styles/*.docx) : le
# brut ecrit "chercheur.e.s", "auteur.e.s", "participant.e.s" au point
# simple ; les editrices PURH convertissent systematiquement au point
# median (U+00B7). Liste fermee choisie pour eviter de toucher de vraies
# abreviations chainees par points (ex. "c.q.f.d.").
_INCLUSIVE_WRITING_SUFFIXES = (
    "iennes", "iens", "ienne", "ien",
    "trices", "trice", "teurs", "teur",
    "eures", "eure", "eurs", "eur",
    "euses", "euse",
    "elles", "elle", "els", "el",
    "ales", "aux", "al",
    "ives", "ifs", "ive", "if",
    "onnes", "onne", "ons", "on",
    "ères", "ère", "ers", "er",
    "rices", "rice",
    "nes", "ne",
    "es", "e", "s",
)
_INCLUSIVE_WRITING_RE = re.compile(
    # Mot de base >= 2 lettres : ecarte les abreviations latines courantes a
    # base d'une seule lettre suivie d'un point (ex. "i.e.", ou le "e" de
    # "e.g." coinciderait avec un suffixe de la liste).
    r"\b[A-ZÀ-Þa-zà-öø-ÿ]{2,}(?:\.(?:"
    + "|".join(sorted(set(_INCLUSIVE_WRITING_SUFFIXES), key=len, reverse=True))
    + r")){1,3}\b"
)
# Date : quantieme (1-31) suivi d'un nom de mois. Liste fermee des 12 mois,
# volontairement plus etroite que purh.numeral_dynastique (chiffre romain
# apres nom propre) : un chiffre arabe apres un mot capitalise est bien
# plus frequent en debut de phrase ("Le 24 decembre...") sans rapport avec
# un nom propre, donc pas generalise au-dela de ce motif jour+mois sans
# risque de faux positif.
_MONTHS = (
    "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
    "août", "septembre", "octobre", "novembre", "décembre",
)
_DATE_JOUR_MOIS_RE = re.compile(
    r"\b([1-9]|[12][0-9]|3[01]) (?=(?:" + "|".join(_MONTHS) + r")\b)",
    re.IGNORECASE,
)
_ORDINAL_RE = re.compile(r"\b(\d+)(ère|ere|ème|eme)\b", re.UNICODE)
_NUMERAL_DYNASTIQUE_RE = re.compile(
    r"\b([A-ZÀ-Þ]\w*) "
    r"(XXI|XX|XIX|XVIII|XVII|XVI|XV|XIV|XIII|XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)\b"
)
_ETC_RE = re.compile(r"etc(?:…\.*|\.{2,})")
_PAGINATION_RE = re.compile(
    r"\b(pp?|vol|t|f|fol|fig|chap|cat|pl|ms|Ms|n°|N°|col)\."
    r"\s+(?=[\dIVXLCivxlc])"
)
_NUMERO_RE = re.compile(r"\b([Nn])[°ºoO]\.?[ \t\u00a0\u202f]*(?=\d)")
# Folio et recto/verso : guide PURH p. 12 (tableau des abreviations), meme
# convention que "numero" -> "no" (lettre o en exposant, pas le symbole
# degre). Portee volontairement etroite : n'abrege que lorsque le mot est
# directement suivi d'un chiffre (comme pour "no"), pour ne pas toucher aux
# emplois ordinaires de "recto"/"verso" en prose courante ("le recto de la
# lettre"), qui ne sont pas des abreviations de pagination.
_FOLIO_RE = re.compile(
    r"\b(?:folio|fol\.?|f[°º])[ \t\u00a0\u202f]*(?=\d)", re.IGNORECASE
)
_RECTO_RE = re.compile(r"\b(?:recto|r[°º])[ \t\u00a0\u202f]*(?=\d)", re.IGNORECASE)
_VERSO_RE = re.compile(r"\b(?:verso|v[°º])[ \t\u00a0\u202f]*(?=\d)", re.IGNORECASE)
_REDOUBLEMENT_RE = re.compile(r"\b(pp|vv|ll)\.|§§")
_THOUSANDS_RE = re.compile(r"\b\d{1,3}(?: \d{3})+\b")
_THOUSANDS_GROUP_RE = re.compile(r"(\d{1,3}) (\d{3})(?!\d)")
_INCISE_DASH_RE = re.compile(r"(?<=\w) [-–—] (?=\w)")
_DOUBLE_DASH_RE = re.compile(r"--")
_QUOTE_PUNCT_SUSPECT_RE = re.compile(r"«([^»]+)»\.")
_QUOTE_STRONG_PUNCT = {".", ";", ":", "?", "!", "…"}
_TECHNICAL_ATTRIBUTE_RE = re.compile(r"\b[\w:-]+\s*=\s*$")

_ROMAN_CENTURIES = (
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
    "XI",
    "XII",
    "XIII",
    "XIV",
    "XV",
    "XVI",
    "XVII",
    "XVIII",
    "XIX",
    "XX",
    "XXI",
)
_NON_FIRST_CENTURIES = tuple(
    sorted(_ROMAN_CENTURIES[1:], key=len, reverse=True)
)
_CENTURY_TOKEN_RE = re.compile(
    rf"\b(?:(?P<first>I)(?P<first_suffix>er)\b|"
    rf"(?P<roman>{'|'.join(_NON_FIRST_CENTURIES)})"
    rf"(?P<suffix>ème|eme|e)\b)",
    re.IGNORECASE,
)
_SIECLE_LOOKAHEAD_RE = re.compile(
    r"\A\s+(?:siècles?|arrondissements?)\b", re.IGNORECASE
)
_CENTURY_CHAIN_SEP_RE = re.compile(
    r"\A(?:\s+|,|-|–|—|/|et|ou|au|à)+\Z", re.IGNORECASE
)
_NUMERO_STYLE_RE = re.compile(rf"\b[Nn](o){NNBSP}(?=\d)")
_FOLIO_STYLE_RE = re.compile(rf"\bf(o){NNBSP}(?=\d)")
_RECTO_VERSO_STYLE_RE = re.compile(rf"\b[rv](o){NNBSP}(?=\d)")
_ORDINAL_STYLE_RE = re.compile(r"\b(?P<number>\d+)(?P<suffix>er|re|e)\b")
_CIVILITY_STYLE_RE = re.compile(r"\b(?:Mme|Mlle|Dr|Pr)(?P<plural>s?)\b")


def find_apostrophe_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _APOSTROPHE_RE, "’")


def find_points_suspension_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _POINTS_SUSPENSION_RE, "…")


def _oe_replacement(match: re.Match[str]) -> str:
    original = match.group(1)
    replacement = _OE_LIGATURE_FORMS[original.lower()]
    if original.isupper():
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def find_oe_ligature_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _OE_RE, _oe_replacement)


def find_open_quote_space_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _OPEN_QUOTE_SPACE_RE, "«" + NNBSP)


def find_close_quote_space_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _CLOSE_QUOTE_SPACE_RE, NNBSP + "»")


def _is_technical_token(text: str, punct_pos: int) -> bool:
    token_start = punct_pos
    while token_start > 0 and not text[token_start - 1].isspace():
        token_start -= 1
    token_end = punct_pos + 1
    while token_end < len(text) and not text[token_end].isspace():
        token_end += 1
    token = text[token_start:token_end]
    lowered = token.lower()
    return (
        "http://" in lowered
        or "https://" in lowered
        or "ftp://" in lowered
        or "/" in token
        or "\\" in token
    )


def find_strong_punctuation_edits(text: str) -> list[TextEdit]:
    edits: list[TextEdit] = []
    for match in _STRONG_PUNCT_RE.finditer(text):
        punct = match.group(1)
        punct_pos = match.start(1)
        if _is_technical_token(text, punct_pos):
            continue
        if punct == ":":
            previous = text[punct_pos - 1] if punct_pos else ""
            following = text[punct_pos + 1] if punct_pos + 1 < len(text) else ""
            if previous.isdigit() and following.isdigit():
                continue
        replacement = NNBSP + punct
        if match.group(0) != replacement:
            edits.append(TextEdit(match.start(), match.end(), replacement))
    return edits


def find_weak_punctuation_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _WEAK_PUNCT_RE, r"\1")


def find_double_space_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _DOUBLE_SPACE_RE, " ")


def find_civility_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _CIVILITY_RE, r"\1" + NBSP)


def find_numeral_dynastique_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _NUMERAL_DYNASTIQUE_RE, r"\1" + NBSP + r"\2")


def find_inclusive_writing_edits(text: str) -> list[TextEdit]:
    return _regex_edits(
        text,
        _INCLUSIVE_WRITING_RE,
        lambda match: match.group(0).replace(".", "·"),
    )


def find_date_jour_mois_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _DATE_JOUR_MOIS_RE, r"\1" + NBSP)


def _century_chains(text: str) -> list[list[re.Match[str]]]:
    tokens = list(_CENTURY_TOKEN_RE.finditer(text))
    chains: list[list[re.Match[str]]] = []
    current: list[re.Match[str]] = []
    for token in tokens:
        if current and _CENTURY_CHAIN_SEP_RE.match(
            text[current[-1].end() : token.start()]
        ):
            current.append(token)
            continue
        if current:
            chains.append(current)
        current = [token]
    if current:
        chains.append(current)
    return chains


def find_centuries(text: str) -> list[CenturyMatch]:
    results: list[CenturyMatch] = []
    for chain in _century_chains(text):
        if not _SIECLE_LOOKAHEAD_RE.match(text[chain[-1].end() :]):
            continue
        for match in chain:
            roman = match.group("first") or match.group("roman")
            suffix = match.group("first_suffix") or match.group("suffix")
            results.append(
                CenturyMatch(
                    start=match.start(),
                    end=match.end(),
                    text=match.group(0),
                    roman=roman,
                    suffix=suffix,
                    normalized=roman.lower()
                    + ("er" if roman.lower() == "i" else "e"),
                )
            )
    results.sort(key=lambda match: match.start)
    return results


def find_century_text_edits(text: str) -> list[TextEdit]:
    return [
        TextEdit(match.start, match.end, match.normalized)
        for match in find_centuries(text)
        if match.text != match.normalized
    ]


def _ordinal_replacement(match: re.Match[str]) -> str:
    number = match.group(1)
    suffix = match.group(2).lower()
    if suffix in {"ère", "ere"} and number == "1":
        return "1re"
    if suffix in {"ème", "eme"}:
        return number + "e"
    return match.group(0)


def find_ordinal_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _ORDINAL_RE, _ordinal_replacement)


def find_ordinal_style_matches(text: str) -> list[re.Match[str]]:
    return list(_ORDINAL_STYLE_RE.finditer(text))


def find_civility_style_matches(text: str) -> list[re.Match[str]]:
    return list(_CIVILITY_STYLE_RE.finditer(text))


def find_etc_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _ETC_RE, "etc.")


def find_pagination_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _PAGINATION_RE, r"\1." + NNBSP)


def find_numero_edits(text: str) -> list[TextEdit]:
    return _regex_edits(
        text,
        _NUMERO_RE,
        lambda match: match.group(1) + "o" + NNBSP,
    )


def find_numero_style_matches(text: str) -> list[re.Match[str]]:
    return list(_NUMERO_STYLE_RE.finditer(text))


def find_folio_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _FOLIO_RE, "fo" + NNBSP)


def find_recto_verso_edits(text: str) -> list[TextEdit]:
    edits = list(_regex_edits(text, _RECTO_RE, "ro" + NNBSP)) + list(
        _regex_edits(text, _VERSO_RE, "vo" + NNBSP)
    )
    edits.sort(key=lambda edit: edit.start)
    return edits


def find_folio_style_matches(text: str) -> list[re.Match[str]]:
    return list(_FOLIO_STYLE_RE.finditer(text))


def find_recto_verso_style_matches(text: str) -> list[re.Match[str]]:
    return list(_RECTO_VERSO_STYLE_RE.finditer(text))


def _redoublement_replacement(match: re.Match[str]) -> str:
    return match.group(1)[0] + "." if match.group(1) else "§"


def find_redoublement_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _REDOUBLEMENT_RE, _redoublement_replacement)


def _normalize_thousands(match: re.Match[str]) -> str:
    result = match.group(0)
    previous = None
    while result != previous:
        previous = result
        result = _THOUSANDS_GROUP_RE.sub(r"\1" + NNBSP + r"\2", result)
    return result


def find_thousands_edits(text: str) -> list[TextEdit]:
    return _regex_edits(text, _THOUSANDS_RE, _normalize_thousands)


def find_incise_dash_diagnostics(text: str) -> list[TextEdit]:
    return [
        TextEdit(match.start(), match.end(), match.group(0))
        for match in _INCISE_DASH_RE.finditer(text)
    ]


def _is_technical_quote_context(
    text: str,
    quote_start: int,
    quote_end: int,
) -> bool:
    before = text[max(0, quote_start - 48) : quote_start]
    after = text[quote_end : min(len(text), quote_end + 48)]
    quoted_content = text[quote_start + 1 : quote_end - 1]
    before_stripped = before.rstrip()
    return bool(
        _TECHNICAL_ATTRIBUTE_RE.search(before_stripped)
        or before_stripped.endswith("(")
        or ("<" in before_stripped and ">" not in before_stripped)
        or (before_stripped.endswith(",") and "(" in before_stripped)
        or "\\" in quoted_content
        # Uniquement une parenthese/crochet fermant juste apres : une
        # virgule, un point-virgule ou un deux-points juste apres la
        # citation est la ponctuation normale d'une phrase francaise (« mot »,
        # « mot »; « mot »:) et ne doit pas etre pris pour un indice
        # technique - ce motif a longtemps fait passer des citations de
        # prose ordinaires pour du code/attribut et les a laissees en
        # guillemets anglais non convertis.
        or re.match(r"^\s*[)\]]", after)
    )


_CURLY_QUOTE_OPEN = "“"  # “
_CURLY_QUOTE_CLOSE = "”"  # ”


def _find_english_quote_pairs(text: str) -> list[tuple[int, int, int]]:
    # Guillemets droits ou anglais (" ou " / ") equilibres par une pile :
    # depth (profondeur retournee) = nombre de paires encore ouvertes
    # autour de celle-ci une fois refermee, donc 0 pour une paire de
    # premier niveau, >=1 pour une paire imbriquee ("guillemets dans les
    # guillemets"). Un guillemet droit est ambigu (meme caractere pour
    # ouvrant et fermant) : on le traite comme ouvrant si aucune paire
    # n'est en cours, comme fermant sinon - ce qui permet aussi de fermer
    # une paire ouverte par un guillemet anglais courbe si le document
    # melange les deux styles.
    #
    # Les chevrons deja presents («/») comptent aussi comme ouvrant/fermant
    # dans la pile (sans etre retournes comme paire a convertir) : sinon,
    # rejouer cette fonction sur un texte deja corrige verrait une paire
    # anglaise imbriquee dans des chevrons comme une paire de premier
    # niveau et la convertirait a tort - non idempotent.
    stack: list[int] = []
    pairs: list[tuple[int, int, int]] = []
    for index, char in enumerate(text):
        if char == "«" or char == _CURLY_QUOTE_OPEN:
            stack.append(index)
        elif char == "»" or char == _CURLY_QUOTE_CLOSE:
            if stack:
                start = stack.pop()
                pairs.append((start, index, len(stack)))
        elif char == '"':
            if stack:
                start = stack.pop()
                pairs.append((start, index, len(stack)))
            else:
                stack.append(index)
    return pairs


def find_english_quote_conversion_edits(text: str) -> list[TextEdit]:
    # Regle de base PURH : les guillemets droits ou anglais deviennent des
    # chevrons francais. Exception : une paire imbriquee dans une autre
    # (depth >= 1) reste en l'etat - c'est la convention pour une citation
    # a l'interieur d'une citation. Les contextes techniques (attribut,
    # URL, parenthese...) sont egalement laisses de cote, comme pour le
    # diagnostic purh.guillemets.droits dont ils partagent la logique.
    edits: list[TextEdit] = []
    for start, end, depth in _find_english_quote_pairs(text):
        if depth != 0:
            continue
        if _is_technical_quote_context(text, start, end + 1):
            continue
        if text[start] != "«":
            edits.append(TextEdit(start, start + 1, "«"))
        if text[end] != "»":
            edits.append(TextEdit(end, end + 1, "»"))
    edits.sort(key=lambda edit: edit.start)
    return edits


def find_straight_quote_diagnostics(text: str) -> list[TextEdit]:
    # Ne signale que les paires de premier niveau que la conversion
    # elle-meme a laissees de cote par prudence (contexte technique
    # ambigu) : une paire imbriquee est la convention attendue et n'a pas
    # besoin d'etre relue, une paire de premier niveau normale vient d'etre
    # convertie en chevrons par find_english_quote_conversion_edits.
    diagnostics: list[TextEdit] = []
    for start, end, depth in _find_english_quote_pairs(text):
        if depth != 0:
            continue
        if text[start] == "«" and text[end] == "»":
            continue
        if not _is_technical_quote_context(text, start, end + 1):
            continue
        diagnostics.append(TextEdit(start, end + 1, text[start : end + 1]))
    return diagnostics


def find_double_dash_diagnostics(text: str) -> list[TextEdit]:
    return [
        TextEdit(match.start(), match.end(), match.group(0))
        for match in _DOUBLE_DASH_RE.finditer(text)
    ]


def find_quote_punctuation_diagnostics(text: str) -> list[TextEdit]:
    diagnostics: list[TextEdit] = []
    for match in _QUOTE_PUNCT_SUSPECT_RE.finditer(text):
        inside = match.group(1).strip()
        if not inside or any(
            quote in inside for quote in ("“", "”", '"', "«", "»")
        ):
            continue
        before_open = text[: match.start()].rstrip()
        if inside[-1] in _QUOTE_STRONG_PUNCT or before_open.endswith(":"):
            diagnostics.append(
                TextEdit(match.start(), match.end(), match.group(0))
            )
    return diagnostics


ORTHOTYPOGRAPHY_DIAGNOSTIC_RULES = (
    ("purh.guillemets.droits", find_straight_quote_diagnostics),
    ("purh.tiret.double", find_double_dash_diagnostics),
    ("purh.guillemets.ponctuation_fermante", find_quote_punctuation_diagnostics),
)


ORTHOTYPOGRAPHY_TEXT_RULES = (
    ("purh.apostrophe", find_apostrophe_edits),
    ("purh.points_suspension", find_points_suspension_edits),
    ("purh.ligature.oe", find_oe_ligature_edits),
    ("purh.guillemets.anglais_vers_chevrons", find_english_quote_conversion_edits),
    ("purh.guillemets.espace_apres_ouvrant", find_open_quote_space_edits),
    ("purh.guillemets.espace_avant_fermant", find_close_quote_space_edits),
    ("purh.espaces.avant_ponct_forte", find_strong_punctuation_edits),
    ("purh.espaces.avant_ponct_faible", find_weak_punctuation_edits),
    ("purh.espaces.double", find_double_space_edits),
    ("purh.civilite", find_civility_edits),
    ("purh.numeral_dynastique", find_numeral_dynastique_edits),
    ("purh.siecles", find_century_text_edits),
    ("purh.ordinaux", find_ordinal_edits),
    ("purh.abreviations.etc", find_etc_edits),
    ("purh.pagination.espace", find_pagination_edits),
    ("purh.numero", find_numero_edits),
    ("purh.folio", find_folio_edits),
    ("purh.recto_verso", find_recto_verso_edits),
    ("purh.abreviations.redoublement", find_redoublement_edits),
    ("purh.nombres.milliers", find_thousands_edits),
    ("purh.ecriture_inclusive.point_median", find_inclusive_writing_edits),
    ("purh.date.jour_mois", find_date_jour_mois_edits),
)


def apply_text_edits(text: str, edits: list[TextEdit]) -> str:
    result = text
    for edit in reversed(edits):
        result = result[: edit.start] + edit.replacement + result[edit.end :]
    return result


def normalize_points_suspension(text: str) -> str:
    return apply_text_edits(text, find_points_suspension_edits(text))
