from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.services import word_review_service as service_module
from purh_editorial.services.word_review_service import (
    WordReviewError,
    WordReviewService,
    document_contains_tracked_changes,
)


class FakeConstants:
    wdCompareDestinationNew = "destination-new"
    wdGranularityCharLevel = "char-level"
    wdFormatXMLDocument = "docx-format"


def write_docx(path: Path, body_xml: str) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", body_xml)


def write_plain_docx(path: Path) -> None:
    write_docx(
        path,
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>Texte</w:t></w:r></w:p></w:body></w:document>",
    )


def write_revision_docx(path: Path) -> None:
    write_docx(
        path,
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:ins><w:r><w:t>Ajout</w:t></w:r></w:ins></w:p></w:body></w:document>",
    )


class FakeDocument:
    def __init__(self, name: str) -> None:
        self.name = name
        self.close_calls: list[dict[str, object]] = []

    def Close(self, **kwargs: object) -> None:
        self.close_calls.append(kwargs)


class FakeComparisonDocument(FakeDocument):
    def __init__(self, name: str = "comparison", *, fail_save: bool = False) -> None:
        super().__init__(name)
        self.fail_save = fail_save
        self.saved_paths: list[Path] = []
        self.save_kwargs: list[dict[str, object]] = []

    def SaveAs2(self, **kwargs: object) -> None:
        self.save_kwargs.append(kwargs)
        path = Path(str(kwargs["FileName"]))
        self.saved_paths.append(path)
        if self.fail_save:
            raise RuntimeError("save failed")
        write_revision_docx(path)


class FakeDocuments:
    def __init__(self) -> None:
        self.open_calls: list[dict[str, object]] = []
        self.opened = [FakeDocument("original"), FakeDocument("revised")]

    def Open(self, **kwargs: object) -> FakeDocument:
        self.open_calls.append(kwargs)
        return self.opened[len(self.open_calls) - 1]


class FakeWordApplication:
    def __init__(self, comparison_doc: FakeComparisonDocument | None = None) -> None:
        self.Documents = FakeDocuments()
        self.comparison_doc = comparison_doc or FakeComparisonDocument()
        self.compare_calls: list[dict[str, object]] = []
        self.quit_calls = 0
        self.Visible = True
        self.DisplayAlerts = 1

    def CompareDocuments(self, **kwargs: object) -> FakeComparisonDocument:
        self.compare_calls.append(kwargs)
        return self.comparison_doc

    def Quit(self) -> None:
        self.quit_calls += 1


class WordReviewServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        self.original = self.tmp / "original.docx"
        self.revised = self.tmp / "revised.docx"
        self.output = self.tmp / "review.docx"
        write_plain_docx(self.original)
        write_plain_docx(self.revised)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _run_with_fake_word(self, fake_app: FakeWordApplication):
        with mock.patch.object(service_module, "_create_word_application", return_value=fake_app), mock.patch.object(
            service_module, "_word_constants", return_value=FakeConstants
        ):
            return WordReviewService().create_review_document(
                original_path=self.original,
                revised_path=self.revised,
                output_path=self.output,
            )

    def test_rejects_missing_source(self) -> None:
        self.original.unlink()
        with self.assertRaisesRegex(WordReviewError, "Document source absent"):
            WordReviewService().create_review_document(
                original_path=self.original,
                revised_path=self.revised,
                output_path=self.output,
            )

    def test_rejects_unsupported_extensions(self) -> None:
        text_path = self.tmp / "source.txt"
        text_path.write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(WordReviewError, "Extension non prise en charge"):
            WordReviewService().create_review_document(
                original_path=text_path,
                revised_path=self.revised,
                output_path=self.output,
            )

    def test_rejects_same_original_and_revised(self) -> None:
        with self.assertRaisesRegex(WordReviewError, "doivent etre distincts"):
            WordReviewService().create_review_document(
                original_path=self.original,
                revised_path=self.original,
                output_path=self.output,
            )

    def test_rejects_output_overwriting_input(self) -> None:
        with self.assertRaisesRegex(WordReviewError, "ne doit pas ecraser"):
            WordReviewService().create_review_document(
                original_path=self.original,
                revised_path=self.revised,
                output_path=self.revised,
            )

    def test_create_word_application_rejects_non_windows(self) -> None:
        with mock.patch.object(service_module, "_is_windows", return_value=False):
            with self.assertRaisesRegex(WordReviewError, "Windows"):
                service_module._create_word_application()

    def test_create_word_application_reports_missing_pywin32(self) -> None:
        with mock.patch.object(service_module, "_is_windows", return_value=True):
            with mock.patch.dict(sys.modules, {"win32com": None, "win32com.client": None}):
                with self.assertRaisesRegex(WordReviewError, "pywin32"):
                    service_module._create_word_application()

    def test_success_uses_expected_word_compare_options_and_replaces_output(self) -> None:
        self.output.write_text("ancien export", encoding="utf-8")
        fake_app = FakeWordApplication()

        result = self._run_with_fake_word(fake_app)

        self.assertEqual(result.output_path, self.output.resolve())
        self.assertTrue(result.has_tracked_changes)
        self.assertTrue(document_contains_tracked_changes(self.output))
        self.assertEqual(fake_app.quit_calls, 1)
        self.assertEqual(fake_app.Visible, False)
        self.assertEqual(fake_app.DisplayAlerts, 0)
        self.assertEqual(len(fake_app.Documents.open_calls), 2)
        for call in fake_app.Documents.open_calls:
            self.assertTrue(call["ReadOnly"])
            self.assertFalse(call["AddToRecentFiles"])
            self.assertFalse(call["Visible"])

        compare_call = fake_app.compare_calls[0]
        self.assertEqual(compare_call["Destination"], FakeConstants.wdCompareDestinationNew)
        self.assertEqual(compare_call["Granularity"], FakeConstants.wdGranularityCharLevel)
        self.assertFalse(compare_call["CompareFormatting"])
        self.assertTrue(compare_call["CompareCaseChanges"])
        self.assertTrue(compare_call["CompareWhitespace"])
        self.assertTrue(compare_call["CompareTables"])
        self.assertTrue(compare_call["CompareHeaders"])
        self.assertTrue(compare_call["CompareFootnotes"])
        self.assertTrue(compare_call["CompareTextboxes"])
        self.assertTrue(compare_call["CompareFields"])
        self.assertFalse(compare_call["CompareComments"])
        self.assertFalse(compare_call["CompareMoves"])
        self.assertEqual(compare_call["RevisedAuthor"], "PURH Editorial")

        save_call = fake_app.comparison_doc.save_kwargs[0]
        self.assertEqual(save_call["FileFormat"], FakeConstants.wdFormatXMLDocument)
        self.assertFalse(save_call["AddToRecentFiles"])

    def test_closes_documents_and_word_instance(self) -> None:
        fake_app = FakeWordApplication()

        self._run_with_fake_word(fake_app)

        original_doc, revised_doc = fake_app.Documents.opened
        self.assertEqual(original_doc.close_calls, [{"SaveChanges": False}])
        self.assertEqual(revised_doc.close_calls, [{"SaveChanges": False}])
        self.assertEqual(fake_app.comparison_doc.close_calls, [{"SaveChanges": False}])
        self.assertEqual(fake_app.quit_calls, 1)

    def test_failure_cleans_temp_and_preserves_existing_output(self) -> None:
        self.output.write_text("ancien export intact", encoding="utf-8")
        fake_app = FakeWordApplication(FakeComparisonDocument(fail_save=True))

        with self.assertRaisesRegex(WordReviewError, "Comparaison Word echouee"):
            self._run_with_fake_word(fake_app)

        self.assertEqual(self.output.read_text(encoding="utf-8"), "ancien export intact")
        self.assertEqual(list(self.tmp.glob(".review.*.tmp.docx")), [])
        self.assertEqual(fake_app.quit_calls, 1)
        original_doc, revised_doc = fake_app.Documents.opened
        self.assertEqual(original_doc.close_calls, [{"SaveChanges": False}])
        self.assertEqual(revised_doc.close_calls, [{"SaveChanges": False}])
        self.assertEqual(fake_app.comparison_doc.close_calls, [{"SaveChanges": False}])


class TrackedChangesDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_detects_insertions_and_deletions(self) -> None:
        insertion = self.tmp / "ins.docx"
        deletion = self.tmp / "del.docx"
        write_revision_docx(insertion)
        write_docx(
            deletion,
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:del><w:r><w:t>Retrait</w:t></w:r></w:del></w:p></w:body></w:document>",
        )

        self.assertTrue(document_contains_tracked_changes(insertion))
        self.assertTrue(document_contains_tracked_changes(deletion))

    def test_returns_false_for_docx_without_revisions(self) -> None:
        path = self.tmp / "plain.docx"
        write_plain_docx(path)

        self.assertFalse(document_contains_tracked_changes(path))

    def test_invalid_docx_is_reported_clearly(self) -> None:
        path = self.tmp / "broken.docx"
        path.write_text("not a zip", encoding="utf-8")

        with self.assertRaisesRegex(WordReviewError, "DOCX illisible"):
            document_contains_tracked_changes(path)


if __name__ == "__main__":
    unittest.main()
