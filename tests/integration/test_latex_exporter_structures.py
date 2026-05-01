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


class LatexExporterStructuresTests(unittest.TestCase):
    def test_export_includes_expected_latex_structures(self) -> None:
        input_xml = ROOT / "tests" / "fixtures" / "tei_latex_structures.xml"
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        output_tex = runtime_dir / f"latex_structures_{uuid.uuid4().hex}.tex"

        export_tei_to_latex(input_xml, output_tex)
        tex = output_tex.read_text(encoding="utf-8")

        self.assertTrue(r"\chapter{" in tex or r"\chapter*{" in tex)
        self.assertIn(r"\begin{quote}", tex)
        self.assertIn(r"\begin{verse}", tex)
        self.assertIn(r"\footnote{", tex)
        self.assertIn(r"\textit{", tex)
        self.assertTrue(r"\section*{Bibliographie}" in tex or "Bibliographie" in tex)


if __name__ == "__main__":
    unittest.main()
