from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from purh_editorial.corrector.ai import (
    AIClient,
    GeminiAIClient,
    GroqAIClient,
    OllamaAIClient,
    active_ollama_model,
    list_ollama_models,
)
from purh_editorial.corrector.runner import correct_docx

_CONFIDENTIALITY_WARNING = (
    "Le mode distant envoie le texte de chaque paragraphe analysé à un service "
    "tiers (Gemini ou Groq) via Internet. Les tapuscrits peuvent contenir des "
    "travaux inédits soumis au secret de la recherche ou sous embargo.\n\n"
    "Confirmez-vous l'envoi de ce document à un service distant ?"
)


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
        # Decochee par defaut : la reapplication du style "Normal" est une
        # operation destructive-puis-reconstructive (mise en forme directe
        # sauvegardee puis restauree) reservee aux documents ou l'artefact
        # de rendu Word est effectivement observe, pas une correction a
        # appliquer systematiquement.
        self._reapply_normal_style = tk.BooleanVar(value=False)

        # Aucune valeur par defaut pour le MODE : l'editrice doit choisir
        # explicitement Desactivee/Locale/Distante a chaque lancement
        # (decision actee avec l'utilisateur - pas de mode memorise d'une
        # session a l'autre). Le nom de modele et la cle API, en revanche,
        # sont prerempits depuis l'environnement (OLLAMA_MODEL,
        # GEMINI_API_KEY, GROQ_API_KEY - voir .env.example) par simple
        # commodite : retaper une cle de 40 caracteres a chaque lancement
        # n'apporte rien a la decision explicite de mode, et le champ reste
        # librement modifiable.
        self._ai_mode = tk.StringVar(value="")
        self._ollama_model = tk.StringVar(value=os.environ.get("OLLAMA_MODEL", ""))
        self._remote_provider = tk.StringVar(value="")
        self._api_key = tk.StringVar(value="")
        # Ne declenche la premiere interrogation d'Ollama (liste des
        # modeles + modele actif) qu'a la premiere selection du mode
        # local, pas au demarrage de l'application - voir
        # _update_ai_fields_state / _refresh_ollama_models.
        self._ollama_models_loaded = False

        self._running = False

        self._build_ui()
        self._ai_mode.trace_add("write", lambda *_args: self._update_ai_fields_state())
        self._remote_provider.trace_add(
            "write", lambda *_args: self._prefill_api_key_from_environment()
        )
        self._update_ai_fields_state()

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

        ttk.Checkbutton(
            frame,
            text="Réappliquer le style 'Normal' ? (déconseillé sur textes longs)",
            variable=self._reapply_normal_style,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(pad, 0))

        self._build_ai_section(frame, row=5, pad=pad)

        self._run_button = ttk.Button(frame, text="Corriger", command=self._on_run)
        self._run_button.grid(row=6, column=0, columnspan=2, pady=(pad, 0), sticky="w")

        ttk.Label(frame, textvariable=self._status, foreground="#333333", wraplength=520).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(pad, 0)
        )

        self._progress = ttk.Progressbar(frame, mode="indeterminate")
        self._progress.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(pad, 0))

        self._result_text = tk.Text(frame, width=70, height=16, state="disabled")
        self._result_text.grid(row=9, column=0, columnspan=2, pady=(pad, 0))

    def _build_ai_section(self, frame: ttk.Frame, row: int, pad: int) -> None:
        ai_frame = ttk.LabelFrame(frame, text="Assistance IA (au-delà de l'ortho-typographie)")
        ai_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(pad, 0))

        ttk.Radiobutton(
            ai_frame, text="Désactivée", variable=self._ai_mode, value="disabled"
        ).grid(row=0, column=0, sticky="w", padx=(0, pad))
        ttk.Radiobutton(
            ai_frame, text="Locale (Ollama)", variable=self._ai_mode, value="local"
        ).grid(row=0, column=1, sticky="w", padx=(0, pad))
        ttk.Radiobutton(
            ai_frame, text="Distante (API)", variable=self._ai_mode, value="remote"
        ).grid(row=0, column=2, sticky="w")

        self._ollama_row = ttk.Frame(ai_frame)
        self._ollama_row.grid(row=1, column=0, columnspan=3, sticky="w", pady=(pad // 2, 0))
        ttk.Label(self._ollama_row, text="Modèle Ollama (préselectionné, modifiable) :").grid(
            row=0, column=0
        )
        self._ollama_model_entry = ttk.Combobox(
            self._ollama_row, textvariable=self._ollama_model, width=28
        )
        self._ollama_model_entry.grid(row=0, column=1, padx=(pad // 2, 0))
        self._ollama_refresh_button = ttk.Button(
            self._ollama_row, text="Rafraîchir", command=self._refresh_ollama_models
        )
        self._ollama_refresh_button.grid(row=0, column=2, padx=(pad // 2, 0))

        self._remote_row = ttk.Frame(ai_frame)
        self._remote_row.grid(row=2, column=0, columnspan=3, sticky="w", pady=(pad // 2, 0))
        self._gemini_radio = ttk.Radiobutton(
            self._remote_row, text="Gemini", variable=self._remote_provider, value="gemini"
        )
        self._gemini_radio.grid(row=0, column=0, sticky="w")
        self._groq_radio = ttk.Radiobutton(
            self._remote_row, text="Groq", variable=self._remote_provider, value="groq"
        )
        self._groq_radio.grid(row=0, column=1, sticky="w", padx=(pad, 0))
        ttk.Label(self._remote_row, text="Clé API :").grid(row=0, column=2, padx=(pad, 0))
        self._api_key_entry = ttk.Entry(
            self._remote_row, textvariable=self._api_key, width=30, show="•"
        )
        self._api_key_entry.grid(row=0, column=3, padx=(pad // 2, 0))

    def _update_ai_fields_state(self) -> None:
        mode = self._ai_mode.get()
        ollama_state = "normal" if mode == "local" else "disabled"
        remote_state = "normal" if mode == "remote" else "disabled"
        self._ollama_model_entry.configure(state=ollama_state)
        self._ollama_refresh_button.configure(state=ollama_state)
        self._gemini_radio.configure(state=remote_state)
        self._groq_radio.configure(state=remote_state)
        self._api_key_entry.configure(state=remote_state)
        if mode == "local" and not self._ollama_models_loaded:
            self._refresh_ollama_models()

    def _refresh_ollama_models(self) -> None:
        """Interroge Ollama pour lister les modèles installés et présélectionner
        celui actuellement chargé en mémoire.

        Ne remplace jamais une valeur déjà présente dans le champ (préremplie
        depuis `OLLAMA_MODEL` ou saisie manuellement) : ne fait que proposer
        un choix par défaut et alimenter la liste déroulante, jamais
        n'impose un modèle. Interrogation synchrone à délai court
        (`_AVAILABILITY_TIMEOUT_SECONDS` côté client) déclenchée par une
        action explicite (sélection du mode local, ou clic sur
        « Rafraîchir »), pas au démarrage de l'application.
        """
        self._ollama_models_loaded = True
        models = list_ollama_models()
        self._ollama_model_entry.configure(values=models)
        if not self._ollama_model.get().strip():
            default_model = active_ollama_model()
            if default_model is None and models:
                default_model = models[0]
            if default_model:
                self._ollama_model.set(default_model)

    def _prefill_api_key_from_environment(self) -> None:
        # Ne remplace jamais une cle deja saisie manuellement par
        # l'editrice : ne prerempit que si le champ est encore vide,
        # typiquement juste apres avoir choisi le fournisseur.
        if self._api_key.get().strip():
            return
        env_var = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY"}.get(
            self._remote_provider.get()
        )
        if env_var is None:
            return
        value = os.environ.get(env_var, "")
        if value:
            self._api_key.set(value)

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

    def _build_ai_client(self) -> AIClient | None:
        """Construit le client IA selon le mode choisi, ou lève `ValueError`
        avec un message destiné à l'éditrice si la configuration est
        incomplète.

        Ne présélectionne jamais un mode par défaut : un mode vide (aucun
        bouton radio coché) est traité comme une configuration incomplète,
        pas comme "désactivé", pour forcer un choix explicite à chaque
        lancement.
        """
        mode = self._ai_mode.get()
        if mode == "":
            raise ValueError("Choisissez un mode d'assistance IA (y compris « Désactivée »).")
        if mode == "disabled":
            return None
        if mode == "local":
            model = self._ollama_model.get().strip()
            if not model:
                raise ValueError("Indiquez le nom du modèle chargé dans Ollama.")
            return OllamaAIClient(model=model)
        if mode == "remote":
            provider = self._remote_provider.get()
            api_key = self._api_key.get().strip()
            if provider == "":
                raise ValueError("Choisissez un fournisseur distant (Gemini ou Groq).")
            if not api_key:
                raise ValueError("Indiquez une clé API pour le fournisseur choisi.")
            if provider == "gemini":
                return GeminiAIClient(api_key=api_key)
            return GroqAIClient(api_key=api_key)
        raise ValueError(f"Mode d'assistance IA inconnu : {mode!r}")

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

        try:
            ai_client = self._build_ai_client()
        except ValueError as exc:
            messagebox.showerror("Assistance IA", str(exc))
            return

        # Avertissement affiché a chaque lancement en mode distant (aucun
        # mode n'est memorise d'une session a l'autre - voir _build_ai_client) :
        # le tapuscrit sera envoye a un service tiers, l'editrice doit
        # confirmer explicitement a chaque fois, pas seulement la premiere.
        if self._ai_mode.get() == "remote":
            if not messagebox.askyesno("Confidentialité", _CONFIDENTIALITY_WARNING):
                return

        self._running = True
        self._run_button.state(["disabled"])
        status = "Correction en cours dans Microsoft Word..."
        if ai_client is not None:
            status += " L'assistance IA peut allonger sensiblement la durée du traitement."
        self._status.set(status)
        self._set_result_text("")
        self._progress.start(12)

        thread = threading.Thread(
            target=self._run_correction,
            args=(input_path, output_path, self._reapply_normal_style.get(), ai_client),
            daemon=True,
        )
        thread.start()

    def _run_correction(
        self,
        input_path: Path,
        output_path: Path,
        reapply_normal_style: bool,
        ai_client: AIClient | None,
    ) -> None:
        try:
            counts = correct_docx(
                input_path,
                output_path,
                reapply_normal_style=reapply_normal_style,
                ai_client=ai_client,
            )
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._on_error, exc)
            return
        self.after(0, self._on_success, output_path, counts)

    def _on_success(self, output_path: Path, counts: dict[str, int]) -> None:
        self._running = False
        self._progress.stop()
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
        self._progress.stop()
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
