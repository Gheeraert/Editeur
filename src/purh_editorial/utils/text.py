from __future__ import annotations

import re


MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
SPACE_BEFORE_STRONG_PUNCT_RE = re.compile(r"(?<![\s\u00A0\u202F])([:;?!])")
SPACE_BEFORE_WEAK_PUNCT_RE = re.compile(r"\s+([,.\)])")
STRAIGHT_QUOTES_RE = re.compile(r'"')


def collapse_spaces(text: str) -> str:
    return MULTI_SPACE_RE.sub(" ", text)


def strip_trailing_spaces(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.splitlines())


def normalize_space_before_strong_punctuation(text: str) -> str:
    text = re.sub(r"\s*([:;?!])", r"\u00A0\1", text)
    return text


def remove_space_before_weak_punctuation(text: str) -> str:
    return SPACE_BEFORE_WEAK_PUNCT_RE.sub(r"\1", text)


def detect_space_before_strong_punctuation_issue(text: str) -> list[str]:
    return [match.group(1) for match in SPACE_BEFORE_STRONG_PUNCT_RE.finditer(text)]


def has_straight_quotes(text: str) -> bool:
    return bool(STRAIGHT_QUOTES_RE.search(text))
