from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.model import Diagnostic, Document, Evidence, ModuleRun, Paragraph, PipelineResult, ProcessingReport
from purh_editorial.pipeline.step1 import Step1Result
from purh_editorial.ui.step1_dialog import (
    build_json_output_path,
    build_completion_message,
    build_result_text,
    extract_output_paths,
    format_diagnostics,
    format_module_runs,
    format_outputs,
    format_warnings,
    output_folders_to_open,
)


class Step1DialogFormattingTests(unittest.TestCase):
    def test_step1_dialog_source_has_no_mojibake_markers(self) -> None:
        source = (ROOT / "src" / "purh_editorial" / "ui" / "step1_dialog.py").read_text(encoding="utf-8")
        for marker in ("Ã", "â€”", "â”", "Ã©", "Ã¨", "Ãª", "Ã ", "Â"):
            self.assertNotIn(marker, source)
        self.assertIn("Exporter le DOCX corrigé", source)
        self.assertIn("Mode de décision", source)
        self.assertIn("Agressivité", source)
        self.assertIn("Modèle", source)
        self.assertIn("Analyse terminée", source)
        self.assertIn("par défaut", source)

    def _build_result(self) -> Step1Result:
        doc = Document(
            document_id="doc-ui",
            source_path="tests/fixtures/minimal_source.txt",
            source_format="txt",
            blocks=[Paragraph(block_id="p1", text="Texte")],
        )
        report = ProcessingReport(report_id="r1", document_id="doc-ui")
        report.transformations = []
        report.diagnostics = [
            Diagnostic(
                diagnostic_id="d1",
                module="footnote_normalizer",
                severity="warning",
                category="footnote_call_placement",
                message="Diagnostic test.",
                target_ref="p1",
                evidence=Evidence(excerpt="mot.1"),
                rule_id="R-AN-002",
            )
        ]
        report.warnings = ["TEI export skipped: test warning"]
        report.module_runs = [
            ModuleRun(
                module_name="orthotypo",
                version="2.0.0",
                started_at="2026-01-01T00:00:00+00:00",
                finished_at="2026-01-01T00:00:01+00:00",
                summary={"corrections": 3},
            )
        ]
        pipeline_result = PipelineResult(
            source_document=doc,
            styled_document=doc,
            report=report,
            tei_xml="<TEI/>",
        )
        return Step1Result(pipeline_result=pipeline_result, output_docx=Path("out.docx"))

    def _build_result_with_outputs(self, docx: Path | None, tei: Path | None) -> Step1Result:
        result = self._build_result()
        result.output_docx = docx
        if tei is not None:
            result.pipeline_result.report.module_runs.append(
                ModuleRun(
                    module_name="tei_xml_write",
                    version="2.0.0",
                    started_at="2026-01-01T00:00:02+00:00",
                    finished_at="2026-01-01T00:00:03+00:00",
                    summary={"output": str(tei)},
                )
            )
        return result

    def _build_result_with_outputs_and_json(
        self,
        docx: Path | None,
        tei: Path | None,
        pivot_json: Path | None,
    ) -> Step1Result:
        result = self._build_result_with_outputs(docx, tei)
        if pivot_json is not None:
            result.pipeline_result.report.module_runs.append(
                ModuleRun(
                    module_name="pivot_json_write",
                    version="2.0.0",
                    started_at="2026-01-01T00:00:04+00:00",
                    finished_at="2026-01-01T00:00:05+00:00",
                    summary={"output": str(pivot_json)},
                )
            )
        return result

    def test_format_diagnostics_includes_expected_fields(self) -> None:
        result = self._build_result()
        text = format_diagnostics(result.pipeline_result.report.diagnostics)
        self.assertIn("rule_id=R-AN-002", text)
        self.assertIn("severity=warning", text)
        self.assertIn("category=footnote_call_placement", text)
        self.assertIn("message=Diagnostic test.", text)
        self.assertIn("excerpt=mot.1", text)
        self.assertIn("target_ref=p1", text)

    def test_format_warnings_and_module_runs(self) -> None:
        result = self._build_result()
        warnings_text = format_warnings(result.pipeline_result.report.warnings)
        modules_text = format_module_runs(result.pipeline_result.report.module_runs)
        self.assertIn("TEI export skipped: test warning", warnings_text)
        self.assertIn("orthotypo", modules_text)
        self.assertIn("status=success", modules_text)

    def test_format_outputs_and_full_report(self) -> None:
        result = self._build_result()
        outputs_text = format_outputs(result)
        report_text = build_result_text(result)
        self.assertIn("DOCX de relecture", outputs_text)
        self.assertIn("XML-TEI", outputs_text)
        self.assertIn("Corrections appliquees", report_text)
        self.assertIn("Diagnostics a verifier", report_text)
        self.assertIn("Warnings techniques", report_text)
        self.assertIn("Resume modules", report_text)

    def test_empty_collections_have_safe_messages(self) -> None:
        self.assertEqual(format_diagnostics([]), "Aucun diagnostic.")
        self.assertEqual(format_warnings([]), "Aucun warning.")
        self.assertEqual(format_module_runs([]), "Aucun module execute.")

    def test_output_folders_no_file_outputs(self) -> None:
        result = self._build_result_with_outputs(None, None)
        self.assertEqual(output_folders_to_open(result), [])

    def test_output_folders_docx_only(self) -> None:
        result = self._build_result_with_outputs(Path("C:/out/relecture.docx"), None)
        self.assertEqual(output_folders_to_open(result), [Path("C:/out")])

    def test_output_folders_xml_only(self) -> None:
        result = self._build_result_with_outputs(None, Path("C:/tei/sortie.xml"))
        self.assertEqual(output_folders_to_open(result), [Path("C:/tei")])

    def test_output_folders_deduplicate_same_folder(self) -> None:
        result = self._build_result_with_outputs(Path("C:/out/relecture.docx"), Path("C:/out/sortie.xml"))
        self.assertEqual(output_folders_to_open(result), [Path("C:/out")])

    def test_output_folders_stable_order_docx_then_xml(self) -> None:
        result = self._build_result_with_outputs(Path("C:/out/relecture.docx"), Path("C:/tei/sortie.xml"))
        self.assertEqual(output_folders_to_open(result), [Path("C:/out"), Path("C:/tei")])

    def test_extract_output_paths(self) -> None:
        result = self._build_result_with_outputs_and_json(
            Path("C:/out/relecture.docx"),
            Path("C:/tei/sortie.xml"),
            Path("C:/json/pivot.json"),
        )
        docx_path, tei_path, json_path = extract_output_paths(result)
        self.assertEqual(docx_path, Path("C:/out/relecture.docx"))
        self.assertEqual(tei_path, Path("C:/tei/sortie.xml"))
        self.assertEqual(json_path, Path("C:/json/pivot.json"))

    def test_extract_output_paths_returns_docx_tei_json(self) -> None:
        result = self._build_result_with_outputs_and_json(
            Path("C:/out/relecture.docx"),
            Path("C:/tei/sortie.xml"),
            Path("C:/json/pivot.json"),
        )
        docx_path, tei_path, json_path = extract_output_paths(result)
        self.assertEqual(docx_path, Path("C:/out/relecture.docx"))
        self.assertEqual(tei_path, Path("C:/tei/sortie.xml"))
        self.assertEqual(json_path, Path("C:/json/pivot.json"))

    def test_format_outputs_has_clean_french_strings(self) -> None:
        result = self._build_result_with_outputs(None, None)
        output = format_outputs(result)
        self.assertIn("non demandée", output)
        self.assertIn("non produit", output)
        result_in_memory = self._build_result_with_outputs(Path("C:/out/relecture.docx"), None)
        output_in_memory = format_outputs(result_in_memory)
        self.assertIn("généré en mémoire", output_in_memory)
        self.assertIn("pas de fichier écrit", output_in_memory)

    def test_build_completion_message_contains_summary_fields(self) -> None:
        result = self._build_result_with_outputs(Path("C:/out/relecture.docx"), None)
        message = build_completion_message(result)
        self.assertIn("Analyse terminée.", message)
        self.assertIn("Transformations:", message)
        self.assertIn("Diagnostics:", message)
        self.assertIn("Warnings:", message)
        self.assertIn("DOCX:", message)
        self.assertIn("XML-TEI:", message)
        self.assertIn("JSON pivot:", message)

    def test_build_json_output_path_suffix(self) -> None:
        source = Path("Mon fichier.docx")
        output_dir = Path("out")
        path = build_json_output_path(source, output_dir, "base")
        self.assertTrue(str(path).endswith("base_pivot.json"))


if __name__ == "__main__":
    unittest.main()
