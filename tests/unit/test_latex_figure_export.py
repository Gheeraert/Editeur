from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.latex.latex_exporter import export_tei_to_latex

TEI_WITH_FIGURE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc><titleStmt><title>Test</title></titleStmt>
  <publicationStmt><p>x</p></publicationStmt>
  <sourceDesc><p>x</p></sourceDesc></fileDesc></teiHeader>
  <text><body>
    <p>Texte avant figure.</p>
    <figure xml:id="fig-1">
      <head>Légende de test</head>
      <graphic url="media/img-1.png"/>
      <figDesc>Texte alternatif</figDesc>
    </figure>
  </body></text>
</TEI>
"""


class LatexFigureExportTests(unittest.TestCase):
    def test_figure_renders_includegraphics_and_copies_media(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            xml_path = tmp_path / "doc_tei.xml"
            xml_path.write_text(TEI_WITH_FIGURE, encoding="utf-8")
            media_dir = tmp_path / "media"
            media_dir.mkdir()
            (media_dir / "img-1.png").write_bytes(b"\x89PNG\r\n\x1a\n")

            output_tex = tmp_path / "out" / "doc.tex"
            export_tei_to_latex(xml_path, output_tex)

            tex_content = output_tex.read_text(encoding="utf-8")
            self.assertIn(r"\includegraphics", tex_content)
            self.assertIn("media/img-1.png", tex_content)
            self.assertIn("Légende de test", tex_content)
            self.assertTrue((output_tex.parent / "media" / "img-1.png").exists())


if __name__ == "__main__":
    unittest.main()
