from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from purh_editorial.model import Document, ProcessingReport
from purh_editorial.services.word_review_service import (
    WordReviewError,
    _create_word_application,
    document_contains_tracked_changes,
)


@dataclass(slots=True)
class WordReviewComment:
    comment_id: str
    target_ref: str
    anchor_text: str
    target_text: str
    comment_text: str
    category: str


@dataclass(slots=True)
class WordReviewAnnotationResult:
    output_path: Path
    comments_requested: int
    comments_added: int
    comments_skipped: int
    ambiguous_anchors: int
    missing_anchors: int


def _target_texts(document: Document) -> dict[str, str]:
    values = {block.block_id: block.text for block in document.blocks}
    values.update({note.note_id: note.text for note in document.notes})
    return values


def build_word_review_comments(document: Document, report: ProcessingReport) -> list[WordReviewComment]:
    """Create a conservative, COM-free plan for human-review comments."""
    targets = _target_texts(document)
    comments: list[WordReviewComment] = []
    for suggestion in report.suggestions:
        target = targets.get(suggestion.target_ref, "")
        anchor = str(suggestion.attributes.get("before") or suggestion.proposed_text or "").strip()
        if not target or not anchor:
            continue
        lines = ["Suggestion à valider", f"Proposition : {suggestion.proposed_text or '(non précisée)'}",
                 f"Justification : {suggestion.rationale or suggestion.message}",
                 f"Confiance : {suggestion.confidence if suggestion.confidence is not None else 'non précisée'}",
                 f"Module : {suggestion.module}"]
        for key, label in (("provider", "Fournisseur"), ("model", "Modèle"), ("rule_id", "Règle")):
            if suggestion.attributes.get(key): lines.append(f"{label} : {suggestion.attributes[key]}")
        lines.append(f"Prudence : {suggestion.caution_level}")
        comments.append(WordReviewComment(suggestion.suggestion_id, suggestion.target_ref, anchor, target, "\n".join(lines), "suggestion"))
    for diagnostic in report.diagnostics:
        if diagnostic.status != "open" or diagnostic.attributes.get("auto_applied") or not diagnostic.target_ref:
            continue
        target = targets.get(diagnostic.target_ref, "")
        anchor = next((str(v).strip() for v in (diagnostic.evidence.excerpt, diagnostic.evidence.after, diagnostic.evidence.before, target) if v), "")
        if not target or not anchor:
            continue
        text = "\n".join(("Point à vérifier", f"Message : {diagnostic.message}",
                            f"Suggestion : {diagnostic.suggested_fix or '(aucune)'}",
                            f"Règle : {diagnostic.rule_id or '(non précisée)'}", f"Niveau : {diagnostic.severity}"))
        comments.append(WordReviewComment(diagnostic.diagnostic_id, diagnostic.target_ref, anchor, target, text, "diagnostic"))
    return comments


class WordReviewAnnotationService:
    """Annotate a review copy atomically; ambiguous anchors are never guessed."""

    def annotate_review_document(self, *, review_path: Path, document: Document, report: ProcessingReport) -> WordReviewAnnotationResult:
        review_path = Path(review_path).resolve()
        comments = build_word_review_comments(document, report)
        result = WordReviewAnnotationResult(review_path, len(comments), 0, 0, 0, 0)
        if not comments:
            return result
        if not review_path.is_file() or review_path.suffix.lower() != ".docx":
            raise WordReviewError(f"Document de révision introuvable ou invalide : {review_path}")
        fd, temp_name = tempfile.mkstemp(prefix=f".{review_path.stem}.", suffix=".comments.tmp.docx", dir=review_path.parent)
        os.close(fd); temp_path = Path(temp_name); temp_path.unlink()
        app = doc = None
        try:
            shutil.copy2(review_path, temp_path)
            app = _create_word_application(); app.Visible = False; app.DisplayAlerts = 0
            doc = app.Documents.Open(FileName=str(temp_path), ReadOnly=False, AddToRecentFiles=False, Visible=False)
            for item in comments:
                matches = self._find_exact_ranges(doc, item.target_text, item.anchor_text)
                if len(matches) == 1:
                    doc.Comments.Add(Range=matches[0], Text=item.comment_text); result.comments_added += 1
                elif not matches:
                    result.comments_skipped += 1; result.missing_anchors += 1
                else:
                    result.comments_skipped += 1; result.ambiguous_anchors += 1
            doc.Save()
            doc.Close(SaveChanges=False); doc = None
            if not document_contains_tracked_changes(temp_path):
                raise WordReviewError("Les modifications suivies ont disparu pendant l'annotation Word.")
            os.replace(temp_path, review_path)
            return result
        finally:
            if doc is not None:
                try: doc.Close(SaveChanges=False)
                except Exception: pass
            if app is not None:
                try: app.Quit()
                except Exception: pass
            if temp_path.exists():
                try: temp_path.unlink()
                except OSError: pass

    @staticmethod
    def _find_exact_ranges(word_document: Any, target_text: str, anchor_text: str) -> list[Any]:
        matches: list[Any] = []
        for paragraph in word_document.Paragraphs:
            scope = paragraph.Range.Duplicate
            if target_text and target_text not in str(scope.Text):
                continue
            finder = scope.Duplicate
            find = finder.Find; find.ClearFormatting(); find.Text = anchor_text; find.Forward = True; find.Wrap = 0
            while find.Execute():
                matches.append(finder.Duplicate)
                finder.Start = finder.End
                finder.End = scope.End
                find = finder.Find; find.ClearFormatting(); find.Text = anchor_text; find.Forward = True; find.Wrap = 0
        return matches
