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


class LatexExporterBiblNotesTests(unittest.TestCase):
    def test_bibliographic_notes_preserve_inline_content_and_spacing(self) -> None:
        input_xml = ROOT / "tests" / "fixtures" / "tei_latex_bibl_notes.xml"
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        output_tex = runtime_dir / f"latex_bibl_notes_{uuid.uuid4().hex}.tex"

        export_tei_to_latex(input_xml, output_tex)
        tex = output_tex.read_text(encoding="utf-8")

        self.assertNotIn(r"\footnote{ ", tex)
        self.assertIn(r"42-46. \textit{Ibid.}, p. 147", tex)
        self.assertIn(r"p. 1313. \textit{Le Mercure galant}", tex)
        self.assertIn(r"p. 147. \textit{Œuvres complètes}", tex)
        self.assertNotIn(r".\textit{Ibid.}", tex)
        self.assertNotIn(r"p.}", tex)


if __name__ == "__main__":
    unittest.main()
