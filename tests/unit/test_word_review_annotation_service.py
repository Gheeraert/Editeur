from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from purh_editorial.model import Diagnostic, Document, Evidence, Paragraph, ProcessingReport, Suggestion
from purh_editorial.services.word_review_annotation_service import (
    WordReviewAnnotationService,
    build_word_review_comments,
)
from purh_editorial.services.word_review_service import WordReviewError
import purh_editorial.services.word_review_annotation_service as annotation_module


class WordReviewCommentPlanTests(unittest.TestCase):
    def _document(self) -> Document:
        return Document(document_id="d", source_path="source.docx", source_format="docx", blocks=[Paragraph(block_id="p1", text="Texte cible")])

    def _report(self) -> ProcessingReport:
        return ProcessingReport(report_id="r", document_id="d")

    def test_suggestion_uses_before_anchor_and_prudent_text(self) -> None:
        report = self._report()
        report.suggestions.append(Suggestion("s1", "ai", "p1", "À revoir", "Justification", "proposition", 0.7, attributes={"before": "Texte"}))
        comment = build_word_review_comments(self._document(), report)[0]
        self.assertEqual(comment.target_ref, "p1")
        self.assertEqual(comment.anchor_text, "Texte")
        self.assertIn("Suggestion à valider", comment.comment_text)
        self.assertIn("Confiance", comment.comment_text)

    def test_open_diagnostic_is_kept_but_auto_applied_and_unanchored_are_ignored(self) -> None:
        report = self._report()
        report.diagnostics.extend([
            Diagnostic("d1", "structure", "warning", "candidate", "Vérifier", "p1", Evidence(excerpt="Texte")),
            Diagnostic("d2", "typo", "warning", "candidate", "Auto", "p1", Evidence(excerpt="Texte"), attributes={"auto_applied": True}),
            Diagnostic("d3", "tei", "error", "technical", "Sans cible", "", Evidence()),
        ])
        comments = build_word_review_comments(self._document(), report)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].comment_id, "d1")
        self.assertIn("Point à vérifier", comments[0].comment_text)

    def test_closed_diagnostic_and_suggestion_without_anchor_are_ignored(self) -> None:
        report = self._report()
        report.suggestions.append(Suggestion("s1", "ai", "p1", "", "raison", "", 0.5))
        report.diagnostics.append(
            Diagnostic("d1", "typo", "warning", "candidate", "Fermé", "p1", Evidence(excerpt="Texte"), status="closed")
        )
        self.assertEqual(build_word_review_comments(self._document(), report), [])


class _FakeComments:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[object, str]] = []

    def Add(self, *, Range: object, Text: str) -> object:
        if self.error is not None:
            raise self.error
        self.calls.append((Range, Text))
        return type("Comment", (), {})()


class _FakeDocument:
    def __init__(self, *, comments_error: Exception | None = None, save_error: Exception | None = None) -> None:
        self.Comments = _FakeComments(error=comments_error)
        self.save_error = save_error
        self.range_calls: list[tuple[int, int]] = []
        self.closed = False

    def Range(self, *, Start: int, End: int) -> object:
        self.range_calls.append((Start, End))
        return (Start, End)

    def Save(self) -> None:
        if self.save_error is not None:
            raise self.save_error

    def Close(self, *, SaveChanges: bool) -> None:
        self.closed = True


class _FakeDocuments:
    def __init__(self, document: _FakeDocument) -> None:
        self.document = document

    def Open(self, **_: object) -> _FakeDocument:
        return self.document


class _FakeApplication:
    def __init__(self, document: _FakeDocument) -> None:
        self.Documents = _FakeDocuments(document)
        self.Visible = None
        self.DisplayAlerts = None
        self.quit_called = False

    def Quit(self) -> None:
        self.quit_called = True


class WordReviewAnnotationServiceTests(unittest.TestCase):
    def _document_and_report(self) -> tuple[Document, ProcessingReport]:
        document = Document(
            document_id="d",
            source_path="source.docx",
            source_format="docx",
            blocks=[Paragraph(block_id="p1", text="Texte cible")],
        )
        report = ProcessingReport(report_id="r", document_id="d")
        report.suggestions.append(
            Suggestion("s1", "ai", "p1", "À revoir", "Justification", "Proposition", 0.7, attributes={"before": "Texte"})
        )
        return document, report

    def _review_path(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "revision.docx"
        path.write_bytes(b"revision originale")
        return directory, path

    @staticmethod
    def _digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _patch_successful_validation(self) -> mock._patch_dict:
        return mock.patch.multiple(
            annotation_module,
            document_contains_highlights=mock.Mock(return_value=False),
            document_contains_tracked_changes=mock.Mock(return_value=True),
            document_contains_word_comments=mock.Mock(return_value=True),
        )

    def test_no_comment_does_not_open_word_or_modify_file(self) -> None:
        directory, review_path = self._review_path()
        self.addCleanup(directory.cleanup)
        document = Document(document_id="d", source_path="source.docx", source_format="docx")
        report = ProcessingReport(report_id="r", document_id="d")
        before = self._digest(review_path)
        with mock.patch.object(annotation_module, "_create_word_application") as create_app:
            result = WordReviewAnnotationService().annotate_review_document(
                review_path=review_path, document=document, report=report
            )
        create_app.assert_not_called()
        self.assertEqual((result.comments_requested, result.comments_added, result.comments_skipped), (0, 0, 0))
        self.assertEqual(self._digest(review_path), before)

    def test_unique_anchor_adds_comment_and_replaces_after_save(self) -> None:
        directory, review_path = self._review_path()
        self.addCleanup(directory.cleanup)
        document, report = self._document_and_report()
        fake_document = _FakeDocument()
        fake_app = _FakeApplication(fake_document)
        with self._patch_successful_validation(), mock.patch.object(annotation_module, "_create_word_application", return_value=fake_app), mock.patch.object(
            WordReviewAnnotationService, "_find_exact_range_bounds", return_value=[(10, 15)]
        ):
            result = WordReviewAnnotationService().annotate_review_document(
                review_path=review_path, document=document, report=report
            )
        self.assertEqual(fake_document.range_calls, [(10, 15)])
        self.assertEqual(len(fake_document.Comments.calls), 1)
        self.assertEqual(fake_document.Comments.calls[0][1], build_word_review_comments(document, report)[0].comment_text)
        self.assertEqual((result.comments_added, result.comments_skipped), (1, 0))
        self.assertTrue(fake_document.closed)
        self.assertTrue(fake_app.quit_called)

    def test_missing_and_ambiguous_anchors_are_refused(self) -> None:
        for bounds, expected_missing, expected_ambiguous in (([], 1, 0), ([(10, 15), (40, 45)], 0, 1)):
            with self.subTest(bounds=bounds):
                directory, review_path = self._review_path()
                self.addCleanup(directory.cleanup)
                document, report = self._document_and_report()
                fake_document = _FakeDocument()
                with self._patch_successful_validation(), mock.patch.object(annotation_module, "_create_word_application", return_value=_FakeApplication(fake_document)), mock.patch.object(
                    WordReviewAnnotationService, "_find_exact_range_bounds", return_value=bounds
                ):
                    result = WordReviewAnnotationService().annotate_review_document(
                        review_path=review_path, document=document, report=report
                    )
                self.assertEqual(fake_document.Comments.calls, [])
                self.assertEqual(result.comments_skipped, 1)
                self.assertEqual(result.missing_anchors, expected_missing)
                self.assertEqual(result.ambiguous_anchors, expected_ambiguous)

    def test_comment_and_save_errors_preserve_original_review_and_cleanup(self) -> None:
        for failure in ("comment", "save"):
            with self.subTest(failure=failure):
                directory, review_path = self._review_path()
                self.addCleanup(directory.cleanup)
                document, report = self._document_and_report()
                error = RuntimeError(f"{failure} error")
                fake_document = _FakeDocument(
                    comments_error=error if failure == "comment" else None,
                    save_error=error if failure == "save" else None,
                )
                fake_app = _FakeApplication(fake_document)
                before = self._digest(review_path)
                with self._patch_successful_validation(), mock.patch.object(annotation_module, "_create_word_application", return_value=fake_app), mock.patch.object(
                    WordReviewAnnotationService, "_find_exact_range_bounds", return_value=[(10, 15)]
                ), self.assertRaises(WordReviewError) as raised:
                    WordReviewAnnotationService().annotate_review_document(
                        review_path=review_path, document=document, report=report
                    )
                self.assertIs(raised.exception.__cause__, error)
                self.assertEqual(self._digest(review_path), before)
                self.assertFalse(list(review_path.parent.glob(".revision.*.comments.tmp.docx")))
                self.assertTrue(fake_document.closed)
                self.assertTrue(fake_app.quit_called)

    def test_failed_validation_preserves_original_review(self) -> None:
        directory, review_path = self._review_path()
        self.addCleanup(directory.cleanup)
        document, report = self._document_and_report()
        fake_document = _FakeDocument()
        fake_app = _FakeApplication(fake_document)
        before = self._digest(review_path)
        with mock.patch.object(annotation_module, "document_contains_highlights", return_value=False), mock.patch.object(
            annotation_module, "document_contains_tracked_changes", return_value=False
        ), mock.patch.object(annotation_module, "document_contains_word_comments", return_value=False), mock.patch.object(
            annotation_module, "_create_word_application", return_value=fake_app
        ), mock.patch.object(WordReviewAnnotationService, "_find_exact_range_bounds", return_value=[(10, 15)]), self.assertRaises(WordReviewError):
            WordReviewAnnotationService().annotate_review_document(review_path=review_path, document=document, report=report)
        self.assertEqual(self._digest(review_path), before)
        self.assertFalse(list(review_path.parent.glob(".revision.*.comments.tmp.docx")))
        self.assertTrue(fake_document.closed)
        self.assertTrue(fake_app.quit_called)

    def test_missing_comment_ooxml_after_add_preserves_original_review(self) -> None:
        directory, review_path = self._review_path()
        self.addCleanup(directory.cleanup)
        document, report = self._document_and_report()
        fake_document = _FakeDocument()
        fake_app = _FakeApplication(fake_document)
        before = self._digest(review_path)
        with mock.patch.object(annotation_module, "document_contains_highlights", return_value=False), mock.patch.object(
            annotation_module, "document_contains_tracked_changes", return_value=True
        ), mock.patch.object(annotation_module, "document_contains_word_comments", return_value=False), mock.patch.object(
            annotation_module, "_create_word_application", return_value=fake_app
        ), mock.patch.object(WordReviewAnnotationService, "_find_exact_range_bounds", return_value=[(10, 15)]), self.assertRaises(WordReviewError):
            WordReviewAnnotationService().annotate_review_document(review_path=review_path, document=document, report=report)
        self.assertEqual(self._digest(review_path), before)
        self.assertFalse(list(review_path.parent.glob(".revision.*.comments.tmp.docx")))
        self.assertTrue(fake_document.closed)
        self.assertTrue(fake_app.quit_called)

    def test_temp_creation_and_copy_errors_are_wrapped_without_opening_word(self) -> None:
        for patched, side_effect in (("mkstemp", OSError("temp error")), ("copy2", OSError("copy error"))):
            with self.subTest(patched=patched):
                directory, review_path = self._review_path()
                self.addCleanup(directory.cleanup)
                document, report = self._document_and_report()
                before = self._digest(review_path)
                target = f"tempfile.{patched}" if patched == "mkstemp" else "shutil.copy2"
                with mock.patch.object(annotation_module, "document_contains_highlights", return_value=False), mock.patch(
                    f"purh_editorial.services.word_review_annotation_service.{target}", side_effect=side_effect
                ), mock.patch.object(annotation_module, "_create_word_application") as create_app, self.assertRaises(WordReviewError) as raised:
                    WordReviewAnnotationService().annotate_review_document(
                        review_path=review_path, document=document, report=report
                    )
                self.assertIs(raised.exception.__cause__, side_effect)
                create_app.assert_not_called()
                self.assertEqual(self._digest(review_path), before)
                self.assertFalse(list(review_path.parent.glob(".revision.*.comments.tmp.docx")))


if __name__ == "__main__":
    unittest.main()
