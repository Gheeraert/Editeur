from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from purh_editorial.config import AppSettings
from purh_editorial.pipeline.step1 import Step1Options, Step1Pipeline


class Step1Dialog(tk.Tk):
    """Fenêtre principale — Étape 1 : préparation éditoriale d'un manuscrit DOCX."""

    _PAD = 10

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.title("PURH Éditorial — Étape 1")
        self.resizable(False, False)

        self._pipeline: Step1Pipeline | None = None
        self._running = False

        # ── Variables de formulaire ───────────────────────────────────────────
        self._input_path = tk.StringVar()
        self._output_dir = tk.StringVar(value=str(settings.exports_dir))
        self._output_name = tk.StringVar()
        self._enable_ai = tk.BooleanVar(value=settings.ai.enabled)
        self._status = tk.StringVar(value="Sélectionnez un fichier DOCX pour commencer.")

        self._input_path.trace_add("write", self._on_input_changed)

        self._build_ui()

    # ── Construction de l'interface ───────────────────────────────────────────

    def _build_ui(self) -> None:
        p = self._PAD
        root_frame = ttk.Frame(self, padding=p)
        root_frame.grid(row=0, column=0, sticky="nsew")

        # Section : fichier source
        src_frame = ttk.LabelFrame(root_frame, text="Fichier source", padding=p)
        src_frame.grid(row=0, column=0, sticky="ew", pady=(0, p))
        src_frame.columnconfigure(0, weight=1)

        self._input_entry = ttk.Entry(src_frame, textvariable=self._input_path, width=60)
        self._input_entry.grid(row=0, column=0, sticky="ew", padx=(0, p))
        ttk.Button(src_frame, text="Parcourir…", command=self._browse_input).grid(row=0, column=1)

        # Section : options
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
                text="(clé API GROQ_API_KEY absente — IA indisponible)",
                foreground="gray",
            ).grid(row=0, column=1, sticky="w", padx=(p, 0))

        # Section : fichier de sortie
        out_frame = ttk.LabelFrame(root_frame, text="Fichier de sortie", padding=p)
        out_frame.grid(row=2, column=0, sticky="ew", pady=(0, p))
        out_frame.columnconfigure(1, weight=1)

        ttk.Label(out_frame, text="Dossier :").grid(row=0, column=0, sticky="w", padx=(0, p))
        self._dir_entry = ttk.Entry(out_frame, textvariable=self._output_dir, width=48)
        self._dir_entry.grid(row=0, column=1, sticky="ew", padx=(0, p))
        ttk.Button(out_frame, text="Choisir…", command=self._browse_output_dir).grid(row=0, column=2)

        ttk.Label(out_frame, text="Nom :").grid(row=1, column=0, sticky="w", padx=(0, p), pady=(6, 0))
        ttk.Entry(out_frame, textvariable=self._output_name, width=48).grid(
            row=1, column=1, sticky="ew", pady=(6, 0)
        )

        # Barre de progression + statut + bouton
        bottom_frame = ttk.Frame(root_frame)
        bottom_frame.grid(row=3, column=0, sticky="ew")
        bottom_frame.columnconfigure(0, weight=1)

        self._progress = ttk.Progressbar(bottom_frame, mode="indeterminate", length=400)
        self._progress.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        ttk.Label(bottom_frame, textvariable=self._status, anchor="w").grid(
            row=1, column=0, sticky="ew"
        )
        self._run_btn = ttk.Button(
            bottom_frame, text="Lancer", command=self._on_run, state="disabled"
        )
        self._run_btn.grid(row=1, column=1, padx=(p, 0))

    # ── Callbacks de navigation ────────────────────────────────────────────────

    def _browse_input(self) -> None:
        initial = Path(self._input_path.get()).parent if self._input_path.get() else self.settings.sources_dir
        path_str = filedialog.askopenfilename(
            title="Sélectionner le manuscrit DOCX",
            filetypes=[("Document Word", "*.docx"), ("Tous les fichiers", "*.*")],
            initialdir=str(initial),
        )
        if path_str:
            self._input_path.set(path_str)

    def _browse_output_dir(self) -> None:
        initial = self._output_dir.get() or str(self.settings.exports_dir)
        chosen = filedialog.askdirectory(title="Choisir le dossier de sortie", initialdir=initial)
        if chosen:
            self._output_dir.set(chosen)

    def _on_input_changed(self, *_) -> None:
        path_str = self._input_path.get().strip()
        if path_str and Path(path_str).suffix.lower() == ".docx":
            self._run_btn.state(["!disabled"])
            # Pré-remplir le nom de sortie si vide ou si l'utilisateur n'a pas encore modifié
            stem = Path(path_str).stem
            if not self._output_name.get() or self._output_name.get().startswith(stem.rsplit("_step1", 1)[0]):
                self._output_name.set(f"{stem}_step1.docx")
        else:
            self._run_btn.state(["disabled"])

    # ── Exécution du pipeline ─────────────────────────────────────────────────

    def _on_run(self) -> None:
        if self._running:
            return

        input_path = Path(self._input_path.get().strip())
        if not input_path.is_file():
            messagebox.showerror("Fichier introuvable", f"Impossible de lire :\n{input_path}")
            return

        out_dir = Path(self._output_dir.get().strip()) if self._output_dir.get().strip() else self.settings.exports_dir
        out_name = self._output_name.get().strip() or f"{input_path.stem}_step1.docx"
        if not out_name.lower().endswith(".docx"):
            out_name += ".docx"
        output_path = out_dir / out_name

        options = Step1Options(
            enable_ai=self._enable_ai.get(),
            output_path=output_path,
        )
        self._set_running(True)
        threading.Thread(
            target=self._run_pipeline,
            args=(input_path, options),
            daemon=True,
        ).start()

    def _run_pipeline(self, input_path: Path, options: Step1Options) -> None:
        try:
            if self._pipeline is None:
                self._pipeline = Step1Pipeline(self.settings)
            result = self._pipeline.run(input_path, options)
            self.after(0, self._on_success, result.output_docx)
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._on_error, exc)

    def _on_success(self, output_path: Path | None) -> None:
        self._set_running(False)
        if output_path and output_path.exists():
            self._status.set(f"Terminé — {output_path.name}")
            if messagebox.showinfo(
                "Traitement terminé",
                f"Le fichier est prêt :\n{output_path}\n\nVoulez-vous l'ouvrir ?",
                type=messagebox.YESNO,
            ) == "yes":
                self._open_file(output_path)
        else:
            self._status.set("Traitement terminé (aucun fichier exporté).")
            messagebox.showinfo("Terminé", "Le pipeline s'est exécuté sans erreur, mais aucun fichier n'a été exporté.")

    def _on_error(self, exc: Exception) -> None:
        self._set_running(False)
        self._status.set(f"Erreur : {exc}")
        messagebox.showerror("Erreur lors du traitement", str(exc))

    def _set_running(self, running: bool) -> None:
        self._running = running
        if running:
            self._progress.start(12)
            self._run_btn.state(["disabled"])
            self._status.set("Traitement en cours…")
        else:
            self._progress.stop()
            self._run_btn.state(["!disabled"])

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
