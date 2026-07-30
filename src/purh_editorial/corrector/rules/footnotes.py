from __future__ import annotations

import re

from purh_editorial.corrector.rules.orthotypography import TextEdit, apply_text_edits

NNBSP = "\u202f"

_OP_CIT_RE = re.compile(
    r"\b(op|art|loc)\.([ \t\u00a0\u202f]+)(cit)\.",
    re.IGNORECASE,
)


def find_op_cit_edits(text: str) -> list[TextEdit]:
    edits: list[TextEdit] = []
    for match in _OP_CIT_RE.finditer(text):
        if match.group(2) == NNBSP:
            continue
        replacement = f"{match.group(1)}.{NNBSP}{match.group(3)}."
        edits.append(TextEdit(match.start(), match.end(), replacement))
    return edits


def normalize_op_cit_spacing(text: str) -> str:
    return apply_text_edits(text, find_op_cit_edits(text))

