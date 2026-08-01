from __future__ import annotations

from typing import Any

from purh_editorial.corrector.ai import LocatedAISuggestion
from purh_editorial.corrector.word_document import WD_DARK_YELLOW, _apply_ai_suggestion

WD_NO_HIGHLIGHT = 0


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


def test_apply_ai_suggestion_highlights_range_and_adds_comment_without_changing_text() -> None:
    paragraph_text = "Il s'avère avéré que ce point est lourd."
    suggestion = LocatedAISuggestion(
        rule_id="ia.style.lourdeur",
        start=0,
        end=len("Il s'avère avéré"),
        original_text="Il s'avère avéré",
        suggested_text="Il est avéré",
        explanation="Pléonasme : redondance entre « s'avérer » et « avéré ».",
    )

    word = _word_application()
    document = None
    try:
        document = word.Documents.Add()
        document.Content.Text = f"{paragraph_text}\r"
        paragraph = document.Paragraphs(1)

        assert document.Comments.Count == 0
        before_highlight = paragraph.Range.Duplicate
        before_highlight.SetRange(
            paragraph.Range.Start, paragraph.Range.Start + suggestion.end
        )
        assert before_highlight.HighlightColorIndex == WD_NO_HIGHLIGHT

        result = _apply_ai_suggestion(document, paragraph, suggestion)
        assert result is True

        # Le texte du paragraphe est strictement inchangé : aucune
        # transformation, seulement une annotation.
        text_after = paragraph.Range.Text
        while text_after.endswith(("\r", "\x07")):
            text_after = text_after[:-1]
        assert text_after == paragraph_text

        highlighted = paragraph.Range.Duplicate
        highlighted.SetRange(
            paragraph.Range.Start, paragraph.Range.Start + suggestion.end
        )
        assert highlighted.HighlightColorIndex == WD_DARK_YELLOW

        assert document.Comments.Count == 1
        comment = document.Comments(1)
        comment_text = comment.Range.Text
        assert "ia.style.lourdeur" in comment_text
        assert "Pléonasme" in comment_text
        assert "Il est avéré" in comment_text
    finally:
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None
