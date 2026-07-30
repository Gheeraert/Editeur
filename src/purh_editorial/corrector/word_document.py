from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from purh_editorial.corrector.rules.footnotes import find_op_cit_edits
from purh_editorial.corrector.rules.orthotypography import (
    CenturyMatch,
    find_centuries,
    find_points_suspension_edits,
)

WD_MAIN_TEXT_STORY = 1
WD_YELLOW = 7

COUNTER_IDS = (
    "purh.points_suspension",
    "purh.siecles",
    "R-SO-001",
    "purh.note.espace_op_cit",
)


def _paragraph_text(paragraph: Any) -> str:
    text = paragraph.Range.Text
    while text.endswith(("\r", "\x07")):
        text = text[:-1]
    return text


def _exact_range(paragraph: Any, start: int, end: int) -> Any:
    target = paragraph.Range.Duplicate
    absolute_start = paragraph.Range.Start + start
    target.SetRange(absolute_start, paragraph.Range.Start + end)
    return target


def _replace_and_highlight(
    paragraph: Any,
    start: int,
    end: int,
    replacement: str,
) -> Any:
    target = _exact_range(paragraph, start, end)
    absolute_start = target.Start
    target.Text = replacement
    target.SetRange(absolute_start, absolute_start + len(replacement))
    target.HighlightColorIndex = WD_YELLOW
    return target


def _apply_text_edits(
    paragraph: Any,
    finder: Callable[[str], list[Any]],
) -> int:
    edits = finder(_paragraph_text(paragraph))
    for edit in reversed(edits):
        _replace_and_highlight(
            paragraph,
            edit.start,
            edit.end,
            edit.replacement,
        )
    return len(edits)


def _is_word_true(value: Any) -> bool:
    return value is True or value == -1


def _is_word_false(value: Any) -> bool:
    return value is False or value == 0


def _century_style_needs_change(paragraph: Any, match: CenturyMatch) -> bool:
    roman_end = match.start + len(match.roman)
    roman_range = _exact_range(paragraph, match.start, roman_end)
    suffix_range = _exact_range(paragraph, roman_end, match.end)
    return not (
        _is_word_true(roman_range.Font.SmallCaps)
        and _is_word_false(roman_range.Font.Superscript)
        and _is_word_false(suffix_range.Font.SmallCaps)
        and _is_word_true(suffix_range.Font.Superscript)
    )


def _style_century(paragraph: Any, match: CenturyMatch) -> None:
    roman_end = match.start + len(match.roman)
    roman_range = _exact_range(paragraph, match.start, roman_end)
    suffix_range = _exact_range(paragraph, roman_end, match.end)
    roman_range.Font.SmallCaps = True
    roman_range.Font.Superscript = False
    suffix_range.Font.SmallCaps = False
    suffix_range.Font.Superscript = True


def _apply_centuries(paragraph: Any, counts: dict[str, int]) -> None:
    matches = find_centuries(_paragraph_text(paragraph))
    for match in reversed(matches):
        text_changed = match.text != match.normalized
        if text_changed:
            target = _exact_range(paragraph, match.start, match.end)
            target.Text = match.normalized

        normalized_match = CenturyMatch(
            start=match.start,
            end=match.start + len(match.normalized),
            text=match.normalized,
            roman=match.roman.lower(),
            suffix=match.suffix.lower(),
            normalized=match.normalized,
        )
        style_changed = _century_style_needs_change(paragraph, normalized_match)
        if style_changed:
            _style_century(paragraph, normalized_match)

        if text_changed or style_changed:
            century_range = _exact_range(
                paragraph,
                normalized_match.start,
                normalized_match.end,
            )
            century_range.HighlightColorIndex = WD_YELLOW
        if text_changed:
            counts["purh.siecles"] += 1
        if style_changed:
            counts["R-SO-001"] += 1


def _apply_main_text(document: Any, counts: dict[str, int]) -> None:
    story = document.StoryRanges(WD_MAIN_TEXT_STORY)
    for paragraph in story.Paragraphs:
        counts["purh.points_suspension"] += _apply_text_edits(
            paragraph,
            find_points_suspension_edits,
        )
        _apply_centuries(paragraph, counts)


def _apply_footnotes(document: Any, counts: dict[str, int]) -> None:
    for footnote in document.Footnotes:
        for paragraph in footnote.Range.Paragraphs:
            counts["purh.note.espace_op_cit"] += _apply_text_edits(
                paragraph,
                find_op_cit_edits,
            )


def correct_word_copy(path: Path) -> dict[str, int]:
    try:
        from win32com.client import DispatchEx
    except ImportError as exc:
        raise RuntimeError(
            "pywin32 est requis pour automatiser Microsoft Word."
        ) from exc

    counts = {rule_id: 0 for rule_id in COUNTER_IDS}
    word = None
    document = None
    try:
        word = DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        document = word.Documents.Open(
            FileName=str(path),
            ReadOnly=False,
            AddToRecentFiles=False,
            Visible=False,
        )
        _apply_main_text(document, counts)
        _apply_footnotes(document, counts)
        document.Save()
        return counts
    except Exception as exc:
        raise RuntimeError(f"Correction Microsoft Word impossible : {exc}") from exc
    finally:
        if document is not None:
            try:
                document.Close(SaveChanges=False)
            except Exception:
                pass
        document = None
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        word = None

