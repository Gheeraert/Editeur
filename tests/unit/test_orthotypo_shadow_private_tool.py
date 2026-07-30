from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

from docx import Document as WordDocument

from purh_editorial.io.importer_registry import ImporterRegistry
from purh_editorial.rules.shadow import ShadowComparisonStatus


ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "tools/evaluate_orthotypo_shadow_private.py"
NNBSP = "\u202f"


def _load_tool():
    module_name = "evaluate_orthotypo_shadow_private_test_module"
    spec = importlib.util.spec_from_file_location(module_name, TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    document = WordDocument()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    document.save(path)


def _private_paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    private_root = tmp_path / "private_corpus_a"
    raw_dir = private_root / "sources/manuscripts_raw"
    reference_dir = private_root / "sources/edited_references"
    output_dir = private_root / "private_reports/orthotypo_shadow_4g"
    raw_dir.mkdir(parents=True)
    reference_dir.mkdir(parents=True)
    return private_root, raw_dir, reference_dir, output_dir


def test_tool_writes_private_reports_from_synthetic_docx(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    tool = _load_tool()
    private_root, raw_dir, reference_dir, output_dir = _private_paths(tmp_path)
    raw_path = raw_dir / "author-001.docx"
    reference_path = reference_dir / "reference-001.docx"
    _write_docx(
        raw_path,
        [
            "Il écrit etc... dans une phrase.",
            "Voir pp. 12-14.",
        ],
    )
    _write_docx(
        reference_path,
        [
            "Il écrit etc. dans une phrase.",
            f"Voir p.{NNBSP}12-14.",
        ],
    )
    monkeypatch.setenv("PURH_PRIVATE_CORPUS_DIR", str(private_root))

    real_registry = ImporterRegistry()
    imported: list[tuple[object, object]] = []
    calls: list[Path] = []

    class RecordingRegistry:
        def load_document(self, path: Path):
            document = real_registry.load_document(path)
            calls.append(path)
            imported.append((document, copy.deepcopy(document)))
            return document

    monkeypatch.setattr(tool, "ImporterRegistry", lambda: RecordingRegistry())
    exit_code = tool.main(
        [
            "--raw-docx",
            str(raw_path),
            "--reference-dir",
            str(reference_dir),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert calls == [raw_path, reference_path]
    assert all(document == snapshot for document, snapshot in imported)
    json_path = output_dir / "orthotypo_shadow_4g.json"
    markdown_path = output_dir / "orthotypo_shadow_4g.md"
    assert json_path.is_file()
    assert markdown_path.is_file()

    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == 1
    assert report["scope"] == {
        "rules": [
            "purh.abreviations.etc",
            "purh.abreviations.redoublement",
        ],
        "author_documents": 1,
        "edited_reference_documents": 1,
    }
    assert (
        report["aggregate"]["author"]["purh.abreviations.etc"]
        ["native_actions_proposed"]
        == 1
    )
    assert (
        report["aggregate"]["author"]["purh.abreviations.redoublement"]
        ["native_actions_proposed"]
        == 1
    )
    assert (
        report["aggregate"]["edited_reference"]["purh.abreviations.etc"]
        ["native_actions_proposed"]
        == 0
    )
    assert (
        report["aggregate"]["edited_reference"]
        ["purh.abreviations.redoublement"]["native_actions_proposed"]
        == 0
    )
    for corpus in ("author", "edited_reference"):
        for rule in report["aggregate"][corpus].values():
            assert rule["comparison_statuses"] == {
                ShadowComparisonStatus.MATCH.value: rule["comparisons"],
                ShadowComparisonStatus.DIVERGENCE.value: 0,
                ShadowComparisonStatus.INCONCLUSIVE.value: 0,
            }
    occurrences = [
        occurrence
        for document in report["documents"]
        for occurrence in document["occurrences"]
    ]
    assert occurrences
    assert occurrences[0]["actions_native"][0]["offset_start"] is not None
    assert occurrences[0]["actions_native"][0]["context_excerpt"]
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Cette comparaison de corpus n’aligne pas automatiquement" in markdown
    assert "## Divergences" in markdown
    captured = capsys.readouterr()
    assert raw_path.name not in captured.out
    assert reference_path.name not in captured.out


def test_tool_reports_residual_reference_without_normative_conclusion(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool = _load_tool()
    private_root, raw_dir, reference_dir, output_dir = _private_paths(tmp_path)
    raw_path = raw_dir / "author-001.docx"
    reference_path = reference_dir / "reference-001.docx"
    _write_docx(raw_path, ["Texte sans motif."])
    _write_docx(reference_path, ["Voir pp. 12-14."])
    monkeypatch.setenv("PURH_PRIVATE_CORPUS_DIR", str(private_root))

    report, _json_path, _markdown_path = tool.evaluate_corpus(
        raw_docx=raw_path,
        reference_dir=reference_dir,
        output_dir=output_dir,
    )

    rule_id = "purh.abreviations.redoublement"
    assert (
        report["aggregate"]["edited_reference"][rule_id]
        ["native_actions_proposed"]
        == 1
    )
    assert (
        report["editorial_contrast"][rule_id]
        ["edited_reference_documents_with_proposals"]
        == 1
    )
    assert set(report["editorial_contrast"][rule_id]) == {
        "author_proposed_actions",
        "author_apply_decisions",
        "author_protected_proposals",
        "edited_reference_proposed_actions",
        "edited_reference_apply_decisions",
        "edited_reference_protected_proposals",
        "edited_reference_documents_with_proposals",
    }


def test_tool_rejects_invalid_private_inputs(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    tool = _load_tool()
    private_root, raw_dir, reference_dir, output_dir = _private_paths(tmp_path)
    raw_path = raw_dir / "author-001.docx"
    _write_docx(raw_path, ["Texte."])
    monkeypatch.setenv("PURH_PRIVATE_CORPUS_DIR", str(private_root))

    assert tool.main(
        [
            "--raw-docx",
            str(raw_dir / "missing.docx"),
            "--reference-dir",
            str(reference_dir),
            "--output-dir",
            str(output_dir),
        ]
    ) == 2
    wrong_suffix = raw_dir / "author-001.txt"
    wrong_suffix.write_text("synthetic", encoding="utf-8")
    assert tool.main(
        [
            "--raw-docx",
            str(wrong_suffix),
            "--reference-dir",
            str(reference_dir),
            "--output-dir",
            str(output_dir),
        ]
    ) == 2
    assert tool.main(
        [
            "--raw-docx",
            str(raw_path),
            "--reference-dir",
            str(reference_dir),
            "--output-dir",
            str(output_dir),
        ]
    ) == 2
    _write_docx(reference_dir / "reference-001.docx", ["Texte."])
    assert tool.main(
        [
            "--raw-docx",
            str(raw_path),
            "--reference-dir",
            str(reference_dir),
            "--output-dir",
            str(ROOT / "private_reports"),
        ]
    ) == 2
    monkeypatch.delenv("PURH_PRIVATE_CORPUS_DIR")
    assert tool.main(
        [
            "--raw-docx",
            str(raw_path),
            "--reference-dir",
            str(reference_dir),
            "--output-dir",
            str(output_dir),
        ]
    ) == 2
    assert "Évaluation impossible" in capsys.readouterr().err
