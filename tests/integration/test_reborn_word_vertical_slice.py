from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from purh_editorial.corrector import correct_docx

WD_COLLAPSE_END = 0
WD_FORMAT_DOCUMENT_DEFAULT = 16
WD_YELLOW = 7


def _word_application() -> Any:
    try:
        from win32com.client import DispatchEx
    except ImportError as exc:
        raise AssertionError("pywin32 n'est pas importable.") from exc
    try:
        word = DispatchEx("Word.Application")
    except Exception as exc:
        raise AssertionError(
            "Microsoft Word ne peut pas être lancé pour le test d'intégration."
        ) from exc
    word.Visible = False
    word.DisplayAlerts = 0
    return word


def _create_source(path: Path) -> None:
    word = _word_application()
    document = None
    second_range = None
    anchor = None
    try:
        document = word.Documents.Add()
        first = "Une phrase... Au XVIème siècle, la vie continue."
        second = "Élément préservé"
        document.Content.Text = f"{first}\r{second}"

        second_range = document.Paragraphs(2).Range
        second_range.Font.Bold = True

        anchor = document.Paragraphs(1).Range.Duplicate
        anchor.Collapse(WD_COLLAPSE_END)
        anchor.MoveEnd(Unit=1, Count=-1)
        document.Footnotes.Add(Range=anchor, Text="Voir op. cit.")
        document.SaveAs2(
            FileName=str(path),
            FileFormat=WD_FORMAT_DOCUMENT_DEFAULT,
            AddToRecentFiles=False,
        )
    finally:
        anchor = None
        second_range = None
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def _clean_main_text(text: str) -> str:
    return text.replace("\x02", "").replace("\r", "\n").rstrip()


def _assert_corrected_document(path: Path) -> None:
    word = _word_application()
    document = None
    first_paragraph = None
    ellipsis = None
    roman = None
    suffix = None
    century = None
    note_range = None
    highlighted_note = None
    second_paragraph = None
    try:
        document = word.Documents.Open(
            FileName=str(path),
            ReadOnly=True,
            AddToRecentFiles=False,
            Visible=False,
        )
        main_text = _clean_main_text(document.StoryRanges(1).Text)
        assert "Une phrase… Au xvie siècle, la vie continue." in main_text

        first_paragraph = document.Paragraphs(1)
        paragraph_text = first_paragraph.Range.Text

        ellipsis_index = paragraph_text.index("…")
        ellipsis = first_paragraph.Range.Duplicate
        ellipsis.SetRange(
            first_paragraph.Range.Start + ellipsis_index,
            first_paragraph.Range.Start + ellipsis_index + 1,
        )
        assert ellipsis.HighlightColorIndex == WD_YELLOW

        century_index = paragraph_text.index("xvie")
        roman = first_paragraph.Range.Duplicate
        roman.SetRange(
            first_paragraph.Range.Start + century_index,
            first_paragraph.Range.Start + century_index + 3,
        )
        suffix = first_paragraph.Range.Duplicate
        suffix.SetRange(
            first_paragraph.Range.Start + century_index + 3,
            first_paragraph.Range.Start + century_index + 4,
        )
        century = first_paragraph.Range.Duplicate
        century.SetRange(
            first_paragraph.Range.Start + century_index,
            first_paragraph.Range.Start + century_index + 4,
        )
        assert roman.Font.SmallCaps == -1
        assert roman.Font.Superscript == 0
        assert suffix.Font.SmallCaps == 0
        assert suffix.Font.Superscript == -1
        assert century.HighlightColorIndex == WD_YELLOW
        assert "vie continue" in paragraph_text

        note_range = document.Footnotes(1).Range
        note_text = note_range.Text
        abbreviation = f"op.\u202fcit."
        assert abbreviation in note_text
        note_index = note_text.index(abbreviation)
        highlighted_note = note_range.Duplicate
        highlighted_note.SetRange(
            note_range.Start + note_index,
            note_range.Start + note_index + len(abbreviation),
        )
        assert highlighted_note.HighlightColorIndex == WD_YELLOW

        second_paragraph = document.Paragraphs(2).Range
        assert second_paragraph.Font.Bold == -1
    finally:
        second_paragraph = None
        highlighted_note = None
        note_range = None
        century = None
        suffix = None
        roman = None
        ellipsis = None
        first_paragraph = None
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def test_reborn_word_vertical_slice(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    corrected = tmp_path / "corrected.docx"
    corrected_twice = tmp_path / "corrected_twice.docx"

    _create_source(source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()

    first_counts = correct_docx(source, corrected)
    assert first_counts == {
        "purh.points_suspension": 1,
        "purh.siecles": 1,
        "R-SO-001": 1,
        "purh.note.espace_op_cit": 1,
    }
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    _assert_corrected_document(corrected)

    second_counts = correct_docx(corrected, corrected_twice)
    assert second_counts == {
        "purh.points_suspension": 0,
        "purh.siecles": 0,
        "R-SO-001": 0,
        "purh.note.espace_op_cit": 0,
    }
    _assert_corrected_document(corrected_twice)
