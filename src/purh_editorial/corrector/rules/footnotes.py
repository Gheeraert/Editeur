from __future__ import annotations

import re

from purh_editorial.corrector.rules.orthotypography import (
    NNBSP,
    TextEdit,
    apply_text_edits,
)

_LEADING_SPACE_RE = re.compile(r"[ \t\u00a0\u202f]*")
_OP_CIT_RE = re.compile(
    r"\b(op|art|loc)\.([ \t\u00a0\u202f]+)(cit)\.",
    re.IGNORECASE,
)
_SL_SD_RE = re.compile(r"\bs\.([ \t\u00a0\u202f]+)([ld])\.", re.IGNORECASE)
_URL_RE = re.compile(r"https?://\S+$")
_VERSE_END_RE = re.compile(r"[»›’]\s*$")
_URL_OR_DOI_START_RE = re.compile(
    r"^\s*(https?://|www\.|doi\s*:)",
    re.IGNORECASE,
)
_PARTICLE_START_RE = re.compile(
    r"^\s*(van|von|de|du|des)\b|^\s*d['’]",
    re.IGNORECASE,
)
_LATIN_ABBR_START_RE = re.compile(
    r"^\s*(ibid|id|idem|op\.\s*cit|art\.\s*cit|loc\.\s*cit|s\.\s*[ld])\.?\b",
    re.IGNORECASE,
)
_MIDNOTE_LATIN_ABBR_RE = re.compile(
    r"(?<!^)\b(Ibid|Id|Idem|Op\.\s*cit|Art\.\s*cit|Loc\.\s*cit)\b\.?",
    re.IGNORECASE,
)
_LATIN_ITALIC_RE = re.compile(
    r"\b(ibid|id|idem|op\.\s*cit|art\.\s*cit|loc\.\s*cit)\b\.?",
    re.IGNORECASE,
)
_LIST_ITEM_RE = re.compile(r"^\s*[-–—•]\s")
_CLOSING_PUNCTUATION_OR_QUOTE = {".", "!", "?", "…", "»", "”", "’"}

NOTE_CALL_SPACES = {" ", "\u00a0", "\u202f"}
NOTE_CALL_FINAL_PUNCTUATION = {".", ",", ";", ":", "?", "!"}
NOTE_CALL_CLOSING_QUOTES = {"»", '"', "”", "›"}


def find_initial_space_edits(text: str) -> list[TextEdit]:
    # Le numero d'appel de note (marque de reference Word, hors texte) n'est
    # jamais suivi d'une espace automatique dans le corps de la note : sans
    # separateur explicite, le texte colle au numero. On normalise donc le
    # debut de note a exactement une espace normale (jamais zero, jamais une
    # tabulation/espace insecable/espaces multiples), sans jamais toucher au
    # premier caractere de contenu reel : un remplacement qui l'engloberait
    # perdrait sa mise en forme de caractere (italique, gras...) puisque Word
    # applique a un Range.Text reecrit la mise en forme du debut de la plage
    # d'origine plutot que celle du caractere remplace.
    content_start = 1 if text.startswith("\x02") else 0
    if content_start >= len(text):
        return []
    match = _LEADING_SPACE_RE.match(text, content_start)
    run_end = match.end()
    if run_end >= len(text):
        return []
    if text[content_start:run_end] == " ":
        return []
    return [TextEdit(content_start, run_end, " ")]


def find_op_cit_edits(text: str) -> list[TextEdit]:
    edits: list[TextEdit] = []
    for match in _OP_CIT_RE.finditer(text):
        if match.group(2) == NNBSP:
            continue
        replacement = f"{match.group(1)}.{NNBSP}{match.group(3)}."
        edits.append(TextEdit(match.start(), match.end(), replacement))
    return edits


def find_sans_lieu_date_edits(text: str) -> list[TextEdit]:
    edits: list[TextEdit] = []
    for match in _SL_SD_RE.finditer(text):
        if match.group(1) == NNBSP:
            continue
        replacement = f"s.{NNBSP}{match.group(2)}."
        edits.append(TextEdit(match.start(), match.end(), replacement))
    return edits


def _content_start(text: str) -> int:
    # Doit rester cohérent avec le séparateur normalisé par
    # find_initial_space_edits (une espace normale unique après le numéro
    # d'appel de note) : les règles qui portent sur le "vrai" premier
    # caractère de la note (majuscule initiale, abréviation latine,
    # ponctuation finale...) doivent l'ignorer.
    start = 1 if text.startswith("\x02") else 0
    if start < len(text) and text[start] == " ":
        start += 1
    return start


def _majuscule_initiale_excluded(text: str) -> bool:
    return bool(
        _URL_OR_DOI_START_RE.match(text)
        or _PARTICLE_START_RE.match(text)
        or _LATIN_ABBR_START_RE.match(text)
    )


def _looks_like_url_or_verse(text: str) -> bool:
    stripped = text.strip()
    return bool(_URL_RE.search(stripped) or _VERSE_END_RE.search(stripped))


def find_initial_capital_edits(text: str) -> list[TextEdit]:
    start = _content_start(text)
    content = text[start:]
    if (
        not content
        or not content[0].islower()
        or _majuscule_initiale_excluded(content)
    ):
        return []
    return [TextEdit(start, start + 1, content[0].upper())]


def find_latin_abbreviation_edits(text: str) -> list[TextEdit]:
    start = _content_start(text)
    content = text[start:]
    edits: list[TextEdit] = []
    for match in _MIDNOTE_LATIN_ABBR_RE.finditer(content):
        replacement = match.group(0).lower()
        if replacement != match.group(0):
            edits.append(
                TextEdit(
                    start + match.start(),
                    start + match.end(),
                    replacement,
                )
            )
    return edits


def find_latin_abbreviation_ranges(text: str) -> list[TextEdit]:
    start = _content_start(text)
    content = text[start:]
    return [
        TextEdit(start + match.start(), start + match.end(), match.group(0))
        for match in _LATIN_ITALIC_RE.finditer(content)
    ]


def find_final_punctuation_edits(text: str) -> list[TextEdit]:
    start = _content_start(text)
    content = text[start:]
    stripped = content.rstrip()
    if (
        not stripped
        or stripped[-1] in _CLOSING_PUNCTUATION_OR_QUOTE
        or _looks_like_url_or_verse(stripped)
        or _LIST_ITEM_RE.match(content)
    ):
        return []
    return [TextEdit(start + len(stripped), len(text), ".")]


def find_lowercase_start_diagnostics(text: str) -> list[TextEdit]:
    start = _content_start(text)
    content = text[start:]
    if (
        content
        and content[0].islower()
        and _majuscule_initiale_excluded(content)
    ):
        return [TextEdit(start, start + 1, content[0])]
    return []


def find_ambiguous_final_punctuation_diagnostics(
    text: str,
) -> list[TextEdit]:
    start = _content_start(text)
    content = text[start:]
    stripped = content.rstrip()
    if (
        stripped
        and stripped[-1] not in _CLOSING_PUNCTUATION_OR_QUOTE
        and (
            _looks_like_url_or_verse(stripped)
            or _LIST_ITEM_RE.match(content)
        )
    ):
        end = start + len(stripped)
        return [TextEdit(end - 1, end, stripped[-1])]
    return []


FOOTNOTE_RULES = (
    ("purh.note.espace_initiale", find_initial_space_edits),
    ("purh.note.majuscule_initiale", find_initial_capital_edits),
    ("purh.note.abreviation_latine", find_latin_abbreviation_edits),
    ("purh.note.espace_op_cit", find_op_cit_edits),
    ("purh.note.espace_sans_lieu_date", find_sans_lieu_date_edits),
    ("purh.note.ponctuation_finale", find_final_punctuation_edits),
)

FOOTNOTE_DIAGNOSTIC_RULES = (
    ("purh.note.diagnostic.debut_minuscule", find_lowercase_start_diagnostics),
    ("purh.note.diagnostic.ponctuation_finale_ambigue", find_ambiguous_final_punctuation_diagnostics),
)


def note_call_diagnostic_ids(previous_character: str) -> tuple[str, ...]:
    rule_ids: list[str] = []
    if previous_character in NOTE_CALL_SPACES:
        rule_ids.append("purh.note.appel.espace_avant")
    if (
        previous_character in NOTE_CALL_FINAL_PUNCTUATION
        or previous_character in NOTE_CALL_CLOSING_QUOTES
    ):
        rule_ids.append("purh.note.appel.placement")
    return tuple(rule_ids)


def normalize_op_cit_spacing(text: str) -> str:
    return apply_text_edits(text, find_op_cit_edits(text))
