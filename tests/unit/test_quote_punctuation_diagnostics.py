from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Paragraph, QuoteBlock
from purh_editorial.services.orthotypo_service import OrthotypoService


def _doc_with_paragraph(text: str) -> Document:
    return Document(
        document_id="doc-quote-punct",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[Paragraph(block_id="p1", text=text)],
    )


class QuotePunctuationDiagnosticsTests(unittest.TestCase):
    def test_redundant_dot_after_strong_punct_inside_quote_is_diagnosed(self) -> None:
        document = _doc_with_paragraph("« Que faire ? ».")
        diagnostics = OrthotypoService().analyze_quote_punctuation(document)

        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].rule_id, "R-GQ-004")
        self.assertEqual(diagnostics[0].category, "quote_punctuation")

    def test_colon_intro_then_dot_after_quote_is_diagnosed_prudently(self) -> None:
        document = _doc_with_paragraph("Il écrit : « La question est ouverte ».")
        diagnostics = OrthotypoService().analyze_quote_punctuation(document)

        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].rule_id, "R-GQ-004")

    def test_double_punctuation_pattern_is_diagnosed(self) -> None:
        document = _doc_with_paragraph("« texte. ».")
        diagnostics = OrthotypoService().analyze_quote_punctuation(document)

        self.assertTrue(any(d.rule_id == "R-GQ-004" for d in diagnostics))

    def test_simple_fused_quote_is_not_diagnosed(self) -> None:
        document = _doc_with_paragraph("Il parle de « réforme ».")
        diagnostics = OrthotypoService().analyze_quote_punctuation(document)

        self.assertEqual(diagnostics, [])

    def test_nested_quote_case_is_ignored(self) -> None:
        document = _doc_with_paragraph("« Il dit “bonjour” puis se tut. ».")
        diagnostics = OrthotypoService().analyze_quote_punctuation(document)

        self.assertEqual(diagnostics, [])

    def test_quote_block_is_ignored(self) -> None:
        document = Document(
            document_id="doc-quote-block",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[QuoteBlock(block_id="q1", text="« Que faire ? ».")],
        )
        diagnostics = OrthotypoService().analyze_quote_punctuation(document)

        self.assertEqual(diagnostics, [])

    def test_technical_text_is_not_diagnosed(self) -> None:
        document = _doc_with_paragraph('<hi rend="italic">')
        diagnostics = OrthotypoService().analyze_quote_punctuation(document)

        self.assertEqual(diagnostics, [])


if __name__ == "__main__":
    unittest.main()
