from __future__ import annotations

import copy
import re
from dataclasses import dataclass

from purh_editorial.model import Diagnostic, Document, Evidence, InlineSpan, Note, Transformation
from purh_editorial.services.orthotypo_service import (
    COLOR_FOOTNOTE, NNBSP, RuleOccurrence, TypoRule, _apply_rule_with_occurrences,
    _find_changed_regions,
)
from purh_editorial.utils import make_id

# URLs et fins de ligne qui acceptent legitimement l'absence de point final.
_URL_RE = re.compile(r"https?://\S+$")
_VERSE_END_RE = re.compile(r"[»›’]\s*$")

# Debuts de note qui ne doivent jamais recevoir de majuscule automatique : URL/DOI,
# noms a particule, abreviations latines deja gerees par purh.note.abreviation_latine.
_URL_OR_DOI_START_RE = re.compile(r"^\s*(https?://|www\.|doi\s*:)", re.IGNORECASE)
_PARTICLE_START_RE = re.compile(r"^\s*(van|von|de|du|des)\b|^\s*d['’]", re.IGNORECASE)
_LATIN_ABBR_START_RE = re.compile(
    r"^\s*(ibid|id|idem|op\.\s*cit|art\.\s*cit|loc\.\s*cit|s\.\s*[ld])\.?\b",
    re.IGNORECASE,
)

# Tirets en liste dans les notes -> pas de correction.
_LIST_ITEM_RE = re.compile(r"^\s*[-–—•]\s")
_FINAL_PUNCT = {".", ",", ";", ":", "?", "!"}
_CLOSING_PUNCT_OR_QUOTE = {".", "!", "?", "…", "»", "”", "’"}
_CLOSING_QUOTES = {"»", '"', "”", "›"}
_SPACING_CHARS = {" ", " ", " "}
_LEADING_SPACE_RE = re.compile(r"^[ \t  ]+")

# Regle "purh.note.abreviation_latine" : minuscule les abreviations de reference
# ailleurs qu'en debut de note (le debut de note est traite par
# purh.note.majuscule_initiale, qui exclut explicitement ces abreviations).
_ABBR_MIDNOTE_RULE = TypoRule(
    rule_id="purh.note.abreviation_latine",
    pattern=re.compile(
        r"(?<!^)\b(Ibid|Id|Idem|Op\.\s*cit|Art\.\s*cit|Loc\.\s*cit)\b\.?",
        re.IGNORECASE,
    ),
    replacement=lambda m: m.group(0).lower(),
    description="Minuscule les abreviations de reference hors debut de note.",
)

_OP_CIT_RULE = TypoRule(
    rule_id="purh.note.espace_op_cit",
    pattern=re.compile(r"\b(op|art|loc)\.[ \t  ]+(cit)\.", re.IGNORECASE),
    replacement=r"\1." + NNBSP + r"\2.",
    description="Espace fine insecable dans op. cit. / art. cit. / loc. cit.",
)

_SL_SD_RULE = TypoRule(
    rule_id="purh.note.espace_sans_lieu_date",
    pattern=re.compile(r"\bs\.[ \t  ]+([ld])\.", re.IGNORECASE),
    replacement="s." + NNBSP + r"\1.",
    description="Espace fine insecable dans s. l. / s. d.",
)


def _looks_like_url_or_verse(text: str) -> bool:
    s = text.strip()
    return bool(_URL_RE.search(s)) or bool(_VERSE_END_RE.search(s))


def _majuscule_initiale_excluded(text: str) -> bool:
    """True si le debut de `text` ne doit jamais recevoir de majuscule automatique."""
    return bool(
        _URL_OR_DOI_START_RE.match(text)
        or _PARTICLE_START_RE.match(text)
        or _LATIN_ABBR_START_RE.match(text)
    )


class FootnoteNormalizer:
    """
    Normalise le contenu des notes de bas de page par une suite de regles locales,
    attribuables et idempotentes (voir docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md) :
    - purh.note.espace_initiale : supprime l'espace de tete parasite
    - purh.note.majuscule_initiale : majuscule de tete, seulement si le debut de note
      n'est pas une URL/DOI, un nom a particule ou une abreviation latine
    - purh.note.abreviation_latine : Ibid./Idem/Id./op. cit./art. cit./loc. cit. en
      minuscule hors debut de note
    - purh.note.espace_op_cit / purh.note.espace_sans_lieu_date : espace fine insecable
    - purh.note.ponctuation_finale : point final si absent, hors URL/vers/liste/guillemet
      fermant (sinon diagnostic informatif, jamais de correction aveugle)
    Surlignage : vert (COLOR_FOOTNOTE)
    """

    module_name = "footnote_normalizer"
    color = COLOR_FOOTNOTE

    def apply(self, document: Document) -> tuple[Document, list[Transformation]]:
        doc = copy.deepcopy(document)
        transformations: list[Transformation] = []
        for note in doc.notes:
            tr = self._process_note(note)
            transformations.extend(tr)
        if transformations:
            doc.history.append(
                f"{self.module_name}: {len(transformations)} correction(s) de notes."
            )
        return doc, transformations

    def analyze_note_call_placement(self, document: Document) -> list[Diagnostic]:
        """
        R-AN-002 (A3): diagnostic seulement sur placement suspect des appels de note.
        Ne modifie ni texte, ni spans, ni notes.
        """
        diagnostics: list[Diagnostic] = []
        for block in document.blocks:
            if not block.inlines:
                continue
            diagnostics.extend(self._diagnose_block_note_calls(block.block_id, block.inlines))
        return diagnostics

    def analyze_note_normalization_exclusions(self, document: Document) -> list[Diagnostic]:
        """
        Diagnostics informatifs pour les cas ou la normalisation des notes s'abstient
        volontairement (majuscule initiale non forcee, point final non ajoute) plutot
        que d'appliquer une regle aveugle sur du contenu ambigu.
        """
        diagnostics: list[Diagnostic] = []
        for note in document.notes:
            text = "".join(s.text for s in note.inlines) if note.inlines else note.text
            if not text:
                continue
            diagnostics.extend(self._diagnose_note_text_exclusions(note.note_id, text))
        return diagnostics

    def _diagnose_note_text_exclusions(self, note_id: str, text: str) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        stripped_leading = _LEADING_SPACE_RE.sub("", text)
        if (
            stripped_leading
            and stripped_leading[0].islower()
            and _majuscule_initiale_excluded(stripped_leading)
        ):
            diagnostics.append(Diagnostic(
                diagnostic_id=make_id("diag"),
                module=self.module_name,
                severity="info",
                category="note_lowercase_start_not_normalized",
                message=(
                    "Note commençant par une minuscule non normalisée automatiquement "
                    "(URL, nom à particule ou abréviation latine)."
                ),
                target_ref=note_id,
                evidence=Evidence(excerpt=stripped_leading[:40]),
                rule_id="R-AN-004",
            ))
        stripped_trailing = text.rstrip()
        if (
            stripped_trailing
            and stripped_trailing[-1] not in _CLOSING_PUNCT_OR_QUOTE
            and (_looks_like_url_or_verse(stripped_trailing) or _LIST_ITEM_RE.match(text))
        ):
            diagnostics.append(Diagnostic(
                diagnostic_id=make_id("diag"),
                module=self.module_name,
                severity="info",
                category="note_missing_final_punctuation_ambiguous",
                message=(
                    "Note sans ponctuation finale : ajout automatique abstenu "
                    "(URL, vers ou liste)."
                ),
                target_ref=note_id,
                evidence=Evidence(excerpt=stripped_trailing[-40:]),
                rule_id="R-AN-005",
            ))
        return diagnostics

    # -- Traitement d'une note ------------------------------------------------

    def _process_note(self, note: Note) -> list[Transformation]:
        if note.inlines:
            return self._process_note_inlines(note)
        return self._process_note_flat(note)

    def _diagnose_block_note_calls(
        self,
        block_id: str,
        inlines: list[InlineSpan],
    ) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for index, span in enumerate(inlines):
            if span.kind != "note_call":
                continue
            previous_char = self._previous_visible_char(inlines, index)
            if previous_char is None:
                continue
            if previous_char in _SPACING_CHARS:
                diagnostics.append(
                    Diagnostic(
                        diagnostic_id=make_id("diag"),
                        module=self.module_name,
                        severity="warning",
                        category="footnote_call_spacing",
                        message="Appel de note précédé d'une espace parasite.",
                        target_ref=block_id,
                        evidence=Evidence(
                            excerpt=self._context_excerpt(inlines, index),
                        ),
                        rule_id="R-AN-003",
                        attributes={
                            "note_ref": span.note_ref,
                            "note_call_index": index,
                            "preceding_char": previous_char,
                            "preceding_space_kind": self._space_kind(previous_char),
                        },
                    )
                )
            if previous_char in _FINAL_PUNCT or previous_char in _CLOSING_QUOTES:
                diagnostics.append(
                    Diagnostic(
                        diagnostic_id=make_id("diag"),
                        module=self.module_name,
                        severity="warning",
                        category="footnote_call_placement",
                        message=(
                            "Appel de note probablement mal placé : il devrait précéder la "
                            "ponctuation finale ou le guillemet fermant."
                        ),
                        target_ref=block_id,
                        evidence=Evidence(
                            excerpt=self._context_excerpt(inlines, index),
                        ),
                        rule_id="R-AN-002",
                        attributes={
                            "note_ref": span.note_ref,
                            "note_call_index": index,
                            "preceding_char": previous_char,
                        },
                    )
                )
        return diagnostics

    @staticmethod
    def _space_kind(char: str) -> str:
        if char == " ":
            return "space"
        if char == " ":
            return "nbsp"
        if char == " ":
            return "nnbsp"
        return "unknown"

    @staticmethod
    def _previous_visible_char(inlines: list[InlineSpan], index: int) -> str | None:
        for i in range(index - 1, -1, -1):
            text = inlines[i].text
            if text:
                return text[-1]
        return None

    @staticmethod
    def _context_excerpt(inlines: list[InlineSpan], index: int, window: int = 1) -> str:
        start = max(0, index - window)
        end = min(len(inlines), index + window + 1)
        return "".join(span.text for span in inlines[start:end])

    def _process_note_inlines(self, note: Note) -> list[Transformation]:
        original = "".join(s.text for s in note.inlines)
        corrected, occurrences = self._apply_rules_with_occurrences(original)
        if corrected == original:
            return []
        regions = _find_changed_regions(original, corrected)
        new_inlines = self._apply_highlights(note.inlines, original, corrected, regions)
        note.inlines[:] = new_inlines
        note.text = corrected
        return self._build_transformations(note.note_id, occurrences)

    def _process_note_flat(self, note: Note) -> list[Transformation]:
        original = note.text
        corrected, occurrences = self._apply_rules_with_occurrences(original)
        if corrected == original:
            return []
        note.text = corrected
        note.attributes["highlight_color"] = self.color
        return self._build_transformations(note.note_id, occurrences)

    def _build_transformations(
        self, note_id: str, occurrences: list[RuleOccurrence],
    ) -> list[Transformation]:
        return [
            Transformation(
                transformation_id=make_id("tr"),
                module=self.module_name,
                target_ref=note_id,
                operation="footnote_normalize",
                before=occ.before,
                after=occ.after,
                rule_id=occ.rule_id,
                applied=True,
                attributes={
                    "offset_start": occ.offset_start,
                    "offset_end": occ.offset_end,
                    "coordinate_space": occ.coordinate_space,
                    "color": self.color,
                },
            )
            for occ in occurrences
        ]

    # -- Regles ----------------------------------------------------------------

    @staticmethod
    def _apply_rules_with_occurrences(text: str) -> tuple[str, list[RuleOccurrence]]:
        occurrences: list[RuleOccurrence] = []

        text, occ = FootnoteNormalizer._rule_espace_initiale(text)
        occurrences.extend(occ)

        text, occ = FootnoteNormalizer._rule_majuscule_initiale(text)
        occurrences.extend(occ)

        text, occ = _apply_rule_with_occurrences(_ABBR_MIDNOTE_RULE, text)
        occurrences.extend(occ)

        text, occ = _apply_rule_with_occurrences(_OP_CIT_RULE, text)
        occurrences.extend(occ)

        text, occ = _apply_rule_with_occurrences(_SL_SD_RULE, text)
        occurrences.extend(occ)

        text, occ = FootnoteNormalizer._rule_ponctuation_finale(text)
        occurrences.extend(occ)

        return text, occurrences

    @staticmethod
    def _rule_espace_initiale(text: str) -> tuple[str, list[RuleOccurrence]]:
        match = _LEADING_SPACE_RE.match(text)
        if not match:
            return text, []
        leading = match.group(0)
        occ = RuleOccurrence(
            rule_id="purh.note.espace_initiale",
            before=leading,
            after="",
            offset_start=0,
            offset_end=len(leading),
        )
        return text[len(leading):], [occ]

    @staticmethod
    def _rule_majuscule_initiale(text: str) -> tuple[str, list[RuleOccurrence]]:
        if not text or not text[0].islower():
            return text, []
        if _majuscule_initiale_excluded(text):
            return text, []
        occ = RuleOccurrence(
            rule_id="purh.note.majuscule_initiale",
            before=text[0],
            after=text[0].upper(),
            offset_start=0,
            offset_end=1,
        )
        return text[0].upper() + text[1:], [occ]

    @staticmethod
    def _rule_ponctuation_finale(text: str) -> tuple[str, list[RuleOccurrence]]:
        stripped = text.rstrip()
        if not stripped:
            return text, []
        if stripped[-1] in _CLOSING_PUNCT_OR_QUOTE:
            return text, []
        if _looks_like_url_or_verse(stripped) or _LIST_ITEM_RE.match(text):
            return text, []
        trailing_ws = text[len(stripped):]
        occ = RuleOccurrence(
            rule_id="purh.note.ponctuation_finale",
            before=trailing_ws,
            after=".",
            offset_start=len(stripped),
            offset_end=len(text),
        )
        return stripped + ".", [occ]

    # -- Reconstruction inlines avec surlignage --------------------------------

    @staticmethod
    def _apply_highlights(
        inlines: list[InlineSpan],
        original_text: str,
        corrected_text: str,
        regions: list[tuple[int, int]],
    ) -> list[InlineSpan]:
        """Marque les spans modifies en vert (COLOR_FOOTNOTE)."""
        if not inlines:
            return inlines

        # Carte char original -> span source
        span_for_char: list[InlineSpan] = []
        for span in inlines:
            for _ in span.text:
                span_for_char.append(span)

        import difflib
        sm = difflib.SequenceMatcher(None, original_text, corrected_text, autojunk=False)
        source_per_char: list[InlineSpan | None] = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for i in range(i2 - i1):
                    src = span_for_char[i1 + i] if (i1 + i) < len(span_for_char) else None
                    source_per_char.append(src)
            elif tag in ("replace", "insert"):
                ref = span_for_char[i1] if i1 < len(span_for_char) else (
                    span_for_char[-1] if span_for_char else None
                )
                for _ in range(j2 - j1):
                    source_per_char.append(ref)

        highlighted_pos: set[int] = set()
        for s, e in regions:
            highlighted_pos.update(range(s, e))

        result: list[InlineSpan] = []
        buf: list[str] = []
        cur_source: InlineSpan | None = None
        cur_hl: bool = False

        def flush() -> None:
            if not buf or cur_source is None:
                return
            new_span = copy.deepcopy(cur_source)
            new_span.text = "".join(buf)
            attrs = {k: v for k, v in new_span.attributes.items() if k != "highlight_color"}
            if cur_hl:
                attrs["highlight_color"] = COLOR_FOOTNOTE
            new_span.attributes = attrs
            result.append(new_span)

        for pos, (ch, src) in enumerate(zip(corrected_text, source_per_char)):
            hl = pos in highlighted_pos
            if src is not cur_source or hl != cur_hl:
                flush()
                buf, cur_source, cur_hl = [ch], src, hl
            else:
                buf.append(ch)
        flush()

        return result if result else inlines
