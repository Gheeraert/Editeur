from __future__ import annotations

from pathlib import Path
from typing import Any

from purh_editorial.services.word_review_service import WordReviewError, _create_word_application, _word_constants


class WordWorkspaceService:
    """Open an isolated, visible Word review workspace without owning its later edits."""

    def open_workspace(self, *, original_path: Path, review_path: Path) -> Any:
        original, review = (Path(original_path).resolve(), Path(review_path).resolve())
        for label, path in (("original", original), ("révision", review)):
            if path.suffix.lower() != ".docx" or not path.is_file():
                raise WordReviewError(f"Document {label} DOCX introuvable : {path}")
        if original == review:
            raise WordReviewError("L'original et la révision Word doivent être distincts.")
        app = _create_word_application()
        try:
            app.Visible = True
            original_doc = app.Documents.Open(FileName=str(original), ReadOnly=True, AddToRecentFiles=False, Visible=True)
            review_doc = app.Documents.Open(FileName=str(review), ReadOnly=False, AddToRecentFiles=False, Visible=True)
            review_doc.Activate()
            review_doc.Windows.CompareSideBySideWith(original_doc)
            app.Windows.ResetPositionsSideBySide()
            app.Windows.SyncScrollingSideBySide = True
            self._configure_review_view(review_doc, _word_constants(app))
            self._ensure_review_on_right(original_doc, review_doc)
            review_doc.Activate()
            return app
        except Exception as exc:
            try: app.Quit()
            except Exception: pass
            if isinstance(exc, WordReviewError): raise
            raise WordReviewError(f"Ouverture de l'espace Word impossible : {exc}") from exc

    @staticmethod
    def _ensure_review_on_right(original_doc: Any, review_doc: Any) -> None:
        left, right = original_doc.Windows(1), review_doc.Windows(1)
        if left.Left > right.Left:
            left.Left, right.Left = right.Left, left.Left

    @staticmethod
    def _configure_review_view(review_doc: Any, constants: Any) -> None:
        view = review_doc.Windows(1).View
        for name, value in (("ShowRevisionsAndComments", True), ("ShowComments", True),
                            ("ShowInsertionsAndDeletions", True), ("ShowFormatChanges", False)):
            try: setattr(view, name, value)
            except Exception: pass
