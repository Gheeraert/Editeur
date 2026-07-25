from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

GOLD_DIR = ROOT / "fixtures" / "orthotypography_gold"
sys.path.insert(0, str(GOLD_DIR))

from loader import load_gold_cases  # noqa: E402

from purh_editorial.model import Document, Paragraph
from purh_editorial.services.orthotypo_service import OrthotypoService


def _apply_via_pipeline(text: str) -> str:
    document = Document(
        document_id="doc-gold",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[Paragraph(block_id="p1", text=text)],
    )
    corrected, _transformations = OrthotypoService().apply(document)
    return corrected.blocks[0].text


class OrthotypoGoldNormativeCorpusTests(unittest.TestCase):
    """
    Corpus d'or normatif : contrairement au corpus de caractérisation, chaque cas ici
    est réellement validé indépendamment du code (voir
    fixtures/orthotypography_gold/SCHEMA.md). Un échec ici signifie que le
    comportement du logiciel s'est écarté d'une prescription établie — pas seulement
    qu'il a changé.
    """

    def test_at_least_one_gold_case_is_loaded(self) -> None:
        cases = load_gold_cases()
        self.assertGreater(len(cases), 0, "Aucun cas d'or normatif chargé — corpus vide ou mal formé.")

    def test_every_gold_case_matches_current_pipeline_output(self) -> None:
        for case in load_gold_cases():
            with self.subTest(rule=case.rule_id, source=case.validation_source_reference):
                self.assertEqual(_apply_via_pipeline(case.input), case.expected_output)

    def test_every_gold_case_has_a_real_validation_source(self) -> None:
        for case in load_gold_cases():
            with self.subTest(rule=case.rule_id):
                self.assertIn(
                    case.validation_source_type,
                    {"guide_purh", "editorial_copy", "human_validation"},
                )
                self.assertTrue(case.validation_source_reference.strip())


if __name__ == "__main__":
    unittest.main()
