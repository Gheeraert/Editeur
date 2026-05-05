from __future__ import annotations

from dataclasses import dataclass, field
import re
from statistics import pstdev
from typing import Any
import unicodedata

from purh_editorial.model import (
    BibliographyItem,
    BlockSemantics,
    Diagnostic,
    Document,
    Evidence,
    InlineSpan,
    Transformation,
    write_block_semantics,
)
from purh_editorial.utils import make_id

# Constantes

_SECTION_BIBLIO_RE = re.compile(
    r"^(sources?|bibliographie|r(?:\u00e9|e)f(?:\u00e9|e)rences\s*bibliographiques?|bibliography|"
    r"travaux\s*cit(?:\u00e9|e)s?|works?\s*cited)",
    re.IGNORECASE | re.UNICODE,
)
_EPIGRAPH_MAX_CHARS = 350
_PUNCT_ENDINGS = {".", "!", "?", ",", ":", ";", "\u2026"}
_NUMBERED_SECTION_RE = re.compile(r"^(\d+)\s*[-\.]\s*")
_CREDIT_START_RE = re.compile(
    r"^(Sous|Dans|Pour|Avec|Sur|Par|Textes?|\u00c9tudes?|Articles?|Ouvrage|Actes?)\s+",
    re.IGNORECASE | re.UNICODE,
)
# Verbe conjugué EN TÊTE de phrase (imparfait 3sg, conditionnel, présent 3e pl.)
_VERB_LEAD_RE = re.compile(
    r"^[A-Z][A-Za-z]*(ait|aient|ront|raient|rait|ions|iez)\b",
    re.UNICODE,
)


# Début de vers différent de début de titre: conjonctions de coordination
_SENTENCE_CONNECTOR_RE = re.compile(
    r"^(Et|Mais|Or|Car|Puis|Alors|Ainsi|Enfin|Cependant|Tandis)\b",
    re.IGNORECASE | re.UNICODE,
)

# Paire de noms propres : "Prénom NOM et Prénom NOM" -> crédit éditorial, pas titre
_NAME_PAIR_RE = re.compile(
    r"^[A-Z][A-Za-z\-]+(\s+[A-Za-z\-]+)+\s+et\s+[A-Z]",
    re.UNICODE,
)

# Liste de 3+ noms propres séparés par virgules : "A B, C D, E F[, G H]"
_COMMA_NAME_LIST_MIN_PARTS = 3
_ROMAN_ONLY_RE = re.compile(r"^[IVXLCDMivxlcdm]{1,5}$")
_PASSAGE_TOKEN_RE = re.compile(r"^(?:[IVXLCDM]+|\d+|[A-Za-z]{1,4})$", re.IGNORECASE)
# Entrée de glossaire/abréviations : SIGLE : développement
_ABBREV_ENTRY_RE = re.compile(r"^[A-Z]{2,6}[ ]?\s*:")
# Institution : Université, École, Institut, CNRS, Laboratoire
_INSTITUTION_RE = re.compile(
    r"^(Universit[\u00e9e]|\u00c9cole|Institut|CNRS|UMR|Laboratoire|Centre|Facult[\u00e9e]|UFR"
    r"|Acad[\u00e9e]mie|Fondation|Museum|Mus\u00e9e|Biblioth[\u00e8e]que)",
    re.IGNORECASE | re.UNICODE,
)

# Noms d'auteur en italique : 2-4 mots, pas de chiffres, pas de ponctuation sauf tiret
_AUTHOR_NAME_RE = re.compile(
    r"^[A-Z][a-z\-]+"       # Prénom ou Nom majuscule
    r"(\s+[A-Za-z\.\-']+){0,3}$",     # 0 à 3 mots supplémentaires
    re.UNICODE,
)

# Seuil d'indentation gauche (twips) au-delà duquel on considère un bloc-citation
# (Ne s'applique que si ind_first_line est absent/nul : retrait bloc, pas alinéa)
_BLOCK_QUOTE_IND_LEFT_THRESHOLD = 400
_BLOCK_QUOTE_MIN_LEN = 60

# Séquences poétiques : taille maximale et seuil de rupture entre strophes
_POETRY_SEQUENCE_MAX_LINES = 20
_POETRY_STANZA_SPACE_THRESHOLD = 240  # twips — environ 1 interligne à 12pt
_LIST_MARKER_RE = re.compile(r"^\s*(?:\d+[\.\)]|[A-Za-zÀ-ÿ][\.\)]|[-–—•*])\s+")

# Bibliographie heuristique (hors section dédiée)
_BIBLIO_HEURISTIC_RE = re.compile(
    r"^[A-Z\(][A-Za-z\'\-\s]{1,40},"
    r".{5,},"
    r"\s*\d{4}",
    re.UNICODE,
)


_HEADING_STYLE_LEVEL_RE = re.compile(
    r"(?:heading|tei_head|tei_titre|titre|head)[_\-\s]*([1-6])",
    re.IGNORECASE,
)
_TECHNICAL_ATTR_RE = re.compile(r"\b[\w:-]+\s*=\s*\"[^\"]*\"")
_TECHNICAL_TAG_RE = re.compile(r"<[^>]+>")
_TECHNICAL_CODE_RE = re.compile(r"\b(print|class|def|return)\s*\(", re.IGNORECASE)
_POETRY_RULE_ID = "R-CI-POETRY-001"
_POETRY_CATEGORY = "poetry_quote_candidate"
_HEADING_RULE_ID = "R-STRUCT-HEADING-001"
_HEADING_CATEGORY = "heading_candidate"
_ALLOWED_HEURISTIC_PROFILES = {"conservative", "balanced", "exploratory"}

_PROFILE_ALIASES = {
    "prudent": "conservative",
    "conservateur": "conservative",
    "conservative": "conservative",

    "équilibré": "balanced",
    "equilibre": "balanced",
    "balanced": "balanced",

    "exploratoire": "exploratory",
    "exploratory": "exploratory",
}

@dataclass(slots=True)
class HeuristicSettings:
    enable_scored_heuristics: bool = True
    poetry_transform_threshold: float = 0.82
    poetry_diagnostic_threshold: float = 0.60
    poetry_ai_min_score: float = 0.60
    poetry_ai_max_score: float = 0.82
    allow_ai_for_poetry_candidates: bool = False
    heading_transform_threshold: float = 0.85
    heading_diagnostic_threshold: float = 0.60
    heading_ai_min_score: float = 0.60
    heading_ai_max_score: float = 0.85
    auto_apply_diagnostics: bool = False


def settings_for_heuristic_profile(
    profile: str | None,
    *,
    heading_transform_threshold: float | None = None,
    heading_diagnostic_threshold: float | None = None,
    poetry_transform_threshold: float | None = None,
    poetry_diagnostic_threshold: float | None = None,
    enable_scored_heuristics: bool = True,
) -> tuple[HeuristicSettings, list[str]]:
    raw = str(profile or "conservative").strip().lower()
    raw = unicodedata.normalize("NFKD", raw)
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    normalized = _PROFILE_ALIASES.get(raw, raw)
    warnings: list[str] = []
    if normalized not in _ALLOWED_HEURISTIC_PROFILES:
        warnings.append(f"Unknown heuristic profile '{profile}', falling back to 'conservative'.")
        normalized = "conservative"

    profile_values = {
        "conservative": (0.90, 0.70, 0.82, 0.60),
        "balanced":     (0.85, 0.60, 0.78, 0.55),
        "exploratory":  (0.75, 0.50, 0.72, 0.48),
    }
    h_t, h_d, p_t, p_d = profile_values[normalized]

    def _resolve(
        value: float | None,
        fallback: float,
        label: str,
    ) -> float:
        if value is None:
            return fallback
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            warnings.append(f"Invalid threshold for {label}: {value!r}; using profile value.")
            return fallback
        if numeric < 0.0 or numeric > 1.0:
            warnings.append(f"Out-of-range threshold for {label}: {value!r}; clamped to [0.0, 1.0].")
        return max(0.0, min(1.0, numeric))

    h_t = _resolve(heading_transform_threshold, h_t, "heading_transform_threshold")
    h_d = _resolve(heading_diagnostic_threshold, h_d, "heading_diagnostic_threshold")
    p_t = _resolve(poetry_transform_threshold, p_t, "poetry_transform_threshold")
    p_d = _resolve(poetry_diagnostic_threshold, p_d, "poetry_diagnostic_threshold")

    if h_d > h_t:
        warnings.append(
            "Inconsistent heading thresholds (diagnostic > transform); restored profile thresholds."
        )
        h_t, h_d = profile_values[normalized][0], profile_values[normalized][1]
    if p_d > p_t:
        warnings.append(
            "Inconsistent poetry thresholds (diagnostic > transform); restored profile thresholds."
        )
        p_t, p_d = profile_values[normalized][2], profile_values[normalized][3]

    settings = HeuristicSettings(
        enable_scored_heuristics=enable_scored_heuristics,
        heading_transform_threshold=h_t,
        heading_diagnostic_threshold=h_d,
        heading_ai_min_score=h_d,
        heading_ai_max_score=h_t,
        poetry_transform_threshold=p_t,
        poetry_diagnostic_threshold=p_d,
        poetry_ai_min_score=p_d,
        poetry_ai_max_score=p_t,
        auto_apply_diagnostics=(normalized == "exploratory"),
    )
    return settings, warnings


@dataclass(slots=True)
class HeuristicDecision:
    rule_id: str
    category: str
    target_refs: list[str] = field(default_factory=list)
    score: float = 0.0
    decision: str = "ignore"
    evidence: dict[str, Any] = field(default_factory=dict)
    veto_reasons: list[str] = field(default_factory=list)
    ai_candidate: bool = False


class StructurePreparationService:
    """
    Détecte et annote la structure d'un document dont l'auteur
    n'a pas utilisé les styles Word de façon normative.

    Patterns détectés :
    - Normal + gras seul -> titre (pattern Dissimuler)
    - Normal + tout-italique -> titre de chapitre OU nom d'auteur (pattern H?raldique)
    - Normal + retrait gauche > 400 twips (sans alinéa) -> citation longue
    - Normal + ALL CAPS court -> titre structurant (déjà partiellement géré à l'ingestion)
    - Titres numérotés "1- Titre" -> intertitre de niveau 2
    - Section bibliographique -> TEI_bibl_reference
    """

    module_name = "structure"

    def __init__(self, heuristic_settings: HeuristicSettings | None = None) -> None:
        self.heuristic_settings = heuristic_settings or HeuristicSettings()

    def process(
        self,
        document: Document,
        *,
        mode: str = "heuristic",
    ) -> tuple[list[Diagnostic], list[Transformation]]:
        diagnostics: list[Diagnostic] = []
        transformations: list[Transformation] = []
        structure_mode = str(mode or "heuristic").strip().lower()
        use_heuristics = structure_mode != "deterministic"

        # Pré-calcul de l'indentation dominante du document
        # (permet de distinguer le retrait standard du retrait de citation)
        dominant_ind_left = self._dominant_ind_left(document)

        bib_index      = len(document.bibliography) + 1
        in_bib_section = False
        # Initialiser le compteur avec les titres déjà détectés à l'ingestion
        # (ALLCAPS, styles Titre1/2/3) pour que l'épigraphe ne s'applique pas
        # à tout le texte avant le premier titre heuristique.
        heading_count = sum(1 for b in document.blocks if b.block_type == "heading")
        auto_apply = self.heuristic_settings.auto_apply_diagnostics
        _apply_decisions = {"transform", "diagnostic"} if auto_apply else {"transform"}

        poetry_decisions: list[HeuristicDecision] = []
        poetry_candidate_block_ids: set[str] = set()
        if use_heuristics:
            transformations.extend(self._merge_blank_bounded_poetry_sequences(document))
            poetry_decisions = self.analyze_poetry_candidates(document)
            transformations.extend(self._annotate_poetry_sequences(document, poetry_decisions, auto_apply=auto_apply))
            transformations.extend(self._merge_poetry_by_group(document, poetry_decisions, auto_apply=auto_apply))

            # Zone grise ou transformation : dans les deux cas,
            # les lignes poétiques doivent neutraliser la promotion en titre.
            for poetry_decision in poetry_decisions:
                if poetry_decision.veto_reasons:
                    continue
                if poetry_decision.decision in {"diagnostic", "transform"}:
                    poetry_candidate_block_ids.update(poetry_decision.target_refs)

        # Retire les blocs vides préservés à l'import pour les heuristiques de frontière.
        # Les attributs blank_para_before/after sur les voisins restent disponibles.
        document.blocks = [b for b in document.blocks if not b.attributes.get("is_blank_para")]

        for block in document.blocks:
            text = block.text.strip()
            if not text:
                continue
            heading_applied = False
            heading_decision = None
            if block.block_type == "paragraph" and use_heuristics:
                extra_veto_reasons: list[str] = []
                if block.block_id in poetry_candidate_block_ids:
                    extra_veto_reasons.append("poetry_sequence_candidate")
                heading_decision = self._score_heading_candidate(
                    block=block,
                    settings=self.heuristic_settings,
                    extra_veto_reasons=extra_veto_reasons,
                )

            #  Titre de section bibliographique 
            if block.block_type == "heading":
                # Garantir heading_level valide (pivot_validator l'exige entre 1 et 6)
                if not isinstance(block.attributes.get("heading_level"), int):
                    inferred = self._source_heading_level(block) or 2
                    block.attributes["heading_level"] = inferred
                if _SECTION_BIBLIO_RE.match(text):
                    in_bib_section = True
                elif in_bib_section:
                    in_bib_section = False
                heading_count += 1
                continue

            source_heading_level = self._source_heading_level(block)
            if (block.block_type == "paragraph"
                    and source_heading_level is not None
            ):
                self._promote_heading(
                    block,
                    level=source_heading_level,
                    rule="structure.source_style.heading",
                    transformations=transformations,
                )
                heading_applied = True
                in_bib_section = False
                heading_count += 1
                continue

            #  Normal + ALL CAPS  titre (peut arriver si l'ingestion a raté)
            if (block.block_type == "paragraph"
                    and text.isupper()
                    and 4 < len(text) < 140
                    and use_heuristics
                    and heading_decision is not None
                    and heading_decision.decision in _apply_decisions):
                self._promote_heading(block, level=1, rule="structure.allcaps.heading",
                                      transformations=transformations)
                heading_applied = True
                in_bib_section = False
                heading_count += 1
                if auto_apply and heading_decision.decision == "diagnostic":
                    block.attributes["highlight_color"] = "exploratory_structure"
                    diagnostics.append(self._make_exploratory_heading_diag(block.block_id, text, heading_decision.score))
                continue

            #  Normal + GRAS seul  titre (pattern Dissimuler)
            if (block.block_type == "paragraph"
                    and block.attributes.get("all_runs_bold")
                    and not block.attributes.get("all_runs_italic")
                    and use_heuristics
                    and heading_decision is not None
                    and heading_decision.decision in _apply_decisions
                    and self._is_heading_candidate(text, block)):
                level = self._bold_heading_level(text)
                self._promote_heading(block, level=level, rule="structure.bold.heading",
                                      transformations=transformations)
                heading_applied = True
                in_bib_section = False
                heading_count += 1
                if auto_apply and heading_decision.decision == "diagnostic":
                    block.attributes["highlight_color"] = "exploratory_structure"
                    diagnostics.append(self._make_exploratory_heading_diag(block.block_id, text, heading_decision.score))
                continue

            #  Normal + ITALIQUE seul  titre OU auteur (pattern Héraldique) 
            if (block.block_type == "paragraph"
                    and use_heuristics
                    and block.attributes.get("all_runs_italic")
                    and not block.attributes.get("all_runs_bold")):
                result = self._classify_italic_block(text, block.attributes, block)
                if result == "author":
                    block.block_type = "author"
                    transformations.append(self._make_tr(
                        block.block_id, "paragraph", "author",
                        "structure.italic.author",
                    ))
                    continue
                if result == "heading":
                    level = self._italic_heading_level(text)
                    if heading_decision is not None and heading_decision.decision in _apply_decisions:
                        self._promote_heading(block, level=level, rule="structure.italic.heading",
                                              transformations=transformations)
                        heading_applied = True
                        in_bib_section = False
                        heading_count += 1
                        if auto_apply and heading_decision.decision == "diagnostic":
                            block.attributes["highlight_color"] = "exploratory_structure"
                            diagnostics.append(self._make_exploratory_heading_diag(block.block_id, text, heading_decision.score))
                        continue

            #  pigraphe (avant le 1er titre, court, pas de ponctuation finale) 
            if (heading_count == 0
                    and use_heuristics
                    and block.block_type == "paragraph"
                    and block is document.blocks[0]
                    and len(text) <= _EPIGRAPH_MAX_CHARS
                    and text[-1] not in _PUNCT_ENDINGS
                    and len(text.split()) >= 5):
                block.block_type = "epigraph"
                transformations.append(self._make_tr(
                    block.block_id, "paragraph", "epigraph",
                    "structure.epigraph.heuristic",
                ))
                continue

            #  Section biblio  entrées 
            if in_bib_section and block.block_type == "paragraph" and text:
                self._mark_biblio(block, document, bib_index, transformations, rule="structure.bibliography.section")
                bib_index += 1
                continue

            #  Retrait gauche > seuil  citation bloc (Héraldique) 
            ind_left     = block.attributes.get("ind_left", 0)
            ind_fl       = block.attributes.get("ind_first_line", 0)
            # Un retrait purement à gauche (pas un alinéa de 1e ligne) = bloc-citation
            if (block.block_type == "paragraph"
                    and use_heuristics
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

            #  Heuristique biblio hors section 
            if (not in_bib_section
                    and use_heuristics
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

            #  Citation longue via guillemets 
            if use_heuristics and block.block_type == "paragraph" and self._looks_like_block_quote(text):
                block.block_type = "quote_block"
                transformations.append(self._make_tr(
                    block.block_id, "paragraph", "quote_block",
                    "structure.quote.guillemets",
                ))

            # Promotion de titre si heuristique (titre non-stylé court)
            if (block.block_type == "paragraph"
                    and use_heuristics
                    and heading_decision is not None
                    and heading_decision.decision in _apply_decisions
                    and self._looks_like_heading_heuristic(text, block)):
                level = self._heuristic_heading_level(text)
                self._promote_heading(block, level=level, rule="structure.heading.heuristic",
                                      transformations=transformations)
                heading_applied = True
                heading_count += 1
                if auto_apply and heading_decision.decision == "diagnostic":
                    block.attributes["highlight_color"] = "exploratory_structure"
                    diagnostics.append(self._make_exploratory_heading_diag(block.block_id, text, heading_decision.score))

            if (block.block_type == "paragraph"
                    and use_heuristics
                    and heading_decision is not None
                    and heading_decision.decision == "diagnostic"):
                diagnostics.append(
                    Diagnostic(
                        diagnostic_id=make_id("diag"),
                        module=self.module_name,
                        severity="info",
                        category=_HEADING_CATEGORY,
                        message="Candidat titre detecte: verifier manuellement la promotion en heading.",
                        target_ref=block.block_id,
                        rule_id=_HEADING_RULE_ID,
                        evidence=Evidence(excerpt=text[:180]),
                        attributes={
                            "score": heading_decision.score,
                            "decision": heading_decision.decision,
                            "evidence": heading_decision.evidence,
                            "veto_reasons": heading_decision.veto_reasons,
                            "ai_candidate": heading_decision.ai_candidate,
                        },
                    )
                )
            elif (
                block.block_type == "paragraph"
                and use_heuristics
                and heading_decision is not None
                and heading_decision.decision == "transform"
                and not heading_applied
            ):
                diagnostics.append(
                    Diagnostic(
                        diagnostic_id=make_id("diag"),
                        module=self.module_name,
                        severity="warning",
                        category=_HEADING_CATEGORY,
                        message=(
                            "Candidat titre score 'transform' non applique automatiquement: "
                            "verification manuelle recommandee."
                        ),
                        target_ref=block.block_id,
                        rule_id=_HEADING_RULE_ID,
                        evidence=Evidence(excerpt=text[:180]),
                        attributes={
                            "score": heading_decision.score,
                            "decision": heading_decision.decision,
                            "evidence": heading_decision.evidence,
                            "veto_reasons": heading_decision.veto_reasons,
                            "ai_candidate": heading_decision.ai_candidate,
                            "reason": "transform_not_applied",
                        },
                    )
                )

        if use_heuristics:
            for poetry_decision in poetry_decisions:
                if poetry_decision.decision not in {"diagnostic", "transform"}:
                    continue
                excerpt = poetry_decision.evidence.get("excerpt", "")
                is_auto = auto_apply and poetry_decision.decision == "diagnostic"
                if poetry_decision.decision == "transform":
                    severity = "info"
                    message = (
                        "Citation poétique détectée avec un score élevé et structurée automatiquement."
                    )
                elif is_auto:
                    severity = "warning"
                    message = (
                        "Citation poétique appliquée automatiquement (mode exploratoire) — à vérifier."
                    )
                else:
                    severity = "info"
                    message = (
                        "Candidate citation poetique detectee: verifier manuellement "
                        "avant toute structuration."
                    )
                diagnostics.append(
                    Diagnostic(
                        diagnostic_id=make_id("diag"),
                        module=self.module_name,
                        severity=severity,
                        category=_POETRY_CATEGORY,
                        message=message,
                        target_ref=poetry_decision.target_refs[0] if poetry_decision.target_refs else "",
                        rule_id=_POETRY_RULE_ID,
                        evidence=Evidence(excerpt=excerpt),
                        attributes={
                            "score": poetry_decision.score,
                            "decision": poetry_decision.decision,
                            "evidence": poetry_decision.evidence,
                            "veto_reasons": poetry_decision.veto_reasons,
                            "ai_candidate": poetry_decision.ai_candidate,
                            "auto_applied": is_auto,
                        },
                    )
                )

        return diagnostics, transformations

    #  Helpers de promotion

    def _make_exploratory_heading_diag(self, block_id: str, text: str, score: float) -> Diagnostic:
        return Diagnostic(
            diagnostic_id=make_id("diag"),
            module=self.module_name,
            severity="warning",
            category=_HEADING_CATEGORY,
            message="Titre promu automatiquement (mode exploratoire) — à vérifier.",
            target_ref=block_id,
            rule_id=_HEADING_RULE_ID,
            evidence=Evidence(excerpt=text[:180]),
            attributes={"score": score, "auto_applied": True},
        )

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

    #  Classifieurs 

    def _merge_short_poetry_sequences(self, document: Document) -> list[Transformation]:
        transformations: list[Transformation] = []
        sequences = self._short_poetry_candidate_sequences(document)
        if not sequences:
            return transformations

        consumed_ids: set[str] = set()
        replacement_by_id: dict[str, Any] = {}

        for sequence in sequences:
            first_block = sequence[0]
            merged_from = [block.block_id for block in sequence]
            merged_text = "\n".join(block.text.strip() for block in sequence)
            verse_lines = [block.text.strip() for block in sequence if block.text.strip()]
            merged_inlines = self._merged_poetry_inlines(sequence)
            first_block.block_type = "lineated_block"
            first_block.text = merged_text
            first_block.inlines = merged_inlines
            first_block.attributes["alignment"] = "left"
            first_block.attributes["ind_left"] = max(
                int(first_block.attributes.get("ind_left", 0) or 0),
                _BLOCK_QUOTE_IND_LEFT_THRESHOLD,
            )
            first_block.attributes["merged_from"] = merged_from
            first_block.attributes.pop("quote_kind", None)
            first_block.attributes.pop("lineation", None)
            first_block.attributes.pop("poetry_group_id", None)
            first_block.attributes.pop("poetry_line_index", None)
            first_block.attributes.pop("protected_zone", None)
            write_block_semantics(
                first_block,
                BlockSemantics(
                    role="lineated_block",
                    layout_kind="lineated_block",
                    lineation="lineated",
                    lines=verse_lines,
                ),
            )

            transformations.append(
                self._make_tr(
                    first_block.block_id,
                    "paragraph",
                    "lineated_block",
                    "structure.lineated.short_sequence.merge",
                    attributes={
                        "merged_from": merged_from,
                    },
                )
            )

            for block in sequence[1:]:
                consumed_ids.add(block.block_id)
            replacement_by_id[first_block.block_id] = first_block

        if not consumed_ids:
            return transformations

        rebuilt_blocks: list = []
        for block in document.blocks:
            if block.block_id in consumed_ids:
                continue
            replacement = replacement_by_id.get(block.block_id)
            if replacement is not None:
                rebuilt_blocks.append(replacement)
            else:
                rebuilt_blocks.append(block)
        document.blocks = rebuilt_blocks
        return transformations

    def _merge_blank_bounded_poetry_sequences(self, document: Document) -> list[Transformation]:
        transformations: list[Transformation] = []
        sequences = self._blank_bounded_poetry_sequences(document)
        if not sequences:
            return transformations

        consumed_ids: set[str] = set()
        replacement_by_id: dict[str, Any] = {}

        for sequence in sequences:
            veto_reasons = self._poetry_veto_reasons(sequence)
            if veto_reasons:
                continue

            first_block = sequence[0]
            merged_from = [block.block_id for block in sequence]
            merged_text = "\n".join(block.text.strip() for block in sequence)
            verse_lines = [block.text.strip() for block in sequence if block.text.strip()]
            merged_inlines = self._merged_poetry_inlines(sequence)
            before = first_block.block_type
            first_block.block_type = "lineated_block"
            first_block.text = merged_text
            first_block.inlines = merged_inlines
            first_block.attributes["alignment"] = "left"
            first_block.attributes["merged_from"] = merged_from
            first_block.attributes.pop("quote_kind", None)
            first_block.attributes.pop("lineation", None)
            first_block.attributes.pop("poetry_group_id", None)
            first_block.attributes.pop("poetry_line_index", None)
            first_block.attributes.pop("protected_zone", None)
            write_block_semantics(
                first_block,
                BlockSemantics(
                    role="lineated_block",
                    layout_kind="lineated_block",
                    lineation="lineated",
                    lines=verse_lines,
                ),
            )

            transformations.append(
                self._make_tr(
                    first_block.block_id,
                    before,
                    "lineated_block",
                    "structure.lineated.blank_bounded.merge",
                    attributes={
                        "alignment": "left",
                        "merged_from": merged_from,
                        "layout_evidence": "blank_bounded_short_lines",
                    },
                )
            )

            for block in sequence[1:]:
                consumed_ids.add(block.block_id)
            replacement_by_id[first_block.block_id] = first_block

        if not consumed_ids:
            return transformations

        rebuilt_blocks: list = []
        for block in document.blocks:
            if block.block_id in consumed_ids:
                continue
            replacement = replacement_by_id.get(block.block_id)
            if replacement is not None:
                rebuilt_blocks.append(replacement)
            else:
                rebuilt_blocks.append(block)
        document.blocks = rebuilt_blocks
        return transformations

    @classmethod
    def _blank_bounded_poetry_sequences(cls, document: Document) -> list[list]:
        blocks = document.blocks
        sequences: list[list] = []
        index = 0
        while index < len(blocks):
            block = blocks[index]
            if not cls._is_strong_poetry_line_candidate(block):
                index += 1
                continue

            start = index
            current: list = []
            while index < len(blocks) and cls._is_strong_poetry_line_candidate(blocks[index]):
                # Un paragraphe vide supprimé à l'import apparaît comme
                # blank_para_before sur le bloc suivant : il marque une
                # frontière de séquence et ne doit pas être absorbé dans
                # le bloc poétique précédent.
                if current and cls._has_blank_before(blocks, index):
                    break
                current.append(blocks[index])
                index += 1
            end = index - 1

            has_blank_before = cls._has_blank_before(blocks, start)
            has_blank_after = cls._has_blank_after(blocks, end)
            if has_blank_before and has_blank_after and 3 <= len(current) <= _POETRY_SEQUENCE_MAX_LINES:
                sequences.append(current.copy())
        return sequences

    @classmethod
    def _has_blank_before(cls, blocks: list, index: int) -> bool:
        if not (0 <= index < len(blocks)):
            return False
        block = blocks[index]
        if block.attributes.get("blank_para_before"):
            return True
        return index > 0 and cls._is_blank_paragraph(blocks[index - 1])

    @classmethod
    def _has_blank_after(cls, blocks: list, index: int) -> bool:
        if not (0 <= index < len(blocks)):
            return False
        block = blocks[index]
        if block.attributes.get("blank_para_after"):
            return True
        return (
            index + 1 < len(blocks)
            and (
                bool(blocks[index + 1].attributes.get("blank_para_before"))
                or cls._is_blank_paragraph(blocks[index + 1])
            )
        )

    @classmethod
    def _is_strong_poetry_line_candidate(cls, block) -> bool:
        if block.block_type != "paragraph":
            return False
        text = block.text.strip()
        if not text:
            return False
        if len(text.split()) > 16:
            return False
        if cls._looks_like_list_item(text):
            return False
        if cls._is_note_zone_block(block):
            return False
        if str(block.attributes.get("protected_zone", "")).lower() == "table":
            return False
        return True

    @staticmethod
    def _is_blank_paragraph(block) -> bool:
        return block.block_type == "paragraph" and not block.text.strip()

    def _annotate_poetry_sequences(
        self,
        document: Document,
        poetry_decisions: list[HeuristicDecision],
        *,
        auto_apply: bool = False,
    ) -> list[Transformation]:
        transformations: list[Transformation] = []
        blocks_by_id = {block.block_id: block for block in document.blocks}
        group_counter = 0

        for poetry_decision in poetry_decisions:
            if poetry_decision.veto_reasons:
                continue
            if poetry_decision.decision not in {"diagnostic", "transform"}:
                continue

            group_counter += 1
            group_id = f"poetry_group_{group_counter:03d}"
            is_auto = auto_apply and poetry_decision.decision == "diagnostic"

            for line_index, block_id in enumerate(poetry_decision.target_refs, start=1):
                block = blocks_by_id.get(block_id)
                if block is None:
                    continue
                if block.block_type not in {"paragraph", "heading", "quote_block", "lineated_block"}:
                    continue

                before = block.block_type
                block.attributes["heuristic_score"] = poetry_decision.score
                if poetry_decision.decision == "transform" or is_auto:
                    block.block_type = "lineated_block"
                    block.attributes["alignment"] = "left"
                    block.attributes.pop("quote_kind", None)
                    block.attributes.pop("lineation", None)
                    block.attributes.pop("protected_zone", None)
                    write_block_semantics(
                        block,
                        BlockSemantics(
                            role="lineated_block",
                            layout_kind="lineated_block",
                            lineation="lineated",
                            lines=[block.text.strip()] if block.text.strip() else [],
                        ),
                    )
                    if is_auto:
                        block.attributes["highlight_color"] = "exploratory_structure"

                transformations.append(
                    self._make_tr(
                        block.block_id,
                        before,
                        block.block_type,
                        "structure.lineated.group.annotate",
                        attributes={
                            "poetry_group_id": group_id,
                            "poetry_line_index": line_index,
                            "score": poetry_decision.score,
                            "decision": poetry_decision.decision,
                        },
                    )
                )
        return transformations

    def _merge_poetry_by_group(
        self,
        document: Document,
        poetry_decisions: list[HeuristicDecision],
        *,
        auto_apply: bool = False,
    ) -> list[Transformation]:
        """Fusionne les vers d'une même strophe en un seul bloc (texte séparé par \\n)."""
        transformations: list[Transformation] = []
        blocks_by_id = {block.block_id: block for block in document.blocks}
        consumed_ids: set[str] = set()

        for decision in poetry_decisions:
            if decision.veto_reasons:
                continue
            is_auto = auto_apply and decision.decision == "diagnostic"
            if decision.decision != "transform" and not is_auto:
                continue
            target_ids = decision.target_refs
            if len(target_ids) < 2:
                continue

            first_block = blocks_by_id.get(target_ids[0])
            if first_block is None:
                continue

            lines = [
                blocks_by_id[bid].text.strip()
                for bid in target_ids
                if bid in blocks_by_id and blocks_by_id[bid].text.strip()
            ]
            source_blocks = [blocks_by_id[bid] for bid in target_ids if bid in blocks_by_id]
            merged_inlines = self._merged_poetry_inlines(source_blocks)
            first_block.text = "\n".join(lines)
            first_block.inlines = merged_inlines
            first_block.attributes["merged_from"] = target_ids
            first_block.block_type = "lineated_block"
            first_block.attributes["alignment"] = "left"
            first_block.attributes.pop("quote_kind", None)
            first_block.attributes.pop("lineation", None)
            first_block.attributes.pop("protected_zone", None)
            write_block_semantics(
                first_block,
                BlockSemantics(
                    role="lineated_block",
                    layout_kind="lineated_block",
                    lineation="lineated",
                    lines=lines,
                ),
            )
            if is_auto:
                first_block.attributes["highlight_color"] = "exploratory_structure"

            for bid in target_ids[1:]:
                consumed_ids.add(bid)

            transformations.append(
                self._make_tr(
                    first_block.block_id,
                    "paragraph",
                    "lineated_block",
                    "structure.lineated.stanza.merge",
                    attributes={"merged_from": target_ids, "score": decision.score},
                )
            )

        if consumed_ids:
            document.blocks = [
                b for b in document.blocks if b.block_id not in consumed_ids
            ]

        return transformations

    @staticmethod
    def _merged_poetry_inlines(sequence: list) -> list[InlineSpan]:
        merged: list[InlineSpan] = []
        for index, block in enumerate(sequence):
            if block.inlines:
                merged.extend(block.inlines)
            else:
                merged.append(InlineSpan(text=block.text.strip()))
            if index < len(sequence) - 1:
                merged.append(InlineSpan(text="", kind="line_break"))
        return merged

    def analyze_poetry_candidates(self, document: Document) -> list[HeuristicDecision]:
        settings = self.heuristic_settings
        decisions: list[HeuristicDecision] = []
        blocks_by_id = {block.block_id: index for index, block in enumerate(document.blocks)}
        for sequence in self._poetry_candidate_sequences(document):
            first_index = blocks_by_id.get(sequence[0].block_id, -1)
            last_index = blocks_by_id.get(sequence[-1].block_id, -1)
            previous_block = document.blocks[first_index - 1] if first_index > 0 else None
            next_block = (
                document.blocks[last_index + 1]
                if last_index >= 0 and last_index + 1 < len(document.blocks)
                else None
            )
            decisions.append(
                self._score_poetry_candidate(
                    sequence=sequence,
                    settings=settings,
                    previous_block=previous_block,
                    next_block=next_block,
                )
            )
        return decisions

    @classmethod
    def _short_poetry_candidate_sequences(cls, document: Document) -> list[list]:
        sequences: list[list] = []
        current: list = []

        for block in document.blocks:
            if cls._is_short_poetry_line_candidate(block):
                current.append(block)
                continue
            if cls._is_valid_short_poetry_sequence(current):
                sequences.append(current.copy())
            current.clear()

        if cls._is_valid_short_poetry_sequence(current):
            sequences.append(current.copy())
        return sequences

    @classmethod
    def _is_short_poetry_line_candidate(cls, block) -> bool:
        if block.block_type != "paragraph":
            return False
        text = block.text.strip()
        if not text:
            return False
        if len(text.split()) > 16:
            return False
        if text.endswith(":"):
            return False
        if block.attributes.get("all_runs_bold"):
            return False
        if block.attributes.get("list_level") is not None:
            return False
        if cls._looks_like_list_item(text):
            return False
        return True

    @classmethod
    def _is_valid_short_poetry_sequence(cls, sequence: list) -> bool:
        if len(sequence) < 3:
            return False
        if cls._poetry_veto_reasons(sequence):
            return False

        punctuated_count = sum(
            1 for block in sequence if cls._line_has_poetry_punctuation(block.text)
        )
        if len(sequence) == 3:
            return punctuated_count >= 1
        minimum_punctuated = max(1.0, len(sequence) / 3.0)
        return punctuated_count >= minimum_punctuated

    @staticmethod
    def _line_has_poetry_punctuation(text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return False
        return stripped.endswith((".", ",", ";", ":", "!", "?", "...", "\u2026"))

    @classmethod
    def _poetry_candidate_sequences(cls, document: Document) -> list[list]:
        sequences: list[list] = []
        current: list = []

        for block in document.blocks:
            text = block.text.strip()
            word_count = len(text.split()) if text else 0
            # Un bloc trop long est de la prose, pas un vers.
            # Un titre brise toujours la séquence.
            is_candidate = (
                block.block_type == "paragraph"
                and text
                and word_count <= 16
                and not cls._looks_like_list_item(text)
            )
            if not is_candidate:
                normalized = cls._normalize_poetry_sequence(current)
                if 3 <= len(normalized) <= _POETRY_SEQUENCE_MAX_LINES:
                    sequences.append(normalized)
                current.clear()
                continue

            # Rupture de strophe : paragraphe vide dans le source DOCX
            # ou écart vertical explicite entre blocs
            blank_before = bool(block.attributes.get("blank_para_before"))
            if current:
                prev_after  = current[-1].attributes.get("space_after",  0) or 0
                curr_before = block.attributes.get("space_before", 0) or 0
                stanza_break = (
                    blank_before
                    or max(prev_after, curr_before) > _POETRY_STANZA_SPACE_THRESHOLD
                )
                if stanza_break:
                    normalized = cls._normalize_poetry_sequence(current)
                    if 3 <= len(normalized) <= _POETRY_SEQUENCE_MAX_LINES:
                        sequences.append(normalized)
                    current.clear()

            # Dépassement de taille : sauvegarder ce qui est valide avant d'effacer
            if len(current) >= _POETRY_SEQUENCE_MAX_LINES:
                normalized = cls._normalize_poetry_sequence(current)
                if 3 <= len(normalized) <= _POETRY_SEQUENCE_MAX_LINES:
                    sequences.append(normalized)
                current.clear()

            current.append(block)

        normalized = cls._normalize_poetry_sequence(current)
        if 3 <= len(normalized) <= _POETRY_SEQUENCE_MAX_LINES:
            sequences.append(normalized)
        return sequences

    @staticmethod
    def _normalize_poetry_sequence(sequence: list) -> list:
        if not sequence:
            return []
        if len(sequence) >= 4:
            first_text = sequence[0].text.strip()
            if first_text.endswith(":") and len(first_text.split()) <= 4:
                return sequence[1:].copy()
        return sequence.copy()

    @classmethod
    def _score_poetry_candidate(
        cls,
        *,
        sequence: list,
        settings: HeuristicSettings,
        previous_block=None,
        next_block=None,
    ) -> HeuristicDecision:
        texts = [block.text.strip() for block in sequence]
        target_refs = [block.block_id for block in sequence]
        veto_reasons = cls._poetry_veto_reasons(sequence)

        lengths = [len(text) for text in texts]
        line_count = len(texts)
        avg_length = (sum(lengths) / line_count) if line_count else 0.0
        length_cv = (pstdev(lengths) / avg_length) if line_count > 1 and avg_length else 0.0

        word_counts = [len(text.split()) for text in texts]
        avg_word_count = (sum(word_counts) / line_count) if line_count else 0.0

        initial_upper_ratio = (
            sum(1 for text in texts if text[:1].isupper()) / line_count if line_count else 0.0
        )
        poetic_endings = (",", ";", ":", ".", "!", "?", "...")
        punctuation_ratio = (
            sum(1 for text in texts if text.endswith(poetic_endings)) / line_count if line_count else 0.0
        )
        intro_hits = 0
        intro_context_ratio = 0.0
        if previous_block is not None:
            prev_text = previous_block.text.strip().lower()
            prev_text_norm = unicodedata.normalize("NFKD", prev_text)
            prev_text_norm = "".join(ch for ch in prev_text_norm if not unicodedata.combining(ch))
            if (
                previous_block.block_type == "paragraph"
                and (
                    previous_block.text.rstrip().endswith(":")
                    or re.search(
                        r"\b(?:annonce|dit|repond|chante|recite|declame|ecrit|cite)\b",
                        prev_text_norm,
                    )
                )
            ):
                intro_hits += 1
        intro_hits += sum(
            1
            for text in texts
            if re.search(r"\b(?:dit|ecrit|\u00e9crit|chant|poeme|po\u00e8me|vers)\b", text.lower())
            or text.rstrip().endswith(":")
        )
        intro_context_ratio = min(1.0, intro_hits / max(1, line_count))

        indents = [int(block.attributes.get("ind_left", 0) or 0) for block in sequence]
        aligns = [str(block.attributes.get("alignment", "")).lower() for block in sequence]
        same_indent = len(set(indents)) <= 1
        same_alignment = len(set(align for align in aligns if align)) <= 1
        visual_homogeneity_component = (
            1.0 if (same_indent and same_alignment) else 0.65 if (same_indent or same_alignment) else 0.0
        )

        first_indent = indents[0] if indents else 0
        prev_indent = int(previous_block.attributes.get("ind_left", 0) or 0) if previous_block is not None else 0
        next_indent = int(next_block.attributes.get("ind_left", 0) or 0) if next_block is not None else 0
        # Isolation structurelle : retrait ou paragraphes vides encadrants (signal fort
        # que l'auteur a délibérément séparé ce bloc du texte courant).
        blank_isolated = bool(sequence[0].attributes.get("blank_para_before")) and (
            next_block is None or bool(next_block.attributes.get("blank_para_before"))
        )
        indentation_boundary_bonus = (
            1.0
            if (first_indent > 0 and prev_indent == 0 and (next_block is None or next_indent == 0))
            or blank_isolated
            else 0.0
        )

        line_count_component = min(1.0, line_count / 4.0)
        length_component = 1.0 if 18 <= avg_length <= 90 else 0.35 if 12 <= avg_length <= 120 else 0.0
        homogeneity_component = 1.0 if length_cv <= 0.35 else 0.45 if length_cv <= 0.60 else 0.0
        initial_component = min(1.0, initial_upper_ratio)
        punctuation_component = min(1.0, punctuation_ratio)
        intro_component = min(1.0, intro_context_ratio)
        # Un vers type : 3-9 mots ; la prose courte en a g\u00e9n\u00e9ralement plus
        word_count_component = 1.0 if 3 <= avg_word_count <= 16 else 0.5 if 2 <= avg_word_count <= 18 else 0.0

        score = (
            0.15 * line_count_component
            + 0.12 * length_component
            + 0.12 * homogeneity_component
            + 0.12 * initial_component
            + 0.12 * punctuation_component
            + 0.14 * word_count_component
            + 0.10 * intro_component
            + 0.08 * visual_homogeneity_component
            + 0.05 * indentation_boundary_bonus
        )
        score = round(max(0.0, min(1.0, score)), 3)

        in_note_zone = any(cls._is_note_zone_block(block) for block in sequence)
        transform_threshold = settings.poetry_transform_threshold
        diagnostic_threshold = settings.poetry_diagnostic_threshold
        if in_note_zone:
            transform_threshold = max(transform_threshold, 0.95)
            diagnostic_threshold = max(diagnostic_threshold, 0.80)

        if not settings.enable_scored_heuristics:
            ai_candidate = False
            decision_name = "ignore"
        else:
            ai_candidate = settings.poetry_ai_min_score <= score < settings.poetry_ai_max_score
            if veto_reasons:
                decision_name = "ignore"
            elif score >= transform_threshold:
                decision_name = "transform"
            elif score >= diagnostic_threshold:
                decision_name = "diagnostic"
            else:
                decision_name = "ignore"

        evidence = {
            "line_count": line_count,
            "avg_length": round(avg_length, 2),
            "avg_word_count": round(avg_word_count, 2),
            "length_cv": round(length_cv, 3),
            "initial_upper_ratio": round(initial_upper_ratio, 3),
            "punctuation_ratio": round(punctuation_ratio, 3),
            "intro_context_ratio": round(intro_context_ratio, 3),
            "visual_homogeneity_component": round(visual_homogeneity_component, 3),
            "indentation_boundary_bonus": round(indentation_boundary_bonus, 3),
            "blank_isolated": blank_isolated,
            "in_note_zone": in_note_zone,
            "word_count_component": round(word_count_component, 3),
            "excerpt": " | ".join(texts[:3])[:240],
            "source_heading_count": sum(
                1
                for block in sequence
                if block.block_type == "heading" or cls._source_heading_level(block) is not None
            ),
        }
        return HeuristicDecision(
            rule_id=_POETRY_RULE_ID,
            category=_POETRY_CATEGORY,
            target_refs=target_refs,
            score=score,
            decision=decision_name,
            evidence=evidence,
            veto_reasons=veto_reasons,
            ai_candidate=ai_candidate,
        )

    @classmethod
    def _poetry_veto_reasons(cls, sequence: list) -> list[str]:
        reasons: set[str] = set()
        in_note_zone = any(cls._is_note_zone_block(block) for block in sequence)
        bibliography_like_count = 0
        all_caps_count = 0
        for block in sequence:
            text = block.text.strip()
            if block.block_type == "heading" or cls._source_heading_level(block) is not None:
                reasons.add("heading_explicit")
            if cls._looks_like_passage_reference(text):
                reasons.add("passage_reference")
            if cls._looks_like_reference_or_caption(text):
                reasons.add("caption_or_reference")
            if text.isupper() and 4 < len(text) < 140:
                all_caps_count += 1
            if cls._looks_like_list_item(text):
                reasons.add("list_like")
            if cls._looks_like_chronology_line(text):
                reasons.add("chronology_like")
            if cls._looks_like_bibliography_reference(text):
                bibliography_like_count += 1
            if cls._looks_like_technical_markup(text):
                reasons.add("technical_markup")
        if all_caps_count == len(sequence) and all_caps_count > 0:
            reasons.add("heading_all_caps")
        if in_note_zone and bibliography_like_count > 0:
            reasons.add("bibliography_like")
        if bibliography_like_count >= max(2, len(sequence) // 2):
            reasons.add("bibliography_like")
        return sorted(reasons)

    @staticmethod
    def _looks_like_chronology_line(text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return False
        return bool(re.match(r"^\d{3,4}\s*[-–—:]\s+\S+", stripped))

    @staticmethod
    def _is_note_zone_block(block) -> bool:
        attrs = block.attributes or {}
        if attrs.get("is_note") or attrs.get("in_note") or attrs.get("note_zone"):
            return True
        style_blob = " ".join(
            str(attrs.get(key, "")) for key in ("style_name", "style_id", "xml_tag", "source")
        ).lower()
        style_norm = unicodedata.normalize("NFKD", style_blob)
        style_norm = "".join(ch for ch in style_norm if not unicodedata.combining(ch))
        return any(token in style_norm for token in ("footnote", "endnote", "note de bas", "notedebasdepage"))

    @staticmethod
    def _looks_like_technical_markup(text: str) -> bool:
        stripped = text.strip()
        if _TECHNICAL_TAG_RE.search(stripped):
            return True
        if _TECHNICAL_ATTR_RE.search(stripped):
            return True
        if _TECHNICAL_CODE_RE.search(stripped):
            return True
        return False

    @classmethod
    def _score_heading_candidate(
        cls,
        *,
        block,
        settings: HeuristicSettings,
        extra_veto_reasons: list[str] | None = None,
    ) -> HeuristicDecision:
        text = block.text.strip()
        source_level = cls._source_heading_level(block)
        veto_reasons = cls._heading_veto_reasons(block)
        if extra_veto_reasons:
            veto_reasons = sorted(set(veto_reasons).union(extra_veto_reasons))
        bold_title_fastpath = False

        if source_level is not None:
            score = 1.0
        elif not settings.enable_scored_heuristics:
            score = 0.0
        else:
            length = len(text)
            words = text.split()
            short_len_component = 1.0 if 8 <= length <= 90 else 0.35 if 4 <= length <= 120 else 0.0
            no_final_punct_component = 1.0 if not text.endswith((".", "!", "?", ";", ":")) else 0.0
            nominal_component = 0.0 if _VERB_LEAD_RE.match(text) else 1.0
            all_caps_component = 1.0 if text.isupper() and 4 < len(text) < 140 else 0.0
            bold_component = 1.0 if block.attributes.get("all_runs_bold") and not block.attributes.get("all_runs_italic") else 0.0
            numbered_component = 1.0 if re.match(r"^(?:\d+|[IVXLCDM]+)\s*[\.\-]\s+\S+", text, re.IGNORECASE) else 0.0
            title_case_component = 1.0 if words and words[0][:1].isupper() else 0.0
            heuristic_title_component = 1.0 if cls._looks_like_heading_heuristic(text, block) else 0.0

            score = (
                0.15 * short_len_component
                + 0.15 * no_final_punct_component
                + 0.10 * nominal_component
                + 0.10 * all_caps_component
                + 0.15 * bold_component
                + 0.10 * numbered_component
                + 0.05 * title_case_component
                + 0.20 * heuristic_title_component
            )
            if heuristic_title_component:
                score = max(score, 0.90)
            bold_title_fastpath = (
                bool(block.attributes.get("all_runs_bold"))
                and not bool(block.attributes.get("all_runs_italic"))
                and 8 <= length <= 120
                and len(words) <= 14
                and not veto_reasons
            )
            if bold_title_fastpath:
                score = max(score, settings.heading_transform_threshold)
            score = round(max(0.0, min(1.0, score)), 3)

        strong_signal = cls._has_strong_heading_signal(block, text)
        ai_candidate = (
            settings.enable_scored_heuristics
            and settings.heading_ai_min_score <= score < settings.heading_ai_max_score
        )
        if veto_reasons:
            decision_name = "ignore"
        elif source_level is not None:
            decision_name = "transform"
        elif strong_signal and score >= settings.heading_transform_threshold:
            decision_name = "transform"
        elif score >= settings.heading_diagnostic_threshold:
            decision_name = "diagnostic"
        else:
            decision_name = "ignore"

        return HeuristicDecision(
            rule_id=_HEADING_RULE_ID,
            category=_HEADING_CATEGORY,
            target_refs=[block.block_id],
            score=score,
            decision=decision_name,
            evidence={
                "text": text[:180],
                "source_heading_level": source_level,
                "all_runs_bold": bool(block.attributes.get("all_runs_bold")),
                "all_runs_italic": bool(block.attributes.get("all_runs_italic")),
                "word_count": len(text.split()),
                "char_count": len(text),
                "bold_title_fastpath": bold_title_fastpath,
                "strong_signal": strong_signal,
            },
            veto_reasons=veto_reasons,
            ai_candidate=ai_candidate,
        )

    @staticmethod
    def _has_strong_heading_signal(block, text: str) -> bool:
        if StructurePreparationService._source_heading_level(block) is not None:
            return True
        if bool(block.attributes.get("all_runs_bold")) and not bool(block.attributes.get("all_runs_italic")):
            return True
        if re.match(r"^(?:\d+|[IVXLCDM]+)\s*[\.\-]\s+\S+", text, re.IGNORECASE):
            return True
        if text.isupper() and 4 < len(text) < 140:
            return True
        try:
            font_size = float(block.attributes.get("font_size_pt", 0) or 0)
        except (TypeError, ValueError):
            font_size = 0.0
        return font_size >= 14.0

    @classmethod
    def _heading_veto_reasons(cls, block) -> list[str]:
        text = block.text.strip()
        reasons: set[str] = set()
        if cls._looks_like_passage_reference(text):
            reasons.add("passage_reference")
        if cls._looks_like_reference_or_caption(text):
            reasons.add("caption_or_reference")
        if cls._looks_like_list_item(text):
            reasons.add("list_like")
        if cls._looks_like_bibliography_reference(text):
            reasons.add("bibliography_like")
        if cls._looks_like_technical_markup(text):
            reasons.add("technical_markup")
        if cls._looks_like_poetry_line_candidate(block, text):
            reasons.add("poetry_line_candidate")
        if cls._looks_like_name_list(text):
            reasons.add("name_list")
        if text.endswith((".", "!", "?", ":", ";")) or _VERB_LEAD_RE.match(text):
            reasons.add("sentence_like")
        if cls._source_heading_level(block) is None and len(text.split()) <= 1:
            reasons.add("too_short_fragment")
        if _SENTENCE_CONNECTOR_RE.match(text):
            reasons.add("sentence_connector")
        return sorted(reasons)
    
    @staticmethod
    def _source_heading_level(block) -> int | None:
        explicit_level = block.attributes.get("heading_level")
        if isinstance(explicit_level, int) and 1 <= explicit_level <= 6:
            return explicit_level

        style_values = (
            str(block.attributes.get("style_id", "")),
            str(block.attributes.get("style_name", "")),
        )
        for style_value in style_values:
            if not style_value:
                continue
            match = _HEADING_STYLE_LEVEL_RE.search(style_value)
            if match:
                return int(match.group(1))
        return None

    @classmethod
    def _has_blocking_heading_signals(cls, block, text: str) -> bool:
        return (
            cls._looks_like_reference_or_caption(text)
            or cls._looks_like_passage_reference(text)
            or cls._looks_like_list_item(text)
            or cls._looks_like_bibliography_reference(text)
            or cls._looks_like_poetry_line_candidate(block, text)
        )

    @staticmethod
    def _looks_like_reference_or_caption(text: str) -> bool:
        stripped = text.strip()
        lower = stripped.lower()
        normalized = unicodedata.normalize("NFKD", lower)
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        if lower.startswith("p.") or lower.startswith("page"):
            return True
        blocked_fragments = (
            "accolade",
            "souligne",
            "soulignee",
            "face a",
            "face a",
            "voir ",
            "cf.",
        )
        return any(fragment in normalized for fragment in blocked_fragments)

    @staticmethod
    def _looks_like_passage_reference(text: str) -> bool:
        stripped = text.strip().strip(",;:.")
        if "," not in stripped:
            return False
        tokens = [token.strip().strip(".") for token in stripped.split(",") if token.strip()]
        if len(tokens) < 2:
            return False
        if not all(_PASSAGE_TOKEN_RE.match(token) for token in tokens):
            return False
        return any(re.search(r"\d|[IVXLCDM]", token, re.IGNORECASE) for token in tokens)

    @staticmethod
    def _looks_like_list_item(text: str) -> bool:
        normalized = re.sub(r"\s+", " ", text.strip())
        return bool(_LIST_MARKER_RE.match(normalized))

    @staticmethod
    def _looks_like_bibliography_reference(text: str) -> bool:
        lower = text.lower()
        markers = (" éd.", " ed.", " p.", " pp.", " vol.", " t.", " n°", " no.")
        if any(marker in lower for marker in markers):
            return True
        if "doi.org" in lower or "http://" in lower or "https://" in lower:
            return True
        return bool(re.search(r",\s*\d{4}\b", text))

    @staticmethod
    def _looks_like_poetry_line_candidate(block, text: str) -> bool:
        if not block.attributes.get("all_runs_italic"):
            return False
        stripped = text.strip()
        if not (20 <= len(stripped) <= 160):
            return False
        if not stripped[:1].isupper():
            return False
        if stripped.endswith((";", ",", ".", "?", "!", ":")):
            return True
        return False

    @staticmethod
    def _looks_like_name_list(text: str) -> bool:
        """Vrai si le texte est une liste d'au moins 3 noms propres séparés par virgules.

        Exemples : 'Tony Gheeraert, Victoire Malenfer, Caroline Labrune, Servane L'Hopital'
                   'A. Dupont, B. Martin et C. Durand'
        """
        normalized = re.sub(r",?\s+et\s+", ",", text.strip())
        parts = [p.strip() for p in normalized.split(",") if p.strip()]
        if len(parts) < _COMMA_NAME_LIST_MIN_PARTS:
            return False
        for part in parts:
            words = part.split()
            if len(words) < 2:
                return False
            if re.search(r"\d|[()[\]{}<>]", part):
                return False
            if not words[0][:1].isupper():
                return False
        return True

    @classmethod
    def _is_heading_candidate(cls, text: str, block=None) -> bool:
        """Vrai si le texte ressemble à un titre (court, sans ponctuation de phrase)."""
        if len(text) > 180:
            return False
        stripped = text.strip()
        if block is not None and cls._has_blocking_heading_signals(block, stripped):
            return False
        if stripped[-1:] in ".?!,":
            return False
        # Entrée bibliographique : virgule + année
        if re.search(r",\s*\d{4}", stripped):
            return False
        # Phrase avec clause subordonée après virgule
        if re.search(r",\s+[a-z]{4,}", stripped):
            return False
        # Point final sans être une abréviation  phrase terminée
        if stripped[-1:] == "." and len(stripped) > 60:
            return False
        # Commence par un mot de crédit éditorial
        if _CREDIT_START_RE.match(stripped):
            return False
        # Se termine par une préposition (ligne de crédit : "Textes réunis par")
        last_word = stripped.rsplit()[-1].lower() if stripped else ""
        if last_word in {"par", "de", "du", "des", "au", "aux", "en", "à"}:
            return False
        # Fragment verbal en tête de phrase  pas un titre
        if _VERB_LEAD_RE.match(stripped):
            return False
        # Paire de noms propres  crédit éditorial
        if _NAME_PAIR_RE.match(stripped):
            return False
        # Entrée abréviation (SIGLE : développement)
        if _ABBREV_ENTRY_RE.match(stripped):
            return False
        # Institution  pas un titre structurant
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
    def _classify_italic_block(text: str, attrs: dict, block=None) -> str:
        """
        Pour un paragraphe tout-italique :
        - 'author'   nom d'auteur (court, < 5 mots, pas de chiffres ni virgule)
        - 'heading'  titre de chapitre ou section
        - ''         laisser tel quel (biblio, traduction, citation, etc.)
        """
        stripped = text.strip()
        if block is not None and StructurePreparationService._has_blocking_heading_signals(block, stripped):
            return ""
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
        # Texte trop long  passage cité, traduction
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
        # Liste de 3+ noms propres  signature éditoriale, pas un titre
        if StructurePreparationService._looks_like_name_list(stripped):
            return ""
        # Titre numéroté  heading
        if _NUMBERED_SECTION_RE.match(stripped):
            return "heading"
        # Titre de chapitre : 4-25 mots, pas de virgule-clause, pas d'année
        if (4 <= len(words) <= 25
                and len(stripped) <= 200
                and not re.search(r",\s+[a-z]{4,}", stripped)):
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
    def _looks_like_heading_heuristic(cls, text: str, block=None) -> bool:
        """
        Heuristique très conservatrice  seulement pour des cas structurels non ambigus.
        On évite les faux positifs au prix de quelques manqués.
        """
        stripped = text.strip()
        if block is not None and cls._has_blocking_heading_signals(block, stripped):
            return False
        words = stripped.split()
        # Taille : 2-8 mots, longueur  70 chars
        if not (2 <= len(words) <= 8 and len(stripped) <= 70):
            return False
        # Pas de ponctuation finale de phrase
        if stripped[-1:] in ".!?,":
            return False
        # Commence par une majuscule
        if not stripped[:1].isupper():
            return False
        # Roman numeral seul (I, II, V)  pas un titre heuristique
        if _ROMAN_ONLY_RE.match(stripped):
            return False
        # Absence de conjonction de coordination en début de phrase
        if _SENTENCE_CONNECTOR_RE.match(stripped):
            return False
        # Pas un item de liste
        if re.match(r"^[-]\s", stripped):
            return False
        # Pas une entrée bibliographique
        if re.search(r",\s*\d{4}", stripped):
            return False
        # Pas une clause subordonnée
        if re.search(r",\s+[a-z]{4,}", stripped):
            return False
        if re.search(r"\s(qui|que|dont|où|car|mais|avec|dans|pour|sur)\s", stripped):
            return False
        # Pas un crédit éditorial
        if _CREDIT_START_RE.match(stripped):
            return False
        last_word = stripped.rsplit()[-1].lower() if stripped else ""
        if last_word in {"par", "de", "du", "des", "au", "aux", "en", "à"}:
            return False
        # Fragment verbal en tête  pas un titre
        if _VERB_LEAD_RE.match(stripped):
            return False
        # Paire de noms propres  crédit éditorial
        if _NAME_PAIR_RE.match(stripped):
            return False
        # Liste de 3+ noms propres séparés par virgules  signature, pas un titre
        if cls._looks_like_name_list(stripped):
            return False
        # Entrée abréviation (SIGLE : développement)
        if _ABBREV_ENTRY_RE.match(stripped):
            return False
        # Institution  pas un titre structurant
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
