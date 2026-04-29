from __future__ import annotations

import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.config import load_settings
from purh_editorial.pipeline.step1 import Step1Options, Step1Pipeline

TEI_NS = "http://www.tei-c.org/ns/1.0"


class Step1PipelineTeiExportTests(unittest.TestCase):
    def test_pipeline_exposes_well_formed_tei_xml(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        source_path = ROOT / "tests" / "fixtures" / "minimal_source.txt"

        result = pipeline.run(source_path, Step1Options(enable_ai=False, output_path=None))
        tei_xml = result.pipeline_result.tei_xml

        self.assertIsNotNone(tei_xml)
        root = ET.fromstring(tei_xml)
        self.assertEqual(root.tag, f"{{{TEI_NS}}}TEI")
        body = root.find(f"./{{{TEI_NS}}}text/{{{TEI_NS}}}body")
        self.assertIsNotNone(body)


if __name__ == "__main__":
    unittest.main()

