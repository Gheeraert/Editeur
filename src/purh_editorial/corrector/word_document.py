from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from purh_editorial.corrector.rules.bibliography import (
    BIBLIOGRAPHY_SECTION_HEADING_RE,
    BIBLIOGRAPHY_TEXT_RULES,
    find_bibliography_author_casing_edits,
    find_bibliography_final_punctuation_edits,
)
from purh_editorial.corrector.rules.footnotes import (
    FOOTNOTE_DIAGNOSTIC_RULES,
    FOOTNOTE_RULES,
    find_latin_abbreviation_ranges,
    note_call_diagnostic_ids,
)
from purh_editorial.corrector.rules.orthotypography import (
    ORTHOTYPOGRAPHY_DIAGNOSTIC_RULES,
    ORTHOTYPOGRAPHY_TEXT_RULES,
    CenturyMatch,
    find_centuries,
    find_civility_style_matches,
    find_folio_style_matches,
    find_incise_dash_diagnostics,
    find_numero_style_matches,
    find_ordinal_style_matches,
    find_recto_verso_style_matches,
)
from purh_editorial.corrector.rules.structure import (
    detect_frontmatter_rule,
    is_allcaps_heading,
)

WD_MAIN_TEXT_STORY = 1
WD_YELLOW = 7
WD_TURQUOISE = 3

# Style Word explicite (Titre 1/2/3/4 en français, Heading 1-4 en anglais) —
# condition observable et déterministe, pas une heuristique de mise en forme
# scorée. Cf. docs/REBORN_ARCHITECTURE.md §6.
_HEADING_STYLE_RE = re.compile(r"(titre|heading)\s*[1-4]\b", re.IGNORECASE)

# Sous-ensemble de ORTHOTYPOGRAPHY_TEXT_RULES applique aussi aux notes de bas
# de page : la conversion des guillemets anglais/droits en chevrons (et
# l'espace insecable qui l'accompagne) doit valoir partout, pas seulement
# dans le texte principal. L'ordre (conversion puis espacement) est celui de
# ORTHOTYPOGRAPHY_TEXT_RULES, indispensable pour que l'espace insecable soit
# posee sur les chevrons fraichement convertis.
FOOTNOTE_QUOTE_TEXT_RULES = tuple(
    (rule_id, finder)
    for rule_id, finder in ORTHOTYPOGRAPHY_TEXT_RULES
    if rule_id
    in {
        "purh.guillemets.anglais_vers_chevrons",
        "purh.guillemets.espace_apres_ouvrant",
        "purh.guillemets.espace_avant_fermant",
    }
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
) -> bool:
    target = _exact_range(paragraph, start, end)
    original = target.Text
    absolute_start = target.Start
    try:
        target.Text = replacement
    except Exception as exc:
        if "Impossible de supprimer la plage" in str(exc):
            target = None
            return False
        raise
    result_length = len(replacement)
    target.SetRange(absolute_start, absolute_start + result_length)
    if target.Text == original:
        target = None
        return False
    target.HighlightColorIndex = WD_YELLOW
    target = None
    return True


def _apply_text_edits(
    paragraph: Any,
    finder: Callable[[str], list[Any]],
) -> int:
    edits = finder(_paragraph_text(paragraph))
    changed = 0
    for edit in reversed(edits):
        if _replace_and_highlight(
            paragraph,
            edit.start,
            edit.end,
            edit.replacement,
        ):
            changed += 1
    return changed


def _is_word_true(value: Any) -> bool:
    return value is True or value == -1


def _is_word_false(value: Any) -> bool:
    return value is False or value == 0


def _century_style_needs_change(paragraph: Any, match: CenturyMatch) -> bool:
    roman_end = match.start + len(match.roman)
    roman_range = _exact_range(paragraph, match.start, roman_end)
    suffix_range = _exact_range(paragraph, roman_end, match.end)
    needs_change = not (
        _is_word_true(roman_range.Font.SmallCaps)
        and _is_word_false(roman_range.Font.Superscript)
        and _is_word_false(suffix_range.Font.SmallCaps)
        and _is_word_true(suffix_range.Font.Superscript)
    )
    suffix_range = None
    roman_range = None
    return needs_change


def _style_century(paragraph: Any, match: CenturyMatch) -> None:
    roman_end = match.start + len(match.roman)
    roman_range = _exact_range(paragraph, match.start, roman_end)
    suffix_range = _exact_range(paragraph, roman_end, match.end)
    roman_range.Font.SmallCaps = True
    roman_range.Font.Superscript = False
    suffix_range.Font.SmallCaps = False
    suffix_range.Font.Superscript = True
    suffix_range = None
    roman_range = None


def _apply_century_styles(paragraph: Any) -> int:
    changed = 0
    for match in reversed(find_centuries(_paragraph_text(paragraph))):
        if not _century_style_needs_change(paragraph, match):
            continue
        _style_century(paragraph, match)
        century_range = _exact_range(paragraph, match.start, match.end)
        century_range.HighlightColorIndex = WD_YELLOW
        century_range = None
        changed += 1
    return changed


def _apply_numero_styles(paragraph: Any) -> int:
    changed = 0
    for match in reversed(find_numero_style_matches(_paragraph_text(paragraph))):
        target = _exact_range(paragraph, match.start(1), match.end(1))
        if not _is_word_true(target.Font.Superscript):
            target.Font.Superscript = True
            complete = _exact_range(paragraph, match.start(), match.end())
            complete.HighlightColorIndex = WD_YELLOW
            complete = None
            changed += 1
        target = None
    return changed


def _apply_folio_styles(paragraph: Any) -> int:
    changed = 0
    for match in reversed(find_folio_style_matches(_paragraph_text(paragraph))):
        target = _exact_range(paragraph, match.start(1), match.end(1))
        if not _is_word_true(target.Font.Superscript):
            target.Font.Superscript = True
            complete = _exact_range(paragraph, match.start(), match.end())
            complete.HighlightColorIndex = WD_YELLOW
            complete = None
            changed += 1
        target = None
    return changed


def _apply_recto_verso_styles(paragraph: Any) -> int:
    changed = 0
    for match in reversed(find_recto_verso_style_matches(_paragraph_text(paragraph))):
        target = _exact_range(paragraph, match.start(1), match.end(1))
        if not _is_word_true(target.Font.Superscript):
            target.Font.Superscript = True
            complete = _exact_range(paragraph, match.start(), match.end())
            complete.HighlightColorIndex = WD_YELLOW
            complete = None
            changed += 1
        target = None
    return changed


def _apply_ordinal_styles(paragraph: Any) -> int:
    changed = 0
    for match in reversed(find_ordinal_style_matches(_paragraph_text(paragraph))):
        target = _exact_range(paragraph, match.start("suffix"), match.end("suffix"))
        if not _is_word_true(target.Font.Superscript):
            target.Font.Superscript = True
            complete = _exact_range(paragraph, match.start(), match.end())
            complete.HighlightColorIndex = WD_YELLOW
            complete = None
            changed += 1
        target = None
    return changed


def _apply_civility_styles(paragraph: Any) -> int:
    changed = 0
    for match in reversed(find_civility_style_matches(_paragraph_text(paragraph))):
        target = _exact_range(paragraph, match.start() + 1, match.end())
        if not _is_word_true(target.Font.Superscript):
            target.Font.Superscript = True
            complete = _exact_range(paragraph, match.start(), match.end())
            complete.HighlightColorIndex = WD_YELLOW
            complete = None
            changed += 1
        target = None
    return changed


def _apply_footnote_latin_italic(paragraph: Any) -> int:
    changed = 0
    for edit in reversed(find_latin_abbreviation_ranges(_paragraph_text(paragraph))):
        target = _exact_range(paragraph, edit.start, edit.end)
        if not _is_word_true(target.Font.Italic):
            target.Font.Italic = True
            target.HighlightColorIndex = WD_YELLOW
            changed += 1
        target = None
    return changed


def _apply_incise_diagnostics(paragraph: Any) -> int:
    diagnostics = find_incise_dash_diagnostics(_paragraph_text(paragraph))
    for diagnostic in diagnostics:
        target = _exact_range(paragraph, diagnostic.start, diagnostic.end)
        target.HighlightColorIndex = WD_TURQUOISE
        target = None
    return len(diagnostics)


def _apply_diagnostics(
    paragraph: Any,
    finder: Callable[[str], list[Any]],
) -> int:
    diagnostics = finder(_paragraph_text(paragraph))
    for diagnostic in diagnostics:
        target = _exact_range(
            paragraph,
            diagnostic.start,
            diagnostic.end,
        )
        target.HighlightColorIndex = WD_TURQUOISE
        target = None
    return len(diagnostics)


def _paragraph_style_name(paragraph: Any) -> str:
    try:
        return str(paragraph.Range.Style.NameLocal)
    except Exception:
        return ""


def _is_heading_paragraph(paragraph: Any) -> bool:
    return bool(_HEADING_STYLE_RE.search(_paragraph_style_name(paragraph)))


def _apply_frontmatter_diagnostic(paragraph: Any, counts: dict[str, int]) -> None:
    rule_id = detect_frontmatter_rule(_paragraph_text(paragraph))
    if rule_id is None:
        return
    paragraph.Range.HighlightColorIndex = WD_TURQUOISE
    counts[rule_id] += 1


def _apply_allcaps_heading_diagnostic(paragraph: Any, counts: dict[str, int]) -> None:
    # Diagnostic seul (surlignage turquoise), pas de transformation de texte :
    # ramener un titre tout capitales a la casse phrase perdrait la casse
    # d'un nom propre eventuellement present dans le titre (aucune information
    # de casse d'origine a preserver une fois le texte tout capitales).
    if not is_allcaps_heading(_paragraph_text(paragraph)):
        return
    paragraph.Range.HighlightColorIndex = WD_TURQUOISE
    counts["structure.allcaps.heading"] += 1


def _apply_bibliography_entry(paragraph: Any, counts: dict[str, int]) -> None:
    counts["purh.biblio.ponctuation_finale"] += _apply_text_edits(
        paragraph, find_bibliography_final_punctuation_edits
    )
    counts["purh.biblio.casse_auteur"] += _apply_text_edits(
        paragraph, find_bibliography_author_casing_edits
    )


def _apply_main_text(document: Any, counts: dict[str, int]) -> None:
    story = document.StoryRanges(WD_MAIN_TEXT_STORY)
    in_bibliography_section = False
    for paragraph_index, paragraph in enumerate(story.Paragraphs, start=1):
        for rule_id, finder in ORTHOTYPOGRAPHY_TEXT_RULES + BIBLIOGRAPHY_TEXT_RULES:
            try:
                counts[rule_id] += _apply_text_edits(paragraph, finder)
            except Exception as exc:
                raise RuntimeError(
                    f"{rule_id}, paragraphe principal {paragraph_index}"
                ) from exc
        counts["purh.siecles.style"] += _apply_century_styles(paragraph)
        counts["purh.numero.style"] += _apply_numero_styles(paragraph)
        counts["purh.folio.style"] += _apply_folio_styles(paragraph)
        counts["purh.recto_verso.style"] += _apply_recto_verso_styles(paragraph)
        counts["purh.ordinaux.style"] += _apply_ordinal_styles(paragraph)
        counts["purh.civilite.style"] += _apply_civility_styles(paragraph)
        counts["purh.tiret.incise.diagnostic"] += _apply_incise_diagnostics(paragraph)
        for rule_id, finder in ORTHOTYPOGRAPHY_DIAGNOSTIC_RULES:
            counts[rule_id] += _apply_diagnostics(paragraph, finder)

        if _is_heading_paragraph(paragraph):
            in_bibliography_section = bool(
                BIBLIOGRAPHY_SECTION_HEADING_RE.match(
                    _paragraph_text(paragraph).strip()
                )
            )
            _apply_frontmatter_diagnostic(paragraph, counts)
            _apply_allcaps_heading_diagnostic(paragraph, counts)
        elif in_bibliography_section:
            _apply_bibliography_entry(paragraph, counts)
        else:
            _apply_frontmatter_diagnostic(paragraph, counts)
    paragraph = None
    story = None


def _apply_note_call_diagnostics(document: Any, counts: dict[str, int]) -> None:
    for footnote in document.Footnotes:
        reference = footnote.Reference
        if reference.Start <= 0:
            reference = None
            continue
        preceding = reference.Duplicate
        preceding.SetRange(reference.Start - 1, reference.Start)
        previous_character = preceding.Text
        for rule_id in note_call_diagnostic_ids(previous_character):
            preceding.HighlightColorIndex = WD_TURQUOISE
            counts[rule_id] += 1
        preceding = None
        reference = None
    footnote = None


def _apply_footnotes(document: Any, counts: dict[str, int]) -> None:
    for footnote_index, footnote in enumerate(document.Footnotes, start=1):
        for paragraph_index, paragraph in enumerate(
            footnote.Range.Paragraphs,
            start=1,
        ):
            for rule_id, finder in (
                FOOTNOTE_QUOTE_TEXT_RULES + FOOTNOTE_RULES + BIBLIOGRAPHY_TEXT_RULES
            ):
                try:
                    counts[rule_id] += _apply_text_edits(paragraph, finder)
                except Exception as exc:
                    raise RuntimeError(
                        f"{rule_id}, note {footnote_index}, "
                        f"paragraphe {paragraph_index}"
                    ) from exc
            for rule_id, finder in FOOTNOTE_DIAGNOSTIC_RULES:
                counts[rule_id] += _apply_diagnostics(paragraph, finder)
            for rule_id, finder in ORTHOTYPOGRAPHY_DIAGNOSTIC_RULES:
                counts[rule_id] += _apply_diagnostics(paragraph, finder)
            counts["purh.siecles.style"] += _apply_century_styles(paragraph)
            counts["purh.numero.style"] += _apply_numero_styles(paragraph)
            counts["purh.folio.style"] += _apply_folio_styles(paragraph)
            counts["purh.recto_verso.style"] += _apply_recto_verso_styles(paragraph)
            counts["purh.ordinaux.style"] += _apply_ordinal_styles(paragraph)
            counts["purh.civilite.style"] += _apply_civility_styles(paragraph)
            counts["purh.note.italique_latin"] += _apply_footnote_latin_italic(
                paragraph
            )
        paragraph = None
        footnote = None
    _apply_note_call_diagnostics(document, counts)


def correct_word_copy(
    path: Path,
    rule_ids: tuple[str, ...],
) -> dict[str, int]:
    try:
        from win32com.client import DispatchEx
    except ImportError as exc:
        raise RuntimeError(
            "pywin32 est requis pour automatiser Microsoft Word."
        ) from exc

    counts = {rule_id: 0 for rule_id in rule_ids}
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
