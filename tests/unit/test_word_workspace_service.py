from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from purh_editorial.services import word_workspace_service as module
from purh_editorial.services.word_review_service import WordReviewError
from purh_editorial.services.word_workspace_service import WordWorkspaceService


class _Constants:
    wdWindowStateNormal = "normal"
    wdRevisionsViewFinal = "final"
    wdInLineRevisions = "inline"


class _View:
    pass


class _Window:
    def __init__(self, left: int) -> None:
        self.Left, self.Top, self.Width, self.Height = left, 10, 400, 600
        self.View = _View()
        self.WindowState = None


class _Windows:
    def __init__(self) -> None:
        self.SyncScrollingSideBySide = False
        self.reset_calls = 0

    def ResetPositionsSideBySide(self) -> None:
        self.reset_calls += 1


class _DocumentWindows:
    def __init__(self, window: _Window) -> None:
        self.window = window
        self.compared_with = None

    def __call__(self, _: int) -> _Window:
        return self.window

    def CompareSideBySideWith(self, other=None, **kwargs) -> None:
        self.compared_with = kwargs.get("Document", other)


class _Document:
    def __init__(self, *, read_only: bool, left: int) -> None:
        self.ReadOnly = read_only
        self.window = _Window(left)
        self.Windows = _DocumentWindows(self.window)
        self.activated = 0
        self.closed: list[bool] = []

    def Activate(self) -> None:
        self.activated += 1

    def Close(self, *, SaveChanges: bool) -> None:
        self.closed.append(SaveChanges)


class _Documents:
    def __init__(self, original: _Document, review: _Document) -> None:
        self.items = [original, review]
        self.open_calls: list[dict] = []
        self.Count = 2

    def Open(self, **kwargs):
        self.open_calls.append(kwargs)
        return self.items[len(self.open_calls) - 1]


class _App:
    def __init__(self, original: _Document, review: _Document) -> None:
        self.Documents = _Documents(original, review)
        self.Windows = _Windows()
        self.Visible = False
        self.quit_calls = 0

    def Quit(self) -> None:
        self.quit_calls += 1


class WordWorkspaceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.original = self.root / "original.docx"
        self.review = self.root / "review.docx"
        self.original.write_bytes(b"original")
        self.review.write_bytes(b"review")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _open(self, *, original_left: int = 0, review_left: int = 500, review_read_only: bool = False):
        original = _Document(read_only=True, left=original_left)
        review = _Document(read_only=review_read_only, left=review_left)
        app = _App(original, review)
        with mock.patch.object(module, "_create_word_application", return_value=app), mock.patch.object(
            module, "_word_constants", return_value=_Constants
        ):
            session = WordWorkspaceService().open_workspace(original_path=self.original, review_path=self.review)
        return session, app, original, review

    def test_validates_paths_and_distinctness(self) -> None:
        self.original.unlink()
        with self.assertRaisesRegex(WordReviewError, "Document original DOCX introuvable"):
            WordWorkspaceService().open_workspace(original_path=self.original, review_path=self.review)
        self.original.write_bytes(b"original")
        with self.assertRaisesRegex(WordReviewError, "doivent être distincts"):
            WordWorkspaceService().open_workspace(original_path=self.original, review_path=self.original)
        text = self.root / "review.txt"; text.write_text("x")
        with self.assertRaisesRegex(WordReviewError, "Document de révision DOCX introuvable"):
            WordWorkspaceService().open_workspace(original_path=self.original, review_path=text)

    def test_opens_isolated_documents_with_expected_modes(self) -> None:
        session, app, original, review = self._open()
        calls = app.Documents.open_calls
        self.assertEqual(calls[0]["ReadOnly"], True)
        self.assertEqual(calls[1]["ReadOnly"], False)
        self.assertFalse(calls[0]["AddToRecentFiles"])
        self.assertTrue(calls[1]["Visible"])
        self.assertIs(session.original_document, original)
        self.assertIs(session.review_document, review)
        self.assertEqual(review.activated, 2)
        self.assertTrue(session.state.synchronized_scrolling)
        self.assertTrue(session.state.original_on_left)
        self.assertIs(app.Documents.items[1].Windows.compared_with, original)
        self.assertEqual(app.Windows.reset_calls, 1)

    def test_inverted_windows_exchange_complete_geometry(self) -> None:
        session, _, original, review = self._open(original_left=500, review_left=0)
        self.assertTrue(session.state.original_on_left)
        self.assertLess(original.window.Left, review.window.Left)
        self.assertEqual((original.window.Top, original.window.Width, original.window.Height), (10, 400, 600))
        self.assertEqual((review.window.Top, review.window.Width, review.window.Height), (10, 400, 600))

    def test_read_only_review_fails_and_cleans_only_owned_objects(self) -> None:
        original = _Document(read_only=True, left=0)
        review = _Document(read_only=True, left=500)
        app = _App(original, review)
        with mock.patch.object(module, "_create_word_application", return_value=app), mock.patch.object(
            module, "_word_constants", return_value=_Constants
        ), self.assertRaisesRegex(WordReviewError, "accessible en écriture"):
            WordWorkspaceService().open_workspace(original_path=self.original, review_path=self.review)
        self.assertEqual(review.closed, [False])
        self.assertEqual(original.closed, [False])
        self.assertEqual(app.quit_calls, 1)

    def test_geometry_failure_keeps_workspace_open_with_warning(self) -> None:
        session, app, _, _ = self._open(original_left=500, review_left=0)
        # The baseline fake supports geometry; exercise the warning path directly.
        warnings: list[str] = []
        failing = mock.Mock()
        type(failing).Left = mock.PropertyMock(side_effect=RuntimeError("locked"))
        self.assertFalse(WordWorkspaceService._ensure_original_on_left(failing, session.review_window, warnings))
        self.assertTrue(warnings)
        self.assertEqual(app.quit_calls, 0)


if __name__ == "__main__":
    unittest.main()
