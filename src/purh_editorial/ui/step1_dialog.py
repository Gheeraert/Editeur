from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from purh_editorial.config import AppSettings
from purh_editorial.model import Diagnostic, ModuleRun
from purh_editorial.pipeline.step1 import Step1Options, Step1Pipeline, Step1Result


DISCLAIMER_TEXT = (
    "Cette interface ne propose pas encore de diff complet avant/apres. "
    "Les diagnostics signalent des points a verifier et ne sont pas des corrections automatiques."
)
CONFIG_VERSION = 1
ALLOWED_DECISION_MODES = {
    "deterministic",
    "heuristic",
    "heuristic_ai_local",
    "ai_exploratory",
}
ALLOWED_AI_AGGRESSIVENESS = {"conservative", "balanced", "aggressive"}
ALLOWED_HEURISTIC_PROFILES = {"conservative", "balanced", "exploratory"}
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
    for code, text in DECISION_MODE_LABELS.items():
        if text == raw:
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
    for code, text in AI_AGGRESSIVENESS_LABELS.items():
        if text == raw:
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
    for code, text in HEURISTIC_PROFILE_LABELS.items():
        if text == raw:
            return code
    return normalize_heuristic_profile(raw)


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
    if mode in {"deterministic", "heuristic", "ai_exploratory"}:
        return False, False
    return False, False


def build_step1_options_from_form(
    *,
    decision_mode_label: str,
    heuristic_profile_label: str,
    heading_transform_threshold: object,
    heading_diagnostic_threshold: object,
    poetry_transform_threshold: object,
    poetry_diagnostic_threshold: object,
    ai_aggressiveness_label: str,
    ai_provider: str,
    ai_api_key: str,
    ai_model: str,
    ai_base_url: str,
    enable_editorial_ai: bool,
    max_ai_calls: int,
    max_structure_ai_calls: int,
    output_path: Path | None,
    tei_output_path: Path | None,
) -> Step1Options:
    decision_mode = decision_mode_from_label(decision_mode_label)
    heuristic_profile = heuristic_profile_from_label(heuristic_profile_label)
    ai_aggressiveness = ai_aggressiveness_from_label(ai_aggressiveness_label)
    enable_structure_ai, _ = derive_ai_flags_from_decision_mode(decision_mode)
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
        ai_provider=str(ai_provider or "groq").strip() or "groq",
        ai_api_key=str(ai_api_key or "").strip() or None,
        ai_model=str(ai_model or "").strip() or None,
        ai_base_url=str(ai_base_url or "").strip() or None,
        max_ai_calls=max(1, int(max_ai_calls)),
        max_structure_ai_calls=max(1, int(max_structure_ai_calls)),
        output_path=output_path,
        tei_output_path=tei_output_path,
    )


def build_config_dict(
    source_path: str,
    output_docx_path: str,
    tei_output_path: str,
    decision_mode: str,
    heuristic_profile: str,
    heading_transform_threshold: float | None,
    heading_diagnostic_threshold: float | None,
    poetry_transform_threshold: float | None,
    poetry_diagnostic_threshold: float | None,
    ai_aggressiveness: str,
    ai_provider: str,
    ai_api_key: str,
    ai_model: str,
    ai_base_url: str,
    enable_structure_ai: bool,
    enable_editorial_ai: bool,
    enable_ai: bool,
    max_ai_calls: int,
    max_structure_ai_calls: int,
) -> dict[str, object]:
    return {
        "version": CONFIG_VERSION,
        "source_path": source_path,
        "output_docx_path": output_docx_path,
        "tei_output_path": tei_output_path,
        "decision_mode": normalize_decision_mode(decision_mode),
        "heuristic_profile": normalize_heuristic_profile(heuristic_profile),
        "heading_transform_threshold": normalize_optional_threshold(heading_transform_threshold),
        "heading_diagnostic_threshold": normalize_optional_threshold(heading_diagnostic_threshold),
        "poetry_transform_threshold": normalize_optional_threshold(poetry_transform_threshold),
        "poetry_diagnostic_threshold": normalize_optional_threshold(poetry_diagnostic_threshold),
        "ai_aggressiveness": normalize_ai_aggressiveness(ai_aggressiveness),
        "ai_provider": str(ai_provider or "groq"),
        "ai_api_key": str(ai_api_key or ""),
        "ai_model": str(ai_model or ""),
        "ai_base_url": str(ai_base_url or ""),
        "enable_structure_ai": bool(enable_structure_ai),
        "enable_editorial_ai": bool(enable_editorial_ai),
        "enable_ai": bool(enable_ai),
        "max_ai_calls": max(1, int(max_ai_calls)),
        "max_structure_ai_calls": max(1, int(max_structure_ai_calls)),
    }


def apply_config_dict(
    current: dict[str, object],
    loaded: dict[str, object],
) -> dict[str, object]:
    merged = {
        "version": CONFIG_VERSION,
        "source_path": str(current.get("source_path", "")),
        "output_docx_path": str(current.get("output_docx_path", "")),
        "tei_output_path": str(current.get("tei_output_path", "")),
        "decision_mode": normalize_decision_mode(str(current.get("decision_mode", "heuristic"))),
        "heuristic_profile": normalize_heuristic_profile(str(current.get("heuristic_profile", "conservative"))),
        "heading_transform_threshold": normalize_optional_threshold(current.get("heading_transform_threshold")),
        "heading_diagnostic_threshold": normalize_optional_threshold(current.get("heading_diagnostic_threshold")),
        "poetry_transform_threshold": normalize_optional_threshold(current.get("poetry_transform_threshold")),
        "poetry_diagnostic_threshold": normalize_optional_threshold(current.get("poetry_diagnostic_threshold")),
        "ai_aggressiveness": normalize_ai_aggressiveness(str(current.get("ai_aggressiveness", "conservative"))),
        "ai_provider": str(current.get("ai_provider", "groq")),
        "ai_api_key": str(current.get("ai_api_key", "")),
        "ai_model": str(current.get("ai_model", "")),
        "ai_base_url": str(current.get("ai_base_url", "")),
        "enable_structure_ai": bool(current.get("enable_structure_ai", False)),
        "enable_editorial_ai": bool(current.get("enable_editorial_ai", False)),
        "enable_ai": bool(current.get("enable_ai", False)),
        "max_ai_calls": max(1, int(current.get("max_ai_calls", Step1Options().max_ai_calls))),
        "max_structure_ai_calls": max(
            1,
            int(current.get("max_structure_ai_calls", Step1Options().max_structure_ai_calls)),
        ),
    }
    if not isinstance(loaded, dict):
        return merged
    if "source_path" in loaded:
        merged["source_path"] = str(loaded.get("source_path") or "")
    if "output_docx_path" in loaded:
        merged["output_docx_path"] = str(loaded.get("output_docx_path") or "")
    if "tei_output_path" in loaded:
        merged["tei_output_path"] = str(loaded.get("tei_output_path") or "")
    if "decision_mode" in loaded:
        merged["decision_mode"] = normalize_decision_mode(str(loaded.get("decision_mode")))
    if "heuristic_profile" in loaded:
        merged["heuristic_profile"] = normalize_heuristic_profile(str(loaded.get("heuristic_profile")))
    if "heading_transform_threshold" in loaded:
        merged["heading_transform_threshold"] = normalize_optional_threshold(loaded.get("heading_transform_threshold"))
    if "heading_diagnostic_threshold" in loaded:
        merged["heading_diagnostic_threshold"] = normalize_optional_threshold(loaded.get("heading_diagnostic_threshold"))
    if "poetry_transform_threshold" in loaded:
        merged["poetry_transform_threshold"] = normalize_optional_threshold(loaded.get("poetry_transform_threshold"))
    if "poetry_diagnostic_threshold" in loaded:
        merged["poetry_diagnostic_threshold"] = normalize_optional_threshold(loaded.get("poetry_diagnostic_threshold"))
    if "ai_aggressiveness" in loaded:
        merged["ai_aggressiveness"] = normalize_ai_aggressiveness(str(loaded.get("ai_aggressiveness")))
    if "ai_provider" in loaded:
        merged["ai_provider"] = str(loaded.get("ai_provider") or "groq")
    if "ai_api_key" in loaded:
        merged["ai_api_key"] = str(loaded.get("ai_api_key") or "")
    if "ai_model" in loaded:
        merged["ai_model"] = str(loaded.get("ai_model") or "")
    if "ai_base_url" in loaded:
        merged["ai_base_url"] = str(loaded.get("ai_base_url") or "")
    if "enable_structure_ai" in loaded:
        merged["enable_structure_ai"] = bool(loaded.get("enable_structure_ai"))
    if "enable_editorial_ai" in loaded:
        merged["enable_editorial_ai"] = bool(loaded.get("enable_editorial_ai"))
    if "enable_ai" in loaded:
        merged["enable_ai"] = bool(loaded.get("enable_ai"))
    if "max_ai_calls" in loaded:
        try:
            merged["max_ai_calls"] = max(1, int(loaded.get("max_ai_calls")))
        except (TypeError, ValueError):
            pass
    if "max_structure_ai_calls" in loaded:
        try:
            merged["max_structure_ai_calls"] = max(1, int(loaded.get("max_structure_ai_calls")))
        except (TypeError, ValueError):
            pass

    if "decision_mode" in loaded:
        # Decision mode is authoritative for structure AI.
        mode = normalize_decision_mode(str(merged["decision_mode"]))
        structure_ai, _ = derive_ai_flags_from_decision_mode(mode)
        merged["enable_structure_ai"] = structure_ai
        # Preserve explicit editorial toggle when mode allows it.
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
        lines.append(f"- DOCX de relecture: {result.output_docx}")
    else:
        lines.append("- DOCX de relecture: non produit (option non demandee)")

    report = result.pipeline_result.report
    tei_path = None
    for module_run in report.module_runs:
        if module_run.module_name == "tei_xml_write":
            tei_path = module_run.summary.get("output")
            break

    if tei_path:
        lines.append(f"- XML-TEI: {tei_path}")
    elif result.pipeline_result.tei_xml:
        lines.append("- XML-TEI: genere en memoire (pas de fichier ecrit)")
    else:
        lines.append("- XML-TEI: non genere")
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


def build_completion_message(result: Step1Result) -> str:
    report = result.pipeline_result.report
    docx_path, tei_path = extract_output_paths(result)
    return (
        "Analyse terminée.\n"
        f"- Transformations: {len(report.transformations)}\n"
        f"- Diagnostics: {len(report.diagnostics)}\n"
        f"- Warnings: {len(report.warnings)}\n"
        f"- DOCX: {docx_path if docx_path else 'non produit'}\n"
        f"- XML-TEI: {tei_path if tei_path else 'non écrit sur disque'}"
    )


def build_result_text(result: Step1Result) -> str:
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
        "",
        "Resume modules",
        format_module_runs(report.module_runs),
        "",
        DISCLAIMER_TEXT,
    ]
    return "\n".join(sections)


class Step1Dialog(tk.Tk):
    """Interface Step 1: collecte options, lance le pipeline, affiche le rapport."""

    _PAD = 10

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.title("PURH Editorial - Step 1")
        self.resizable(True, True)
        self.minsize(960, 700)

        self._pipeline: Step1Pipeline | None = None
        self._running = False

        self._input_path = tk.StringVar()
        self._output_docx_path = tk.StringVar()
        self._output_tei_path = tk.StringVar()
        self._enable_ai = tk.BooleanVar(value=False)
        self._max_ai_calls = tk.IntVar(value=Step1Options().max_ai_calls)
        self._decision_mode = tk.StringVar(value="heuristic")
        self._heuristic_profile = tk.StringVar(value="conservative")
        self._decision_mode_label = tk.StringVar(value=decision_mode_to_label(self._decision_mode.get()))
        self._heuristic_profile_label = tk.StringVar(value=heuristic_profile_to_label(self._heuristic_profile.get()))
        self._heading_transform_threshold = tk.StringVar(value="")
        self._heading_diagnostic_threshold = tk.StringVar(value="")
        self._poetry_transform_threshold = tk.StringVar(value="")
        self._poetry_diagnostic_threshold = tk.StringVar(value="")
        self._ai_aggressiveness = tk.StringVar(value="conservative")
        self._ai_aggressiveness_label = tk.StringVar(value=ai_aggressiveness_to_label(self._ai_aggressiveness.get()))
        self._ai_provider = tk.StringVar(value="groq")
        self._ai_api_key = tk.StringVar(value="")
        self._ai_model = tk.StringVar(value=self.settings.ai.model)
        self._ai_base_url = tk.StringVar(value=self.settings.ai.base_url)
        self._enable_structure_ai = tk.BooleanVar(value=False)
        self._enable_editorial_ai = tk.BooleanVar(value=False)
        self._max_structure_ai_calls = tk.IntVar(value=Step1Options().max_structure_ai_calls)
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
        root.rowconfigure(6, weight=1)

        src_frame = ttk.LabelFrame(root, text="1. Fichier source", padding=p)
        src_frame.grid(row=0, column=0, sticky="ew", pady=(0, p))
        src_frame.columnconfigure(0, weight=1)
        ttk.Entry(src_frame, textvariable=self._input_path).grid(row=0, column=0, sticky="ew", padx=(0, p))
        ttk.Button(src_frame, text="Choisir...", command=self._browse_input).grid(row=0, column=1)

        out_frame = ttk.LabelFrame(root, text="2. Sorties optionnelles", padding=p)
        out_frame.grid(row=1, column=0, sticky="ew", pady=(0, p))
        out_frame.columnconfigure(1, weight=1)
        ttk.Label(out_frame, text="DOCX de relecture:").grid(row=0, column=0, sticky="w", padx=(0, p))
        ttk.Entry(out_frame, textvariable=self._output_docx_path).grid(row=0, column=1, sticky="ew", padx=(0, p))
        ttk.Button(out_frame, text="Choisir...", command=self._browse_output_docx).grid(row=0, column=2)
        ttk.Label(out_frame, text="XML-TEI:").grid(row=1, column=0, sticky="w", padx=(0, p), pady=(6, 0))
        ttk.Entry(out_frame, textvariable=self._output_tei_path).grid(row=1, column=1, sticky="ew", padx=(0, p), pady=(6, 0))
        ttk.Button(out_frame, text="Choisir...", command=self._browse_output_tei).grid(row=1, column=2, pady=(6, 0))

        opt_frame = ttk.LabelFrame(root, text="3. Politique de traitement", padding=p)
        opt_frame.grid(row=2, column=0, sticky="ew", pady=(0, p))
        opt_frame.columnconfigure(1, weight=1)
        ttk.Label(opt_frame, text="Mode de décision:").grid(row=0, column=0, sticky="w")
        mode_combo = ttk.Combobox(
            opt_frame,
            textvariable=self._decision_mode_label,
            values=list(DECISION_MODE_LABELS.values()),
            state="readonly",
        )
        mode_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(opt_frame, text="Profil heuristique:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        profile_combo = ttk.Combobox(
            opt_frame,
            textvariable=self._heuristic_profile_label,
            values=list(HEURISTIC_PROFILE_LABELS.values()),
            state="readonly",
        )
        profile_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))

        thresh_frame = ttk.LabelFrame(root, text="4. Seuils avancés", padding=p)
        thresh_frame.grid(row=3, column=0, sticky="ew", pady=(0, p))
        thresh_frame.columnconfigure(1, weight=1)
        thresh_frame.columnconfigure(3, weight=1)
        ttk.Label(thresh_frame, text="Heading transform:").grid(row=0, column=0, sticky="w")
        ttk.Entry(thresh_frame, textvariable=self._heading_transform_threshold, width=8).grid(row=0, column=1, sticky="w", padx=(6, 16))
        ttk.Label(thresh_frame, text="Heading diagnostic:").grid(row=0, column=2, sticky="w")
        ttk.Entry(thresh_frame, textvariable=self._heading_diagnostic_threshold, width=8).grid(row=0, column=3, sticky="w", padx=(6, 0))
        ttk.Label(thresh_frame, text="Poetry transform:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(thresh_frame, textvariable=self._poetry_transform_threshold, width=8).grid(row=1, column=1, sticky="w", padx=(6, 16), pady=(6, 0))
        ttk.Label(thresh_frame, text="Poetry diagnostic:").grid(row=1, column=2, sticky="w", pady=(6, 0))
        ttk.Entry(thresh_frame, textvariable=self._poetry_diagnostic_threshold, width=8).grid(row=1, column=3, sticky="w", padx=(6, 0), pady=(6, 0))
        ttk.Label(thresh_frame, text="Vide = valeurs du profil.", foreground="#555555").grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(8, 0)
        )

        ai_frame = ttk.LabelFrame(root, text="5. IA locale et éditoriale", padding=p)
        ai_frame.grid(row=4, column=0, sticky="ew", pady=(0, p))
        ai_frame.columnconfigure(1, weight=1)
        ttk.Label(ai_frame, text="Agressivité IA locale:").grid(row=0, column=0, sticky="w")
        ai_aggr_combo = ttk.Combobox(
            ai_frame,
            textvariable=self._ai_aggressiveness_label,
            values=list(AI_AGGRESSIVENESS_LABELS.values()),
            state="readonly",
        )
        ai_aggr_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(ai_frame, text="Provider:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(ai_frame, textvariable=self._ai_provider).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))
        ttk.Label(ai_frame, text="API key:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(ai_frame, textvariable=self._ai_api_key, show="*").grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))
        ttk.Label(ai_frame, text="Model:").grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(ai_frame, textvariable=self._ai_model).grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))
        ttk.Label(ai_frame, text="Base URL:").grid(row=4, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(ai_frame, textvariable=self._ai_base_url).grid(row=4, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))
        ttk.Label(ai_frame, text="Max appels IA locale:").grid(row=5, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(ai_frame, from_=1, to=50, textvariable=self._max_structure_ai_calls, width=6).grid(
            row=5, column=1, sticky="w", padx=(8, 0), pady=(6, 0)
        )
        ttk.Label(ai_frame, text="Max appels IA éditoriale:").grid(row=6, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(ai_frame, from_=1, to=50, textvariable=self._max_ai_calls, width=6).grid(
            row=6, column=1, sticky="w", padx=(8, 0), pady=(6, 0)
        )
        ttk.Checkbutton(
            ai_frame,
            text="Activer l’IA éditoriale correctrice",
            variable=self._enable_editorial_ai,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(
            ai_frame,
            text="Attention : la clef API est enregistrée en clair dans le fichier JSON local.",
            foreground="#8a5a00",
            wraplength=900,
            justify="left",
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(8, 0))
        if not self.settings.ai.enabled:
            ttk.Label(
                ai_frame,
                text="(Aucune clef globale chargée : fournissez une clef API de session si nécessaire.)",
                foreground="gray",
            ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(6, 0))

        actions_frame = ttk.Frame(root)
        actions_frame.grid(row=5, column=0, sticky="ew", pady=(0, p))
        actions_frame.columnconfigure(0, weight=1)
        self._progress = ttk.Progressbar(actions_frame, mode="indeterminate")
        self._progress.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 6))
        ttk.Button(
            actions_frame,
            text="Charger configuration...",
            command=self._on_load_config,
        ).grid(row=1, column=0, sticky="w")
        ttk.Button(
            actions_frame,
            text="Enregistrer configuration...",
            command=self._on_save_config,
        ).grid(row=1, column=1, padx=(p, p), sticky="w")
        self._run_btn = ttk.Button(
            actions_frame,
            text="Lancer l'analyse editoriale",
            command=self._on_run,
            state="disabled",
        )
        self._run_btn.grid(row=1, column=3, sticky="e")
        ttk.Label(actions_frame, textvariable=self._status, anchor="w").grid(row=2, column=0, columnspan=4, sticky="ew", pady=(6, 0))

        result_frame = ttk.LabelFrame(root, text="5. Resultats", padding=p)
        result_frame.grid(row=6, column=0, sticky="nsew")
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

    def _on_main_frame_configure(self, _event: tk.Event) -> None:
        self._main_canvas.configure(scrollregion=self._main_canvas.bbox("all"))

    def _on_main_canvas_configure(self, event: tk.Event) -> None:
        self._main_canvas.itemconfigure(self._main_window_id, width=event.width)

    def _bind_mousewheel(self, widget: tk.Widget) -> None:
        widget.bind_all("<MouseWheel>", self._on_mousewheel)      # Windows / macOS
        widget.bind_all("<Button-4>", self._on_mousewheel_linux)  # Linux up
        widget.bind_all("<Button-5>", self._on_mousewheel_linux)  # Linux down

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

    def _browse_output_docx(self) -> None:
        chosen = filedialog.asksaveasfilename(
            title="Choisir le DOCX de relecture",
            defaultextension=".docx",
            filetypes=[("Document Word", "*.docx"), ("Tous les fichiers", "*.*")],
            initialdir=str(self.settings.exports_dir),
        )
        if chosen:
            self._output_docx_path.set(chosen)

    def _browse_output_tei(self) -> None:
        chosen = filedialog.asksaveasfilename(
            title="Choisir le fichier XML-TEI",
            defaultextension=".xml",
            filetypes=[("XML", "*.xml"), ("Tous les fichiers", "*.*")],
            initialdir=str(self.settings.exports_dir),
        )
        if chosen:
            self._output_tei_path.set(chosen)

    def _on_input_changed(self, *_) -> None:
        path = self._input_path.get().strip()
        is_docx = bool(path) and Path(path).suffix.lower() == ".docx"
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

        max_ai_calls = max(1, int(self._max_ai_calls.get()))
        max_structure_ai_calls = max(1, int(self._max_structure_ai_calls.get()))
        options = build_step1_options_from_form(
            decision_mode_label=self._decision_mode_label.get(),
            heuristic_profile_label=self._heuristic_profile_label.get(),
            heading_transform_threshold=self._heading_transform_threshold.get(),
            heading_diagnostic_threshold=self._heading_diagnostic_threshold.get(),
            poetry_transform_threshold=self._poetry_transform_threshold.get(),
            poetry_diagnostic_threshold=self._poetry_diagnostic_threshold.get(),
            ai_aggressiveness_label=self._ai_aggressiveness_label.get(),
            ai_provider=self._ai_provider.get(),
            ai_api_key=self._ai_api_key.get(),
            ai_model=self._ai_model.get(),
            ai_base_url=self._ai_base_url.get(),
            enable_editorial_ai=self._enable_editorial_ai.get(),
            max_ai_calls=max_ai_calls,
            max_structure_ai_calls=max_structure_ai_calls,
            output_path=self._optional_path(self._output_docx_path.get(), ".docx"),
            tei_output_path=self._optional_path(self._output_tei_path.get(), ".xml"),
        )

        self._set_running(True)
        threading.Thread(target=self._run_pipeline, args=(source, options), daemon=True).start()

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

    def _run_pipeline(self, source: Path, options: Step1Options) -> None:
        try:
            if self._pipeline is None:
                self._pipeline = Step1Pipeline(self.settings)
            result = self._pipeline.run(source, options)
            self.after(0, self._on_success, result)
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._on_error, exc)

    def _on_success(self, result: Step1Result) -> None:
        self._set_running(False)
        self._status.set("Analyse terminee.")
        self._set_result_text(build_result_text(result))
        completion_message = build_completion_message(result)
        folders = output_folders_to_open(result)
        if not folders:
            messagebox.showinfo("Analyse terminée", completion_message)
            return
        if messagebox.askyesno(
            "Analyse terminée",
            completion_message + "\n\nOuvrir le dossier de sortie ?",
        ):
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
        return build_config_dict(
            source_path=self._input_path.get().strip(),
            output_docx_path=self._output_docx_path.get().strip(),
            tei_output_path=self._output_tei_path.get().strip(),
            decision_mode=decision_mode,
            heuristic_profile=heuristic_profile,
            heading_transform_threshold=normalize_optional_threshold(self._heading_transform_threshold.get()),
            heading_diagnostic_threshold=normalize_optional_threshold(self._heading_diagnostic_threshold.get()),
            poetry_transform_threshold=normalize_optional_threshold(self._poetry_transform_threshold.get()),
            poetry_diagnostic_threshold=normalize_optional_threshold(self._poetry_diagnostic_threshold.get()),
            ai_aggressiveness=ai_aggressiveness,
            ai_provider=self._ai_provider.get(),
            ai_api_key=self._ai_api_key.get(),
            ai_model=self._ai_model.get(),
            ai_base_url=self._ai_base_url.get(),
            enable_structure_ai=enable_structure_ai,
            enable_editorial_ai=self._enable_editorial_ai.get(),
            enable_ai=False,
            max_ai_calls=self._max_ai_calls.get(),
            max_structure_ai_calls=self._max_structure_ai_calls.get(),
        )

    def _apply_config_to_ui(self, config: dict[str, object]) -> None:
        self._input_path.set(str(config.get("source_path", "")))
        self._output_docx_path.set(str(config.get("output_docx_path", "")))
        self._output_tei_path.set(str(config.get("tei_output_path", "")))
        self._decision_mode.set(normalize_decision_mode(str(config.get("decision_mode", "heuristic"))))
        self._decision_mode_label.set(decision_mode_to_label(self._decision_mode.get()))
        self._heuristic_profile.set(normalize_heuristic_profile(str(config.get("heuristic_profile", "conservative"))))
        self._heuristic_profile_label.set(heuristic_profile_to_label(self._heuristic_profile.get()))
        self._heading_transform_threshold.set(
            "" if config.get("heading_transform_threshold") is None else str(config.get("heading_transform_threshold"))
        )
        self._heading_diagnostic_threshold.set(
            "" if config.get("heading_diagnostic_threshold") is None else str(config.get("heading_diagnostic_threshold"))
        )
        self._poetry_transform_threshold.set(
            "" if config.get("poetry_transform_threshold") is None else str(config.get("poetry_transform_threshold"))
        )
        self._poetry_diagnostic_threshold.set(
            "" if config.get("poetry_diagnostic_threshold") is None else str(config.get("poetry_diagnostic_threshold"))
        )
        self._ai_aggressiveness.set(normalize_ai_aggressiveness(str(config.get("ai_aggressiveness", "conservative"))))
        self._ai_aggressiveness_label.set(ai_aggressiveness_to_label(self._ai_aggressiveness.get()))
        self._ai_provider.set(str(config.get("ai_provider", "groq")))
        self._ai_api_key.set(str(config.get("ai_api_key", "")))
        self._ai_model.set(str(config.get("ai_model", self.settings.ai.model)))
        self._ai_base_url.set(str(config.get("ai_base_url", self.settings.ai.base_url)))
        self._enable_structure_ai.set(bool(config.get("enable_structure_ai", False)))
        self._enable_editorial_ai.set(bool(config.get("enable_editorial_ai", False)))
        self._enable_ai.set(False)
        self._max_ai_calls.set(max(1, int(config.get("max_ai_calls", Step1Options().max_ai_calls))))
        self._max_structure_ai_calls.set(
            max(1, int(config.get("max_structure_ai_calls", Step1Options().max_structure_ai_calls)))
        )

    @staticmethod
    def _optional_path(raw_value: str, extension: str) -> Path | None:
        value = raw_value.strip()
        if not value:
            return None
        path = Path(value)
        if path.suffix.lower() != extension:
            path = path.with_suffix(extension)
        return path

    @staticmethod
    def _open_file(path: Path) -> None:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)

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
