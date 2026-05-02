# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from purh_editorial.config import AppSettings
from purh_editorial.latex.latex_exporter import export_tei_to_latex
from purh_editorial.model import Diagnostic, ModuleRun
from purh_editorial.pipeline.step1 import Step1Options, Step1Pipeline, Step1Result


DISCLAIMER_TEXT = (
    "Cette interface ne propose pas encore de diff complet avant/apres. "
    "Les diagnostics signalent des points a verifier et ne sont pas des corrections automatiques."
)


@dataclass(slots=True)
class ExportRunResult:
    step1_result: Step1Result
    latex_output_path: Path | None = None
    latex_error: str | None = None


CONFIG_VERSION = 1

ALLOWED_DECISION_MODES = {
    "deterministic",
    "heuristic",
    "heuristic_ai_local",
    "ai_exploratory",
}
ALLOWED_AI_AGGRESSIVENESS = {"conservative", "balanced", "aggressive"}
ALLOWED_HEURISTIC_PROFILES = {"conservative", "balanced", "exploratory"}
ALLOWED_PROVIDERS = {"groq", "anthropic"}

DECISION_MODE_LABELS = {
    "deterministic": "Déterministe strict",
    "heuristic": "Heuristique",
    "heuristic_ai_local": "Heuristique + IA locale",
    "ai_exploratory": "IA exploratoire future",
}
HEURISTIC_PROFILE_LABELS = {
    "conservative": "Prudent",
    "balanced": "Équilibré",
    "exploratory": "Exploratoire",
}
AI_AGGRESSIVENESS_LABELS = {
    "conservative": "Conservatrice",
    "balanced": "Équilibrée",
    "aggressive": "Agressive",
}
PROVIDER_LABELS = {
    "groq": "Groq (llama, OpenAI-compatible)",
    "anthropic": "Anthropic (Claude)",
}
PROVIDER_DEFAULTS = {
    "groq": {
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
    },
    "anthropic": {
        "model": "claude-haiku-4-5-20251001",
        "base_url": "https://api.anthropic.com/v1",
    },
}


# ── Fonctions de normalisation ────────────────────────────────────────────────

def _label_key(value: str | None) -> str:
    """Normalize UI labels for accent- and case-insensitive comparisons."""
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.casefold()


def normalize_decision_mode(value: str | None) -> str:
    if not value:
        return "heuristic"
    mode = str(value).strip().lower()
    if mode in ALLOWED_DECISION_MODES:
        return mode
    return "heuristic"


def decision_mode_to_label(value: str | None) -> str:
    return DECISION_MODE_LABELS[normalize_decision_mode(value)]


def decision_mode_from_label(label: str | None) -> str:
    raw = str(label or "").strip()
    raw_key = _label_key(raw)
    for code, text in DECISION_MODE_LABELS.items():
        if _label_key(text) == raw_key:
            return code
    return normalize_decision_mode(raw)


def normalize_ai_aggressiveness(value: str | None) -> str:
    if not value:
        return "conservative"
    mode = str(value).strip().lower()
    if mode in ALLOWED_AI_AGGRESSIVENESS:
        return mode
    return "conservative"


def ai_aggressiveness_to_label(value: str | None) -> str:
    return AI_AGGRESSIVENESS_LABELS[normalize_ai_aggressiveness(value)]


def ai_aggressiveness_from_label(label: str | None) -> str:
    raw = str(label or "").strip()
    raw_key = _label_key(raw)
    for code, text in AI_AGGRESSIVENESS_LABELS.items():
        if _label_key(text) == raw_key:
            return code
    return normalize_ai_aggressiveness(raw)


def normalize_heuristic_profile(value: str | None) -> str:
    if not value:
        return "conservative"
    profile = str(value).strip().lower()
    if profile in ALLOWED_HEURISTIC_PROFILES:
        return profile
    return "conservative"


def heuristic_profile_to_label(value: str | None) -> str:
    return HEURISTIC_PROFILE_LABELS[normalize_heuristic_profile(value)]


def heuristic_profile_from_label(label: str | None) -> str:
    raw = str(label or "").strip()
    raw_key = _label_key(raw)
    for code, text in HEURISTIC_PROFILE_LABELS.items():
        if _label_key(text) == raw_key:
            return code
    return normalize_heuristic_profile(raw)


def normalize_provider(value: str | None) -> str:
    if not value:
        return "groq"
    v = str(value).strip().lower()
    return v if v in ALLOWED_PROVIDERS else "groq"


def provider_to_label(value: str | None) -> str:
    return PROVIDER_LABELS.get(normalize_provider(value), PROVIDER_LABELS["groq"])


def provider_from_label(label: str | None) -> str:
    raw = str(label or "").strip()
    raw_key = _label_key(raw)
    for code, text in PROVIDER_LABELS.items():
        if _label_key(text) == raw_key:
            return code
    return normalize_provider(raw)


def normalize_optional_threshold(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, numeric))


def derive_ai_flags_from_decision_mode(decision_mode: str) -> tuple[bool, bool]:
    mode = normalize_decision_mode(decision_mode)
    if mode == "heuristic_ai_local":
        return True, False
    return False, False


# ── Construction des options Step1 ────────────────────────────────────────────

def build_step1_options_from_form(
    *,
    decision_mode_label: str,
    heuristic_profile_label: str,
    heading_transform_threshold: object,
    heading_diagnostic_threshold: object,
    poetry_transform_threshold: object,
    poetry_diagnostic_threshold: object,
    ai_aggressiveness_label: str,
    # IA structurelle (nouveaux noms)
    struct_ai_provider: str = "",
    struct_ai_api_key: str = "",
    struct_ai_model: str = "",
    struct_ai_base_url: str = "",
    max_structure_ai_calls: int = 6,
    # IA structurelle (anciens noms — rétrocompatibilité)
    ai_provider: str = "",
    ai_api_key: str = "",
    ai_model: str = "",
    ai_base_url: str = "",
    # IA éditoriale
    enable_editorial_ai: bool = False,
    editorial_ai_provider: str = "",
    editorial_ai_api_key: str = "",
    editorial_ai_model: str = "",
    editorial_ai_base_url: str = "",
    max_ai_calls: int = 6,
    # Sorties
    output_path: Path | None = None,
    tei_output_path: Path | None = None,
) -> Step1Options:
    decision_mode = decision_mode_from_label(decision_mode_label)
    heuristic_profile = heuristic_profile_from_label(heuristic_profile_label)
    ai_aggressiveness = ai_aggressiveness_from_label(ai_aggressiveness_label)
    enable_structure_ai, _ = derive_ai_flags_from_decision_mode(decision_mode)

    # Résolution : nouveaux noms > anciens noms
    actual_struct_provider = str(struct_ai_provider or ai_provider or "groq").strip() or "groq"
    actual_struct_key = str(struct_ai_api_key or ai_api_key or "").strip() or None
    actual_struct_model = str(struct_ai_model or ai_model or "").strip() or None
    actual_struct_base_url = str(struct_ai_base_url or ai_base_url or "").strip() or None

    edi_provider = str(editorial_ai_provider or "").strip()
    edi_key = str(editorial_ai_api_key or "").strip() or None
    edi_model = str(editorial_ai_model or "").strip() or None
    edi_base_url = str(editorial_ai_base_url or "").strip() or None

    return Step1Options(
        enable_ai=False,
        enable_structure_ai=enable_structure_ai,
        enable_editorial_ai=bool(enable_editorial_ai),
        decision_mode=decision_mode,
        heuristic_profile=heuristic_profile,
        heading_transform_threshold=normalize_optional_threshold(heading_transform_threshold),
        heading_diagnostic_threshold=normalize_optional_threshold(heading_diagnostic_threshold),
        poetry_transform_threshold=normalize_optional_threshold(poetry_transform_threshold),
        poetry_diagnostic_threshold=normalize_optional_threshold(poetry_diagnostic_threshold),
        ai_aggressiveness=ai_aggressiveness,
        ai_provider=actual_struct_provider,
        ai_api_key=actual_struct_key,
        ai_model=actual_struct_model,
        ai_base_url=actual_struct_base_url,
        max_structure_ai_calls=max(1, int(max_structure_ai_calls)),
        editorial_ai_provider=edi_provider,
        editorial_ai_api_key=edi_key,
        editorial_ai_model=edi_model,
        editorial_ai_base_url=edi_base_url,
        max_ai_calls=max(1, int(max_ai_calls)),
        output_path=output_path,
        tei_output_path=tei_output_path,
    )


# ── Fonctions config dict ─────────────────────────────────────────────────────

def build_config_dict(
    source_path: str = "",
    output_docx_path: str = "",
    tei_output_path: str = "",
    decision_mode: str = "heuristic",
    heuristic_profile: str = "conservative",
    heading_transform_threshold: float | None = None,
    heading_diagnostic_threshold: float | None = None,
    poetry_transform_threshold: float | None = None,
    poetry_diagnostic_threshold: float | None = None,
    ai_aggressiveness: str = "conservative",
    ai_provider: str = "",
    ai_api_key: str = "",
    ai_model: str = "",
    ai_base_url: str = "",
    enable_structure_ai: bool = False,
    enable_editorial_ai: bool = False,
    enable_ai: bool = False,
    max_ai_calls: int = 6,
    max_structure_ai_calls: int = 6,
    *,
    output_dir: str = "",
    base_name: str = "",
    export_docx: bool = True,
    export_tei: bool = True,
    export_latex: bool = True,
    # IA structurelle (nouveaux noms)
    struct_ai_provider: str = "",
    struct_ai_api_key: str = "",
    struct_ai_model: str = "",
    struct_ai_base_url: str = "",
    # IA éditoriale dédiée
    editorial_ai_provider: str = "",
    editorial_ai_api_key: str = "",
    editorial_ai_model: str = "",
    editorial_ai_base_url: str = "",
) -> dict[str, object]:
    """Build a Step 1 dialog config while preserving v1 positional compatibility.

    Older tests and saved-call sites used positional arguments up to
    ``max_structure_ai_calls``. New v2-like fields are intentionally
    keyword-only so they cannot shift legacy values.
    """
    actual_struct_provider = normalize_provider(struct_ai_provider or ai_provider or "groq")
    actual_struct_api_key = str(struct_ai_api_key or ai_api_key or "")
    actual_struct_model = str(struct_ai_model or ai_model or "")
    actual_struct_base_url = str(struct_ai_base_url or ai_base_url or "")
    return {
        "version": CONFIG_VERSION,
        "source_path": source_path,
        "output_dir": output_dir,
        "base_name": base_name,
        "export_docx": bool(export_docx),
        "export_tei": bool(export_tei),
        "export_latex": bool(export_latex),
        "output_docx_path": output_docx_path,
        "tei_output_path": tei_output_path,
        "decision_mode": normalize_decision_mode(decision_mode),
        "heuristic_profile": normalize_heuristic_profile(heuristic_profile),
        "heading_transform_threshold": normalize_optional_threshold(heading_transform_threshold),
        "heading_diagnostic_threshold": normalize_optional_threshold(heading_diagnostic_threshold),
        "poetry_transform_threshold": normalize_optional_threshold(poetry_transform_threshold),
        "poetry_diagnostic_threshold": normalize_optional_threshold(poetry_diagnostic_threshold),
        "ai_aggressiveness": normalize_ai_aggressiveness(ai_aggressiveness),
        # Structurelle (noms dédiés + miroir legacy)
        "struct_ai_provider": actual_struct_provider,
        "struct_ai_api_key": actual_struct_api_key,
        "struct_ai_model": actual_struct_model,
        "struct_ai_base_url": actual_struct_base_url,
        "max_structure_ai_calls": max(1, int(max_structure_ai_calls)),
        # Éditoriale
        "enable_editorial_ai": bool(enable_editorial_ai),
        "editorial_ai_provider": str(editorial_ai_provider or ""),
        "editorial_ai_api_key": str(editorial_ai_api_key or ""),
        "editorial_ai_model": str(editorial_ai_model or ""),
        "editorial_ai_base_url": str(editorial_ai_base_url or ""),
        "max_ai_calls": max(1, int(max_ai_calls)),
        # Legacy v1 — conservé pour compatibilité config/tests
        "enable_structure_ai": bool(enable_structure_ai),
        "enable_ai": bool(enable_ai),
        "ai_provider": actual_struct_provider,
        "ai_api_key": actual_struct_api_key,
        "ai_model": actual_struct_model,
        "ai_base_url": actual_struct_base_url,
    }


def apply_config_dict(
    current: dict[str, object],
    loaded: dict[str, object],
) -> dict[str, object]:
    def _s(d: dict, key: str, default: str = "") -> str:
        return str(d.get(key) or default)

    def _b(d: dict, key: str, default: bool = False) -> bool:
        return bool(d.get(key, default))

    def _i(d: dict, key: str, default: int, *, minimum: int = 1) -> int:
        try:
            return max(minimum, int(d.get(key, default)))
        except (TypeError, ValueError):
            return default

    # Base from current state
    merged: dict[str, object] = {
        "version": CONFIG_VERSION,
        "source_path": _s(current, "source_path"),
        "output_dir": _s(current, "output_dir"),
        "base_name": _s(current, "base_name"),
        "export_docx": _b(current, "export_docx", True),
        "export_tei": _b(current, "export_tei", True),
        "export_latex": _b(current, "export_latex", True),
        "output_docx_path": _s(current, "output_docx_path"),
        "tei_output_path": _s(current, "tei_output_path"),
        "decision_mode": normalize_decision_mode(_s(current, "decision_mode", "heuristic")),
        "heuristic_profile": normalize_heuristic_profile(_s(current, "heuristic_profile", "conservative")),
        "heading_transform_threshold": normalize_optional_threshold(current.get("heading_transform_threshold")),
        "heading_diagnostic_threshold": normalize_optional_threshold(current.get("heading_diagnostic_threshold")),
        "poetry_transform_threshold": normalize_optional_threshold(current.get("poetry_transform_threshold")),
        "poetry_diagnostic_threshold": normalize_optional_threshold(current.get("poetry_diagnostic_threshold")),
        "ai_aggressiveness": normalize_ai_aggressiveness(_s(current, "ai_aggressiveness", "conservative")),
        # Structurelle
        "struct_ai_provider": normalize_provider(_s(current, "struct_ai_provider", _s(current, "ai_provider", "groq"))),
        "struct_ai_api_key": _s(current, "struct_ai_api_key", _s(current, "ai_api_key")),
        "struct_ai_model": _s(current, "struct_ai_model", _s(current, "ai_model")),
        "struct_ai_base_url": _s(current, "struct_ai_base_url", _s(current, "ai_base_url")),
        "max_structure_ai_calls": _i(current, "max_structure_ai_calls", Step1Options().max_structure_ai_calls),
        # Éditoriale
        "enable_editorial_ai": _b(current, "enable_editorial_ai"),
        "editorial_ai_provider": _s(current, "editorial_ai_provider"),
        "editorial_ai_api_key": _s(current, "editorial_ai_api_key"),
        "editorial_ai_model": _s(current, "editorial_ai_model"),
        "editorial_ai_base_url": _s(current, "editorial_ai_base_url"),
        "max_ai_calls": _i(current, "max_ai_calls", Step1Options().max_ai_calls),
        # Legacy
        "enable_structure_ai": _b(current, "enable_structure_ai"),
        "enable_ai": _b(current, "enable_ai"),
        "ai_provider": _s(current, "ai_provider", "groq"),
        "ai_api_key": _s(current, "ai_api_key"),
        "ai_model": _s(current, "ai_model"),
        "ai_base_url": _s(current, "ai_base_url"),
    }

    if not isinstance(loaded, dict):
        return merged

    # Champs simples
    for key in ("source_path", "output_dir", "base_name", "output_docx_path", "tei_output_path"):
        if key in loaded:
            merged[key] = str(loaded.get(key) or "")
    for key in ("export_docx", "export_tei", "export_latex"):
        if key in loaded:
            merged[key] = bool(loaded.get(key))

    if "decision_mode" in loaded:
        merged["decision_mode"] = normalize_decision_mode(str(loaded.get("decision_mode")))
    if "heuristic_profile" in loaded:
        merged["heuristic_profile"] = normalize_heuristic_profile(str(loaded.get("heuristic_profile")))
    for key in ("heading_transform_threshold", "heading_diagnostic_threshold",
                "poetry_transform_threshold", "poetry_diagnostic_threshold"):
        if key in loaded:
            merged[key] = normalize_optional_threshold(loaded.get(key))
    if "ai_aggressiveness" in loaded:
        merged["ai_aggressiveness"] = normalize_ai_aggressiveness(str(loaded.get("ai_aggressiveness")))

    # IA structurelle — supporte v1 (ai_*) et v2 (struct_ai_*)
    struct_provider_raw = (
        loaded.get("struct_ai_provider")
        or loaded.get("ai_provider")
        or "groq"
    )
    if "struct_ai_provider" in loaded or "ai_provider" in loaded:
        merged["struct_ai_provider"] = normalize_provider(str(struct_provider_raw))
        merged["ai_provider"] = merged["struct_ai_provider"]
    for new_key, old_key in (
        ("struct_ai_api_key", "ai_api_key"),
        ("struct_ai_model", "ai_model"),
        ("struct_ai_base_url", "ai_base_url"),
    ):
        if new_key in loaded:
            merged[new_key] = str(loaded.get(new_key) or "")
            merged[old_key] = merged[new_key]
        elif old_key in loaded:
            merged[new_key] = str(loaded.get(old_key) or "")
            merged[old_key] = merged[new_key]

    if "max_structure_ai_calls" in loaded:
        merged["max_structure_ai_calls"] = _i(loaded, "max_structure_ai_calls", Step1Options().max_structure_ai_calls)

    # IA éditoriale
    if "enable_editorial_ai" in loaded:
        merged["enable_editorial_ai"] = bool(loaded.get("enable_editorial_ai"))
    for key in ("editorial_ai_provider", "editorial_ai_api_key", "editorial_ai_model", "editorial_ai_base_url"):
        if key in loaded:
            merged[key] = str(loaded.get(key) or "")
    if "max_ai_calls" in loaded:
        merged["max_ai_calls"] = _i(loaded, "max_ai_calls", Step1Options().max_ai_calls)
    if "enable_ai" in loaded:
        merged["enable_ai"] = bool(loaded.get("enable_ai"))

    # Decision mode est autoritaire sur l'IA structurelle
    if "decision_mode" in loaded:
        mode = str(merged["decision_mode"])
        structure_ai, _ = derive_ai_flags_from_decision_mode(mode)
        merged["enable_structure_ai"] = structure_ai
        if mode in {"deterministic", "ai_exploratory"}:
            merged["enable_editorial_ai"] = False
        elif "enable_editorial_ai" in loaded:
            merged["enable_editorial_ai"] = bool(loaded.get("enable_editorial_ai"))
        merged["enable_ai"] = False

    return merged


def load_config_file(path: Path) -> dict[str, object]:
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON invalide: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Lecture impossible: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("JSON invalide: objet attendu en racine.")
    return data


def save_config_file(path: Path, config: dict[str, object]) -> None:
    payload = apply_config_dict({}, config)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Formatage des résultats ───────────────────────────────────────────────────

def format_diagnostics(diagnostics: list[Diagnostic]) -> str:
    if not diagnostics:
        return "Aucun diagnostic."
    lines: list[str] = []
    for diag in diagnostics:
        lines.append(
            f"- rule_id={diag.rule_id or '(sans rule_id)'} | "
            f"severity={diag.severity} | category={diag.category}"
        )
        lines.append(f"  message={diag.message}")
        if diag.evidence and diag.evidence.excerpt:
            lines.append(f"  excerpt={diag.evidence.excerpt.strip()}")
        if diag.target_ref:
            lines.append(f"  target_ref={diag.target_ref}")
    return "\n".join(lines)


def format_warnings(warnings: list[str]) -> str:
    if not warnings:
        return "Aucun warning."
    return "\n".join(f"- {warning}" for warning in warnings)


def format_module_runs(module_runs: list[ModuleRun]) -> str:
    if not module_runs:
        return "Aucun module execute."
    return "\n".join(
        f"- {run.module_name} | status={run.status} | summary={run.summary}"
        for run in module_runs
    )


def format_outputs(result: Step1Result) -> str:
    lines: list[str] = []
    if result.output_docx:
        lines.append(f"- DOCX de relecture : {result.output_docx}")
    else:
        lines.append("- DOCX de relecture : non produit (option non demandée)")
    report = result.pipeline_result.report
    tei_path = None
    for module_run in report.module_runs:
        if module_run.module_name == "tei_xml_write":
            tei_path = module_run.summary.get("output")
            break
    if tei_path:
        lines.append(f"- XML-TEI : {tei_path}")
    elif result.pipeline_result.tei_xml:
        lines.append("- XML-TEI : généré en mémoire (pas de fichier écrit)")
    else:
        lines.append("- XML-TEI : non produit")
    return "\n".join(lines)


def extract_output_paths(result: Step1Result) -> tuple[Path | None, Path | None]:
    docx_path = result.output_docx
    tei_path: Path | None = None
    for module_run in result.pipeline_result.report.module_runs:
        if module_run.module_name != "tei_xml_write":
            continue
        output = module_run.summary.get("output")
        if isinstance(output, str) and output.strip():
            tei_path = Path(output)
            break
    return docx_path, tei_path


def output_folders_to_open(result: Step1Result) -> list[Path]:
    docx_path, tei_path = extract_output_paths(result)
    folders: list[Path] = []
    seen: set[str] = set()

    def _append_parent(path: Path | None) -> None:
        if path is None:
            return
        parent = path.parent
        key = str(parent).lower()
        if key in seen:
            return
        seen.add(key)
        folders.append(parent)

    _append_parent(docx_path)
    _append_parent(tei_path)
    return folders


def build_output_paths(source: Path, output_dir: Path, base_name: str) -> tuple[Path, Path, Path]:
    normalized_base = base_name.strip() or source.stem
    safe_base = normalized_base.replace(" ", "_")
    docx_path = output_dir / f"{safe_base}_purh.docx"
    tei_path = output_dir / f"{safe_base}_tei.xml"
    tex_path = output_dir / f"{safe_base}_latex.tex"
    return docx_path, tei_path, tex_path


def run_export_bundle(
    *,
    pipeline: Step1Pipeline,
    source: Path,
    options: Step1Options,
    export_latex: bool,
    latex_output_path: Path | None,
) -> ExportRunResult:
    step1_result = pipeline.run(source, options)
    latex_path: Path | None = None
    latex_error: str | None = None
    if export_latex and latex_output_path is not None:
        _docx_path, tei_path = extract_output_paths(step1_result)
        if tei_path is None or not tei_path.exists():
            latex_error = "Export LaTeX ignoré : XML-TEI non disponible."
        else:
            try:
                latex_output_path.parent.mkdir(parents=True, exist_ok=True)
                latex_path = export_tei_to_latex(tei_path, latex_output_path)
            except Exception as exc:  # noqa: BLE001
                latex_error = f"Erreur export LaTeX: {exc}"
    return ExportRunResult(
        step1_result=step1_result,
        latex_output_path=latex_path,
        latex_error=latex_error,
    )


def build_completion_message(
    result: Step1Result,
    latex_path: Path | None = None,
    latex_error: str | None = None,
) -> str:
    report = result.pipeline_result.report
    docx_path, tei_path = extract_output_paths(result)
    latex_value = str(latex_path) if latex_path else ("erreur" if latex_error else "non produit")
    return (
        "Analyse terminée.\n"
        f"- Transformations: {len(report.transformations)}\n"
        f"- Diagnostics: {len(report.diagnostics)}\n"
        f"- Warnings: {len(report.warnings)}\n"
        f"- DOCX: {docx_path if docx_path else 'non produit'}\n"
        f"- XML-TEI: {tei_path if tei_path else 'non écrit sur disque'}\n"
        f"- LaTeX: {latex_value}"
    )


def build_result_text(result: Step1Result, latex_path: Path | None = None, latex_error: str | None = None) -> str:
    report = result.pipeline_result.report
    sections = [
        "Corrections appliquees",
        f"Transformations: {len(report.transformations)}",
        "",
        "Diagnostics a verifier",
        format_diagnostics(report.diagnostics),
        "",
        "Warnings techniques",
        format_warnings(report.warnings),
        "",
        "Sorties",
        format_outputs(result),
        *(["- LaTeX : " + str(latex_path)] if latex_path else []),
        *(["- LaTeX : " + latex_error] if latex_error else []),
        "",
        "Resume modules",
        format_module_runs(report.module_runs),
        "",
        DISCLAIMER_TEXT,
    ]
    return "\n".join(sections)


# ── Boîte de dialogue ─────────────────────────────────────────────────────────

class Step1Dialog(tk.Tk):
    """Interface Step 1: collecte options, lance le pipeline, affiche le rapport."""

    _PAD = 10

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.title("PURH Editorial - Step 1")
        self.resizable(True, True)
        self.minsize(980, 720)

        self._pipeline: Step1Pipeline | None = None
        self._running = False

        # Fichiers
        self._input_path = tk.StringVar()
        self._output_dir = tk.StringVar(value=str(self.settings.exports_dir))
        self._base_name = tk.StringVar()
        self._export_docx = tk.BooleanVar(value=True)
        self._export_tei = tk.BooleanVar(value=True)
        self._export_latex = tk.BooleanVar(value=True)
        self._output_docx_path = tk.StringVar()
        self._output_tei_path = tk.StringVar()
        self._output_latex_path = tk.StringVar()

        # Politique
        self._decision_mode = tk.StringVar(value="heuristic")
        self._decision_mode_label = tk.StringVar(value=decision_mode_to_label("heuristic"))
        self._heuristic_profile = tk.StringVar(value="conservative")
        self._heuristic_profile_label = tk.StringVar(value=heuristic_profile_to_label("conservative"))
        self._heading_transform_threshold = tk.StringVar(value="")
        self._heading_diagnostic_threshold = tk.StringVar(value="")
        self._poetry_transform_threshold = tk.StringVar(value="")
        self._poetry_diagnostic_threshold = tk.StringVar(value="")
        self._ai_aggressiveness = tk.StringVar(value="conservative")
        self._ai_aggressiveness_label = tk.StringVar(value=ai_aggressiveness_to_label("conservative"))

        # IA structurelle
        self._enable_structure_ai = tk.BooleanVar(value=False)
        self._struct_ai_provider_label = tk.StringVar(value=provider_to_label(settings.ai.provider))
        self._struct_ai_api_key = tk.StringVar(value=settings.ai.api_key or "")
        self._struct_ai_model = tk.StringVar(value=settings.ai.model)
        self._struct_ai_base_url = tk.StringVar(value=settings.ai.base_url)
        self._max_structure_ai_calls = tk.IntVar(value=Step1Options().max_structure_ai_calls)

        # IA éditoriale
        self._enable_editorial_ai = tk.BooleanVar(value=False)
        self._editorial_ai_provider_label = tk.StringVar(value="")
        self._editorial_ai_api_key = tk.StringVar(value=settings.ai.anthropic_api_key or "")
        self._editorial_ai_model = tk.StringVar(value=settings.ai.anthropic_model)
        self._editorial_ai_base_url = tk.StringVar(value=settings.ai.anthropic_base_url)
        self._max_ai_calls = tk.IntVar(value=Step1Options().max_ai_calls)

        # Legacy (compatibilité)
        self._enable_ai = tk.BooleanVar(value=False)
        self._ai_provider = tk.StringVar(value=settings.ai.provider)
        self._ai_api_key = tk.StringVar(value=settings.ai.api_key or "")
        self._ai_model = tk.StringVar(value=settings.ai.model)
        self._ai_base_url = tk.StringVar(value=settings.ai.base_url)

        self._status = tk.StringVar(value="Selectionnez un DOCX source puis lancez l'analyse.")

        self._input_path.trace_add("write", self._on_input_changed)
        self._build_ui()

    def _build_ui(self) -> None:
        p = self._PAD
        outer = ttk.Frame(self)
        outer.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        self._main_canvas = tk.Canvas(outer, highlightthickness=0)
        self._main_canvas.grid(row=0, column=0, sticky="nsew")
        self._main_scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self._main_canvas.yview)
        self._main_scrollbar.grid(row=0, column=1, sticky="ns")
        self._main_canvas.configure(yscrollcommand=self._main_scrollbar.set)

        root = ttk.Frame(self._main_canvas, padding=p)
        self._main_window_id = self._main_canvas.create_window((0, 0), window=root, anchor="nw")
        root.bind("<Configure>", self._on_main_frame_configure)
        self._main_canvas.bind("<Configure>", self._on_main_canvas_configure)
        self._bind_mousewheel(self._main_canvas)

        root.columnconfigure(0, weight=1)
        root.rowconfigure(8, weight=1)

        # ── Section 1 : Fichier source ────────────────────────────────────────
        src_frame = ttk.LabelFrame(root, text="1. Fichier source", padding=p)
        src_frame.grid(row=0, column=0, sticky="ew", pady=(0, p))
        src_frame.columnconfigure(0, weight=1)
        ttk.Entry(src_frame, textvariable=self._input_path).grid(row=0, column=0, sticky="ew", padx=(0, p))
        ttk.Button(src_frame, text="Choisir...", command=self._browse_input).grid(row=0, column=1)

        # ── Section 2 : Export ────────────────────────────────────────────────
        out_frame = ttk.LabelFrame(root, text="2. Export des fichiers", padding=p)
        out_frame.grid(row=1, column=0, sticky="ew", pady=(0, p))
        out_frame.columnconfigure(1, weight=1)
        ttk.Label(out_frame, text="Dossier d'export").grid(row=0, column=0, sticky="w", padx=(0, p))
        ttk.Entry(out_frame, textvariable=self._output_dir).grid(row=0, column=1, sticky="ew", padx=(0, p))
        ttk.Button(out_frame, text="Choisir...", command=self._browse_output_dir).grid(row=0, column=2)
        ttk.Label(out_frame, text="Nom de base").grid(row=1, column=0, sticky="w", padx=(0, p), pady=(6, 0))
        ttk.Entry(out_frame, textvariable=self._base_name).grid(row=1, column=1, sticky="ew", padx=(0, p), pady=(6, 0))
        ttk.Label(out_frame, text="(par défaut: nom du fichier source)", foreground="#555555").grid(
            row=2, column=1, sticky="w"
        )
        ttk.Checkbutton(out_frame, text="Exporter le DOCX corrigé", variable=self._export_docx).grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Checkbutton(out_frame, text="Exporter le XML-TEI", variable=self._export_tei).grid(row=3, column=1, sticky="w", pady=(6, 0))
        ttk.Checkbutton(out_frame, text="Exporter le LaTeX", variable=self._export_latex).grid(row=3, column=2, sticky="w", pady=(6, 0))

        # ── Section 3 : Politique ─────────────────────────────────────────────
        opt_frame = ttk.LabelFrame(root, text="3. Politique de traitement", padding=p)
        opt_frame.grid(row=2, column=0, sticky="ew", pady=(0, p))
        opt_frame.columnconfigure(1, weight=1)
        ttk.Label(opt_frame, text="Mode de décision:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            opt_frame,
            textvariable=self._decision_mode_label,
            values=list(DECISION_MODE_LABELS.values()),
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(opt_frame, text="Profil heuristique:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(
            opt_frame,
            textvariable=self._heuristic_profile_label,
            values=list(HEURISTIC_PROFILE_LABELS.values()),
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))

        # ── Section 4 : Seuils ────────────────────────────────────────────────
        thresh_frame = ttk.LabelFrame(root, text="4. Seuils avancés", padding=p)
        thresh_frame.grid(row=3, column=0, sticky="ew", pady=(0, p))
        thresh_frame.columnconfigure(1, weight=1)
        thresh_frame.columnconfigure(3, weight=1)
        for (r, lbl, var) in (
            (0, "Heading transform:", self._heading_transform_threshold),
            (1, "Poetry transform:", self._poetry_transform_threshold),
        ):
            ttk.Label(thresh_frame, text=lbl).grid(row=r, column=0, sticky="w", pady=(0 if r == 0 else 6, 0))
            ttk.Entry(thresh_frame, textvariable=var, width=8).grid(row=r, column=1, sticky="w", padx=(6, 16), pady=(0 if r == 0 else 6, 0))
        for (r, lbl, var) in (
            (0, "Heading diagnostic:", self._heading_diagnostic_threshold),
            (1, "Poetry diagnostic:", self._poetry_diagnostic_threshold),
        ):
            ttk.Label(thresh_frame, text=lbl).grid(row=r, column=2, sticky="w", pady=(0 if r == 0 else 6, 0))
            ttk.Entry(thresh_frame, textvariable=var, width=8).grid(row=r, column=3, sticky="w", padx=(6, 0), pady=(0 if r == 0 else 6, 0))
        ttk.Label(thresh_frame, text="Vide = valeurs du profil.", foreground="#555555").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(8, 0)
        )

        # ── Section 5 : IA structurelle ───────────────────────────────────────
        struct_frame = ttk.LabelFrame(
            root,
            text="5. IA structurelle — classification des zones grises (Groq recommandé)",
            padding=p,
        )
        struct_frame.grid(row=4, column=0, sticky="ew", pady=(0, p))
        struct_frame.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            struct_frame,
            text="Activer l'IA structurelle (zones grises)",
            variable=self._enable_structure_ai,
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(struct_frame, text="Agressivité:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(
            struct_frame,
            textvariable=self._ai_aggressiveness_label,
            values=list(AI_AGGRESSIVENESS_LABELS.values()),
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))

        ttk.Label(struct_frame, text="Provider:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(
            struct_frame,
            textvariable=self._struct_ai_provider_label,
            values=list(PROVIDER_LABELS.values()),
            state="readonly",
        ).grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))

        ttk.Label(struct_frame, text="API key:").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(struct_frame, textvariable=self._struct_ai_api_key, show="*").grid(
            row=3, column=1, sticky="ew", padx=(8, 0), pady=(6, 0)
        )
        ttk.Label(struct_frame, text="Modèle:").grid(row=4, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(struct_frame, textvariable=self._struct_ai_model).grid(
            row=4, column=1, sticky="ew", padx=(8, 0), pady=(6, 0)
        )
        ttk.Label(struct_frame, text="Base URL:").grid(row=5, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(struct_frame, textvariable=self._struct_ai_base_url).grid(
            row=5, column=1, sticky="ew", padx=(8, 0), pady=(6, 0)
        )
        ttk.Label(struct_frame, text="Max appels:").grid(row=6, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(struct_frame, from_=1, to=50, textvariable=self._max_structure_ai_calls, width=6).grid(
            row=6, column=1, sticky="w", padx=(8, 0), pady=(6, 0)
        )
        if not self.settings.ai.enabled:
            ttk.Label(
                struct_frame,
                text="(Aucune clé globale chargée depuis .env — saisissez une clé de session ci-dessus.)",
                foreground="gray",
            ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # ── Section 6 : IA éditoriale ─────────────────────────────────────────
        edi_frame = ttk.LabelFrame(
            root,
            text="6. IA éditoriale — corrections orthotypo (Anthropic/Claude recommandé)",
            padding=p,
        )
        edi_frame.grid(row=5, column=0, sticky="ew", pady=(0, p))
        edi_frame.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            edi_frame,
            text="Activer l'IA éditoriale correctrice",
            variable=self._enable_editorial_ai,
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(edi_frame, text="Provider:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        edi_provider_combo = ttk.Combobox(
            edi_frame,
            textvariable=self._editorial_ai_provider_label,
            values=[""] + list(PROVIDER_LABELS.values()),
            state="readonly",
        )
        edi_provider_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))

        ttk.Label(edi_frame, text="API key:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(edi_frame, textvariable=self._editorial_ai_api_key, show="*").grid(
            row=2, column=1, sticky="ew", padx=(8, 0), pady=(6, 0)
        )
        ttk.Label(edi_frame, text="Modèle:").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(edi_frame, textvariable=self._editorial_ai_model).grid(
            row=3, column=1, sticky="ew", padx=(8, 0), pady=(6, 0)
        )
        ttk.Label(edi_frame, text="Base URL:").grid(row=4, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(edi_frame, textvariable=self._editorial_ai_base_url).grid(
            row=4, column=1, sticky="ew", padx=(8, 0), pady=(6, 0)
        )
        ttk.Label(edi_frame, text="Max appels:").grid(row=5, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(edi_frame, from_=1, to=50, textvariable=self._max_ai_calls, width=6).grid(
            row=5, column=1, sticky="w", padx=(8, 0), pady=(6, 0)
        )
        ttk.Label(
            edi_frame,
            text="Laissez Provider/Clé vides pour hériter de l'IA structurelle ci-dessus.",
            foreground="#555555",
            wraplength=900,
            justify="left",
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(
            edi_frame,
            text="Attention : les clés API sont enregistrées en clair dans le fichier JSON local.",
            foreground="#8a5a00",
            wraplength=900,
            justify="left",
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # ── Section 7 : Actions ───────────────────────────────────────────────
        actions_frame = ttk.Frame(root)
        actions_frame.grid(row=6, column=0, sticky="ew", pady=(0, p))
        actions_frame.columnconfigure(0, weight=1)
        self._progress = ttk.Progressbar(actions_frame, mode="indeterminate")
        self._progress.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 6))
        ttk.Button(
            actions_frame, text="Charger configuration...", command=self._on_load_config,
        ).grid(row=1, column=0, sticky="w")
        ttk.Button(
            actions_frame, text="Enregistrer configuration...", command=self._on_save_config,
        ).grid(row=1, column=1, padx=(p, p), sticky="w")
        self._run_btn = ttk.Button(
            actions_frame,
            text="Lancement de l'analyse",
            command=self._on_run,
            state="disabled",
        )
        self._run_btn.grid(row=1, column=3, sticky="e")
        ttk.Label(actions_frame, textvariable=self._status, anchor="w").grid(
            row=2, column=0, columnspan=4, sticky="ew", pady=(6, 0)
        )

        # ── Section 8 : Résultats ─────────────────────────────────────────────
        result_frame = ttk.LabelFrame(root, text="7. Resultats", padding=p)
        result_frame.grid(row=8, column=0, sticky="nsew")
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(1, weight=1)
        ttk.Label(
            result_frame,
            text=DISCLAIMER_TEXT,
            wraplength=900,
            justify="left",
            foreground="#555555",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._result_text = tk.Text(result_frame, height=24, wrap="word")
        self._result_text.grid(row=1, column=0, sticky="nsew")
        self._result_text.configure(state="disabled")
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self._result_text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self._result_text.configure(yscrollcommand=scrollbar.set)

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_main_frame_configure(self, _event: tk.Event) -> None:
        self._main_canvas.configure(scrollregion=self._main_canvas.bbox("all"))

    def _on_main_canvas_configure(self, event: tk.Event) -> None:
        self._main_canvas.itemconfigure(self._main_window_id, width=event.width)

    def _bind_mousewheel(self, widget: tk.Widget) -> None:
        widget.bind_all("<MouseWheel>", self._on_mousewheel)
        widget.bind_all("<Button-4>", self._on_mousewheel_linux)
        widget.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _on_mousewheel(self, event: tk.Event) -> None:
        delta = getattr(event, "delta", 0)
        if delta:
            step = int(-delta / 120) if delta % 120 == 0 else (-1 if delta > 0 else 1)
            self._main_canvas.yview_scroll(step, "units")

    def _on_mousewheel_linux(self, event: tk.Event) -> None:
        num = getattr(event, "num", 0)
        if num == 4:
            self._main_canvas.yview_scroll(-1, "units")
        elif num == 5:
            self._main_canvas.yview_scroll(1, "units")

    def _browse_input(self) -> None:
        initial = (
            Path(self._input_path.get()).parent
            if self._input_path.get().strip()
            else self.settings.sources_dir
        )
        path_str = filedialog.askopenfilename(
            title="Selectionner le manuscrit DOCX",
            filetypes=[("Document Word", "*.docx"), ("Tous les fichiers", "*.*")],
            initialdir=str(initial),
        )
        if path_str:
            self._input_path.set(path_str)

    def _browse_output_dir(self) -> None:
        initial = self._output_dir.get().strip() or str(self.settings.exports_dir)
        chosen = filedialog.askdirectory(title="Choisir le dossier de sortie", initialdir=initial)
        if chosen:
            self._output_dir.set(chosen)

    def _on_input_changed(self, *_) -> None:
        path = self._input_path.get().strip()
        is_docx = bool(path) and Path(path).suffix.lower() == ".docx"
        if is_docx and not self._base_name.get().strip():
            self._base_name.set(Path(path).stem)
        if is_docx and not self._running:
            self._run_btn.state(["!disabled"])
        else:
            self._run_btn.state(["disabled"])

    def _on_run(self) -> None:
        if self._running:
            return
        source = Path(self._input_path.get().strip())
        if not source.is_file() or source.suffix.lower() != ".docx":
            messagebox.showerror("Source invalide", "Veuillez selectionner un fichier DOCX source valide.")
            return
        output_dir_value = self._output_dir.get().strip()
        if not output_dir_value:
            messagebox.showerror("Sortie invalide", "Veuillez choisir un dossier de sortie.")
            return
        output_dir = Path(output_dir_value)
        output_dir.mkdir(parents=True, exist_ok=True)

        docx_path, tei_path, tex_path = build_output_paths(source, output_dir, self._base_name.get())
        self._output_docx_path.set(str(docx_path))
        self._output_tei_path.set(str(tei_path))
        self._output_latex_path.set(str(tex_path))

        options = build_step1_options_from_form(
            decision_mode_label=self._decision_mode_label.get(),
            heuristic_profile_label=self._heuristic_profile_label.get(),
            heading_transform_threshold=self._heading_transform_threshold.get(),
            heading_diagnostic_threshold=self._heading_diagnostic_threshold.get(),
            poetry_transform_threshold=self._poetry_transform_threshold.get(),
            poetry_diagnostic_threshold=self._poetry_diagnostic_threshold.get(),
            ai_aggressiveness_label=self._ai_aggressiveness_label.get(),
            struct_ai_provider=provider_from_label(self._struct_ai_provider_label.get()),
            struct_ai_api_key=self._struct_ai_api_key.get(),
            struct_ai_model=self._struct_ai_model.get(),
            struct_ai_base_url=self._struct_ai_base_url.get(),
            max_structure_ai_calls=max(1, int(self._max_structure_ai_calls.get())),
            enable_editorial_ai=self._enable_editorial_ai.get(),
            editorial_ai_provider=provider_from_label(self._editorial_ai_provider_label.get()) if self._editorial_ai_provider_label.get().strip() else "",
            editorial_ai_api_key=self._editorial_ai_api_key.get(),
            editorial_ai_model=self._editorial_ai_model.get(),
            editorial_ai_base_url=self._editorial_ai_base_url.get(),
            max_ai_calls=max(1, int(self._max_ai_calls.get())),
            output_path=docx_path if self._export_docx.get() else None,
            tei_output_path=tei_path if self._export_tei.get() else None,
        )

        self._set_running(True)
        threading.Thread(
            target=self._run_pipeline,
            args=(source, options, self._export_latex.get(), tex_path),
            daemon=True,
        ).start()

    def _on_save_config(self) -> None:
        path_str = filedialog.asksaveasfilename(
            title="Enregistrer configuration Step 1",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Tous les fichiers", "*.*")],
            initialdir=str(self.settings.exports_dir),
        )
        if not path_str:
            return
        try:
            config = self._current_config_dict()
            save_config_file(Path(path_str), config)
            self._status.set(f"Configuration enregistree: {path_str}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erreur configuration", str(exc))

    def _on_load_config(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Charger configuration Step 1",
            filetypes=[("JSON", "*.json"), ("Tous les fichiers", "*.*")],
            initialdir=str(self.settings.exports_dir),
        )
        if not path_str:
            return
        try:
            loaded = load_config_file(Path(path_str))
            merged = apply_config_dict(self._current_config_dict(), loaded)
            self._apply_config_to_ui(merged)
            self._status.set(f"Configuration chargee: {path_str}")
        except ValueError as exc:
            messagebox.showerror("Configuration invalide", str(exc))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erreur configuration", str(exc))

    def _run_pipeline(self, source: Path, options: Step1Options, export_latex: bool, latex_output_path: Path) -> None:
        try:
            if self._pipeline is None:
                self._pipeline = Step1Pipeline(self.settings)
            bundle = run_export_bundle(
                pipeline=self._pipeline,
                source=source,
                options=options,
                export_latex=export_latex,
                latex_output_path=latex_output_path if export_latex else None,
            )
            self.after(0, self._on_success, bundle)
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._on_error, exc)

    def _on_success(self, bundle: ExportRunResult) -> None:
        result = bundle.step1_result
        self._set_running(False)
        self._status.set("Analyse terminee." if not bundle.latex_error else bundle.latex_error)
        self._set_result_text(build_result_text(result, bundle.latex_output_path, bundle.latex_error))
        completion_message = build_completion_message(result, bundle.latex_output_path, bundle.latex_error)
        folders = output_folders_to_open(result)
        if bundle.latex_output_path is not None:
            folders.append(bundle.latex_output_path.parent)
        if not folders:
            messagebox.showinfo("Analyse terminée", completion_message)
            return
        if messagebox.askyesno("Analyse terminée", completion_message + "\n\nOuvrir le dossier de sortie ?"):
            for folder in folders:
                try:
                    self._open_folder(folder)
                except Exception as exc:  # noqa: BLE001
                    messagebox.showerror("Ouverture impossible", f"Impossible d'ouvrir {folder}: {exc}")

    def _on_error(self, exc: Exception) -> None:
        self._set_running(False)
        self._status.set(f"Erreur: {exc}")
        messagebox.showerror("Erreur pipeline", str(exc))

    def _set_running(self, running: bool) -> None:
        self._running = running
        if running:
            self._progress.start(12)
            self._run_btn.state(["disabled"])
            self._status.set("Analyse en cours...")
        else:
            self._progress.stop()
            self._on_input_changed()

    def _set_result_text(self, text: str) -> None:
        self._result_text.configure(state="normal")
        self._result_text.delete("1.0", tk.END)
        self._result_text.insert("1.0", text)
        self._result_text.configure(state="disabled")

    def _current_config_dict(self) -> dict[str, object]:
        decision_mode = decision_mode_from_label(self._decision_mode_label.get())
        heuristic_profile = heuristic_profile_from_label(self._heuristic_profile_label.get())
        ai_aggressiveness = ai_aggressiveness_from_label(self._ai_aggressiveness_label.get())
        enable_structure_ai, _ = derive_ai_flags_from_decision_mode(decision_mode)
        edi_provider_raw = self._editorial_ai_provider_label.get().strip()
        edi_provider = provider_from_label(edi_provider_raw) if edi_provider_raw else ""
        return build_config_dict(
            source_path=self._input_path.get().strip(),
            output_dir=self._output_dir.get().strip(),
            base_name=self._base_name.get().strip(),
            export_docx=self._export_docx.get(),
            export_tei=self._export_tei.get(),
            export_latex=self._export_latex.get(),
            output_docx_path=self._output_docx_path.get().strip(),
            tei_output_path=self._output_tei_path.get().strip(),
            decision_mode=decision_mode,
            heuristic_profile=heuristic_profile,
            heading_transform_threshold=normalize_optional_threshold(self._heading_transform_threshold.get()),
            heading_diagnostic_threshold=normalize_optional_threshold(self._heading_diagnostic_threshold.get()),
            poetry_transform_threshold=normalize_optional_threshold(self._poetry_transform_threshold.get()),
            poetry_diagnostic_threshold=normalize_optional_threshold(self._poetry_diagnostic_threshold.get()),
            ai_aggressiveness=ai_aggressiveness,
            struct_ai_provider=provider_from_label(self._struct_ai_provider_label.get()),
            struct_ai_api_key=self._struct_ai_api_key.get(),
            struct_ai_model=self._struct_ai_model.get(),
            struct_ai_base_url=self._struct_ai_base_url.get(),
            max_structure_ai_calls=self._max_structure_ai_calls.get(),
            enable_editorial_ai=self._enable_editorial_ai.get(),
            editorial_ai_provider=edi_provider,
            editorial_ai_api_key=self._editorial_ai_api_key.get(),
            editorial_ai_model=self._editorial_ai_model.get(),
            editorial_ai_base_url=self._editorial_ai_base_url.get(),
            max_ai_calls=self._max_ai_calls.get(),
            enable_structure_ai=enable_structure_ai,
            enable_ai=False,
        )

    def _apply_config_to_ui(self, config: dict[str, object]) -> None:
        self._input_path.set(str(config.get("source_path", "")))
        self._output_dir.set(str(config.get("output_dir", self.settings.exports_dir)))
        self._base_name.set(str(config.get("base_name", "")))
        self._export_docx.set(bool(config.get("export_docx", True)))
        self._export_tei.set(bool(config.get("export_tei", True)))
        self._export_latex.set(bool(config.get("export_latex", True)))
        self._output_docx_path.set(str(config.get("output_docx_path", "")))
        self._output_tei_path.set(str(config.get("tei_output_path", "")))
        self._decision_mode.set(normalize_decision_mode(str(config.get("decision_mode", "heuristic"))))
        self._decision_mode_label.set(decision_mode_to_label(self._decision_mode.get()))
        self._heuristic_profile.set(normalize_heuristic_profile(str(config.get("heuristic_profile", "conservative"))))
        self._heuristic_profile_label.set(heuristic_profile_to_label(self._heuristic_profile.get()))
        for key, var in (
            ("heading_transform_threshold", self._heading_transform_threshold),
            ("heading_diagnostic_threshold", self._heading_diagnostic_threshold),
            ("poetry_transform_threshold", self._poetry_transform_threshold),
            ("poetry_diagnostic_threshold", self._poetry_diagnostic_threshold),
        ):
            val = config.get(key)
            var.set("" if val is None else str(val))
        self._ai_aggressiveness.set(normalize_ai_aggressiveness(str(config.get("ai_aggressiveness", "conservative"))))
        self._ai_aggressiveness_label.set(ai_aggressiveness_to_label(self._ai_aggressiveness.get()))

        # IA structurelle (v2 struct_ai_* ou v1 ai_*)
        struct_provider = str(config.get("struct_ai_provider") or config.get("ai_provider") or "groq")
        self._struct_ai_provider_label.set(provider_to_label(struct_provider))
        self._struct_ai_api_key.set(str(config.get("struct_ai_api_key") or config.get("ai_api_key") or ""))
        self._struct_ai_model.set(str(config.get("struct_ai_model") or config.get("ai_model") or self.settings.ai.model))
        self._struct_ai_base_url.set(str(config.get("struct_ai_base_url") or config.get("ai_base_url") or self.settings.ai.base_url))
        self._max_structure_ai_calls.set(max(1, int(config.get("max_structure_ai_calls", Step1Options().max_structure_ai_calls))))

        # IA éditoriale
        self._enable_editorial_ai.set(bool(config.get("enable_editorial_ai", False)))
        edi_provider_code = str(config.get("editorial_ai_provider") or "")
        self._editorial_ai_provider_label.set(provider_to_label(edi_provider_code) if edi_provider_code else "")
        self._editorial_ai_api_key.set(str(config.get("editorial_ai_api_key") or ""))
        self._editorial_ai_model.set(str(config.get("editorial_ai_model") or self.settings.ai.anthropic_model))
        self._editorial_ai_base_url.set(str(config.get("editorial_ai_base_url") or self.settings.ai.anthropic_base_url))
        self._max_ai_calls.set(max(1, int(config.get("max_ai_calls", Step1Options().max_ai_calls))))

        # Legacy
        self._enable_ai.set(False)
        self._enable_structure_ai.set(bool(config.get("enable_structure_ai", False)))
        self._ai_provider.set(struct_provider)
        self._ai_api_key.set(str(config.get("ai_api_key") or ""))
        self._ai_model.set(str(config.get("ai_model") or self.settings.ai.model))
        self._ai_base_url.set(str(config.get("ai_base_url") or self.settings.ai.base_url))

    @staticmethod
    def _open_folder(path: Path) -> None:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)


def run_step1_dialog() -> None:
    from purh_editorial.config import load_settings

    settings = load_settings()
    app = Step1Dialog(settings=settings)
    app.mainloop()
