from __future__ import annotations

import re

from purh_editorial.model import BibliographyItem, Diagnostic, Document, Evidence, Transformation
from purh_editorial.utils import make_id

# ── Constantes ────────────────────────────────────────────────────────────────

_SECTION_BIBLIO_RE = re.compile(
    r"^(sources?|bibliographie|références\s*bibliographiques?|bibliography|"
    r"travaux\s*cités?|works?\s*cited)",
    re.IGNORECASE | re.UNICODE,
)
_EPIGRAPH_MAX_CHARS   = 350
_PUNCT_ENDINGS        = set(".!?…,")
_NUMBERED_SECTION_RE  = re.compile(r"^(\d+)\s*[-\.]\s*")
_CREDIT_START_RE      = re.compile(
    r"^(Sous|Dans|Pour|Avec|Sur|Par|Textes?|Études?|Articles?|Ouvrage|Actes?)\s+",
    re.IGNORECASE | re.UNICODE,
)
# Verbe conjugué EN TÊTE de phrase (imparfait 3sg, conditionnel, présent 3e pl.)
_VERB_LEAD_RE         = re.compile(
    r"^[A-ZÀÂÉÈÊËÙÛÜ][a-zà-ÿ]*(ait|aient|ront|raient|rait|ions|iez)\b",
    re.UNICODE,
)
# Paire de noms propres : "Prénom NOM et Prénom NOM" → crédit éditorial, pas titre
_NAME_PAIR_RE         = re.compile(
    r"^[A-ZÀÂÉÈÊËÙÛÜ][a-zà-ÿ\-]+(\s+[A-Za-zÀ-ÿ\-]+)+\s+et\s+[A-ZÀÂÉÈÊËÙÛÜ]",
    re.UNICODE,
)
_ROMAN_ONLY_RE        = re.compile(r"^[IVXLCDMivxlcdm]{1,5}$")
# Entrée de glossaire/abréviations : SIGLE : développement
_ABBREV_ENTRY_RE      = re.compile(r"^[A-ZÀÂÉÈÊËÙÛÜ]{2,6}[  ]?\s*:")
# Institution : Université, École, Institut, CNRS, Laboratoire…
_INSTITUTION_RE       = re.compile(
    r"^(Universit[eé]|École|Institut|CNRS|UMR|Laboratoire|Centre|Facult[eé]|UFR"
    r"|Acad[eé]mie|Fondation|Museum|Musée|Biblioth[eè]que)",
    re.IGNORECASE | re.UNICODE,
)

# Noms d'auteur en italique : 2-4 mots, pas de chiffres, pas de ponctuation sauf tiret
_AUTHOR_NAME_RE = re.compile(
    r"^[A-ZÀÂÉÈÊËÙÛÜ][a-zà-ÿ\-]+"       # Prénom ou Nom majuscule
    r"(\s+[A-Za-zÀ-ÿ\.\-']+){0,3}$",     # 0 à 3 mots supplémentaires
    re.UNICODE,
)

# Seuil d'indentation gauche (twips) au-delà duquel on considère un bloc-citation
# (Ne s'applique que si ind_first_line est absent/nul — retrait bloc, pas alinéa)
_BLOCK_QUOTE_IND_LEFT_THRESHOLD = 400
_BLOCK_QUOTE_MIN_LEN = 60

# Bibliographie heuristique (hors section dédiée)
_BIBLIO_HEURISTIC_RE = re.compile(
    r"^[A-ZÀÂÉÈÊËÙÛÜ\(][A-Za-zÀ-ÿ\'\-\s]{1,40},"
    r".{5,},"
    r"\s*\d{4}",
    re.UNICODE,
)


class StructurePreparationService:
    """
    Détecte et annote la structure d'un document dont l'auteur
    n'a pas utilisé les styles Word de façon normative.

    Patterns détectés :
    - Normal + gras seul → titre (pattern Dissimuler)
    - Normal + tout-italique → titre de chapitre OU nom d'auteur (pattern Héraldique)
    - Normal + retrait gauche > 400 twips (sans alinéa) → citation longue
    - Normal + ALL CAPS court → titre structurant (déjà partiellement géré à l'ingestion)
    - Titres numérotés "1- Titre" → intertitre de niveau 2
    - Section bibliographique → TEI_bibl_reference
    """

    module_name = "structure"

    def process(self, document: Document) -> tuple[list[Diagnostic], list[Transformation]]:
        diagnostics: list[Diagnostic] = []
        transformations: list[Transformation] = []

        # Pré-calcul de l'indentation dominante du document
        # (permet de distinguer le retrait standard du retrait de citation)
        dominant_ind_left = self._dominant_ind_left(document)

        bib_index      = len(document.bibliography) + 1
        in_bib_section = False
        # Initialiser le compteur avec les titres déjà détectés à l'ingestion
        # (ALLCAPS, styles Titre1/2/3…) pour que l'épigraphe ne s'applique pas
        # à tout le texte avant le premier titre heuristique.
        heading_count = sum(1 for b in document.blocks if b.block_type == "heading")

        for block in document.blocks:
            text = block.text.strip()
            if not text:
                continue

            # ── Titre de section bibliographique ──────────────────────────────
            if block.block_type == "heading" and _SECTION_BIBLIO_RE.match(text):
                in_bib_section = True
                heading_count += 1
                continue

            # ── Sortie de mode biblio sur tout titre ──────────────────────────
            if block.block_type == "heading" and in_bib_section:
                in_bib_section = False
                heading_count += 1
                continue

            # ── Normal + ALL CAPS → titre (peut arriver si l'ingestion a raté) ──
            if (block.block_type == "paragraph"
                    and text.isupper()
                    and 4 < len(text) < 140):
                self._promote_heading(block, level=1, rule="structure.allcaps.heading",
                                      transformations=transformations)
                in_bib_section = False
                heading_count += 1
                continue

            # ── Normal + GRAS seul → titre (pattern Dissimuler) ───────────────
            if (block.block_type == "paragraph"
                    and block.attributes.get("all_runs_bold")
                    and not block.attributes.get("all_runs_italic")
                    and self._is_heading_candidate(text)):
                level = self._bold_heading_level(text)
                self._promote_heading(block, level=level, rule="structure.bold.heading",
                                      transformations=transformations)
                in_bib_section = False
                heading_count += 1
                continue

            # ── Normal + ITALIQUE seul → titre OU auteur (pattern Héraldique) ─
            if (block.block_type == "paragraph"
                    and block.attributes.get("all_runs_italic")
                    and not block.attributes.get("all_runs_bold")):
                result = self._classify_italic_block(text, block.attributes)
                if result == "author":
                    block.block_type = "author"
                    transformations.append(self._make_tr(
                        block.block_id, "paragraph", "author",
                        "structure.italic.author",
                    ))
                    continue
                if result == "heading":
                    level = self._italic_heading_level(text)
                    self._promote_heading(block, level=level, rule="structure.italic.heading",
                                          transformations=transformations)
                    in_bib_section = False
                    heading_count += 1
                    continue

            # ── Épigraphe (avant le 1er titre, court, pas de ponctuation finale) ─
            if (heading_count == 0
                    and block.block_type == "paragraph"
                    and len(text) <= _EPIGRAPH_MAX_CHARS
                    and text[-1] not in _PUNCT_ENDINGS
                    and len(text.split()) >= 5):
                block.block_type = "epigraph"
                transformations.append(self._make_tr(
                    block.block_id, "paragraph", "epigraph",
                    "structure.epigraph.heuristic",
                ))
                continue

            # ── Section biblio → entrées ───────────────────────────────────────
            if in_bib_section and block.block_type == "paragraph" and text:
                self._mark_biblio(block, document, bib_index, transformations, rule="structure.bibliography.section")
                bib_index += 1
                continue

            # ── Retrait gauche > seuil → citation bloc (Héraldique) ───────────
            ind_left     = block.attributes.get("ind_left", 0)
            ind_fl       = block.attributes.get("ind_first_line", 0)
            # Un retrait purement à gauche (pas un alinéa de 1e ligne) = bloc-citation
            if (block.block_type == "paragraph"
                    and ind_left > _BLOCK_QUOTE_IND_LEFT_THRESHOLD
                    and not ind_fl                   # pas d'alinéa de 1e ligne
                    and ind_left != dominant_ind_left # pas le retrait dominant du doc
                    and len(text) >= _BLOCK_QUOTE_MIN_LEN):
                block.block_type = "quote_block"
                transformations.append(self._make_tr(
                    block.block_id, "paragraph", "quote_block",
                    "structure.indent.quote",
                ))
                continue

            # ── Heuristique biblio hors section ───────────────────────────────
            if (not in_bib_section
                    and block.block_type in {"paragraph", "quote_block"}
                    and _BIBLIO_HEURISTIC_RE.match(text)):
                self._mark_biblio(block, document, bib_index, transformations,
                                   rule="structure.bibliography.heuristic", confidence="low")
                bib_index += 1
                diagnostics.append(Diagnostic(
                    diagnostic_id=make_id("diag"),
                    module=self.module_name,
                    severity="info",
                    category="structure",
                    message="Entrée bibliographique potentielle détectée hors section.",
                    target_ref=block.block_id,
                    rule_id="structure.bibliography.heuristic",
                    evidence=Evidence(excerpt=text[:180]),
                ))
                continue

            # ── Citation longue via guillemets ────────────────────────────────
            if block.block_type == "paragraph" and self._looks_like_block_quote(text):
                block.block_type = "quote_block"
                transformations.append(self._make_tr(
                    block.block_id, "paragraph", "quote_block",
                    "structure.quote.guillemets",
                ))

            # Promotion de titre si heuristique (titre non-stylé court)
            if (block.block_type == "paragraph"
                    and self._looks_like_heading_heuristic(text)):
                level = self._heuristic_heading_level(text)
                self._promote_heading(block, level=level, rule="structure.heading.heuristic",
                                      transformations=transformations)
                heading_count += 1

        return diagnostics, transformations

    # ── Helpers de promotion ──────────────────────────────────────────────────

    def _promote_heading(self, block, *, level: int, rule: str,
                          transformations: list) -> None:
        before = block.block_type
        block.block_type = "heading"
        block.attributes["heading_level"] = level
        transformations.append(self._make_tr(block.block_id, before, "heading", rule,
                                             attributes={"level": level}))

    def _mark_biblio(self, block, document: Document, bib_index: int,
                      transformations: list, *, rule: str,
                      confidence: str = "high") -> None:
        before = block.block_type
        block.block_type = "bibliography_item"
        document.bibliography.append(
            BibliographyItem(item_id=f"bib{bib_index}",
                             raw_text=block.text.strip(), item_type="raw")
        )
        transformations.append(self._make_tr(
            block.block_id, before, "bibliography_item", rule,
            attributes={"confidence": confidence},
        ))

    @staticmethod
    def _make_tr(target_ref: str, before: str, after: str, rule: str,
                  attributes: dict | None = None) -> Transformation:
        return Transformation(
            transformation_id=make_id("tr"),
            module="structure",
            target_ref=target_ref,
            operation="annotate_structure",
            before=before,
            after=after,
            rule_id=rule,
            applied=True,
            attributes=attributes or {},
        )

    # ── Classifieurs ─────────────────────────────────────────────────────────

    @classmethod
    def _is_heading_candidate(cls, text: str) -> bool:
        """Vrai si le texte ressemble à un titre (court, sans ponctuation de phrase)."""
        if len(text) > 180:
            return False
        stripped = text.strip()
        # Entrée bibliographique : virgule + année
        if re.search(r",\s*\d{4}", stripped):
            return False
        # Phrase avec clause subordonée après virgule
        if re.search(r",\s+[a-zà-ÿ]{4,}", stripped):
            return False
        # Point final sans être une abréviation → phrase terminée
        if stripped[-1:] == "." and len(stripped) > 60:
            return False
        # Commence par un mot de crédit éditorial
        if _CREDIT_START_RE.match(stripped):
            return False
        # Se termine par une préposition (ligne de crédit : "Textes réunis par")
        last_word = stripped.rsplit()[-1].lower() if stripped else ""
        if last_word in {"par", "de", "du", "des", "au", "aux", "en", "à"}:
            return False
        # Fragment verbal en tête de phrase → pas un titre
        if _VERB_LEAD_RE.match(stripped):
            return False
        # Paire de noms propres → crédit éditorial
        if _NAME_PAIR_RE.match(stripped):
            return False
        # Entrée abréviation (SIGLE : développement)
        if _ABBREV_ENTRY_RE.match(stripped):
            return False
        # Institution → pas un titre structurant
        if _INSTITUTION_RE.match(stripped):
            return False
        return True

    @staticmethod
    def _bold_heading_level(text: str) -> int:
        """Détermine le niveau d'un titre formaté en gras."""
        stripped = text.strip()
        if stripped.isupper():
            return 1
        if _NUMBERED_SECTION_RE.match(stripped):
            num = int(_NUMBERED_SECTION_RE.match(stripped).group(1))
            return 2 if num <= 9 else 3
        if len(stripped) <= 45:
            return 2
        return 3

    @staticmethod
    def _italic_heading_level(text: str) -> int:
        """Détermine le niveau d'un titre formaté en italique."""
        stripped = text.strip()
        if _NUMBERED_SECTION_RE.match(stripped):
            return 2
        if len(stripped) <= 60:
            return 2
        return 1

    @staticmethod
    def _classify_italic_block(text: str, attrs: dict) -> str:
        """
        Pour un paragraphe tout-italique :
        - 'author'  → nom d'auteur (court, < 5 mots, pas de chiffres ni virgule)
        - 'heading' → titre de chapitre ou section
        - ''        → laisser tel quel (biblio, traduction, citation, etc.)
        """
        stripped = text.strip()
        words = stripped.split()
        # Trop court (1 mot)
        if len(words) < 2:
            return ""
        # Entrée bibliographique : virgule + année
        if re.search(r",\s*\d{4}", stripped):
            return ""
        # Entrée bibliographique : présence d'un DOI ou URL
        if "http" in stripped or "doi.org" in stripped:
            return ""
        # Texte trop long → passage cité, traduction
        if len(stripped) > 250:
            return ""
        # Nom d'auteur : 2-4 mots, pas de chiffres, pas de guillemets, pas de virgule
        if (2 <= len(words) <= 4
                and not re.search(r"\d", stripped)
                and "," not in stripped
                and "«" not in stripped
                and "(" not in stripped):
            # Heuristique complémentaire : les noms propres commencent par une majuscule
            if all(w[0].isupper() for w in words if w and w[0].isalpha()):
                return "author"
        # Titre numéroté → heading
        if _NUMBERED_SECTION_RE.match(stripped):
            return "heading"
        # Titre de chapitre : 4-25 mots, pas de virgule-clause, pas d'année
        if (4 <= len(words) <= 25
                and len(stripped) <= 200
                and not re.search(r",\s+[a-zà-ÿ]{4,}", stripped)):
            return "heading"
        return ""

    @staticmethod
    def _looks_like_block_quote(text: str) -> bool:
        """Détecte une citation longue entre guillemets ou avec tiret."""
        if len(text) > 180 and text.startswith("«"):
            return True
        if len(text) > 120 and text.startswith("«") and text.endswith("»"):
            return True
        return False

    @classmethod
    def _looks_like_heading_heuristic(cls, text: str) -> bool:
        """
        Heuristique très conservatrice — seulement pour des cas structurels non ambigus.
        On évite les faux positifs au prix de quelques manqués.
        """
        stripped = text.strip()
        words = stripped.split()
        # Taille : 2-8 mots, longueur ≤ 70 chars
        if not (2 <= len(words) <= 8 and len(stripped) <= 70):
            return False
        # Pas de ponctuation finale de phrase
        if stripped[-1:] in ".!?…,":
            return False
        # Commence par une majuscule
        if not stripped[:1].isupper():
            return False
        # Roman numeral seul (I, II, V…) → pas un titre heuristique
        if _ROMAN_ONLY_RE.match(stripped):
            return False
        # Pas un item de liste
        if re.match(r"^[-–—•]\s", stripped):
            return False
        # Pas une entrée bibliographique
        if re.search(r",\s*\d{4}", stripped):
            return False
        # Pas une clause subordonnée
        if re.search(r",\s+[a-zà-ÿ]{4,}", stripped):
            return False
        if re.search(r"\s(qui|que|dont|où|car|mais|avec|dans|pour|sur)\s", stripped):
            return False
        # Pas un crédit éditorial
        if _CREDIT_START_RE.match(stripped):
            return False
        last_word = stripped.rsplit()[-1].lower() if stripped else ""
        if last_word in {"par", "de", "du", "des", "au", "aux", "en", "à"}:
            return False
        # Fragment verbal en tête → pas un titre
        if _VERB_LEAD_RE.match(stripped):
            return False
        # Paire de noms propres → crédit éditorial
        if _NAME_PAIR_RE.match(stripped):
            return False
        # Entrée abréviation (SIGLE : développement)
        if _ABBREV_ENTRY_RE.match(stripped):
            return False
        # Institution → pas un titre structurant
        if _INSTITUTION_RE.match(stripped):
            return False
        return True

    @staticmethod
    def _heuristic_heading_level(text: str) -> int:
        stripped = text.strip()
        if stripped.isupper():
            return 1
        if _NUMBERED_SECTION_RE.match(stripped):
            return 2
        if len(stripped) <= 50:
            return 2
        return 3

    @staticmethod
    def _dominant_ind_left(document: Document) -> int:
        """Retourne le retrait gauche le plus fréquent dans le document (ou 0)."""
        from collections import Counter
        counter: Counter = Counter()
        for block in document.blocks:
            v = block.attributes.get("ind_left", 0)
            if v:
                counter[v] += 1
        if counter:
            return counter.most_common(1)[0][0]
        return 0
