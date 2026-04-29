from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Document, Paragraph
from purh_editorial.services.orthotypo_service import NBSP, NNBSP, OrthotypoService


def _apply_orthotypo(text: str) -> str:
    document = Document(
        document_id="doc-orthotypo",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[Paragraph(block_id="p1", text=text)],
    )
    service = OrthotypoService()
    corrected, _transformations = service.apply(document)
    return corrected.blocks[0].text


class OrthotypoServiceGuardrailsTests(unittest.TestCase):
    def test_r_sp_001_simple_cases(self) -> None:
        self.assertEqual(_apply_orthotypo("Voici: un cas"), f"Voici{NNBSP}: un cas")
        self.assertEqual(_apply_orthotypo("Pourquoi?"), f"Pourquoi{NNBSP}?")

    def test_r_sp_001_does_not_change_technical_tokens(self) -> None:
        self.assertEqual(
            _apply_orthotypo("http://exemple.org:8080/test"),
            "http://exemple.org:8080/test",
        )
        self.assertEqual(
            _apply_orthotypo("https://exemple.org/a:b"),
            "https://exemple.org/a:b",
        )
        self.assertEqual(_apply_orthotypo("10:30"), "10:30")
        self.assertEqual(_apply_orthotypo("1:2"), "1:2")
        self.assertEqual(_apply_orthotypo("format 16:9"), "format 16:9")
        self.assertEqual(_apply_orthotypo(r"C:\dossier\fichier"), r"C:\dossier\fichier")
        self.assertEqual(_apply_orthotypo("RFC 1234:5"), "RFC 1234:5")

    def test_r_sp_002_space_before_comma_or_dot(self) -> None:
        self.assertEqual(_apply_orthotypo("mot , suite"), "mot, suite")
        self.assertEqual(_apply_orthotypo("mot . Suite"), "mot. Suite")
        self.assertEqual(_apply_orthotypo("Attends… , oui"), "Attends…, oui")

    def test_r_sp_003_reduce_double_spaces_only(self) -> None:
        self.assertEqual(_apply_orthotypo("mot  mot"), "mot mot")
        self.assertEqual(_apply_orthotypo("mot \t mot"), "mot mot")
        self.assertEqual(_apply_orthotypo(f"mot{NBSP}mot"), f"mot{NBSP}mot")
        self.assertEqual(_apply_orthotypo(f"mot{NNBSP}mot"), f"mot{NNBSP}mot")

    def test_r_ab_001_etc_variants(self) -> None:
        self.assertEqual(_apply_orthotypo("etc..."), "etc.")
        self.assertEqual(_apply_orthotypo("etc…"), "etc.")
        self.assertEqual(_apply_orthotypo("etc...."), "etc.")


if __name__ == "__main__":
    unittest.main()
