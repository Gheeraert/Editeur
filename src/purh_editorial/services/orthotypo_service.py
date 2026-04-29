from __future__ import annotations

import copy
import difflib
import re
from dataclasses import dataclass
from typing import Callable

from purh_editorial.model import Document, InlineSpan, Transformation
from purh_editorial.utils import make_id

# ── Couleurs de surlignage ────────────────────────────────────────────────────
COLOR_ORTHOTYPO = "orthotypo"   # jaune
COLOR_FOOTNOTE  = "footnote"    # vert
COLOR_BIBLIO    = "biblio"      # turquoise
COLOR_AI        = "ai"          # rose

# ── Caractères typographiques ─────────────────────────────────────────────────
NNBSP  = " "   # espace fine insécable
NBSP   = " "   # espace insécable normale
APOS   = "’"   # apostrophe typographique  '
ELLIP  = "…"   # points de suspension  …
ENDASH = "–"   # tiret demi-cadratin  –
EMDASH = "—"   # tiret cadratin  —
LQUOT  = "«"   # guillemet ouvrant  «
RQUOT  = "»"   # guillemet fermant  »

# Guillemets anglais (curly) et droits
_OPEN_QUOTES  = '"“'   # " "
_CLOSE_QUOTES = '"”'   # " "

# ── Siècles reconnus (whitelist) ──────────────────────────────────────────────
_VALID_CENTURIES: frozenset[str] = frozenset({
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix",
    "xx", "xxi", "xxii", "xxiii",
})

# ── Règle typographique ───────────────────────────────────────────────────────

@dataclass
class TypoRule:
    rule_id: str
    pattern: re.Pattern
    replacement: str | Callable[[re.Match], str]
    description: str
    auto: bool = True

    def apply(self, text: str) -> str:
        if callable(self.replacement):
            return self.pattern.sub(self.replacement, text)
        return self.pattern.sub(self.replacement, text)


def _build_rules() -> list[TypoRule]:
    rules: list[TypoRule] = []

    # 1. Apostrophe typographique — ' ASCII entre lettres → U+2019
    rules.append(TypoRule(
        rule_id="purh.apostrophe",
        pattern=re.compile(r"([A-Za-zÀ-ɏ])'", re.UNICODE),
        replacement=r"\1" + APOS,
        description="Apostrophe typographique",
    ))

    # 2. Points de suspension — ... → …
    rules.append(TypoRule(
        rule_id="purh.points_suspension",
        pattern=re.compile(r"\.{3}"),
        replacement=ELLIP,
        description="Points de suspension … ",
    ))

    # 3. Guillemets français depuis guillemets droits/anglais — "..." → « ... »
    _gq_open  = "[" + _OPEN_QUOTES  + "]"
    _gq_close = "[" + _CLOSE_QUOTES + "]"
    rules.append(TypoRule(
        rule_id="purh.guillemets.droits",
        pattern=re.compile(_gq_open + r"(.*?)" + _gq_close, re.DOTALL),
        replacement=lambda m: LQUOT + NNBSP + m.group(1).strip() + NNBSP + RQUOT,
        description="Guillemets droits → guillemets français",
    ))

    # 4. Espace fine insécable après «
    rules.append(TypoRule(
        rule_id="purh.guillemets.espace_apres_ouvrant",
        pattern=re.compile(LQUOT + r"(?!" + NNBSP + r")[ \t]?"),
        replacement=LQUOT + NNBSP,
        description="Espace fine insécable après «",
    ))

    # 5. Espace fine insécable avant »
    rules.append(TypoRule(
        rule_id="purh.guillemets.espace_avant_fermant",
        pattern=re.compile(r"(?<!" + NNBSP + r")[ \t]?" + RQUOT),
        replacement=NNBSP + RQUOT,
        description="Espace fine insécable avant »",
    ))

    # 6. Espace fine insécable avant ponctuation forte : ; ? !
    #    [ \t  ]* = tout type d'espace (ou rien)
    _any_space = r"[ \t  ]*"
    rules.append(TypoRule(
        rule_id="purh.espaces.avant_ponct_forte",
        pattern=re.compile(_any_space + r"([:;?!])"),
        replacement=NNBSP + r"\1",
        description="Espace fine insécable avant : ; ? !",
    ))

    # 7. Suppression d'espace avant virgule ou point (hors décimaux)
    rules.append(TypoRule(
        rule_id="purh.espaces.avant_ponct_faible",
        pattern=re.compile(r"[ \t  ]+([,\.])(?!\d)"),
        replacement=r"\1",
        description="Suppression espace avant , et .",
    ))

    # 8. Double espace → espace simple
    rules.append(TypoRule(
        rule_id="purh.espaces.double",
        pattern=re.compile(r"[ \t]{2,}"),
        replacement=" ",
        description="Double espace → espace simple",
    ))

    # 9. Espace insécable après titres de civilité
    rules.append(TypoRule(
        rule_id="purh.civilite",
        pattern=re.compile(
            r"\b(M\.|Mme[s]?|Dr?|Pr?|Prof\.) (?=[A-ZÀ-ÖØ-Þ])",
            re.UNICODE,
        ),
        replacement=r"\1" + NBSP,
        description="Espace insécable après titre de civilité",
    ))

    # 10. Siècles — XIIème, xiiième, XIIe → XIIe
    #     Whitelist des nombres romains valides pour éviter les faux positifs
    def _fix_siecle(m: re.Match) -> str:
        roman = m.group(1)
        if roman.lower() not in _VALID_CENTURIES:
            return m.group(0)   # pas un siècle connu, pas de remplacement
        return roman.upper() + "e"

    rules.append(TypoRule(
        rule_id="purh.siecles",
        pattern=re.compile(
            r"\b([IVXLCDMivxlcdm]{1,8})[eè][rm]?[eé]?\b",
            re.UNICODE,
        ),
        replacement=_fix_siecle,
        description="Normalisation des siècles (XIXe)",
    ))

    # 11. Double tiret → tiret demi-cadratin
    rules.append(TypoRule(
        rule_id="purh.tiret.double",
        pattern=re.compile(r"--"),
        replacement=ENDASH,
        description="Double tiret → –",
    ))

    # 12. etc... ou etc… → etc.
    rules.append(TypoRule(
        rule_id="purh.abreviations.etc",
        pattern=re.compile(r"etc[" + ELLIP + r"\.]{2,}"),
        replacement="etc.",
        description="etc… → etc.",
    ))

    # 13. Espace fine insécable après abréviations de pagination
    #     p. 3, pp. 3-5, vol. II, t. I, f. 12, n° 5, fig. 2, art. cit., chap. 4
    #     On cible uniquement quand ce qui suit est un chiffre ou numéral romain
    _abbr = r"\b(pp?|vol|t|f|fol|fig|chap|cat|pl|ms|Ms|n°|N°|col)\."
    rules.append(TypoRule(
        rule_id="purh.pagination.espace",
        pattern=re.compile(_abbr + r"\s+(?=[\dIVXLCivxlc])"),
        replacement=r"\1." + NNBSP,
        description="Espace fine insécable après abréviations de pagination",
    ))

    # 14. Espace fine insécable dans les numéros (n° 3, N° 12)
    rules.append(TypoRule(
        rule_id="purh.numero",
        pattern=re.compile(r"\b([Nn]°)\s+(?=\d)"),
        replacement=r"\1" + NNBSP,
        description="Espace fine insécable après n°",
    ))

    # 15. Séparateur de milliers : espace ordinaire entre groupes de chiffres
    #     1 000 → 1 000, 1 500 000 → 1 500 000
    #     (appliqué 2 fois pour couvrir les millions)
    _thousands_re = re.compile(r"(\d{1,3}) (\d{3})(?!\d)")
    def _fix_thousands(text: str) -> str:
        # Deux passages pour couvrir 1 000 000
        prev = None
        while prev != text:
            prev = text
            text = _thousands_re.sub(r"\1" + NNBSP + r"\2", text)
        return text
    # Encapsulé comme callable
    rules.append(TypoRule(
        rule_id="purh.nombres.milliers",
        pattern=re.compile(r"(\d{1,3}) (\d{3})(?!\d)"),
        replacement=r"\1" + NNBSP + r"\2",
        description="Espace fine insécable dans les nombres (milliers)",
    ))

    # 16. Tiret cadratin dans les incises : " - " entre mots → " — "
    #     (seulement quand entouré d'espaces et pas en début de ligne)
    rules.append(TypoRule(
        rule_id="purh.tiret.incise",
        pattern=re.compile(r"(?<=\w) – (?=\w)|(?<=\w) - (?=[A-Za-zÀ-ÿA-Z])"),
        replacement=" " + EMDASH + " ",
        description="Tiret cadratin pour les incises",
    ))

    return rules


TYPO_RULES: list[TypoRule] = _build_rules()


# ── Utilitaires de diff ───────────────────────────────────────────────────────

def _find_changed_regions(before: str, after: str) -> list[tuple[int, int]]:
    """Régions modifiées dans `after` (positions de caractères)."""
    sm = difflib.SequenceMatcher(None, before, after, autojunk=False)
    regions: list[tuple[int, int]] = []
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "insert") and j1 < j2:
            regions.append((j1, j2))
    # Fusion des régions adjacentes (< 3 chars d'écart)
    merged: list[list[int]] = []
    for s, e in regions:
        if merged and s - merged[-1][1] <= 3:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


# ── Service principal ─────────────────────────────────────────────────────────

class OrthotypoService:
    """Applique les règles typographiques PURH avec surlignage localisé."""

    module_name = "orthotypo"
    color = COLOR_ORTHOTYPO

    def apply(self, document: Document) -> tuple[Document, list[Transformation]]:
        doc = copy.deepcopy(document)
        transformations: list[Transformation] = []
        for block in doc.blocks:
            transformations.extend(self._process_block(block))
        for note in doc.notes:
            transformations.extend(self._process_note(note))
        if transformations:
            doc.history.append(
                f"{self.module_name}: {len(transformations)} correction(s)."
            )
        return doc, transformations

    # ── Bloc ─────────────────────────────────────────────────────────────────

    def _process_block(self, block) -> list[Transformation]:
        if block.inlines:
            return self._process_inlines_owner(
                block.inlines,
                target_ref=block.block_id,
                update_text=lambda t: setattr(block, "text", t),
            )
        return self._process_flat(
            block.text,
            target_ref=block.block_id,
            update_text=lambda t: setattr(block, "text", t),
            update_color=lambda: block.attributes.update({"highlight_color": self.color}),
        )

    def _process_note(self, note) -> list[Transformation]:
        if note.inlines:
            return self._process_inlines_owner(
                note.inlines,
                target_ref=note.note_id,
                update_text=lambda t: setattr(note, "text", t),
            )
        return self._process_flat(
            note.text,
            target_ref=note.note_id,
            update_text=lambda t: setattr(note, "text", t),
            update_color=lambda: None,
        )

    def _process_inlines_owner(self, inlines, *, target_ref, update_text) -> list[Transformation]:
        original = "".join(s.text for s in inlines)
        corrected = self._apply_all_rules(original)
        if corrected == original:
            return []
        regions = _find_changed_regions(original, corrected)
        new_inlines = self._rebuild_inlines(inlines, original, corrected, regions)
        inlines[:] = new_inlines
        update_text(corrected)
        return [Transformation(
            transformation_id=make_id("tr"),
            module=self.module_name,
            target_ref=target_ref,
            operation="orthotypo",
            before=original,
            after=corrected,
            rule_id="purh.orthotypo.batch",
            applied=True,
            attributes={"highlight_regions": regions, "color": self.color},
        )]

    def _process_flat(self, text, *, target_ref, update_text, update_color) -> list[Transformation]:
        corrected = self._apply_all_rules(text)
        if corrected == text:
            return []
        update_text(corrected)
        update_color()
        return [Transformation(
            transformation_id=make_id("tr"),
            module=self.module_name,
            target_ref=target_ref,
            operation="orthotypo",
            before=text,
            after=corrected,
            rule_id="purh.orthotypo.batch",
            applied=True,
            attributes={"color": self.color},
        )]

    # ── Application des règles ────────────────────────────────────────────────

    @staticmethod
    def _apply_all_rules(text: str) -> str:
        for rule in TYPO_RULES:
            if rule.auto:
                text = rule.apply(text)
        return text

    # ── Reconstruction des inlines avec surlignage ────────────────────────────

    @staticmethod
    def _rebuild_inlines(
        original_inlines: list[InlineSpan],
        original_text: str,
        corrected_text: str,
        regions: list[tuple[int, int]],
    ) -> list[InlineSpan]:
        """
        Redistribue le texte corrigé sur les spans en préservant les styles inline.
        Les caractères modifiés héritent du surlignage orthotypo.
        """
        if not original_inlines:
            return original_inlines

        # Carte original_pos → span source
        span_for_char: list[InlineSpan] = []
        for span in original_inlines:
            for _ in span.text:
                span_for_char.append(span)

        # Aligner original ↔ corrigé au niveau caractère
        sm = difflib.SequenceMatcher(None, original_text, corrected_text, autojunk=False)
        source_per_corrected_char: list[InlineSpan | None] = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for i in range(i2 - i1):
                    src = span_for_char[i1 + i] if (i1 + i) < len(span_for_char) else None
                    source_per_corrected_char.append(src)
            elif tag in ("replace", "insert"):
                ref = span_for_char[i1] if i1 < len(span_for_char) else (
                    span_for_char[-1] if span_for_char else None
                )
                for _ in range(j2 - j1):
                    source_per_corrected_char.append(ref)

        # Ensemble des positions surlignées dans le texte corrigé
        highlighted_positions: set[int] = set()
        for s, e in regions:
            highlighted_positions.update(range(s, e))

        # Grouper les caractères consécutifs partageant même span source + même état de surlignage
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
                attrs["highlight_color"] = COLOR_ORTHOTYPO
            new_span.attributes = attrs
            result.append(new_span)

        for pos, (ch, src) in enumerate(zip(corrected_text, source_per_corrected_char)):
            hl = pos in highlighted_positions
            if src is not cur_source or hl != cur_hl:
                flush()
                buf, cur_source, cur_hl = [ch], src, hl
            else:
                buf.append(ch)
        flush()

        return result if result else original_inlines
