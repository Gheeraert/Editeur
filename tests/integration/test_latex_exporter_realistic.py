from __future__ import annotations

import os
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.latex.latex_exporter import export_tei_to_latex


class LatexExporterRealisticTests(unittest.TestCase):
    def test_cli_entrypoint_exports_latex_file(self) -> None:
        input_xml = ROOT / "tests" / "fixtures" / "tei_latex_realistic.xml"
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        output_tex = runtime_dir / f"latex_cli_{uuid.uuid4().hex}.tex"

        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC)
        command = [
            sys.executable,
            "-m",
            "purh_editorial.latex.latex_exporter",
            str(input_xml),
            str(output_tex),
        ]
        result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        self.assertTrue(output_tex.exists())

    def test_realistic_export_contains_expected_structures(self) -> None:
        input_xml = ROOT / "tests" / "fixtures" / "tei_latex_realistic.xml"
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        output_tex = runtime_dir / f"latex_realistic_{uuid.uuid4().hex}.tex"

        export_tei_to_latex(input_xml, output_tex)
        tex = output_tex.read_text(encoding="utf-8")

        self.assertIn(r"\documentclass[11pt,oneside,openany]{memoir}", tex)
        self.assertIn(r"\setstocksize{230mm}{155mm}", tex)
        self.assertIn(r"\setmainlanguage{french}", tex)
        self.assertIn(r"\usepackage[final]{microtype}", tex)
        self.assertIn(r"\begin{quote}\small", tex)
        self.assertIn(r"\begin{verse}", tex)
        self.assertIn(r"\footnote{Voir l", tex)
        self.assertIn(r"\textit{princeps}", tex)
        self.assertIn("Liminaires", tex)
        self.assertIn("Chapitre 1. Méthodes", tex)
        self.assertIn("Bibliographie", tex)


if __name__ == "__main__":
    unittest.main()
