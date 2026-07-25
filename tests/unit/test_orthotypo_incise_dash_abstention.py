from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Paragraph
from purh_editorial.services.orthotypo_service import OrthotypoService


class OrthotypoIncideDashAbstentionTests(unittest.TestCase):
    """
    purh.tiret.incise ne corrige plus automatiquement (auto=False) : la pratique
    éditoriale observée va dans le sens opposé de ce que la règle produisait, et le
    guide PURH ne tranche pas la convention attendue. Voir
    docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md et docs/PHASE6BIS_ASSAINISSEMENT.md.
    """

    def _apply(self, text: str) -> tuple[str, list]:
        document = Document(
            document_id="doc-incise",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text=text)],
        )
        service = OrthotypoService()
        corrected, transformations = service.apply(document)
        diagnostics = service.analyze_incise_dash(corrected)
        return corrected.blocks[0].text, transformations, diagnostics

    def test_hyphen_form_is_left_unchanged(self) -> None:
        text = "une phrase - incise - continue"
        result, transformations, _diags = self._apply(text)
        self.assertEqual(result, text)
        self.assertEqual(transformations, [])

    def test_en_dash_form_is_left_unchanged(self) -> None:
        text = "une phrase – incise – continue"
        result, transformations, _diags = self._apply(text)
        self.assertEqual(result, text)
        self.assertEqual(transformations, [])

    def test_em_dash_form_is_left_unchanged(self) -> None:
        text = "une phrase — incise — continue"
        result, transformations, _diags = self._apply(text)
        self.assertEqual(result, text)
        self.assertEqual(transformations, [])

    def test_each_incise_dash_produces_a_diagnostic(self) -> None:
        text = "une phrase - incise - continue"
        _result, _tr, diagnostics = self._apply(text)
        self.assertEqual(len(diagnostics), 2)
        for diag in diagnostics:
            self.assertEqual(diag.rule_id, "R-TI-001")
            self.assertEqual(diag.category, "incise_dash")

    def test_text_without_incise_dash_has_no_diagnostic(self) -> None:
        _result, _tr, diagnostics = self._apply("une phrase sans tiret du tout")
        self.assertEqual(diagnostics, [])


if __name__ == "__main__":
    unittest.main()
