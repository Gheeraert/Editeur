from __future__ import annotations

import re
from dataclasses import dataclass


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


_POINTS_SUSPENSION_RE = re.compile(r"(?<!\.)\.\.\.(?!\.)")

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
_CENTURY_RE = re.compile(
    rf"\b(?:(?P<first>I)(?P<first_suffix>er)|"
    rf"(?P<roman>{'|'.join(_NON_FIRST_CENTURIES)})"
    rf"(?P<suffix>ème|eme|e))(?=\s+siècles?\b)",
    re.IGNORECASE,
)


def find_points_suspension_edits(text: str) -> list[TextEdit]:
    return [
        TextEdit(match.start(), match.end(), "…")
        for match in _POINTS_SUSPENSION_RE.finditer(text)
    ]


def find_centuries(text: str) -> list[CenturyMatch]:
    results: list[CenturyMatch] = []
    for match in _CENTURY_RE.finditer(text):
        roman = match.group("first") or match.group("roman")
        suffix = match.group("first_suffix") or match.group("suffix")
        results.append(
            CenturyMatch(
                start=match.start(),
                end=match.end(),
                text=match.group(0),
                roman=roman,
                suffix=suffix,
                normalized=roman.lower() + ("er" if roman.lower() == "i" else "e"),
            )
        )
    return results


def apply_text_edits(text: str, edits: list[TextEdit]) -> str:
    result = text
    for edit in reversed(edits):
        result = result[: edit.start] + edit.replacement + result[edit.end :]
    return result


def normalize_points_suspension(text: str) -> str:
    return apply_text_edits(text, find_points_suspension_edits(text))

