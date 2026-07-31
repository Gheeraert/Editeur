from __future__ import annotations

import re

from purh_editorial.corrector.rules.orthotypography import NNBSP, TextEdit

_PAGINATION_RE = re.compile(
    r"\b(pp?|vol|t|f|fig|col|n°|N°)\.\s+(?=[\dIVXLCivxlc])"
)
_NUMERO_RE = re.compile(r"\b([Nn]°)\s+(?=\d)")

# Titre de section bibliographique reconnu par son style Word (Titre 1/2 —
# voir _is_heading_style dans word_document.py), pas par une heuristique de
# mise en forme scorée : condition explicite et testable, cf.
# docs/REBORN_ARCHITECTURE.md §6.
BIBLIOGRAPHY_SECTION_HEADING_RE = re.compile(
    r"^(sources?|bibliographie|références\s*bibliographiques?|bibliography|"
    r"travaux\s*cités?|works?\s*cited|références)\b",
    re.IGNORECASE,
)

_CLOSING_PUNCTUATION_OR_QUOTE = {".", "!", "?", "…", "»"}
_LIST_ITEM_RE = re.compile(r"^\s*[-–—•]\s")
_URL_OR_DOI_END_RE = re.compile(r"(https?://\S+|doi\s*:\s*\S+)$", re.IGNORECASE)


def find_bibliography_final_punctuation_edits(text: str) -> list[TextEdit]:
    """Ajoute un point final à une entrée bibliographique qui n'en a pas.

    Ne s'applique qu'aux paragraphes déjà identifiés comme entrées d'une
    section bibliographique par l'appelant (cf. `_apply_bibliography_section`
    dans word_document.py) : ce détecteur n'a aucun moyen, à lui seul, de
    distinguer une entrée bibliographique d'un paragraphe ordinaire.
    """
    stripped = text.rstrip()
    if (
        not stripped
        or stripped[-1] in _CLOSING_PUNCTUATION_OR_QUOTE
        or _LIST_ITEM_RE.match(text)
        or _URL_OR_DOI_END_RE.search(stripped)
    ):
        return []
    return [TextEdit(len(stripped), len(text), ".")]


def find_bibliography_pagination_edits(text: str) -> list[TextEdit]:
    return [
        TextEdit(
            match.start(),
            match.end(),
            match.group(1) + "." + NNBSP,
        )
        for match in _PAGINATION_RE.finditer(text)
        if match.group(0) != match.group(1) + "." + NNBSP
    ]


def find_bibliography_numero_edits(text: str) -> list[TextEdit]:
    return [
        TextEdit(
            match.start(),
            match.end(),
            match.group(1) + NNBSP,
        )
        for match in _NUMERO_RE.finditer(text)
        if match.group(0) != match.group(1) + NNBSP
    ]


BIBLIOGRAPHY_TEXT_RULES = (
    ("purh.biblio.pagination_nnbsp", find_bibliography_pagination_edits),
    ("purh.biblio.numero_nnbsp", find_bibliography_numero_edits),
)

