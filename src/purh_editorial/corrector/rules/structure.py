from __future__ import annotations

import re

FRONTMATTER_PATTERNS = (
    (
        "structure.frontmatter.abstract",
        re.compile(r"^(résumé|abstract|summary)(?:\s*[:—-].*)?$", re.IGNORECASE),
    ),
    (
        "structure.frontmatter.keywords",
        re.compile(r"^(mots[- ]clés?|keywords?)(?:\s*[:—-].*)?$", re.IGNORECASE),
    ),
    (
        "structure.frontmatter.acknowledgment",
        re.compile(
            r"^(remerciements?|acknowledgments?)(?:\s*[:—-].*)?$",
            re.IGNORECASE,
        ),
    ),
)


def detect_frontmatter_rule(text: str) -> str | None:
    stripped = text.strip()
    for rule_id, pattern in FRONTMATTER_PATTERNS:
        if pattern.fullmatch(stripped):
            return rule_id
    return None


# Seuil de 4 lettres : ecarte les marqueurs courts de type "I", "A" (chiffre
# romain ou lettre de partie/annexe), qui sont legitimement tout capitales
# et ne doivent pas etre signales.
_ALLCAPS_HEADING_MIN_LETTERS = 4


def is_allcaps_heading(text: str) -> bool:
    stripped = text.strip()
    if sum(char.isalpha() for char in stripped) < _ALLCAPS_HEADING_MIN_LETTERS:
        return False
    return stripped.isupper()

