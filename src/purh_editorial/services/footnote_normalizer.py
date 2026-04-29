from __future__ import annotations

import copy
import re
from dataclasses import dataclass

from purh_editorial.model import Document, InlineSpan, Note, Transformation
from purh_editorial.services.orthotypo_service import (
    COLOR_FOOTNOTE, NNBSP, APOS, _find_changed_regions,
)
from purh_editorial.utils import make_id

# Abréviations latines devant toujours apparaître en italique dans les notes
_LATIN_ABBR_RE = re.compile(
    r"\b(ibid|id|op\.?\s*cit|art\.?\s*cit|loc\.?\s*cit|cf|supra|infra|idem)\b\.?",
    re.IGNORECASE,
)

# URLs et fins de ligne qui acceptent légitimement l'absence de point final
_URL_RE = re.compile(r"https?://\S+$")
_VERSE_END_RE = re.compile(r"[»›’]\s*$")

# Tirets en liste dans les notes → pas de correction
_LIST_ITEM_RE = re.compile(r"^\s*[-–—•]\s")


def _looks_like_url_or_verse(text: str) -> bool:
    s = text.strip()
    return bool(_URL_RE.search(s)) or bool(_VERSE_END_RE.search(s))


class FootnoteNormalizer:
    """
    Normalise le contenu des notes de bas de page :
    - Supprime l'espace de tête parasite (après le marqueur de note)
    - Ajoute un point final si absent (hors URL, vers, etc.)
    - Normalise les abréviations de référence (Ibid. → ibid.)
    - Corrige op. cit. / art. cit. (espace insécable)
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

    # ── Traitement d'une note ─────────────────────────────────────────────────

    def _process_note(self, note: Note) -> list[Transformation]:
        if note.inlines:
            return self._process_note_inlines(note)
        return self._process_note_flat(note)

    def _process_note_inlines(self, note: Note) -> list[Transformation]:
        original = "".join(s.text for s in note.inlines)
        corrected = self._apply_rules(original)
        if corrected == original:
            return []
        regions = _find_changed_regions(original, corrected)
        new_inlines = self._apply_highlights(note.inlines, original, corrected, regions)
        note.inlines[:] = new_inlines
        note.text = corrected
        return [Transformation(
            transformation_id=make_id("tr"),
            module=self.module_name,
            target_ref=note.note_id,
            operation="footnote_normalize",
            before=original,
            after=corrected,
            rule_id="purh.note.batch",
            applied=True,
            attributes={"highlight_regions": regions, "color": self.color},
        )]

    def _process_note_flat(self, note: Note) -> list[Transformation]:
        original = note.text
        corrected = self._apply_rules(original)
        if corrected == original:
            return []
        note.text = corrected
        note.attributes["highlight_color"] = self.color
        return [Transformation(
            transformation_id=make_id("tr"),
            module=self.module_name,
            target_ref=note.note_id,
            operation="footnote_normalize",
            before=original,
            after=corrected,
            rule_id="purh.note.batch",
            applied=True,
            attributes={"color": self.color},
        )]

    # ── Règles ────────────────────────────────────────────────────────────────

    @staticmethod
    def _apply_rules(text: str) -> str:
        # R1. Supprimer l'espace de tête parasite (issu du marqueur de note Word)
        text = text.lstrip(" \t")

        # R2. Majuscule en début de note
        if text and text[0].islower():
            text = text[0].upper() + text[1:]

        # R3. Normalisation Ibid. / Idem / Id. → ibid. / idem / id. (minuscule)
        #     Sauf en début de note (déjà traité en R2)
        def _lower_latin(m: re.Match) -> str:
            w = m.group(0)
            # En début de note après R2, la première lettre est en majuscule → on la laisse
            return w  # on normalise uniquement si ce n'est pas le premier mot
        text = re.sub(
            r"(?<!^)\b(Ibid|Id|Idem|Op\.\s*cit|Art\.\s*cit|Loc\.\s*cit)\b\.?",
            lambda m: m.group(0).lower(),
            text,
            flags=re.IGNORECASE,
        )

        # R4. Espace fine insécable dans op. cit. / art. cit. / loc. cit.
        text = re.sub(
            r"\b(op|art|loc)\.\s+(cit)\.",
            r"\1." + NNBSP + r"\2.",
            text,
            flags=re.IGNORECASE,
        )

        # R5. Point final si absent (hors URL, vers, guillemet fermant de citation)
        stripped = text.rstrip()
        if stripped and not stripped[-1] in ".!?…»" and not _looks_like_url_or_verse(stripped):
            text = stripped + "."

        return text

    # ── Reconstruction inlines avec surlignage ────────────────────────────────

    @staticmethod
    def _apply_highlights(
        inlines: list[InlineSpan],
        original_text: str,
        corrected_text: str,
        regions: list[tuple[int, int]],
    ) -> list[InlineSpan]:
        """Marque les spans modifiés en vert (COLOR_FOOTNOTE)."""
        if not inlines:
            return inlines

        # Carte char original → span source
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
