from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from purh_editorial.corrector.runner import correct_docx


def _default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_corrige.docx")


class CorrectorApp(tk.Tk):
    """Fenêtre unique : choisir un DOCX, lancer la correction, voir le résultat."""

    def __init__(self) -> None:
        super().__init__()
        self.title("PURH — Correcteur ortho-typographique")
        self.resizable(False, False)

        self._input_path = tk.StringVar()
        self._output_path = tk.StringVar()
        self._status = tk.StringVar(value="Sélectionnez un document Word (.docx).")
        self._running = False

        self._build_ui()

    def _build_ui(self) -> None:
        pad = 10
        frame = ttk.Frame(self, padding=pad)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="Document source (.docx)").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Entry(frame, textvariable=self._input_path, width=60).grid(row=1, column=0, sticky="ew")
        ttk.Button(frame, text="Choisir...", command=self._browse_input).grid(row=1, column=1, padx=(pad, 0))

        ttk.Label(frame, text="Document corrigé (sortie)").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(pad, 0)
        )
        ttk.Entry(frame, textvariable=self._output_path, width=60).grid(row=3, column=0, sticky="ew")
        ttk.Button(frame, text="Choisir...", command=self._browse_output).grid(row=3, column=1, padx=(pad, 0))

        self._run_button = ttk.Button(frame, text="Corriger", command=self._on_run)
        self._run_button.grid(row=4, column=0, columnspan=2, pady=(pad, 0), sticky="w")

        ttk.Label(frame, textvariable=self._status, foreground="#333333", wraplength=520).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(pad, 0)
        )

        self._result_text = tk.Text(frame, width=70, height=16, state="disabled")
        self._result_text.grid(row=6, column=0, columnspan=2, pady=(pad, 0))

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Choisir le document source",
            filetypes=[("Documents Word", "*.docx")],
        )
        if not path:
            return
        self._input_path.set(path)
        if not self._output_path.get().strip():
            self._output_path.set(str(_default_output_path(Path(path))))

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Choisir le document de sortie",
            defaultextension=".docx",
            filetypes=[("Documents Word", "*.docx")],
        )
        if path:
            self._output_path.set(path)

    def _on_run(self) -> None:
        if self._running:
            return
        input_str = self._input_path.get().strip()
        output_str = self._output_path.get().strip()
        if not input_str:
            messagebox.showerror("Document manquant", "Choisissez un document source.")
            return
        if not output_str:
            messagebox.showerror("Sortie manquante", "Choisissez un emplacement de sortie.")
            return

        input_path = Path(input_str)
        output_path = Path(output_str)

        if input_path.resolve() == output_path.resolve():
            messagebox.showerror(
                "Chemins identiques", "Le document source et le document de sortie doivent être différents."
            )
            return

        if output_path.exists():
            if not messagebox.askyesno(
                "Fichier existant",
                f"{output_path.name} existe déjà. Le remplacer ?",
            ):
                return
            try:
                output_path.unlink()
            except OSError as exc:
                messagebox.showerror("Erreur", f"Impossible de remplacer le fichier : {exc}")
                return

        self._running = True
        self._run_button.state(["disabled"])
        self._status.set("Correction en cours dans Microsoft Word...")
        self._set_result_text("")

        thread = threading.Thread(
            target=self._run_correction,
            args=(input_path, output_path),
            daemon=True,
        )
        thread.start()

    def _run_correction(self, input_path: Path, output_path: Path) -> None:
        try:
            counts = correct_docx(input_path, output_path)
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._on_error, exc)
            return
        self.after(0, self._on_success, output_path, counts)

    def _on_success(self, output_path: Path, counts: dict[str, int]) -> None:
        self._running = False
        self._run_button.state(["!disabled"])
        total = sum(counts.values())
        self._status.set(f"Terminé. {total} intervention(s) surlignée(s) dans {output_path.name}.")
        lines = [f"Document corrigé : {output_path}", f"Total des interventions : {total}", ""]
        for rule_id, count in sorted(counts.items()):
            if count:
                lines.append(f"{rule_id} : {count}")
        self._set_result_text("\n".join(lines))
        self._open_in_word(output_path)

    def _open_in_word(self, output_path: Path) -> None:
        # correct_word_copy a deja ferme sa propre instance Word en fin de
        # correction (document.Close + word.Quit) : on rouvre le fichier via
        # l'association Windows plutot que de reutiliser une automation COM,
        # pour que l'editrice le retrouve ouvert, pret a relire, sans manip
        # supplementaire.
        try:
            os.startfile(str(output_path))  # noqa: S606
        except OSError as exc:
            messagebox.showwarning(
                "Ouverture impossible",
                f"Le document corrigé n'a pas pu être ouvert automatiquement : {exc}",
            )

    def _on_error(self, exc: Exception) -> None:
        self._running = False
        self._run_button.state(["!disabled"])
        self._status.set("Échec de la correction.")
        self._set_result_text(f"Erreur : {exc}")
        messagebox.showerror("Erreur", str(exc))

    def _set_result_text(self, text: str) -> None:
        self._result_text.configure(state="normal")
        self._result_text.delete("1.0", tk.END)
        self._result_text.insert(tk.END, text)
        self._result_text.configure(state="disabled")


def run_corrector_gui() -> None:
    app = CorrectorApp()
    app.mainloop()
