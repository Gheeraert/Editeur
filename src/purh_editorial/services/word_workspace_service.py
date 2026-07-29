from __future__ import annotations

import os
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


@dataclass(frozen=True, slots=True)
class SideBySideAttempt:
    strategy: str
    succeeded: bool
    return_value: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    hresult: int | None = None


@dataclass(slots=True)
class SideBySideResult:
    established: bool
    synchronized: bool
    strategy: str | None
    attempts: list[SideBySideAttempt]


@dataclass(slots=True)
class WordWorkspaceState:
    original_path: Path
    review_path: Path
    original_read_only: bool
    review_read_only: bool
    original_on_left: bool
    synchronized_scrolling: bool
    side_by_side_established: bool
    side_by_side_strategy: str | None
    side_by_side_attempts: list[SideBySideAttempt]
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


def _describe_com_error(strategy: str, exc: Exception) -> SideBySideAttempt:
    hresult = getattr(exc, "hresult", None)
    excepinfo = getattr(exc, "excepinfo", None)
    detail = ""
    if isinstance(excepinfo, tuple) and len(excepinfo) > 2 and excepinfo[2]:
        detail = str(excepinfo[2])
    message = detail or str(exc)
    return SideBySideAttempt(
        strategy=strategy,
        succeeded=False,
        error_type=type(exc).__name__,
        error_message=message,
        hresult=hresult if isinstance(hresult, int) else None,
    )


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
            warnings: list[str] = []
            side_by_side = self._establish_side_by_side(
                app=app,
                review_document=review_document,
                original_document=original_document,
                review_window=review_window,
                original_window=original_window,
            )
            if not side_by_side.established:
                warnings.append("Word a refusé le mode côte à côte natif ; géométrie appliquée manuellement.")
            try:
                app.Windows.ResetPositionsSideBySide()
            except Exception:
                warnings.append("Word n’a pas réinitialisé les positions côte à côte.")
            original_on_left = self._ensure_original_on_left(original_window, review_window, warnings)
            synchronized = self._enable_and_confirm_sync_scrolling(app=app, attempts=side_by_side.attempts)
            side_by_side.synchronized = synchronized
            if not synchronized:
                warnings.append("Les documents sont ouverts côte à côte, mais Word n’a pas activé le défilement synchronisé.")
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
                side_by_side_established=side_by_side.established,
                side_by_side_strategy=side_by_side.strategy,
                side_by_side_attempts=side_by_side.attempts,
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

    def _establish_side_by_side(
        self, *, app: Any, review_document: Any, original_document: Any,
        review_window: Any, original_window: Any,
    ) -> SideBySideResult:
        attempts: list[SideBySideAttempt] = []

        def invoke(strategy: str, callback) -> bool:
            try:
                review_document.Activate()
                try:
                    review_window.Activate()
                except Exception:
                    pass
                returned = callback()
                success = returned is not False
                attempts.append(SideBySideAttempt(strategy, success, repr(returned)))
                return success and self._confirm_side_by_side(app, original_window, review_window)
            except Exception as exc:
                attempts.append(_describe_com_error(strategy, exc))
                return False

        if invoke("positional_simple", lambda: review_document.Windows.CompareSideBySideWith(original_document)):
            return SideBySideResult(True, False, "positional_simple", attempts)
        if invoke("named_argument", lambda: review_document.Windows.CompareSideBySideWith(Document=original_document)):
            return SideBySideResult(True, False, "named_argument", attempts)
        try:
            from win32com.client.dynamic import Dispatch
            dynamic_windows = Dispatch(review_document.Windows._oleobj_)
            if invoke("dynamic_dispatch", lambda: dynamic_windows.CompareSideBySideWith(original_document)):
                return SideBySideResult(True, False, "dynamic_dispatch", attempts)
        except Exception as exc:
            attempts.append(_describe_com_error("dynamic_dispatch", exc))
        try:
            enabled = bool(app.CommandBars.GetEnabledMso("ViewSideBySide"))
            if not enabled:
                attempts.append(SideBySideAttempt("execute_mso", False, error_message="ViewSideBySide indisponible"))
            else:
                review_document.Activate()
                returned = app.CommandBars.ExecuteMso("ViewSideBySide")
                confirmed = self._confirm_side_by_side(app, original_window, review_window)
                attempts.append(SideBySideAttempt("execute_mso", confirmed, repr(returned)))
                if confirmed:
                    return SideBySideResult(True, False, "execute_mso", attempts)
        except Exception as exc:
            attempts.append(_describe_com_error("execute_mso", exc))
        return SideBySideResult(False, False, None, attempts)

    @staticmethod
    def _confirm_side_by_side(app: Any, original_window: Any, review_window: Any) -> bool:
        try:
            return original_window is not None and review_window is not None and bool(app.Windows.SyncScrollingSideBySide)
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
    def _enable_and_confirm_sync_scrolling(*, app: Any, attempts: list[SideBySideAttempt]) -> bool:
        try:
            app.Windows.SyncScrollingSideBySide = True
            if bool(app.Windows.SyncScrollingSideBySide):
                attempts.append(SideBySideAttempt("sync_property", True, "True"))
                return True
            attempts.append(SideBySideAttempt("sync_property", False, "False"))
        except Exception as exc:
            attempts.append(_describe_com_error("sync_property", exc))
        try:
            bars = app.CommandBars
            if bool(bars.GetEnabledMso("SynchronousScrolling")):
                if not bool(bars.GetPressedMso("SynchronousScrolling")):
                    bars.ExecuteMso("SynchronousScrolling")
                pressed = bool(bars.GetPressedMso("SynchronousScrolling"))
                attempts.append(SideBySideAttempt("sync_command", pressed, str(pressed)))
                return pressed
        except Exception as exc:
            attempts.append(_describe_com_error("sync_command", exc))
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
