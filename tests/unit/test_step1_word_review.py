from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from shutil import copy2
from unittest.mock import patch

from docx import Document

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.config import load_settings
from purh_editorial.pipeline.step1 import Step1Options, Step1Pipeline
from purh_editorial.services.word_review_service import WordReviewError, WordReviewResult
from purh_editorial.services.word_review_annotation_service import WordReviewAnnotationResult


class FakeWordReviewService:
    def __init__(self, error: WordReviewError | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Path]] = []

    def create_review_document(
        self,
        *,
        original_path: Path,
        revised_path: Path,
        output_path: Path,
    ) -> WordReviewResult:
        self.calls.append(
            {
                "original_path": original_path,
                "revised_path": revised_path,
                "output_path": output_path,
            }
        )
        if self.error is not None:
            raise self.error
        return WordReviewResult(
            original_path=original_path,
            revised_path=revised_path,
            output_path=output_path,
            has_tracked_changes=True,
        )


class FakeWordReviewAnnotationService:
    def __init__(self, error: WordReviewError | None = None) -> None:
        self.error = error
    def annotate_review_document(self, *, review_path, document, report):
        if self.error:
            raise self.error
        return WordReviewAnnotationResult(review_path, 0, 0, 0, 0, 0)


class Step1WordReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        self.source = self.tmp / "source.docx"
        document = Document()
        document.add_paragraph("Le XVIIème siècle.")
        document.save(self.source)
        self.settings = load_settings()

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _module_run(self, result, name: str):
        return next(run for run in result.pipeline_result.report.module_runs if run.module_name == name)

    def test_pipeline_uses_reborn_corrector_for_the_candidate(self) -> None:
        candidate = self.tmp / "candidate.docx"

        def fake_corrector(source: Path, output: Path) -> dict[str, int]:
            copy2(source, output)
            return {"purh.points_suspension": 1}

        with patch("purh_editorial.pipeline.step1.correct_docx", side_effect=fake_corrector) as corrector:
            result = Step1Pipeline(settings=self.settings).run(
                self.source, Step1Options(output_path=candidate)
            )

        corrector.assert_called_once_with(self.source, candidate)
        self.assertTrue(candidate.exists())
        self.assertEqual(self._module_run(result, "reborn_corrector").summary["corrections"], 1)

    def test_absent_option_does_not_call_word_review_service(self) -> None:
        service = FakeWordReviewService()
        candidate = self.tmp / "candidate.docx"
        pipeline = Step1Pipeline(settings=self.settings, word_review_service=service)

        result = pipeline.run(self.source, Step1Options(output_path=candidate))

        self.assertTrue(candidate.exists())
        self.assertEqual(service.calls, [])
        self.assertIsNone(result.word_review_result)
        self.assertFalse(
            any(run.module_name == "word_review" for run in result.pipeline_result.report.module_runs)
        )

    def test_success_compares_original_to_exported_candidate(self) -> None:
        service = FakeWordReviewService()
        candidate = self.tmp / "candidate.docx"
        review = self.tmp / "review.docx"
        pipeline = Step1Pipeline(settings=self.settings, word_review_service=service)

        result = pipeline.run(
            self.source,
            Step1Options(output_path=candidate, word_review_output_path=review),
        )

        self.assertTrue(candidate.exists())
        self.assertEqual(len(service.calls), 1)
        self.assertEqual(service.calls[0]["original_path"], self.source)
        self.assertEqual(service.calls[0]["revised_path"], result.output_docx)
        self.assertEqual(service.calls[0]["output_path"], review)
        self.assertIsNotNone(result.word_review_result)
        self.assertTrue(result.word_review_result.has_tracked_changes)
        module_run = self._module_run(result, "word_review")
        self.assertEqual(module_run.status, "success")
        self.assertEqual(module_run.summary["candidate"], str(result.output_docx))
        self.assertEqual(module_run.summary["output"], str(review))

    def test_review_requested_without_candidate_records_a_failure(self) -> None:
        service = FakeWordReviewService()
        review = self.tmp / "review.docx"
        pipeline = Step1Pipeline(settings=self.settings, word_review_service=service)

        result = pipeline.run(self.source, Step1Options(word_review_output_path=review))

        self.assertEqual(service.calls, [])
        self.assertIsNone(result.output_docx)
        self.assertIsNone(result.word_review_result)
        self.assertTrue(
            any("aucun DOCX candidat" in error for error in result.pipeline_result.report.errors)
        )
        self.assertEqual(self._module_run(result, "word_review").status, "failed")

    def test_word_review_failure_keeps_exported_candidate(self) -> None:
        service = FakeWordReviewService(WordReviewError("Microsoft Word indisponible"))
        candidate = self.tmp / "candidate.docx"
        review = self.tmp / "review.docx"
        pipeline = Step1Pipeline(settings=self.settings, word_review_service=service)

        result = pipeline.run(
            self.source,
            Step1Options(output_path=candidate, word_review_output_path=review),
        )

        self.assertTrue(candidate.exists())
        self.assertEqual(len(service.calls), 1)
        self.assertIsNone(result.word_review_result)
        self.assertTrue(
            any("WordReviewError" in error and "Microsoft Word indisponible" in error
                for error in result.pipeline_result.report.errors)
        )
        self.assertEqual(self._module_run(result, "word_review").status, "failed")

    def test_annotation_failure_keeps_candidate_and_review_result(self) -> None:
        candidate = self.tmp / "candidate.docx"
        review = self.tmp / "review.docx"
        pivot_json = self.tmp / "pivot.json"
        pipeline = Step1Pipeline(
            settings=self.settings,
            word_review_service=FakeWordReviewService(),
            word_review_annotation_service=FakeWordReviewAnnotationService(
                WordReviewError("échec annotation simulé")
            ),
        )
        result = pipeline.run(
            self.source,
            Step1Options(
                output_path=candidate,
                word_review_output_path=review,
                pivot_json_output_path=pivot_json,
            ),
        )
        self.assertTrue(candidate.exists())
        self.assertTrue(pivot_json.exists())
        self.assertIsNotNone(result.word_review_result)
        self.assertIsNone(result.word_review_annotation_result)
        self.assertEqual(self._module_run(result, "word_review").status, "success")
        self.assertEqual(self._module_run(result, "word_review_comments").status, "failed")
        self.assertTrue(any("échec annotation simulé" in error for error in result.pipeline_result.report.errors))

    def test_empty_annotation_is_skipped(self) -> None:
        candidate = self.tmp / "candidate.docx"
        review = self.tmp / "review.docx"
        pipeline = Step1Pipeline(
            settings=self.settings,
            word_review_service=FakeWordReviewService(),
            word_review_annotation_service=FakeWordReviewAnnotationService(),
        )
        result = pipeline.run(
            self.source,
            Step1Options(output_path=candidate, word_review_output_path=review),
        )
        self.assertEqual(self._module_run(result, "word_review_comments").status, "skipped")


if __name__ == "__main__":
    unittest.main()
