from __future__ import annotations

import copy
import re

from purh_editorial.model import BibliographyItem, Document, Transformation
from purh_editorial.services.orthotypo_service import COLOR_BIBLIO, NNBSP, _find_changed_regions
from purh_editorial.utils import make_id

# ── Détection d'une section bibliographique ───────────────────────────────────
_SECTION_BIBLIO_RE = re.compile(
    r"^(sources?|bibliographie|références\s*bibliographiques?|bibliography|"
    r"travaux\s*cités?|works?\s*cited|références)",
    re.IGNORECASE | re.UNICODE,
)

# ── Heuristiques d'entrée bibliographique ─────────────────────────────────────
# Format PURH courant : NOM Prénom, *Titre*, Lieu, Éditeur, année.
_BIBLIO_ENTRY_RE = re.compile(
    r"^[A-ZÀÂÉÈÊËÙÛÜ\(][A-Za-zÀ-ÿ\'\-\s]{1,40},"   # auteur (Nom, ou [Nom])
    r".{5,},"                                          # titre + détails
    r"\s*\d{4}",                                       # année
    re.UNICODE,
)

# Titre d'article entre guillemets dans une entrée biblio
_ARTICLE_TITLE_RE = re.compile(r'[«""]([^»""]{3,})[»""]')


def _looks_like_biblio_entry(text: str) -> bool:
    return bool(_BIBLIO_ENTRY_RE.match(text.strip()))


def _normalize_biblio_entry(text: str) -> str:
    """Normalise une entrée bibliographique : point final, NNBSP pagination."""
    text = text.strip()

    # NNBSP après abréviations de pagination
    text = re.sub(
        r"\b(pp?|vol|t|f|fig|col|n°|N°)\.\s+(?=[\dIVXLCivxlc])",
        lambda m: m.group(1) + "." + NNBSP,
        text,
    )
    # NNBSP pour n° suivi d'un nombre
    text = re.sub(r"\b([Nn]°)\s+(?=\d)", r"\1" + NNBSP, text)

    # Point final si absent
    stripped = text.rstrip()
    if stripped and stripped[-1] not in ".!?…»":
        text = stripped + "."

    return text


class BibliographyNormalizer:
    """
    Améliore la détection et la normalisation des entrées bibliographiques.

    Stratégie :
    1. Repérer les titres de sections bibliographiques (Bibliographie, Sources…)
    2. Marquer les blocs suivants comme bibliography_item jusqu'au prochain grand titre
    3. Normaliser chaque entrée (point final, pagination, NNBSP)
    4. Surlignage turquoise (COLOR_BIBLIO)
    """

    module_name = "bibliography_normalizer"
    color = COLOR_BIBLIO

    def apply(self, document: Document) -> tuple[Document, list[Transformation]]:
        doc = copy.deepcopy(document)
        transformations: list[Transformation] = []
        bib_index = len(doc.bibliography) + 1
        in_bib_section = False

        for block in doc.blocks:
            text = block.text.strip()
            if not text:
                continue

            # Détection du titre de section bibliographique
            if block.block_type == "heading" and _SECTION_BIBLIO_RE.match(text):
                in_bib_section = True
                continue

            # Sortie de la section à la prochaine rubrique principale
            if block.block_type == "heading" and in_bib_section:
                level = block.attributes.get("style_id", "")
                if level in ("Titre1", "Titre2", "heading 1", "heading 2"):
                    in_bib_section = False
                    continue

            # Entrée bibliographique
            if in_bib_section and block.block_type in ("paragraph",) and text:
                block.block_type = "bibliography_item"
                doc.bibliography.append(
                    BibliographyItem(item_id=f"bib{bib_index}", raw_text=text, item_type="raw")
                )
                bib_index += 1

            # Normalisation des entrées (qu'elles soient issues de la section ou détectées avant)
            if block.block_type == "bibliography_item":
                original = block.text
                corrected = _normalize_biblio_entry(original)
                if corrected != original:
                    regions = _find_changed_regions(original, corrected)
                    block.text = corrected
                    if block.inlines:
                        # Reconstruction localisée — seules les parties modifiées sont surlignées
                        from purh_editorial.services.orthotypo_service import (
                            OrthotypoService, COLOR_BIBLIO as _CB,
                        )
                        new_inlines = OrthotypoService._rebuild_inlines(
                            block.inlines, original, corrected, regions
                        )
                        # Forcer la couleur biblio sur les spans modifiés
                        for span in new_inlines:
                            if span.attributes.get("highlight_color") == "orthotypo":
                                span.attributes["highlight_color"] = self.color
                            elif span.attributes.get("highlight_color") is None:
                                pass  # pas de surlignage sur les parties inchangées
                        block.inlines = new_inlines
                    else:
                        block.attributes["highlight_color"] = self.color
                    transformations.append(Transformation(
                        transformation_id=make_id("tr"),
                        module=self.module_name,
                        target_ref=block.block_id,
                        operation="biblio_normalize",
                        before=original,
                        after=corrected,
                        rule_id="purh.biblio.batch",
                        applied=True,
                        attributes={"highlight_regions": regions, "color": self.color},
                    ))

        if transformations:
            doc.history.append(
                f"{self.module_name}: {len(transformations)} entrée(s) bibliographique(s) normalisée(s)."
            )
        return doc, transformations

    # (méthode retirée — la reconstruction localisée est gérée inline ci-dessus)
