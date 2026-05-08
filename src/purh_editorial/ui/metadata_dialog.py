# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import field
from typing import Callable
import tkinter as tk
from tkinter import ttk

from purh_editorial.model.document import Metadata, PersonMetadata


_ROLE_LABELS = {
    "pbd": "Auteur",
    "edt": "Éditeur scientifique",
    "trl": "Traducteur",
}
_ROLE_CODES = {v: k for k, v in _ROLE_LABELS.items()}
_ROLE_LIST = list(_ROLE_LABELS.values())


class _PersonRow:
    """Ligne d'un contributeur dans le tableau dynamique."""

    def __init__(self, parent: ttk.Frame, row: int, on_delete: Callable[[], None]) -> None:
        self.forename = tk.StringVar()
        self.surname = tk.StringVar()
        self.affiliation = tk.StringVar()
        self.role_label = tk.StringVar(value="Auteur")

        ttk.Entry(parent, textvariable=self.forename, width=14).grid(
            row=row, column=0, padx=(0, 4), pady=2, sticky="ew"
        )
        ttk.Entry(parent, textvariable=self.surname, width=16).grid(
            row=row, column=1, padx=(0, 4), pady=2, sticky="ew"
        )
        ttk.Entry(parent, textvariable=self.affiliation, width=22).grid(
            row=row, column=2, padx=(0, 4), pady=2, sticky="ew"
        )
        ttk.Combobox(
            parent,
            textvariable=self.role_label,
            values=_ROLE_LIST,
            state="readonly",
            width=18,
        ).grid(row=row, column=3, padx=(0, 4), pady=2)
        ttk.Button(parent, text="✕", width=3, command=on_delete).grid(
            row=row, column=4, pady=2
        )

    def to_person(self) -> PersonMetadata:
        role_code = _ROLE_CODES.get(self.role_label.get(), "pbd")
        return PersonMetadata(
            forename=self.forename.get().strip(),
            surname=self.surname.get().strip(),
            affiliation=self.affiliation.get().strip(),
            role=role_code,
        )


class MetadataDialog(tk.Toplevel):
    """Boîte de dialogue facultative de saisie des métadonnées du livre."""

    _PAD = 8

    def __init__(self, parent: tk.Tk, initial: Metadata | None = None) -> None:
        super().__init__(parent)
        self.title("Métadonnées du livre")
        self.resizable(True, True)
        self.minsize(760, 560)
        self.grab_set()

        self._result: Metadata | None = None
        self._person_rows: list[_PersonRow] = []

        self._title_var = tk.StringVar()
        self._subtitle_var = tk.StringVar()
        self._series_var = tk.StringVar()
        self._collection_var = tk.StringVar()
        self._volume_var = tk.StringVar()
        self._publisher_var = tk.StringVar(value="Presses universitaires de Rouen et du Havre")
        self._pub_place_var = tk.StringVar(value="Mont-Saint-Aignan")
        self._isbn_print_var = tk.StringVar()
        self._isbn_epub_var = tk.StringVar()
        self._isbn_pdf_var = tk.StringVar()
        self._issn_var = tk.StringVar()
        self._pub_date_var = tk.StringVar()
        self._legal_dep_var = tk.StringVar()
        self._edition_note_var = tk.StringVar()

        self._build_ui()

        if initial is not None:
            self._load_metadata(initial)

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window(self)

    # ── Construction UI ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        p = self._PAD
        outer = ttk.Frame(self, padding=p)
        outer.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        # Cadre défilable
        canvas = tk.Canvas(outer, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        outer.rowconfigure(0, weight=1)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        sb.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=sb.set)

        root = ttk.Frame(canvas, padding=p)
        win_id = canvas.create_window((0, 0), window=root, anchor="nw")
        root.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win_id, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        root.columnconfigure(1, weight=1)
        r = 0

        # ── Identification ──────────────────────────────────────────────────
        id_frame = ttk.LabelFrame(root, text="Identification", padding=p)
        id_frame.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(0, p))
        id_frame.columnconfigure(1, weight=1)
        r += 1

        for lbl, var in (
            ("Titre principal *", self._title_var),
            ("Sous-titre", self._subtitle_var),
            ("Titre de la série", self._series_var),
            ("Collection", self._collection_var),
            ("Numéro de volume", self._volume_var),
        ):
            ttk.Label(id_frame, text=lbl).grid(row=id_frame.grid_size()[1], column=0, sticky="w", pady=2)
            ttk.Entry(id_frame, textvariable=var).grid(
                row=id_frame.grid_size()[1] - 1, column=1, sticky="ew", padx=(8, 0), pady=2
            )

        # ── Contributeurs ───────────────────────────────────────────────────
        contrib_frame = ttk.LabelFrame(root, text="Contributeurs", padding=p)
        contrib_frame.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(0, p))
        contrib_frame.columnconfigure(0, weight=1)
        contrib_frame.columnconfigure(1, weight=1)
        contrib_frame.columnconfigure(2, weight=2)
        r += 1

        # En-têtes colonnes
        for col, lbl in enumerate(("Prénom", "Nom", "Affiliation", "Rôle", "")):
            ttk.Label(contrib_frame, text=lbl, font=("TkDefaultFont", 9, "bold")).grid(
                row=0, column=col, sticky="w", padx=(0, 4)
            )

        self._contrib_inner = ttk.Frame(contrib_frame)
        self._contrib_inner.grid(row=1, column=0, columnspan=5, sticky="ew")
        self._contrib_inner.columnconfigure(0, weight=1)
        self._contrib_inner.columnconfigure(1, weight=1)
        self._contrib_inner.columnconfigure(2, weight=2)

        ttk.Button(
            contrib_frame, text="+ Ajouter un contributeur", command=self._add_person_row
        ).grid(row=2, column=0, columnspan=5, sticky="w", pady=(6, 0))

        # ── Publication ─────────────────────────────────────────────────────
        pub_frame = ttk.LabelFrame(root, text="Publication", padding=p)
        pub_frame.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(0, p))
        pub_frame.columnconfigure(1, weight=1)
        pub_frame.columnconfigure(3, weight=1)
        r += 1

        pub_fields = [
            (0, 0, "Éditeur", self._publisher_var),
            (1, 0, "Lieu", self._pub_place_var),
            (2, 0, "Date de publication", self._pub_date_var),
            (3, 0, "Dépôt légal", self._legal_dep_var),
            (4, 0, "Note d'édition", self._edition_note_var),
        ]
        for fr, fc, lbl, var in pub_fields:
            ttk.Label(pub_frame, text=lbl).grid(row=fr, column=fc, sticky="w", pady=2)
            ttk.Entry(pub_frame, textvariable=var).grid(
                row=fr, column=fc + 1, sticky="ew", padx=(8, 0), pady=2
            )

        # ── Identifiants ────────────────────────────────────────────────────
        id2_frame = ttk.LabelFrame(root, text="Identifiants", padding=p)
        id2_frame.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(0, p))
        id2_frame.columnconfigure(1, weight=1)
        id2_frame.columnconfigure(3, weight=1)
        r += 1

        id_fields = [
            (0, 0, "ISBN (imprimé)", self._isbn_print_var),
            (1, 0, "ISBN (ePub)", self._isbn_epub_var),
            (0, 2, "ISBN (PDF)", self._isbn_pdf_var),
            (1, 2, "ISSN", self._issn_var),
        ]
        for fr, fc, lbl, var in id_fields:
            ttk.Label(id2_frame, text=lbl).grid(row=fr, column=fc, sticky="w", pady=2, padx=(8 if fc else 0, 0))
            ttk.Entry(id2_frame, textvariable=var, width=20).grid(
                row=fr, column=fc + 1, sticky="ew", padx=(4, 8), pady=2
            )

        # ── Boutons ─────────────────────────────────────────────────────────
        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="e", pady=(p, 0))
        ttk.Button(btn_frame, text="Annuler", command=self._on_cancel).pack(side="right", padx=(p, 0))
        ttk.Button(btn_frame, text="Valider", command=self._on_validate).pack(side="right")

    # ── Gestion des contributeurs ─────────────────────────────────────────────

    def _add_person_row(self, person: PersonMetadata | None = None) -> None:
        row_index = len(self._person_rows)

        def _delete(idx: int = row_index) -> None:
            # Reconstruit la liste proprement après suppression
            if idx < len(self._person_rows):
                self._person_rows.pop(idx)
            self._refresh_contrib_grid()

        row = _PersonRow(self._contrib_inner, row_index, on_delete=_delete)
        self._person_rows.append(row)
        if person is not None:
            row.forename.set(person.forename)
            row.surname.set(person.surname)
            row.affiliation.set(person.affiliation)
            row.role_label.set(_ROLE_LABELS.get(person.role, "Auteur"))

    def _refresh_contrib_grid(self) -> None:
        for widget in self._contrib_inner.winfo_children():
            widget.destroy()
        rows_data = [
            PersonMetadata(
                forename=r.forename.get(),
                surname=r.surname.get(),
                affiliation=r.affiliation.get(),
                role=_ROLE_CODES.get(r.role_label.get(), "pbd"),
            )
            for r in self._person_rows
        ]
        self._person_rows.clear()
        for person in rows_data:
            self._add_person_row(person)

    # ── Chargement / validation ───────────────────────────────────────────────

    def _load_metadata(self, meta: Metadata) -> None:
        self._title_var.set(meta.title or "")
        self._subtitle_var.set(meta.subtitle or "")
        self._series_var.set(meta.series_title or "")
        self._collection_var.set(meta.collection or "")
        self._volume_var.set(meta.volume_number or "")
        self._publisher_var.set(meta.publisher or "Presses universitaires de Rouen et du Havre")
        self._pub_place_var.set(meta.pub_place or "Mont-Saint-Aignan")
        self._isbn_print_var.set(meta.isbn_print or "")
        self._isbn_epub_var.set(meta.isbn_epub or "")
        self._isbn_pdf_var.set(meta.isbn_pdf or "")
        self._issn_var.set(meta.issn or "")
        self._pub_date_var.set(meta.publication_date or "")
        self._legal_dep_var.set(meta.legal_deposit_date or "")
        self._edition_note_var.set(meta.edition_note or "")
        for person in (meta.persons or []):
            self._add_person_row(person)

    def _on_validate(self) -> None:
        self._result = Metadata(
            title=self._title_var.get().strip() or None,
            subtitle=self._subtitle_var.get().strip() or None,
            persons=[r.to_person() for r in self._person_rows
                     if r.forename.get().strip() or r.surname.get().strip()],
            series_title=self._series_var.get().strip() or None,
            collection=self._collection_var.get().strip() or None,
            volume_number=self._volume_var.get().strip() or None,
            publisher=self._publisher_var.get().strip() or None,
            pub_place=self._pub_place_var.get().strip() or None,
            isbn_print=self._isbn_print_var.get().strip() or None,
            isbn_epub=self._isbn_epub_var.get().strip() or None,
            isbn_pdf=self._isbn_pdf_var.get().strip() or None,
            issn=self._issn_var.get().strip() or None,
            publication_date=self._pub_date_var.get().strip() or None,
            legal_deposit_date=self._legal_dep_var.get().strip() or None,
            edition_note=self._edition_note_var.get().strip() or None,
        )
        self.destroy()

    def _on_cancel(self) -> None:
        self._result = None
        self.destroy()

    @property
    def result(self) -> Metadata | None:
        return self._result


def open_metadata_dialog(parent: tk.Tk, initial: Metadata | None = None) -> Metadata | None:
    """Ouvre la boîte de dialogue et retourne les métadonnées saisies, ou None si annulé."""
    dlg = MetadataDialog(parent, initial=initial)
    return dlg.result
