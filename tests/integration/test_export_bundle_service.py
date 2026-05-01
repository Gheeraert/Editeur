from __future__ import annotations

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


class ExportBundleServiceTests(unittest.TestCase):
    def test_export_bundle_writes_xml_and_latex(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        source = ROOT / "tests" / "fixtures" / "minimal_source.txt"
        output_dir = ROOT / "tests" / "_runtime" / f"bundle_{uuid.uuid4().hex}"
        output_dir.mkdir(parents=True, exist_ok=True)

        docx_path, tei_path, tex_path = build_output_paths(source, output_dir, "minimal_source")
        options = Step1Options(
            enable_ai=False,
            output_path=docx_path,
            tei_output_path=tei_path,
        )

        bundle = run_export_bundle(
            pipeline=pipeline,
            source=source,
            options=options,
            export_latex=True,
            latex_output_path=tex_path,
        )

        self.assertTrue(docx_path.exists())
        self.assertTrue(tei_path.exists())
        self.assertIsNone(bundle.latex_error)
        self.assertIsNotNone(bundle.latex_output_path)
        self.assertTrue(tex_path.exists())


if __name__ == "__main__":
    unittest.main()
