from __future__ import annotations

import unittest

from purh_editorial.model import Diagnostic, Document, Evidence, Paragraph, ProcessingReport, Suggestion
from purh_editorial.services.word_review_annotation_service import build_word_review_comments


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


if __name__ == "__main__":
    unittest.main()
