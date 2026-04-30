from __future__ import annotations

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
        self._progress.grid(row=0, column=0, sticky="ew", padx=(0, p))
        self._run_btn = ttk.Button(
            actions_frame,
            text="Lancer l'analyse editoriale",
            command=self._on_run,
            state="disabled",
        )
        self._run_btn.grid(row=0, column=1)
        ttk.Label(actions_frame, textvariable=self._status, anchor="w").grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

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
        options = Step1Options(
            enable_ai=self._enable_ai.get(),
            max_ai_calls=max_ai_calls,
            output_path=self._optional_path(self._output_docx_path.get(), ".docx"),
            tei_output_path=self._optional_path(self._output_tei_path.get(), ".xml"),
        )

        self._set_running(True)
        threading.Thread(target=self._run_pipeline, args=(source, options), daemon=True).start()

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
