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
        # Vers dans <cit><quote><lg> : chaque ligne doit être sur sa propre ligne LaTeX
        self.assertIn("Vers dans cit un" + r"\\", tex)
        self.assertIn("Vers dans cit deux" + r"\\", tex)
        self.assertIn("Vers dans cit trois" + r"\\", tex)
        cit_un_idx = tex.index("Vers dans cit un")
        cit_deux_idx = tex.index("Vers dans cit deux")
        cit_trois_idx = tex.index("Vers dans cit trois")
        self.assertIn("\n", tex[cit_un_idx:cit_deux_idx])
        self.assertIn("\n", tex[cit_deux_idx:cit_trois_idx])

    def test_export_tei_table_as_longtable_without_paragraph_explosion(self) -> None:
        input_xml = ROOT / "tests" / "fixtures" / "tei_latex_table.xml"
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        output_tex = runtime_dir / f"latex_table_{uuid.uuid4().hex}.tex"

        export_tei_to_latex(input_xml, output_tex)
        tex = output_tex.read_text(encoding="utf-8")

        self.assertIn(r"\usepackage{longtable}", tex)
        self.assertIn(r"\begin{longtable}", tex)
        self.assertIn(r"\end{longtable}", tex)
        self.assertIn(r"\newcommand{\purhTableSize}{\small}", tex)
        self.assertIn(r"\begingroup", tex)
        self.assertIn(r"\purhTableSize", tex)
        self.assertIn(r"\endgroup", tex)
        self.assertIn("% table_exported_to_latex rows=2 cols=2", tex)
        self.assertIn("Avant tableau.", tex)
        self.assertIn("Après tableau.", tex)
        self.assertLess(tex.index("Avant tableau."), tex.index(r"\begin{longtable}"))
        self.assertLess(tex.index(r"\end{longtable}"), tex.index("Après tableau."))
        group_idx = tex.index(r"\begingroup")
        local_size_idx = tex.index(r"\purhTableSize", group_idx)
        longtable_begin_idx = tex.index(r"\begin{longtable}")
        longtable_end_idx = tex.index(r"\end{longtable}")
        group_end_idx = tex.index(r"\endgroup", longtable_end_idx)
        self.assertLess(group_idx, local_size_idx)
        self.assertLess(local_size_idx, longtable_begin_idx)
        self.assertLess(longtable_begin_idx, longtable_end_idx)
        self.assertLess(longtable_end_idx, group_end_idx)
        self.assertIn("VIII, Pr., \\textit{p. 390} \\& accolade", tex)
        self.assertIn("VIII, Pr., \\textbf{18}\\footnote{Note cellule}", tex)
        self.assertIn("\\textsuperscript{2} Il me faut en effet aller...", tex)
        self.assertIn(" & ", tex)
        self.assertIn(r"\\", tex)


    def test_preamble_paragraphs_before_first_div_are_not_lost(self) -> None:
        """Régression : paragraphes orphelins (avant-propos sans heading) perdus quand des <div> existent."""
        input_xml = ROOT / "tests" / "fixtures" / "tei_latex_preamble.xml"
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        output_tex = runtime_dir / f"latex_preamble_{uuid.uuid4().hex}.tex"

        export_tei_to_latex(input_xml, output_tex)
        tex = output_tex.read_text(encoding="utf-8")

        self.assertIn("Premier paragraphe de l'avant-propos.", tex)
        self.assertIn("Deuxième paragraphe de l'avant-propos.", tex)
        self.assertIn("Chapitre 1", tex)
        self.assertIn("Contenu du chapitre 1.", tex)
        # L'avant-propos doit précéder le chapitre 1
        self.assertLess(tex.index("avant-propos"), tex.index("Chapitre 1"))


if __name__ == "__main__":
    unittest.main()
