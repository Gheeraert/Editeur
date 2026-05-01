from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.latex.latex_exporter import export_tei_to_latex


class LatexExporterMinimalTests(unittest.TestCase):
    def test_export_tei_to_latex_writes_expected_markers(self) -> None:
        input_xml = ROOT / "tests" / "fixtures" / "tei_latex_minimal.xml"
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        output_tex = runtime_dir / f"latex_export_{uuid.uuid4().hex}.tex"

        written_path = export_tei_to_latex(input_xml, output_tex)

        self.assertEqual(written_path, output_tex)
        self.assertTrue(output_tex.exists())

        tex = output_tex.read_text(encoding="utf-8")
        self.assertIn(r"\documentclass", tex)
        self.assertIn(r"\begin{document}", tex)
        self.assertIn("Titre de test PURH", tex)
        self.assertIn("Un paragraphe avec", tex)
        self.assertIn(r"\textit{", tex)
        self.assertIn(r"\textsc{", tex)
        self.assertIn(r"\textsuperscript{", tex)
        self.assertIn(r"\footnote{", tex)


if __name__ == "__main__":
    unittest.main()
