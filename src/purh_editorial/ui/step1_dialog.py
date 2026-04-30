from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from purh_editorial.config import AppSettings
from purh_editorial.pipeline.step1 import Step1Options, Step1Pipeline, Step1Result


class Step1Dialog(tk.Tk):
    """Fenetre principale - Etape 1 : preparation editoriale d'un manuscrit DOCX."""

    _PAD = 10

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.title("PURH Editorial - Etape 1")
        self.resizable(False, False)

        self._pipeline: Step1Pipeline | None = None
        self._running = False

        self._input_path = tk.StringVar()
        self._output_docx_path = tk.StringVar()
        self._output_tei_path = tk.StringVar()
        self._enable_ai = tk.BooleanVar(value=False)
        self._status = tk.StringVar(value="Selectionnez un fichier DOCX pour commencer.")

        self._input_path.trace_add("write", self._on_input_changed)
        self._build_ui()

    def _build_ui(self) -> None:
        p = self._PAD
        root_frame = ttk.Frame(self, padding=p)
        root_frame.grid(row=0, column=0, sticky="nsew")

        src_frame = ttk.LabelFrame(root_frame, text="Fichier source", padding=p)
        src_frame.grid(row=0, column=0, sticky="ew", pady=(0, p))
        src_frame.columnconfigure(0, weight=1)

        self._input_entry = ttk.Entry(src_frame, textvariable=self._input_path, width=60)
        self._input_entry.grid(row=0, column=0, sticky="ew", padx=(0, p))
        ttk.Button(src_frame, text="Parcourir...", command=self._browse_input).grid(row=0, column=1)

        opt_frame = ttk.LabelFrame(root_frame, text="Options", padding=p)
        opt_frame.grid(row=1, column=0, sticky="ew", pady=(0, p))
        self._ai_check = ttk.Checkbutton(
            opt_frame,
            text="Activer l'IA (Groq)",
            variable=self._enable_ai,
        )
        self._ai_check.grid(row=0, column=0, sticky="w")
        if not self.settings.ai.enabled:
            self._ai_check.state(["disabled"])
            ttk.Label(
                opt_frame,
                text="(cle API GROQ_API_KEY absente - IA indisponible)",
                foreground="gray",
            ).grid(row=0, column=1, sticky="w", padx=(p, 0))

        out_frame = ttk.LabelFrame(root_frame, text="Sorties optionnelles", padding=p)
        out_frame.grid(row=2, column=0, sticky="ew", pady=(0, p))
        out_frame.columnconfigure(1, weight=1)

        ttk.Label(out_frame, text="DOCX sortie :").grid(row=0, column=0, sticky="w", padx=(0, p))
        ttk.Entry(out_frame, textvariable=self._output_docx_path, width=48).grid(
            row=0, column=1, sticky="ew", padx=(0, p)
        )
        ttk.Button(out_frame, text="Choisir...", command=self._browse_output_docx).grid(row=0, column=2)

        ttk.Label(out_frame, text="XML-TEI sortie :").grid(row=1, column=0, sticky="w", padx=(0, p), pady=(6, 0))
        ttk.Entry(out_frame, textvariable=self._output_tei_path, width=48).grid(
            row=1, column=1, sticky="ew", padx=(0, p), pady=(6, 0)
        )
        ttk.Button(out_frame, text="Choisir...", command=self._browse_output_tei).grid(row=1, column=2, pady=(6, 0))

        bottom_frame = ttk.Frame(root_frame)
        bottom_frame.grid(row=3, column=0, sticky="ew")
        bottom_frame.columnconfigure(0, weight=1)

        self._progress = ttk.Progressbar(bottom_frame, mode="indeterminate", length=420)
        self._progress.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        ttk.Label(bottom_frame, textvariable=self._status, anchor="w").grid(row=1, column=0, sticky="ew")
        self._run_btn = ttk.Button(bottom_frame, text="Lancer", command=self._on_run, state="disabled")
        self._run_btn.grid(row=1, column=1, padx=(p, 0))

    def _browse_input(self) -> None:
        initial = Path(self._input_path.get()).parent if self._input_path.get() else self.settings.sources_dir
        path_str = filedialog.askopenfilename(
            title="Selectionner le manuscrit DOCX",
            filetypes=[("Document Word", "*.docx"), ("Tous les fichiers", "*.*")],
            initialdir=str(initial),
        )
        if path_str:
            self._input_path.set(path_str)

    def _browse_output_docx(self) -> None:
        initial = self._output_docx_path.get() or str(self.settings.exports_dir / "manuscrit_step1.docx")
        chosen = filedialog.asksaveasfilename(
            title="Choisir le DOCX de sortie",
            defaultextension=".docx",
            filetypes=[("Document Word", "*.docx"), ("Tous les fichiers", "*.*")],
            initialfile=Path(initial).name,
            initialdir=str(Path(initial).parent),
        )
        if chosen:
            self._output_docx_path.set(chosen)

    def _browse_output_tei(self) -> None:
        initial = self._output_tei_path.get() or str(self.settings.exports_dir / "manuscrit_step1.xml")
        chosen = filedialog.asksaveasfilename(
            title="Choisir le XML-TEI de sortie",
            defaultextension=".xml",
            filetypes=[("XML", "*.xml"), ("Tous les fichiers", "*.*")],
            initialfile=Path(initial).name,
            initialdir=str(Path(initial).parent),
        )
        if chosen:
            self._output_tei_path.set(chosen)

    def _on_input_changed(self, *_) -> None:
        path_str = self._input_path.get().strip()
        if path_str and Path(path_str).suffix.lower() == ".docx":
            self._run_btn.state(["!disabled"])
            stem = Path(path_str).stem
            if not self._output_docx_path.get().strip():
                self._output_docx_path.set(str(self.settings.exports_dir / f"{stem}_step1.docx"))
            if not self._output_tei_path.get().strip():
                self._output_tei_path.set(str(self.settings.exports_dir / f"{stem}_step1.xml"))
        else:
            self._run_btn.state(["disabled"])

    def _on_run(self) -> None:
        if self._running:
            return

        input_path = Path(self._input_path.get().strip())
        if not input_path.is_file():
            messagebox.showerror("Fichier introuvable", f"Impossible de lire :\n{input_path}")
            return

        options = Step1Options(
            enable_ai=self._enable_ai.get(),
            output_path=self._optional_path(self._output_docx_path.get(), ".docx"),
            tei_output_path=self._optional_path(self._output_tei_path.get(), ".xml"),
        )

        self._set_running(True)
        threading.Thread(target=self._run_pipeline, args=(input_path, options), daemon=True).start()

    def _run_pipeline(self, input_path: Path, options: Step1Options) -> None:
        try:
            if self._pipeline is None:
                self._pipeline = Step1Pipeline(self.settings)
            result = self._pipeline.run(input_path, options)
            self.after(0, self._on_success, result)
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._on_error, exc)

    def _on_success(self, result: Step1Result) -> None:
        self._set_running(False)
        report = result.pipeline_result.report
        self._status.set("Traitement termine.")
        messagebox.showinfo("Traitement termine", self._build_result_summary(result))

        if result.output_docx and result.output_docx.exists():
            if messagebox.showinfo(
                "Ouvrir le DOCX ?",
                f"Le DOCX de relecture est pret :\n{result.output_docx}\n\nVoulez-vous l'ouvrir ?",
                type=messagebox.YESNO,
            ) == "yes":
                self._open_file(result.output_docx)
        if report.warnings:
            self._status.set("Termine avec warnings techniques.")

    def _on_error(self, exc: Exception) -> None:
        self._set_running(False)
        self._status.set(f"Erreur : {exc}")
        messagebox.showerror("Erreur lors du traitement", str(exc))

    def _set_running(self, running: bool) -> None:
        self._running = running
        if running:
            self._progress.start(12)
            self._run_btn.state(["disabled"])
            self._status.set("Traitement en cours...")
        else:
            self._progress.stop()
            self._run_btn.state(["!disabled"])

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
    def _build_result_summary(result: Step1Result) -> str:
        report = result.pipeline_result.report
        lines: list[str] = []

        lines.append("Corrections appliquees")
        lines.append(f"- Transformations: {len(report.transformations)}")

        lines.append("")
        lines.append("Diagnostics a verifier")
        if report.diagnostics:
            for diag in report.diagnostics:
                rid = diag.rule_id or "(sans rule_id)"
                target = diag.target_ref or ""
                lines.append(f"- [{rid}] {diag.severity} / {diag.category} / target={target}")
                lines.append(f"  {diag.message}")
                if diag.evidence and diag.evidence.excerpt:
                    lines.append(f"  Extrait: {diag.evidence.excerpt.strip()}")
        else:
            lines.append("- Aucun diagnostic.")

        lines.append("")
        lines.append("Warnings techniques")
        if report.warnings:
            for warning in report.warnings:
                lines.append(f"- {warning}")
        else:
            lines.append("- Aucun warning.")

        lines.append("")
        lines.append("Sorties")
        if result.output_docx:
            lines.append(f"- DOCX: {result.output_docx}")
        else:
            lines.append("- DOCX: non demande")
        if result.pipeline_result.tei_xml:
            lines.append("- XML-TEI: genere")
        else:
            lines.append("- XML-TEI: non genere")

        lines.append("")
        lines.append("Resume modules")
        for run in report.module_runs:
            lines.append(f"- {run.module_name} ({run.status}): {run.summary}")

        lines.append("")
        lines.append("Note: pas de diff source/corrige complet dans cette interface.")
        return "\n".join(lines)

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
