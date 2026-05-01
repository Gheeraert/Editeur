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


def normalize_decision_mode(value: str | None) -> str:
    if not value:
        return "heuristic"
    mode = str(value).strip().lower()
    if mode in ALLOWED_DECISION_MODES:
        return mode
    return "heuristic"


def normalize_ai_aggressiveness(value: str | None) -> str:
    if not value:
        return "conservative"
    mode = str(value).strip().lower()
    if mode in ALLOWED_AI_AGGRESSIVENESS:
        return mode
    return "conservative"


def derive_ai_flags_from_decision_mode(decision_mode: str) -> tuple[bool, bool]:
    mode = normalize_decision_mode(decision_mode)
    if mode == "heuristic_ai_local":
        return True, False
    if mode in {"deterministic", "heuristic", "ai_exploratory"}:
        return False, False
    return False, False


def build_config_dict(
    source_path: str,
    output_docx_path: str,
    tei_output_path: str,
    decision_mode: str,
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
        # Decision mode is authoritative when explicitly provided in config.
        structure_ai, editorial_ai = derive_ai_flags_from_decision_mode(str(merged["decision_mode"]))
        merged["enable_structure_ai"] = structure_ai
        merged["enable_editorial_ai"] = editorial_ai
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
        self._decision_mode = tk.StringVar(value="")
        self._ai_aggressiveness = tk.StringVar(value="conservative")
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
        root = ttk.Frame(self, padding=p)
        root.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)

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

        opt_frame = ttk.LabelFrame(root, text="3. Options", padding=p)
        opt_frame.grid(row=2, column=0, sticky="ew", pady=(0, p))
        ttk.Checkbutton(
            opt_frame,
            text="Activer les suggestions IA",
            variable=self._enable_ai,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(opt_frame, text="Max appels IA:").grid(row=0, column=1, sticky="w", padx=(16, 6))
        ttk.Spinbox(opt_frame, from_=1, to=20, textvariable=self._max_ai_calls, width=5).grid(row=0, column=2, sticky="w")
        if not self.settings.ai.enabled:
            ttk.Label(
                opt_frame,
                text="(IA indisponible: GROQ_API_KEY absente)",
                foreground="gray",
            ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

        actions_frame = ttk.Frame(root)
        actions_frame.grid(row=3, column=0, sticky="ew", pady=(0, p))
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
        result_frame.grid(row=4, column=0, sticky="nsew")
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
        raw_decision_mode = self._decision_mode.get().strip()
        decision_mode = normalize_decision_mode(raw_decision_mode) if raw_decision_mode else None
        ai_aggressiveness = normalize_ai_aggressiveness(self._ai_aggressiveness.get())
        # Keep current UI behavior: checkbox still toggles editorial AI.
        enable_editorial_ai = bool(self._enable_ai.get() or self._enable_editorial_ai.get())
        options = Step1Options(
            enable_ai=self._enable_ai.get(),
            enable_structure_ai=self._enable_structure_ai.get(),
            enable_editorial_ai=enable_editorial_ai,
            decision_mode=decision_mode,
            ai_aggressiveness=ai_aggressiveness,
            ai_provider=self._ai_provider.get().strip() or "groq",
            ai_api_key=self._ai_api_key.get().strip() or None,
            ai_model=self._ai_model.get().strip() or None,
            ai_base_url=self._ai_base_url.get().strip() or None,
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
        return build_config_dict(
            source_path=self._input_path.get().strip(),
            output_docx_path=self._output_docx_path.get().strip(),
            tei_output_path=self._output_tei_path.get().strip(),
            decision_mode=self._decision_mode.get(),
            ai_aggressiveness=self._ai_aggressiveness.get(),
            ai_provider=self._ai_provider.get(),
            ai_api_key=self._ai_api_key.get(),
            ai_model=self._ai_model.get(),
            ai_base_url=self._ai_base_url.get(),
            enable_structure_ai=self._enable_structure_ai.get(),
            enable_editorial_ai=self._enable_editorial_ai.get(),
            enable_ai=self._enable_ai.get(),
            max_ai_calls=self._max_ai_calls.get(),
            max_structure_ai_calls=self._max_structure_ai_calls.get(),
        )

    def _apply_config_to_ui(self, config: dict[str, object]) -> None:
        self._input_path.set(str(config.get("source_path", "")))
        self._output_docx_path.set(str(config.get("output_docx_path", "")))
        self._output_tei_path.set(str(config.get("tei_output_path", "")))
        self._decision_mode.set(str(config.get("decision_mode", "")))
        self._ai_aggressiveness.set(
            normalize_ai_aggressiveness(str(config.get("ai_aggressiveness", "conservative")))
        )
        self._ai_provider.set(str(config.get("ai_provider", "groq")))
        self._ai_api_key.set(str(config.get("ai_api_key", "")))
        self._ai_model.set(str(config.get("ai_model", self.settings.ai.model)))
        self._ai_base_url.set(str(config.get("ai_base_url", self.settings.ai.base_url)))
        self._enable_structure_ai.set(bool(config.get("enable_structure_ai", False)))
        self._enable_editorial_ai.set(bool(config.get("enable_editorial_ai", False)))
        self._enable_ai.set(bool(config.get("enable_ai", False)))
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


def run_step1_dialog() -> None:
    from purh_editorial.config import load_settings

    settings = load_settings()
    app = Step1Dialog(settings=settings)
    app.mainloop()
