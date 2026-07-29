from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from purh_editorial.services.word_review_service import (
    WordReviewError,
    _create_word_application,
    _word_constants,
)


@dataclass(frozen=True, slots=True)
class WindowGeometry:
    left: int
    top: int
    width: int
    height: int


@dataclass(slots=True)
class WordWorkspaceState:
    original_path: Path
    review_path: Path
    original_read_only: bool
    review_read_only: bool
    original_on_left: bool
    synchronized_scrolling: bool
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WordWorkspaceSession:
    """COM proxies owned solely by the workspace helper process."""

    app: Any
    original_document: Any
    review_document: Any
    original_window: Any
    review_window: Any
    state: WordWorkspaceState

    def documents_are_open(self) -> bool:
        try:
            return bool(self.app.Documents.Count)
        except Exception:
            return False

    def close_owned_documents(self, *, save_review: bool = False) -> None:
        for document, save_changes in (
            (self.review_document, save_review),
            (self.original_document, False),
        ):
            if document is None:
                continue
            try:
                document.Close(SaveChanges=save_changes)
            except Exception:
                pass

    def quit_application(self) -> None:
        if self.app is None:
            return
        try:
            self.app.Quit()
        except Exception:
            pass


def _read_window_geometry(window: Any) -> WindowGeometry:
    return WindowGeometry(
        left=int(window.Left), top=int(window.Top), width=int(window.Width), height=int(window.Height)
    )


def _apply_window_geometry(window: Any, geometry: WindowGeometry) -> None:
    window.Left = geometry.left
    window.Top = geometry.top
    window.Width = geometry.width
    window.Height = geometry.height


def _try_set_property(target: Any, name: str, value: Any) -> bool:
    try:
        setattr(target, name, value)
        return True
    except Exception:
        return False


class WordWorkspaceService:
    """Open original and review DOCX files in one dedicated Word instance."""

    def open_workspace(self, *, original_path: Path, review_path: Path) -> WordWorkspaceSession:
        original = self._validate_path(original_path, "original")
        review = self._validate_path(review_path, "révision")
        if original == review:
            raise WordReviewError("L’original et la révision Word doivent être distincts.")
        if not os.access(review, os.W_OK):
            raise WordReviewError(f"Le document de révision n’est pas accessible en écriture : {review}")

        app = original_document = review_document = original_window = review_window = None
        try:
            app = _create_word_application()
            app.Visible = True
            # Side-by-side automation is more reliable in Word's MDI mode.
            # This affects only the dedicated instance created above.
            _try_set_property(app, "ShowWindowsInTaskbar", False)
            constants = _word_constants(app)
            original_document = app.Documents.Open(
                FileName=str(original), ReadOnly=True, AddToRecentFiles=False, Visible=True
            )
            review_document = app.Documents.Open(
                FileName=str(review), ReadOnly=False, AddToRecentFiles=False, Visible=True
            )
            if not bool(original_document.ReadOnly):
                raise WordReviewError("Le document original n’a pas pu être ouvert en lecture seule.")
            if bool(review_document.ReadOnly):
                raise WordReviewError(f"Le document de révision n’est pas accessible en écriture : {review}")

            original_window = original_document.Windows(1)
            review_window = review_document.Windows(1)
            if original_window is None or review_window is None:
                raise WordReviewError("Les fenêtres Word du workspace sont indisponibles.")
            self._set_normal_window_state(original_window, review_window, constants)
            review_document.Activate()
            try:
                review_window.Activate()
            except Exception:
                pass
            # Word may expose a Window proxy before its interactive view has
            # finished initializing; give the dedicated UI instance one turn.
            time.sleep(0.25)
            warnings: list[str] = []
            if not self._compare_side_by_side(app, review_document, original_document):
                warnings.append("Word a refusé le mode côte à côte natif ; géométrie appliquée manuellement.")
            try:
                app.Windows.ResetPositionsSideBySide()
            except Exception:
                warnings.append("Word n’a pas réinitialisé les positions côte à côte.")
            try:
                app.Windows.SyncScrollingSideBySide = True
            except Exception:
                warnings.append("Word a refusé l’activation du défilement synchronisé.")
            original_on_left = self._ensure_original_on_left(original_window, review_window, warnings)
            synchronized = self._confirm_sync_scrolling(app, warnings)
            self._configure_review_view(review_window, constants)
            self._configure_original_view(original_window)
            review_document.Activate()
            state = WordWorkspaceState(
                original_path=original,
                review_path=review,
                original_read_only=bool(original_document.ReadOnly),
                review_read_only=bool(review_document.ReadOnly),
                original_on_left=original_on_left,
                synchronized_scrolling=synchronized,
                warnings=warnings,
            )
            return WordWorkspaceSession(
                app=app,
                original_document=original_document,
                review_document=review_document,
                original_window=original_window,
                review_window=review_window,
                state=state,
            )
        except WordReviewError:
            self._cleanup_failed_initialization(review_document, original_document, app)
            raise
        except Exception as exc:
            self._cleanup_failed_initialization(review_document, original_document, app)
            raise WordReviewError(f"Ouverture de l’espace Word impossible : {exc}") from exc

    @staticmethod
    def _validate_path(path: Path, kind: str) -> Path:
        candidate = Path(path).expanduser().resolve()
        label = "Document original" if kind == "original" else "Document de révision"
        if candidate.suffix.lower() != ".docx" or not candidate.is_file():
            raise WordReviewError(f"{label} DOCX introuvable : {candidate}")
        return candidate

    @staticmethod
    def _cleanup_failed_initialization(review_document: Any, original_document: Any, app: Any) -> None:
        for document in (review_document, original_document):
            if document is not None:
                try:
                    document.Close(SaveChanges=False)
                except Exception:
                    pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass

    @staticmethod
    def _set_normal_window_state(original_window: Any, review_window: Any, constants: Any) -> None:
        state = getattr(constants, "wdWindowStateNormal", None)
        if state is None:
            return
        _try_set_property(original_window, "WindowState", state)
        _try_set_property(review_window, "WindowState", state)

    @staticmethod
    def _compare_side_by_side(app: Any, review_document: Any, original_document: Any) -> bool:
        """Use the Word native API, tolerating collection differences between versions."""
        try:
            review_document.Windows.CompareSideBySideWith(Document=original_document)
            return True
        except Exception:
            pass
        try:
            # Word declares this argument as a by-reference Object.  The
            # generated pywin32 wrapper on some Office builds requires an
            # explicit VARIANT rather than a bare Document proxy.
            import pythoncom
            from win32com.client import VARIANT

            for document in (original_document, original_document._oleobj_):
                argument = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_DISPATCH, document)
                try:
                    review_document.Windows.CompareSideBySideWith(argument)
                    return True
                except Exception:
                    continue
        except Exception:
            return False

    @staticmethod
    def _ensure_original_on_left(original_window: Any, review_window: Any, warnings: list[str]) -> bool:
        try:
            original = _read_window_geometry(original_window)
            review = _read_window_geometry(review_window)
            if original.left >= review.left:
                _apply_window_geometry(original_window, review)
                _apply_window_geometry(review_window, original)
                original = _read_window_geometry(original_window)
                review = _read_window_geometry(review_window)
            if original.left < review.left:
                return True
            warnings.append("Word n’a pas confirmé le placement original à gauche / révision à droite.")
        except Exception:
            warnings.append("La géométrie des fenêtres Word n’a pas pu être ajustée.")
        return False

    @staticmethod
    def _confirm_sync_scrolling(app: Any, warnings: list[str]) -> bool:
        try:
            if bool(app.Windows.SyncScrollingSideBySide):
                return True
        except Exception:
            pass
        warnings.append("Word n’a pas confirmé le défilement synchronisé.")
        return False

    @staticmethod
    def _configure_review_view(review_window: Any, constants: Any) -> None:
        view = review_window.View
        for name, value in (
            ("ShowRevisionsAndComments", True),
            ("ShowComments", True),
            ("ShowInsertionsAndDeletions", True),
            ("ShowFormatChanges", False),
        ):
            _try_set_property(view, name, value)
        revisions_view = getattr(constants, "wdRevisionsViewFinal", None)
        if revisions_view is not None:
            _try_set_property(view, "RevisionsView", revisions_view)
        inline = getattr(constants, "wdInLineRevisions", None)
        if inline is not None:
            _try_set_property(view, "RevisionsMode", inline)

    @staticmethod
    def _configure_original_view(original_window: Any) -> None:
        view = original_window.View
        _try_set_property(view, "ShowComments", False)
        _try_set_property(view, "ShowRevisionsAndComments", False)
