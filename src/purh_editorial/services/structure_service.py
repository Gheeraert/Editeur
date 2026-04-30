from __future__ import annotations

from dataclasses import dataclass, field
import re
from statistics import pstdev
from typing import Any
import unicodedata

from purh_editorial.model import BibliographyItem, Diagnostic, Document, Evidence, Transformation
from purh_editorial.utils import make_id

# â”€â”€ Constantes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_SECTION_BIBLIO_RE = re.compile(
    r"^(sources?|bibliographie|rÃ©fÃ©rences\s*bibliographiques?|bibliography|"
    r"travaux\s*citÃ©s?|works?\s*cited)",
    re.IGNORECASE | re.UNICODE,
)
_EPIGRAPH_MAX_CHARS   = 350
_PUNCT_ENDINGS        = set(".!?â€¦,")
_NUMBERED_SECTION_RE  = re.compile(r"^(\d+)\s*[-\.]\s*")
_CREDIT_START_RE      = re.compile(
    r"^(Sous|Dans|Pour|Avec|Sur|Par|Textes?|Ã‰tudes?|Articles?|Ouvrage|Actes?)\s+",
    re.IGNORECASE | re.UNICODE,
)
# Verbe conjuguÃ© EN TÃŠTE de phrase (imparfait 3sg, conditionnel, prÃ©sent 3e pl.)
_VERB_LEAD_RE         = re.compile(
    r"^[A-Z][A-Za-z]*(ait|aient|ront|raient|rait|ions|iez)\b",
    re.UNICODE,
)
# Paire de noms propres : "PrÃ©nom NOM et PrÃ©nom NOM" â†’ crÃ©dit Ã©ditorial, pas titre
_NAME_PAIR_RE         = re.compile(
    r"^[A-Z][A-Za-z\-]+(\s+[A-Za-z\-]+)+\s+et\s+[A-Z]",
    re.UNICODE,
)
_ROMAN_ONLY_RE        = re.compile(r"^[IVXLCDMivxlcdm]{1,5}$")
_PASSAGE_TOKEN_RE     = re.compile(r"^(?:[IVXLCDM]+|\d+|[A-Za-z]{1,4})$", re.IGNORECASE)
# EntrÃ©e de glossaire/abrÃ©viations : SIGLE : dÃ©veloppement
_ABBREV_ENTRY_RE      = re.compile(r"^[A-Z]{2,6}[ ]?\s*:")
# Institution : UniversitÃ©, Ã‰cole, Institut, CNRS, Laboratoireâ€¦
_INSTITUTION_RE       = re.compile(
    r"^(Universit[eÃ©]|Ã‰cole|Institut|CNRS|UMR|Laboratoire|Centre|Facult[eÃ©]|UFR"
    r"|Acad[eÃ©]mie|Fondation|Museum|MusÃ©e|Biblioth[eÃ¨]que)",
    re.IGNORECASE | re.UNICODE,
)

# Noms d'auteur en italique : 2-4 mots, pas de chiffres, pas de ponctuation sauf tiret
_AUTHOR_NAME_RE = re.compile(
    r"^[A-Z][a-z\-]+"       # PrÃ©nom ou Nom majuscule
    r"(\s+[A-Za-z\.\-']+){0,3}$",     # 0 Ã  3 mots supplÃ©mentaires
    re.UNICODE,
)

# Seuil d'indentation gauche (twips) au-delÃ  duquel on considÃ¨re un bloc-citation
# (Ne s'applique que si ind_first_line est absent/nul â€” retrait bloc, pas alinÃ©a)
_BLOCK_QUOTE_IND_LEFT_THRESHOLD = 400
_BLOCK_QUOTE_MIN_LEN = 60

# Bibliographie heuristique (hors section dÃ©diÃ©e)
_BIBLIO_HEURISTIC_RE = re.compile(
    r"^[A-Z\(][A-Za-z\'\-\s]{1,40},"
    r".{5,},"
    r"\s*\d{4}",
    re.UNICODE,
)


_HEADING_STYLE_LEVEL_RE = re.compile(r"(?:heading|titre)\s*([1-6])", re.IGNORECASE)
_TECHNICAL_ATTR_RE = re.compile(r"\b[\w:-]+\s*=\s*\"[^\"]*\"")
_TECHNICAL_TAG_RE = re.compile(r"<[^>]+>")
_TECHNICAL_CODE_RE = re.compile(r"\b(print|class|def|return)\s*\(", re.IGNORECASE)
_POETRY_RULE_ID = "R-CI-POETRY-001"
_POETRY_CATEGORY = "poetry_quote_candidate"
_HEADING_RULE_ID = "R-STRUCT-HEADING-001"
_HEADING_CATEGORY = "heading_candidate"


@dataclass(slots=True)
class HeuristicSettings:
    poetry_transform_threshold: float = 0.90
    poetry_diagnostic_threshold: float = 0.65
    poetry_ai_min_score: float = 0.65
    poetry_ai_max_score: float = 0.90
    allow_ai_for_poetry_candidates: bool = False
    heading_transform_threshold: float = 0.85
    heading_diagnostic_threshold: float = 0.60
    heading_ai_min_score: float = 0.60
    heading_ai_max_score: float = 0.85


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
    DÃ©tecte et annote la structure d'un document dont l'auteur
    n'a pas utilisÃ© les styles Word de faÃ§on normative.

    Patterns dÃ©tectÃ©s :
    - Normal + gras seul â†’ titre (pattern Dissimuler)
    - Normal + tout-italique â†’ titre de chapitre OU nom d'auteur (pattern HÃ©raldique)
    - Normal + retrait gauche > 400 twips (sans alinÃ©a) â†’ citation longue
    - Normal + ALL CAPS court â†’ titre structurant (dÃ©jÃ  partiellement gÃ©rÃ© Ã  l'ingestion)
    - Titres numÃ©rotÃ©s "1- Titre" â†’ intertitre de niveau 2
    - Section bibliographique â†’ TEI_bibl_reference
    """

    module_name = "structure"

    def __init__(self, heuristic_settings: HeuristicSettings | None = None) -> None:
        self.heuristic_settings = heuristic_settings or HeuristicSettings()

    def process(self, document: Document) -> tuple[list[Diagnostic], list[Transformation]]:
        diagnostics: list[Diagnostic] = []
        transformations: list[Transformation] = []

        # PrÃ©-calcul de l'indentation dominante du document
        # (permet de distinguer le retrait standard du retrait de citation)
        dominant_ind_left = self._dominant_ind_left(document)

        bib_index      = len(document.bibliography) + 1
        in_bib_section = False
        # Initialiser le compteur avec les titres dÃ©jÃ  dÃ©tectÃ©s Ã  l'ingestion
        # (ALLCAPS, styles Titre1/2/3â€¦) pour que l'Ã©pigraphe ne s'applique pas
        # Ã  tout le texte avant le premier titre heuristique.
        heading_count = sum(1 for b in document.blocks if b.block_type == "heading")

        for block in document.blocks:
            text = block.text.strip()
            if not text:
                continue
            has_blocking_heading_signals = self._has_blocking_heading_signals(block, text)
            heading_decision = None
            if block.block_type == "paragraph":
                heading_decision = self._score_heading_candidate(block=block, settings=self.heuristic_settings)

            # â”€â”€ Titre de section bibliographique â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if block.block_type == "heading" and _SECTION_BIBLIO_RE.match(text):
                in_bib_section = True
                heading_count += 1
                continue

            # â”€â”€ Sortie de mode biblio sur tout titre â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if block.block_type == "heading" and in_bib_section:
                in_bib_section = False
                heading_count += 1
                continue

            source_heading_level = self._source_heading_level(block)
            if (block.block_type == "paragraph"
                    and source_heading_level is not None
                    and heading_decision is not None
                    and heading_decision.decision == "transform"):
                self._promote_heading(
                    block,
                    level=source_heading_level,
                    rule="structure.source_style.heading",
                    transformations=transformations,
                )
                in_bib_section = False
                heading_count += 1
                continue

            # â”€â”€ Normal + ALL CAPS â†’ titre (peut arriver si l'ingestion a ratÃ©) â”€â”€
            if (block.block_type == "paragraph"
                    and text.isupper()
                    and 4 < len(text) < 140
                    and heading_decision is not None
                    and heading_decision.decision == "transform"):
                self._promote_heading(block, level=1, rule="structure.allcaps.heading",
                                      transformations=transformations)
                in_bib_section = False
                heading_count += 1
                continue

            # â”€â”€ Normal + GRAS seul â†’ titre (pattern Dissimuler) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if (block.block_type == "paragraph"
                    and block.attributes.get("all_runs_bold")
                    and not block.attributes.get("all_runs_italic")
                    and heading_decision is not None
                    and heading_decision.decision == "transform"
                    and self._is_heading_candidate(text, block)):
                level = self._bold_heading_level(text)
                self._promote_heading(block, level=level, rule="structure.bold.heading",
                                      transformations=transformations)
                in_bib_section = False
                heading_count += 1
                continue

            # â”€â”€ Normal + ITALIQUE seul â†’ titre OU auteur (pattern HÃ©raldique) â”€
            if (block.block_type == "paragraph"
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
                    if heading_decision is not None and heading_decision.decision == "transform":
                        self._promote_heading(block, level=level, rule="structure.italic.heading",
                                              transformations=transformations)
                        in_bib_section = False
                        heading_count += 1
                        continue

            # â”€â”€ Ã‰pigraphe (avant le 1er titre, court, pas de ponctuation finale) â”€
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

            # â”€â”€ Section biblio â†’ entrÃ©es â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if in_bib_section and block.block_type == "paragraph" and text:
                self._mark_biblio(block, document, bib_index, transformations, rule="structure.bibliography.section")
                bib_index += 1
                continue

            # â”€â”€ Retrait gauche > seuil â†’ citation bloc (HÃ©raldique) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            ind_left     = block.attributes.get("ind_left", 0)
            ind_fl       = block.attributes.get("ind_first_line", 0)
            # Un retrait purement Ã  gauche (pas un alinÃ©a de 1e ligne) = bloc-citation
            if (block.block_type == "paragraph"
                    and ind_left > _BLOCK_QUOTE_IND_LEFT_THRESHOLD
                    and not ind_fl                   # pas d'alinÃ©a de 1e ligne
                    and ind_left != dominant_ind_left # pas le retrait dominant du doc
                    and len(text) >= _BLOCK_QUOTE_MIN_LEN):
                block.block_type = "quote_block"
                transformations.append(self._make_tr(
                    block.block_id, "paragraph", "quote_block",
                    "structure.indent.quote",
                ))
                continue

            # â”€â”€ Heuristique biblio hors section â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
                    message="EntrÃ©e bibliographique potentielle dÃ©tectÃ©e hors section.",
                    target_ref=block.block_id,
                    rule_id="structure.bibliography.heuristic",
                    evidence=Evidence(excerpt=text[:180]),
                ))
                continue

            # â”€â”€ Citation longue via guillemets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if block.block_type == "paragraph" and self._looks_like_block_quote(text):
                block.block_type = "quote_block"
                transformations.append(self._make_tr(
                    block.block_id, "paragraph", "quote_block",
                    "structure.quote.guillemets",
                ))

            # Promotion de titre si heuristique (titre non-stylÃ© court)
            if (block.block_type == "paragraph"
                    and heading_decision is not None
                    and heading_decision.decision == "transform"
                    and self._looks_like_heading_heuristic(text, block)):
                level = self._heuristic_heading_level(text)
                self._promote_heading(block, level=level, rule="structure.heading.heuristic",
                                      transformations=transformations)
                heading_count += 1

            if (block.block_type == "paragraph"
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

        poetry_decisions = self.analyze_poetry_candidates(document)
        for poetry_decision in poetry_decisions:
            if poetry_decision.decision != "diagnostic":
                continue
            excerpt = poetry_decision.evidence.get("excerpt", "")
            diagnostics.append(
                Diagnostic(
                    diagnostic_id=make_id("diag"),
                    module=self.module_name,
                    severity="info",
                    category=_POETRY_CATEGORY,
                    message=(
                        "Candidate citation poetique detectee: verifier manuellement "
                        "avant toute structuration."
                    ),
                    target_ref=poetry_decision.target_refs[0] if poetry_decision.target_refs else "",
                    rule_id=_POETRY_RULE_ID,
                    evidence=Evidence(excerpt=excerpt),
                    attributes={
                        "score": poetry_decision.score,
                        "decision": poetry_decision.decision,
                        "evidence": poetry_decision.evidence,
                        "veto_reasons": poetry_decision.veto_reasons,
                        "ai_candidate": poetry_decision.ai_candidate,
                    },
                )
            )

        return diagnostics, transformations

    # â”€â”€ Helpers de promotion â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    # â”€â”€ Classifieurs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def analyze_poetry_candidates(self, document: Document) -> list[HeuristicDecision]:
        settings = self.heuristic_settings
        decisions: list[HeuristicDecision] = []
        for sequence in self._poetry_candidate_sequences(document):
            decisions.append(self._score_poetry_candidate(sequence=sequence, settings=settings))
        return decisions

    @staticmethod
    def _poetry_candidate_sequences(document: Document) -> list[list]:
        sequences: list[list] = []
        current: list = []

        for block in document.blocks:
            if block.block_type == "paragraph" and block.text.strip():
                current.append(block)
                continue
            if len(current) >= 3:
                sequences.append(current.copy())
            current.clear()

        if len(current) >= 3:
            sequences.append(current.copy())
        return sequences

    @classmethod
    def _score_poetry_candidate(
        cls,
        *,
        sequence: list,
        settings: HeuristicSettings,
    ) -> HeuristicDecision:
        texts = [block.text.strip() for block in sequence]
        target_refs = [block.block_id for block in sequence]
        veto_reasons = cls._poetry_veto_reasons(sequence)

        lengths = [len(text) for text in texts]
        line_count = len(texts)
        avg_length = (sum(lengths) / line_count) if line_count else 0.0
        length_cv = (pstdev(lengths) / avg_length) if line_count > 1 and avg_length else 0.0

        initial_upper_ratio = (
            sum(1 for text in texts if text[:1].isupper()) / line_count if line_count else 0.0
        )
        poetic_endings = (",", ";", ":", ".", "!", "?", "...")
        punctuation_ratio = (
            sum(1 for text in texts if text.endswith(poetic_endings)) / line_count if line_count else 0.0
        )
        intro_context_ratio = (
            sum(
                1
                for text in texts
                if re.search(r"\b(?:dit|ecrit|écrit|chant|poeme|poème|vers)\b", text.lower())
                or text.rstrip().endswith(":")
            )
            / line_count
            if line_count
            else 0.0
        )

        line_count_component = min(1.0, line_count / 4.0)
        length_component = 1.0 if 18 <= avg_length <= 90 else 0.35 if 12 <= avg_length <= 120 else 0.0
        homogeneity_component = 1.0 if length_cv <= 0.35 else 0.45 if length_cv <= 0.60 else 0.0
        initial_component = min(1.0, initial_upper_ratio)
        punctuation_component = min(1.0, punctuation_ratio)
        intro_component = min(1.0, intro_context_ratio)

        score = (
            0.20 * line_count_component
            + 0.18 * length_component
            + 0.16 * homogeneity_component
            + 0.18 * initial_component
            + 0.18 * punctuation_component
            + 0.10 * intro_component
        )
        score = round(max(0.0, min(1.0, score)), 3)

        ai_candidate = settings.poetry_ai_min_score <= score < settings.poetry_ai_max_score
        if veto_reasons:
            decision_name = "ignore"
        elif score >= settings.poetry_transform_threshold:
            decision_name = "transform"
        elif score >= settings.poetry_diagnostic_threshold:
            decision_name = "diagnostic"
        else:
            decision_name = "ignore"

        evidence = {
            "line_count": line_count,
            "avg_length": round(avg_length, 2),
            "length_cv": round(length_cv, 3),
            "initial_upper_ratio": round(initial_upper_ratio, 3),
            "punctuation_ratio": round(punctuation_ratio, 3),
            "intro_context_ratio": round(intro_context_ratio, 3),
            "excerpt": " | ".join(texts[:3])[:240],
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
        for block in sequence:
            text = block.text.strip()
            if cls._looks_like_passage_reference(text):
                reasons.add("passage_reference")
            if cls._looks_like_reference_or_caption(text):
                reasons.add("caption_or_reference")
            if cls._looks_like_list_item(text):
                reasons.add("list_like")
            if cls._looks_like_bibliography_reference(text):
                reasons.add("bibliography_like")
            if block.block_type == "heading" or cls._source_heading_level(block) is not None:
                reasons.add("heading_explicit")
            if cls._looks_like_technical_markup(text):
                reasons.add("technical_markup")
        return sorted(reasons)

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
    def _score_heading_candidate(cls, *, block, settings: HeuristicSettings) -> HeuristicDecision:
        text = block.text.strip()
        source_level = cls._source_heading_level(block)
        veto_reasons = cls._heading_veto_reasons(block)
        bold_title_fastpath = False

        if source_level is not None:
            score = 1.0
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

        ai_candidate = settings.heading_ai_min_score <= score < settings.heading_ai_max_score
        if veto_reasons:
            decision_name = "ignore"
        elif source_level is not None:
            decision_name = "transform"
        elif score >= settings.heading_transform_threshold:
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
            },
            veto_reasons=veto_reasons,
            ai_candidate=ai_candidate,
        )

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
        if text.endswith((".", "!", "?")) or _VERB_LEAD_RE.match(text):
            reasons.add("sentence_like")
        if cls._source_heading_level(block) is None and len(text.split()) <= 1:
            reasons.add("too_short_fragment")
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
        stripped = text.lstrip()
        if re.match(r"^[-â€“â€”â€¢]\s+", stripped):
            return True
        if re.match(r"^\d+\s*[\.\)]\s+", stripped):
            return True
        if re.match(r"^[A-Za-z]\)\s+", stripped):
            return True
        return False

    @staticmethod
    def _looks_like_bibliography_reference(text: str) -> bool:
        lower = text.lower()
        markers = (" Ã©d.", " ed.", " p.", " pp.", " vol.", " t.", " nÂ°", " no.")
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

    @classmethod
    def _is_heading_candidate(cls, text: str, block=None) -> bool:
        """Vrai si le texte ressemble Ã  un titre (court, sans ponctuation de phrase)."""
        if len(text) > 180:
            return False
        stripped = text.strip()
        if block is not None and cls._has_blocking_heading_signals(block, stripped):
            return False
        if stripped[-1:] in ".?!,":
            return False
        # EntrÃ©e bibliographique : virgule + annÃ©e
        if re.search(r",\s*\d{4}", stripped):
            return False
        # Phrase avec clause subordonÃ©e aprÃ¨s virgule
        if re.search(r",\s+[a-z]{4,}", stripped):
            return False
        # Point final sans Ãªtre une abrÃ©viation â†’ phrase terminÃ©e
        if stripped[-1:] == "." and len(stripped) > 60:
            return False
        # Commence par un mot de crÃ©dit Ã©ditorial
        if _CREDIT_START_RE.match(stripped):
            return False
        # Se termine par une prÃ©position (ligne de crÃ©dit : "Textes rÃ©unis par")
        last_word = stripped.rsplit()[-1].lower() if stripped else ""
        if last_word in {"par", "de", "du", "des", "au", "aux", "en", "Ã "}:
            return False
        # Fragment verbal en tÃªte de phrase â†’ pas un titre
        if _VERB_LEAD_RE.match(stripped):
            return False
        # Paire de noms propres â†’ crÃ©dit Ã©ditorial
        if _NAME_PAIR_RE.match(stripped):
            return False
        # EntrÃ©e abrÃ©viation (SIGLE : dÃ©veloppement)
        if _ABBREV_ENTRY_RE.match(stripped):
            return False
        # Institution â†’ pas un titre structurant
        if _INSTITUTION_RE.match(stripped):
            return False
        return True

    @staticmethod
    def _bold_heading_level(text: str) -> int:
        """DÃ©termine le niveau d'un titre formatÃ© en gras."""
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
        """DÃ©termine le niveau d'un titre formatÃ© en italique."""
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
        - 'author'  â†’ nom d'auteur (court, < 5 mots, pas de chiffres ni virgule)
        - 'heading' â†’ titre de chapitre ou section
        - ''        â†’ laisser tel quel (biblio, traduction, citation, etc.)
        """
        stripped = text.strip()
        if block is not None and StructurePreparationService._has_blocking_heading_signals(block, stripped):
            return ""
        words = stripped.split()
        # Trop court (1 mot)
        if len(words) < 2:
            return ""
        # EntrÃ©e bibliographique : virgule + annÃ©e
        if re.search(r",\s*\d{4}", stripped):
            return ""
        # EntrÃ©e bibliographique : prÃ©sence d'un DOI ou URL
        if "http" in stripped or "doi.org" in stripped:
            return ""
        # Texte trop long â†’ passage citÃ©, traduction
        if len(stripped) > 250:
            return ""
        # Nom d'auteur : 2-4 mots, pas de chiffres, pas de guillemets, pas de virgule
        if (2 <= len(words) <= 4
                and not re.search(r"\d", stripped)
                and "," not in stripped
                and "Â«" not in stripped
                and "(" not in stripped):
            # Heuristique complÃ©mentaire : les noms propres commencent par une majuscule
            if all(w[0].isupper() for w in words if w and w[0].isalpha()):
                return "author"
        # Titre numÃ©rotÃ© â†’ heading
        if _NUMBERED_SECTION_RE.match(stripped):
            return "heading"
        # Titre de chapitre : 4-25 mots, pas de virgule-clause, pas d'annÃ©e
        if (4 <= len(words) <= 25
                and len(stripped) <= 200
                and not re.search(r",\s+[a-z]{4,}", stripped)):
            return "heading"
        return ""

    @staticmethod
    def _looks_like_block_quote(text: str) -> bool:
        """DÃ©tecte une citation longue entre guillemets ou avec tiret."""
        if len(text) > 180 and text.startswith("Â«"):
            return True
        if len(text) > 120 and text.startswith("Â«") and text.endswith("Â»"):
            return True
        return False

    @classmethod
    def _looks_like_heading_heuristic(cls, text: str, block=None) -> bool:
        """
        Heuristique trÃ¨s conservatrice â€” seulement pour des cas structurels non ambigus.
        On Ã©vite les faux positifs au prix de quelques manquÃ©s.
        """
        stripped = text.strip()
        if block is not None and cls._has_blocking_heading_signals(block, stripped):
            return False
        words = stripped.split()
        # Taille : 2-8 mots, longueur â‰¤ 70 chars
        if not (2 <= len(words) <= 8 and len(stripped) <= 70):
            return False
        # Pas de ponctuation finale de phrase
        if stripped[-1:] in ".!?â€¦,":
            return False
        # Commence par une majuscule
        if not stripped[:1].isupper():
            return False
        # Roman numeral seul (I, II, Vâ€¦) â†’ pas un titre heuristique
        if _ROMAN_ONLY_RE.match(stripped):
            return False
        # Pas un item de liste
        if re.match(r"^[-â€“â€”â€¢]\s", stripped):
            return False
        # Pas une entrÃ©e bibliographique
        if re.search(r",\s*\d{4}", stripped):
            return False
        # Pas une clause subordonnÃ©e
        if re.search(r",\s+[a-z]{4,}", stripped):
            return False
        if re.search(r"\s(qui|que|dont|oÃ¹|car|mais|avec|dans|pour|sur)\s", stripped):
            return False
        # Pas un crÃ©dit Ã©ditorial
        if _CREDIT_START_RE.match(stripped):
            return False
        last_word = stripped.rsplit()[-1].lower() if stripped else ""
        if last_word in {"par", "de", "du", "des", "au", "aux", "en", "Ã "}:
            return False
        # Fragment verbal en tÃªte â†’ pas un titre
        if _VERB_LEAD_RE.match(stripped):
            return False
        # Paire de noms propres â†’ crÃ©dit Ã©ditorial
        if _NAME_PAIR_RE.match(stripped):
            return False
        # EntrÃ©e abrÃ©viation (SIGLE : dÃ©veloppement)
        if _ABBREV_ENTRY_RE.match(stripped):
            return False
        # Institution â†’ pas un titre structurant
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
        """Retourne le retrait gauche le plus frÃ©quent dans le document (ou 0)."""
        from collections import Counter
        counter: Counter = Counter()
        for block in document.blocks:
            v = block.attributes.get("ind_left", 0)
            if v:
                counter[v] += 1
        if counter:
            return counter.most_common(1)[0][0]
        return 0

