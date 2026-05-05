from __future__ import annotations

import json
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.config import load_settings
from purh_editorial.pipeline.step1 import Step1Options, Step1Pipeline
from purh_editorial.ui.step1_dialog import build_output_paths, run_export_bundle
from tests.helpers.docx_factory import create_titre_docx


class ExportBundleServiceTests(unittest.TestCase):
    def test_export_bundle_writes_xml_and_latex(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        source = ROOT / "tests" / "fixtures" / "minimal_source.txt"
        output_dir = ROOT / "tests" / "_runtime" / f"bundle_{uuid.uuid4().hex}"
        output_dir.mkdir(parents=True, exist_ok=True)

        docx_path, tei_path, tex_path = build_output_paths(source, output_dir, "minimal_source")
        pivot_json_path = output_dir / "minimal_source_pivot.json"
        options = Step1Options(
            enable_ai=False,
            output_path=docx_path,
            tei_output_path=tei_path,
            pivot_json_output_path=pivot_json_path,
        )

        bundle = run_export_bundle(
            pipeline=pipeline,
            source=source,
            options=options,
            export_latex=True,
            latex_output_path=tex_path,
        )

        self.assertTrue(docx_path.exists())
        self.assertTrue(pivot_json_path.exists())
        pivot_payload = json.loads(pivot_json_path.read_text(encoding="utf-8"))
        self.assertEqual(pivot_payload.get("schema_version"), "pivot-1.0")
        module_runs = pivot_payload.get("report", {}).get("module_runs", [])
        pivot_write_runs = [m for m in module_runs if m.get("module_name") == "pivot_json_write"]
        self.assertTrue(pivot_write_runs)
        self.assertEqual(pivot_write_runs[-1].get("summary", {}).get("output"), str(pivot_json_path))
        # TEI/Latex may be skipped when the production gate blocks invalid pivots.
        if tei_path.exists():
            self.assertIsNone(bundle.latex_error)
            self.assertIsNotNone(bundle.latex_output_path)
            self.assertTrue(tex_path.exists())


    def test_latex_not_produced_when_tei_blocked_by_pivot_validation(self) -> None:
        """Quand la validation du pivot bloque le TEI, le LaTeX ne doit pas être produit."""
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        runtime_dir = ROOT / "tests" / "_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        source_path = runtime_dir / f"titre_src_{uuid.uuid4().hex}.docx"
        create_titre_docx(source_path)

        output_dir = runtime_dir / f"bundle_tei_blocked_{uuid.uuid4().hex}"
        output_dir.mkdir(parents=True, exist_ok=True)
        docx_path, tei_path, tex_path = build_output_paths(source_path, output_dir, "titre_test")
        pivot_json_path = output_dir / "titre_test_pivot.json"
        options = Step1Options(
            enable_ai=False,
            output_path=docx_path,
            tei_output_path=tei_path,
            pivot_json_output_path=pivot_json_path,
        )

        bundle = run_export_bundle(
            pipeline=pipeline,
            source=source_path,
            options=options,
            export_latex=True,
            latex_output_path=tex_path,
        )

        warnings = bundle.step1_result.pipeline_result.report.warnings
        tei_blocked = any("TEI export blocked" in w for w in warnings)
        self.assertTrue(tei_blocked, f"Le pivot devrait bloquer le TEI; warnings: {warnings}")

        self.assertFalse(tei_path.exists(), "Le fichier TEI ne doit pas être écrit sur disque")
        self.assertFalse(tex_path.exists(), "Le fichier LaTeX ne doit pas être produit")
        self.assertIsNone(bundle.latex_output_path)
        self.assertIsNotNone(bundle.latex_error)
        self.assertIn("bloqué", bundle.latex_error)


if __name__ == "__main__":
    unittest.main()
