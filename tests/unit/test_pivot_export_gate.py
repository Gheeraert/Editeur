from __future__ import annotations

import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.io.tei_xml_exporter import TEI_NS, TeiXmlExporter
from purh_editorial.model import Document, Paragraph, QuoteBlock
from purh_editorial.services.pivot_export_gate import PivotValidationError, export_tei_for_production


def _q(local_name: str) -> str:
    return f"{{{TEI_NS}}}{local_name}"


class PivotExportGateTests(unittest.TestCase):
    def test_production_gate_defaults_to_canonicalization_for_legacy_poetry(self) -> None:
        document = Document(
            document_id="doc-legacy-poetry-default-gate",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                QuoteBlock(
                    block_id="q1",
                    text="Premier vers\nDeuxieme vers",
                    attributes={
                        "quote_kind": "poetry",
                        "lineation": "verse",
                    },
                )
            ],
        )

        xml_text, diagnostics = export_tei_for_production(document)
        self.assertIsNotNone(xml_text)
        self.assertFalse(any(diag.severity == "error" for diag in diagnostics))
        root = ET.fromstring(xml_text or "")
        lines = root.findall(f".//{_q('lg')}/{_q('l')}")
        self.assertEqual([line.text for line in lines], ["Premier vers", "Deuxieme vers"])

    def test_pipeline_blocks_tei_export_on_pivot_error(self) -> None:
        document = Document(
            document_id="doc-invalid-semantic",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Paragraph(
                    block_id="p1",
                    text="Paragraphe",
                    attributes={
                        "semantic": {
                            "role": "paragraph",
                            "quote_kind": "poetry",
                            "lineation": "verse",
                            "lines": ["bad"],
                        }
                    },
                )
            ],
        )

        with self.assertRaises(PivotValidationError) as caught:
            export_tei_for_production(
                document,
                fail_on_pivot_error=True,
                run_canonicalization=False,
            )

        error = caught.exception
        self.assertEqual(error.document_id, "doc-invalid-semantic")
        rule_ids = {diag.rule_id for diag in error.diagnostics}
        self.assertIn("pivot.semantic.quote_fields_on_non_quote", rule_ids)
        self.assertIn("pivot.semantic.lines_on_non_poetry", rule_ids)

    def test_debug_tei_export_can_still_run_without_gate(self) -> None:
        document = Document(
            document_id="doc-debug-direct-export",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                Paragraph(
                    block_id="p1",
                    text="Paragraphe",
                    attributes={
                        "semantic": {
                            "role": "paragraph",
                            "quote_kind": "poetry",
                            "lineation": "verse",
                            "lines": ["bad"],
                        }
                    },
                )
            ],
        )

        xml_text = TeiXmlExporter().export_document(document)
        root = ET.fromstring(xml_text)
        self.assertEqual(root.tag, _q("TEI"))

    def test_pipeline_allows_tei_export_after_canonicalization_and_validation(self) -> None:
        document = Document(
            document_id="doc-valid-poetry",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                QuoteBlock(
                    block_id="q1",
                    text="Premier vers\nDeuxieme vers",
                    attributes={
                        "quote_kind": "poetry",
                        "lineation": "verse",
                        "protected_zone": "poetry",
                    },
                )
            ],
        )

        xml_text, diagnostics = export_tei_for_production(
            document,
            fail_on_pivot_error=True,
            run_canonicalization=True,
        )
        self.assertIsNotNone(xml_text)
        self.assertFalse(any(diag.severity == "error" for diag in diagnostics))
        root = ET.fromstring(xml_text or "")
        lines = root.findall(f".//{_q('lg')}/{_q('l')}")
        self.assertEqual([line.text for line in lines], ["Premier vers", "Deuxieme vers"])

    def test_run_without_canonicalization_is_explicit_advanced_mode(self) -> None:
        document = Document(
            document_id="doc-legacy-poetry-no-canonicalization",
            source_path="source.docx",
            source_format="docx",
            blocks=[
                QuoteBlock(
                    block_id="q1",
                    text="Premier vers\nDeuxieme vers",
                    attributes={
                        "quote_kind": "poetry",
                        "lineation": "verse",
                    },
                )
            ],
        )

        xml_text, diagnostics = export_tei_for_production(
            document,
            fail_on_pivot_error=True,
            run_canonicalization=False,
        )
        self.assertIsNotNone(xml_text)
        self.assertFalse(any(diag.severity == "error" for diag in diagnostics))
        root = ET.fromstring(xml_text or "")
        # Advanced mode assumes pre-canonicalized pivot: legacy-only poetry does
        # not become canonical verse export when canonicalization is disabled.
        self.assertEqual(len(root.findall(f".//{_q('lg')}")), 0)


if __name__ == "__main__":
    unittest.main()
