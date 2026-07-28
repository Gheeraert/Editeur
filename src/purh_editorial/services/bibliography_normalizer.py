from __future__ import annotations

import copy
import re

from purh_editorial.model import BibliographyItem, Document, Transformation
from purh_editorial.services.orthotypo_service import (
    COLOR_BIBLIO,
    NNBSP,
    TypoRule,
    _apply_rule_with_occurrences,
    _find_changed_regions,
)
from purh_editorial.utils import make_id
from purh_editorial.utils.protection import is_protected_by_attributes

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


# Chaque règle porte son propre rule_id, distinct de "purh.biblio.batch" :
# la granularité par règle (plutôt qu'une seule transformation agrégée par
# entrée) permet de savoir précisément quelle correction a été appliquée où,
# comme le fait déjà orthotypo_service pour ses propres règles.
_BIBLIO_RULES: list[TypoRule] = [
    TypoRule(
        rule_id="purh.biblio.pagination_nnbsp",
        pattern=re.compile(r"\b(pp?|vol|t|f|fig|col|n°|N°)\.\s+(?=[\dIVXLCivxlc])"),
        replacement=lambda m: m.group(1) + "." + NNBSP,
        description="Espace insécable fine après une abréviation de pagination (p., vol., t., n°...).",
    ),
    TypoRule(
        rule_id="purh.biblio.numero_nnbsp",
        pattern=re.compile(r"\b([Nn]°)\s+(?=\d)"),
        replacement=lambda m: m.group(1) + NNBSP,
        description="Espace insécable fine après « n° » suivi d'un nombre.",
    ),
    TypoRule(
        rule_id="purh.biblio.ponctuation_finale",
        pattern=re.compile(r"(?<![.!?…»])\Z"),
        replacement=".",
        description="Point final ajouté en fin d'entrée bibliographique.",
    ),
]


def _normalize_biblio_entry_with_occurrences(text: str):
    """Applique les règles biblio en chaîne, en conservant une RuleOccurrence
    distincte (avec son propre rule_id) par correction effectuée."""
    current = text.strip()
    all_occurrences = []
    for rule in _BIBLIO_RULES:
        current, occurrences = _apply_rule_with_occurrences(rule, current)
        all_occurrences.extend(occurrences)
    return current, all_occurrences


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
                # Note : is_protected_by_attributes (pas is_protected_block) — le
                # block_type "bibliography_item" est lui-même dans la liste des
                # types protégés pour empêcher les *autres* modules (orthotypo...)
                # d'y toucher ; ce module en est le propriétaire et ne doit vetoter
                # que sur une protection explicite (attribut/inline), pas sur son
                # propre type de bloc.
                if is_protected_by_attributes(block):
                    continue
                original = block.text
                corrected, occurrences = _normalize_biblio_entry_with_occurrences(original)
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
                    # Une Transformation distincte par occurrence corrigée, taguée par
                    # son propre rule_id (cf. orthotypo_service._build_transformations) —
                    # plutôt qu'une seule transformation "purh.biblio.batch" agrégeant
                    # toutes les règles, qui empêchait de savoir laquelle avait agi où.
                    for sequence, occ in enumerate(occurrences):
                        transformations.append(Transformation(
                            transformation_id=make_id("tr"),
                            module=self.module_name,
                            target_ref=block.block_id,
                            operation="biblio_normalize",
                            before=occ.before,
                            after=occ.after,
                            rule_id=occ.rule_id,
                            applied=True,
                            attributes={
                                "highlight_regions": regions,
                                "color": self.color,
                                "offset_start": occ.offset_start,
                                "offset_end": occ.offset_end,
                                "sequence": sequence,
                                "coordinate_space": occ.coordinate_space,
                            },
                        ))

        if transformations:
            doc.history.append(
                f"{self.module_name}: {len(transformations)} entrée(s) bibliographique(s) normalisée(s)."
            )
        return doc, transformations

    # (méthode retirée — la reconstruction localisée est gérée inline ci-dessus)
