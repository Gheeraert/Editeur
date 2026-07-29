"""Diagnostic reproductible de CompareSideBySideWith, hors suite pytest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from docx import Document as DocxDocument

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from purh_editorial.services.word_review_service import (
    WordReviewService,
    _create_word_application,
    _word_constants,
    document_contains_tracked_changes,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _error(exc: Exception) -> dict[str, Any]:
    hresult = getattr(exc, "hresult", None)
    excepinfo = getattr(exc, "excepinfo", None)
    scode = None
    message = str(exc)
    if isinstance(excepinfo, tuple):
        if len(excepinfo) > 2 and excepinfo[2]:
            message = str(excepinfo[2])
        if len(excepinfo) > 5 and isinstance(excepinfo[5], int):
            scode = excepinfo[5]
    return {
        "succeeded": False,
        "return_value": None,
        "error_type": type(exc).__name__,
        "hresult": hresult if isinstance(hresult, int) else None,
        "scode": scode,
        "message": message,
        "raw_exception": repr(exc),
    }


def _operation(callback) -> dict[str, Any]:
    try:
        return {"succeeded": True, "return_value": _json_value(callback())}
    except Exception as exc:  # Diagnostics must continue after one COM failure.
        return _error(exc)


def _optional(callback) -> dict[str, Any]:
    try:
        return {"available": True, "value": _json_value(callback())}
    except Exception as exc:
        return {"available": False, "error": str(exc), "error_type": type(exc).__name__}


def _window_geometry(window: Any) -> dict[str, Any]:
    return {name.lower(): _optional(lambda name=name: getattr(window, name)) for name in ("Left", "Top", "Width", "Height")}


def _command_state(app: Any, name: str) -> dict[str, Any]:
    return {
        "enabled": _optional(lambda: app.CommandBars.GetEnabledMso(name)),
        "pressed": _optional(lambda: app.CommandBars.GetPressedMso(name)),
    }


def _document_state(app: Any, first: Any, second: Any, first_window: Any, second_window: Any) -> dict[str, Any]:
    def doc_values(document: Any) -> dict[str, Any]:
        return {
            "name": _optional(lambda: document.Name),
            "full_name": _optional(lambda: document.FullName),
            "read_only": _optional(lambda: bool(document.ReadOnly)),
            "revisions_count": _optional(lambda: document.Revisions.Count),
            "windows_count": _optional(lambda: document.Windows.Count),
            "protection_type": _optional(lambda: document.ProtectionType),
            "saved": _optional(lambda: document.Saved),
            "compatibility_mode": _optional(lambda: document.CompatibilityMode),
        }
    return {
        "first_document": doc_values(first),
        "second_document": doc_values(second),
        "application_documents_count": _optional(lambda: app.Documents.Count),
        "application_windows_count": _optional(lambda: app.Windows.Count),
        "first_window_caption": _optional(lambda: first_window.Caption),
        "second_window_caption": _optional(lambda: second_window.Caption),
        "active_document_name": _optional(lambda: app.ActiveDocument.Name),
        "active_window_caption": _optional(lambda: app.ActiveWindow.Caption),
        "second_show_source_documents": _optional(lambda: second_window.ShowSourceDocuments),
        "commands": {
            "ViewSideBySide": _command_state(app, "ViewSideBySide"),
            "SynchronousScrolling": _command_state(app, "SynchronousScrolling"),
        },
    }


def _close(document: Any, cleanup: list[dict[str, Any]], label: str) -> None:
    if document is None:
        return
    outcome = _operation(lambda: document.Close(SaveChanges=False))
    outcome["target"] = label
    cleanup.append(outcome)


def _run_scenario(spec: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    import pythoncom

    pythoncom.CoInitialize()
    app = first = second = first_window = second_window = None
    result: dict[str, Any] = {"id": spec["id"], "name": spec["name"], "cleanup": []}
    try:
        app = _create_word_application()
        app.Visible = True
        result["word_version"] = _optional(lambda: app.Version)
        result["word_build"] = _optional(lambda: app.Build)
        result["word_product_code"] = _optional(
            lambda: app.ProductCode() if callable(app.ProductCode) else app.ProductCode
        )
        constants = _word_constants(app)
        if spec["blank"]:
            first = app.Documents.Add()
            second = app.Documents.Add()
            first.Content.Text = "Premier document vierge."
            second.Content.Text = "Second document vierge."
        else:
            first = app.Documents.Open(
                FileName=str(paths[spec["first"]]), ReadOnly=spec["first_read_only"],
                AddToRecentFiles=False, Visible=True,
            )
            second = app.Documents.Open(
                FileName=str(paths[spec["second"]]), ReadOnly=False,
                AddToRecentFiles=False, Visible=True,
            )
        time.sleep(0.5)
        first_window = first.Windows(1)
        second_window = second.Windows(1)
        second.Activate()
        second_window.Activate()
        pythoncom.PumpWaitingMessages()
        time.sleep(0.5)
        result["before"] = _document_state(app, first, second, first_window, second_window)
        if spec.get("hide_sources"):
            result["show_source_documents_before"] = _optional(lambda: second_window.ShowSourceDocuments)
            if hasattr(constants, "wdShowSourceDocumentsNone"):
                result["show_source_documents_set"] = _operation(
                    lambda: setattr(second_window, "ShowSourceDocuments", constants.wdShowSourceDocumentsNone)
                )
            else:
                result["show_source_documents_set"] = {"succeeded": False, "message": "Constante indisponible"}
            result["show_source_documents_after"] = _optional(lambda: second_window.ShowSourceDocuments)
        result["compare"] = _operation(lambda: second.Windows.CompareSideBySideWith(first))
        pythoncom.PumpWaitingMessages(); time.sleep(0.3)
        result["reset_positions"] = _operation(lambda: app.Windows.ResetPositionsSideBySide())
        result["sync_set"] = _operation(lambda: setattr(app.Windows, "SyncScrollingSideBySide", True))
        result["sync_read"] = _operation(lambda: app.Windows.SyncScrollingSideBySide)
        result["after"] = _document_state(app, first, second, first_window, second_window)
        result["geometry"] = {"first": _window_geometry(first_window), "second": _window_geometry(second_window)}
    except Exception as exc:
        result["scenario_error"] = _error(exc)
    finally:
        _close(second, result["cleanup"], "second_document")
        second = None
        _close(first, result["cleanup"], "first_document")
        first = None
        if app is not None:
            outcome = _operation(app.Quit); outcome["target"] = "application"; result["cleanup"].append(outcome)
        app = None
        try:
            pythoncom.PumpWaitingMessages()
        except Exception as exc:
            result["cleanup"].append(_error(exc))
        pythoncom.CoUninitialize()
    return result


def _conclusion(scenarios: list[dict[str, Any]]) -> str:
    succeeded = {item["id"] for item in scenarios if item.get("compare", {}).get("succeeded")}
    if 0 not in succeeded:
        return "L’échec ne dépend ni des fichiers, ni de la lecture seule, ni du document de révision : il concerne l’API Word ou cette installation."
    if {0, 1}.issubset(succeeded) and 2 not in succeeded:
        return "La lecture seule du premier document bloque CompareSideBySideWith."
    if {0, 1, 2}.issubset(succeeded) and not ({3, 4} & succeeded):
        return "Le document de révision contenant les résultats de CompareDocuments déclenche l’échec."
    if 4 not in succeeded and 5 in succeeded:
        return "L’affichage des documents sources de comparaison entre en conflit avec le mode côte à côte."
    if len(succeeded) == 6:
        return "Tous les scénarios isolés réussissent : le défaut vient probablement de la séquence du workspace."
    if 0 in succeeded and 1 not in succeeded:
        return "Les documents créés directement par Word réussissent, mais les DOCX ouverts depuis le disque échouent déjà : la lecture seule et le document de révision ne sont pas la cause isolée."
    return "La matrice ne permet pas encore d’isoler une cause unique."


def _create_documents(root: Path) -> dict[str, Path]:
    paths = {name: root / f"{name}.docx" for name in ("ordinary_a", "ordinary_b", "original", "candidate", "review")}
    for name, paragraphs in {
        "ordinary_a": ("Premier document ordinaire.", "Deuxième paragraphe."),
        "ordinary_b": ("Second document ordinaire.", "Deuxième paragraphe."),
        "original": ("Le XVIIème siècle.", "Ce passage doit être vérifié."),
        "candidate": ("Le XVIIe siècle.", "Ce passage doit être vérifié."),
    }.items():
        document = DocxDocument()
        for paragraph in paragraphs:
            document.add_paragraph(paragraph)
        document.save(paths[name])
    WordReviewService().create_review_document(original_path=paths["original"], revised_path=paths["candidate"], output_path=paths["review"])
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("word_side_by_side_diagnostic.json"))
    args = parser.parse_args()
    if sys.platform != "win32":
        print("Ce diagnostic requiert Windows et Microsoft Word.", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix="purh-word-sxs-") as temp:
        root = Path(temp)
        paths = _create_documents(root)
        hashes_before = {path.name: _sha256(path) for path in paths.values()}
        scenarios = [
            {"id": 0, "name": "blank_writable_documents", "blank": True},
            {"id": 1, "name": "ordinary_writable_documents", "first": "ordinary_a", "second": "ordinary_b", "first_read_only": False, "blank": False},
            {"id": 2, "name": "ordinary_first_read_only", "first": "ordinary_a", "second": "ordinary_b", "first_read_only": True, "blank": False},
            {"id": 3, "name": "review_with_writable_original", "first": "original", "second": "review", "first_read_only": False, "blank": False},
            {"id": 4, "name": "review_with_read_only_original", "first": "original", "second": "review", "first_read_only": True, "blank": False},
            {"id": 5, "name": "review_read_only_original_hide_sources", "first": "original", "second": "review", "first_read_only": True, "hide_sources": True, "blank": False},
        ]
        result = {
            "environment": {"platform": platform.platform(), "python_version": sys.version},
            "review_has_tracked_changes": document_contains_tracked_changes(paths["review"]),
            "scenarios": [_run_scenario(item, paths) for item in scenarios],
        }
        hashes_after = {path.name: _sha256(path) for path in paths.values()}
        first_scenario = result["scenarios"][0]
        result["environment"].update({
            "word_version": first_scenario.get("word_version"),
            "word_build": first_scenario.get("word_build"),
            "word_product_code": first_scenario.get("word_product_code"),
        })
        result["file_integrity"] = {name: {"before": before, "after": hashes_after[name], "unchanged": before == hashes_after[name]} for name, before in hashes_before.items()}
        result["conclusion"] = _conclusion(result["scenarios"])
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in result["scenarios"]:
        compare = item.get("compare", item.get("scenario_error", {}))
        print(f"{item['id']} {item['name']}: {compare.get('succeeded')} {compare.get('message', compare.get('return_value', ''))}")
    print(result["conclusion"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
