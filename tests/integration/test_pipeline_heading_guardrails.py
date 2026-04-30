from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.config import load_settings
from purh_editorial.model import Document, Paragraph
from purh_editorial.pipeline.step1 import Step1Options, Step1Pipeline


def _pipeline_document() -> Document:
    return Document(
        document_id="doc-pipeline-heading-guardrails",
        source_path="tests/fixtures/minimal_source.txt",
        source_format="txt",
        blocks=[
            Paragraph(
                block_id="p1",
                text="VI, I, 52",
                attributes={"all_runs_bold": True, "all_runs_italic": False},
            ),
            Paragraph(
                block_id="p2",
                text="page 305, accolade",
                attributes={"all_runs_bold": True, "all_runs_italic": False},
            ),
            Paragraph(
                block_id="p3",
                text="VIII, Pr., 18",
                attributes={"all_runs_bold": True, "all_runs_italic": False},
            ),
        ],
    )


class Step1PipelineHeadingGuardrailsTests(unittest.TestCase):
    def test_pipeline_keeps_reference_like_lines_out_of_headings(self) -> None:
        settings = load_settings()
        pipeline = Step1Pipeline(settings=settings)
        document = _pipeline_document()

        with patch("purh_editorial.pipeline.step1.ImporterRegistry.load_document", return_value=document):
            result = pipeline.run(Path("dummy.txt"), Step1Options(enable_ai=False, output_path=None))

        styled_blocks = result.pipeline_result.styled_document.blocks
        by_id = {block.block_id: block for block in styled_blocks}
        for block_id in ("p1", "p2", "p3"):
            block = by_id[block_id]
            self.assertNotEqual(block.block_type, "heading")
            self.assertNotEqual(block.attributes.get("metopes_style"), "Heading 2")


if __name__ == "__main__":
    unittest.main()

