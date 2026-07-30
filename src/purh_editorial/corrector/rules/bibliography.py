from __future__ import annotations

import re

from purh_editorial.corrector.rules.orthotypography import NNBSP, TextEdit

_PAGINATION_RE = re.compile(
    r"\b(pp?|vol|t|f|fig|col|n°|N°)\.\s+(?=[\dIVXLCivxlc])"
)
_NUMERO_RE = re.compile(r"\b([Nn]°)\s+(?=\d)")


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

