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


class LatexExporterInlineSpacingTests(unittest.TestCase):
    def test_inline_spacing_is_preserved_around_tags(self) -> None:
        input_xml = ROOT / "tests" / "fixtures" / "tei_latex_inline_spacing.xml"
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        output_tex = runtime_dir / f"latex_inline_spacing_{uuid.uuid4().hex}.tex"

        export_tei_to_latex(input_xml, output_tex)
        tex = output_tex.read_text(encoding="utf-8")

        self.assertIn(r"mentions en \textsc{petites capitales} et des datations", tex)
        self.assertIn(r"XIX\textsuperscript{e} siècle", tex)
        self.assertIn(r"\footnote{note avec \textit{italique} interne} pour", tex)
        self.assertIn(r"\textit{italique}, puis", tex)
        self.assertIn(r"\textbf{gras}.", tex)


if __name__ == "__main__":
    unittest.main()
