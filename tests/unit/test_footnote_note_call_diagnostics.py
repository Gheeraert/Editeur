from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, InlineSpan, Paragraph
from purh_editorial.services.footnote_normalizer import FootnoteNormalizer


def _build_document_with_inlines(inlines: list[InlineSpan]) -> Document:
    return Document(
        document_id="doc-note-calls",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[Paragraph(block_id="p1", text="".join(span.text for span in inlines), inlines=inlines)],
    )


class FootnoteNoteCallDiagnosticsTests(unittest.TestCase):
    def test_note_call_after_final_dot_produces_r_an_002_diagnostic(self) -> None:
        document = _build_document_with_inlines(
            [
                InlineSpan(text="mot."),
                InlineSpan(text="1", kind="note_call", note_ref="ftn1"),
            ]
        )
        diagnostics = FootnoteNormalizer().analyze_note_call_placement(document)

        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].rule_id, "R-AN-002")

    def test_note_call_before_final_dot_does_not_produce_diagnostic(self) -> None:
        document = _build_document_with_inlines(
            [
                InlineSpan(text="mot"),
                InlineSpan(text="1", kind="note_call", note_ref="ftn1"),
                InlineSpan(text="."),
            ]
        )
        diagnostics = FootnoteNormalizer().analyze_note_call_placement(document)

        self.assertEqual(diagnostics, [])

    def test_note_call_after_closing_quote_produces_diagnostic(self) -> None:
        document = _build_document_with_inlines(
            [
                InlineSpan(text="mot »"),
                InlineSpan(text="1", kind="note_call", note_ref="ftn1"),
            ]
        )
        diagnostics = FootnoteNormalizer().analyze_note_call_placement(document)

        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].rule_id, "R-AN-002")

    def test_no_inlines_or_no_note_call_produces_no_false_diagnostic(self) -> None:
        without_inlines = Document(
            document_id="doc-no-inlines",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="mot.")],
        )
        diagnostics_without_inlines = FootnoteNormalizer().analyze_note_call_placement(without_inlines)
        self.assertEqual(diagnostics_without_inlines, [])

        without_note_call = _build_document_with_inlines([InlineSpan(text="mot.")])
        diagnostics_without_note_call = FootnoteNormalizer().analyze_note_call_placement(without_note_call)
        self.assertEqual(diagnostics_without_note_call, [])

    def test_note_call_after_regular_space_produces_r_an_003_diagnostic(self) -> None:
        document = _build_document_with_inlines(
            [
                InlineSpan(text="mot "),
                InlineSpan(text="1", kind="note_call", note_ref="ftn1"),
            ]
        )
        diagnostics = FootnoteNormalizer().analyze_note_call_placement(document)
        r_an_003 = [d for d in diagnostics if d.rule_id == "R-AN-003"]
        self.assertEqual(len(r_an_003), 1)
        self.assertEqual(r_an_003[0].category, "footnote_call_spacing")
        self.assertEqual(r_an_003[0].attributes.get("preceding_space_kind"), "space")

    def test_note_call_after_nbsp_produces_r_an_003_diagnostic(self) -> None:
        document = _build_document_with_inlines(
            [
                InlineSpan(text="mot\u00A0"),
                InlineSpan(text="1", kind="note_call", note_ref="ftn1"),
            ]
        )
        diagnostics = FootnoteNormalizer().analyze_note_call_placement(document)
        r_an_003 = [d for d in diagnostics if d.rule_id == "R-AN-003"]
        self.assertEqual(len(r_an_003), 1)
        self.assertEqual(r_an_003[0].attributes.get("preceding_space_kind"), "nbsp")

    def test_note_call_after_nnbsp_produces_r_an_003_diagnostic(self) -> None:
        document = _build_document_with_inlines(
            [
                InlineSpan(text="mot\u202F"),
                InlineSpan(text="1", kind="note_call", note_ref="ftn1"),
            ]
        )
        diagnostics = FootnoteNormalizer().analyze_note_call_placement(document)
        r_an_003 = [d for d in diagnostics if d.rule_id == "R-AN-003"]
        self.assertEqual(len(r_an_003), 1)
        self.assertEqual(r_an_003[0].attributes.get("preceding_space_kind"), "nnbsp")

    def test_note_call_directly_after_word_has_no_r_an_003_diagnostic(self) -> None:
        document = _build_document_with_inlines(
            [
                InlineSpan(text="mot"),
                InlineSpan(text="1", kind="note_call", note_ref="ftn1"),
            ]
        )
        diagnostics = FootnoteNormalizer().analyze_note_call_placement(document)
        self.assertFalse(any(d.rule_id == "R-AN-003" for d in diagnostics))

    def test_note_call_isolated_or_at_block_start_has_no_r_an_003_diagnostic(self) -> None:
        isolated = _build_document_with_inlines([InlineSpan(text="1", kind="note_call", note_ref="ftn1")])
        isolated_diags = FootnoteNormalizer().analyze_note_call_placement(isolated)
        self.assertFalse(any(d.rule_id == "R-AN-003" for d in isolated_diags))

        start_then_text = _build_document_with_inlines(
            [
                InlineSpan(text="1", kind="note_call", note_ref="ftn1"),
                InlineSpan(text=" mot"),
            ]
        )
        start_diags = FootnoteNormalizer().analyze_note_call_placement(start_then_text)
        self.assertFalse(any(d.rule_id == "R-AN-003" for d in start_diags))


if __name__ == "__main__":
    unittest.main()
