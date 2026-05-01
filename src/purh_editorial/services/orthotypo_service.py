from __future__ import annotations

import copy
import difflib
import re
from dataclasses import dataclass
from typing import Callable

from purh_editorial.model import Diagnostic, Document, Evidence, InlineSpan, Transformation
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

_CENTURY_TOKEN_RE = re.compile(r"\b([IVXLCDMivxlcdm]{1,8})e\b", re.UNICODE | re.IGNORECASE)
_QUOTE_PUNCT_SUSPECT_RE = re.compile(r"«([^»]+)»\.")
_QUOTE_STRONG_PUNCT = {".", ";", ":", "?", "!", "…"}
_TECHNICAL_TEXT_RE = re.compile(r"<[^>]+>|[\w:-]+\s*=\s*\"[^\"]*\"")
_CENTURY_CONTEXT_RE = re.compile(r"^\s*(si[eè]cles?|s\.)\b", re.IGNORECASE | re.UNICODE)
_OE_LIGATURE_FORMS: dict[str, str] = {
    "boeuf": "bœuf",
    "boeufs": "bœufs",
    "oeuf": "œuf",
    "oeufs": "œufs",
    "soeur": "sœur",
    "soeurs": "sœurs",
    "coeur": "cœur",
    "coeurs": "cœurs",
    "oeuvre": "œuvre",
    "oeuvres": "œuvres",
    "oeil": "œil",
    "voeu": "vœu",
    "voeux": "vœux",
    "noeud": "nœud",
    "noeuds": "nœuds",
    "moeurs": "mœurs",
}

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

    # 3. Guillemets droits ou anglais typographiques (prudence) :
    #    - texte courant: "..." -> « ... »
    #    - second niveau dans « ... »: "..." -> “...”
    #    - contextes techniques: inchangés (print("x"), attributs XML/HTML, etc.)
    _technical_attr_re = re.compile(r"\b[\w:-]+\s*=\s*$")

    def _is_technical_quote_context(text: str, quote_start: int, quote_end: int) -> bool:
        before = text[max(0, quote_start - 48):quote_start]
        after = text[quote_end:min(len(text), quote_end + 48)]
        quoted_content = text[quote_start + 1:quote_end - 1]

        before_stripped = before.rstrip()
        if _technical_attr_re.search(before_stripped):
            return True
        if before_stripped.endswith("("):
            return True
        if "<" in before_stripped and ">" not in before_stripped:
            return True
        if before_stripped.endswith(",") and "(" in before_stripped:
            return True
        if "\\" in quoted_content:
            return True
        if re.match(r"^\s*[)\],;:]", after):
            return True
        return False

    def _is_inside_french_quotes(text: str, quote_start: int, quote_end: int) -> bool:
        last_open = text.rfind(LQUOT, 0, quote_start)
        if last_open < 0:
            return False
        last_close_before = text.rfind(RQUOT, 0, quote_start)
        if last_close_before > last_open:
            return False
        next_close = text.find(RQUOT, quote_end)
        return next_close >= 0

    def _replace_straight_quotes(m: re.Match) -> str:
        full = m.group(0)
        content = m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)
        text = m.string
        quote_start = m.start(0)
        quote_end = m.end(0)

        if _is_technical_quote_context(text, quote_start, quote_end):
            return full

        if _is_inside_french_quotes(text, quote_start, quote_end):
            return "“" + content.strip() + "”"

        return LQUOT + NNBSP + content.strip() + NNBSP + RQUOT

    rules.append(TypoRule(
        rule_id="purh.guillemets.droits",
        pattern=re.compile(r'(["“])([^"\n”]+)(["”])'),
        replacement=_replace_straight_quotes,
        description="Guillemets droits -> guillemets français ou second niveau",
    ))

    # 3b. Ligatures françaises courantes en oe (table fermée)
    _oe_pattern = re.compile(
        r"\b(" + "|".join(sorted(_OE_LIGATURE_FORMS.keys(), key=len, reverse=True)) + r")\b",
        re.IGNORECASE,
    )

    def _replace_oe_ligature(m: re.Match) -> str:
        original = m.group(1)
        replacement = _OE_LIGATURE_FORMS.get(original.lower())
        if replacement is None:
            return original
        if original.isupper():
            return replacement.upper()
        if original[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement

    rules.append(TypoRule(
        rule_id="R-ORTHO-LIGATURE-OE-001",
        pattern=_oe_pattern,
        replacement=_replace_oe_ligature,
        description="Ligatures en œ sur formes lexicales courantes",
    ))

    # 4. Espace fine insécable après « — absorbe tout type d'espace (NNBSP, NBSP, ordinaire)
    #    Pattern sans lookahead pour être idempotent et gérer les NBSP auteur (U+00A0)
    rules.append(TypoRule(
        rule_id="purh.guillemets.espace_apres_ouvrant",
        pattern=re.compile(LQUOT + r"[   \t]*"),
        replacement=LQUOT + NNBSP,
        description="Espace fine insécable après «",
    ))

    # 5. Espace fine insécable avant » — absorbe tout type d'espace
    rules.append(TypoRule(
        rule_id="purh.guillemets.espace_avant_fermant",
        pattern=re.compile(r"[   \t]*" + RQUOT),
        replacement=NNBSP + RQUOT,
        description="Espace fine insécable avant »",
    ))

    # 6. Espace fine insécable avant ponctuation forte : ; ?!
    #    [ \t  ]* = tout type d'espace (ou rien)
    _any_space = r"[ \t  ]*"
    def _is_technical_token(text: str, punct_pos: int) -> bool:
        token_start = punct_pos
        while token_start > 0 and not text[token_start - 1].isspace():
            token_start -= 1
        token_end = punct_pos + 1
        while token_end < len(text) and not text[token_end].isspace():
            token_end += 1
        token = text[token_start:token_end]
        lowered = token.lower()
        if "http://" in lowered or "https://" in lowered or "ftp://" in lowered:
            return True
        if "/" in token or "\\" in token:
            return True
        return False

    def _replace_strong_punct(m: re.Match) -> str:
        text = m.string
        punct = m.group(1)
        punct_pos = m.start(1)

        # Garde-fous R-SP-001 : ne pas corriger les tokens techniques.
        if _is_technical_token(text, punct_pos):
            return m.group(0)
        if punct == ":":
            prev_char = text[punct_pos - 1] if punct_pos > 0 else ""
            next_char = text[punct_pos + 1] if punct_pos + 1 < len(text) else ""
            # Heures, ratios, références techniques numériques : 10:30, 16:9, 1234:5
            if prev_char.isdigit() and next_char.isdigit():
                return m.group(0)

        return NNBSP + punct

    rules.append(TypoRule(
        rule_id="purh.espaces.avant_ponct_forte",
        pattern=re.compile(_any_space + r"([:;?!])"),
        replacement=_replace_strong_punct,
        description="Espace fine insécable avant : ; ?!",
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

    # 11. Ordinaux simples — 1ère/1ere → 1re, nème/neme → ne
    def _fix_ordinal(m: re.Match) -> str:
        number = m.group(1)
        suffix = m.group(2).lower()
        if suffix in {"ère", "ere"} and number == "1":
            return "1re"
        if suffix in {"ème", "eme"}:
            return f"{number}e"
        return m.group(0)

    rules.append(TypoRule(
        rule_id="purh.ordinaux",
        pattern=re.compile(r"\b(\d+)(ère|ere|ème|eme)\b", re.UNICODE),
        replacement=_fix_ordinal,
        description="Normalisation prudente des ordinaux simples (1re, 5e)",
    ))

    # 12. Double tiret → tiret demi-cadratin
    rules.append(TypoRule(
        rule_id="purh.tiret.double",
        pattern=re.compile(r"--"),
        replacement=ENDASH,
        description="Double tiret → –",
    ))

    # 13. etc... ou etc… → etc.
    #     Après normalisation des points de suspension, on rencontre surtout "etc…"
    #     (éventuellement suivi d'un ou plusieurs points parasites).
    rules.append(TypoRule(
        rule_id="purh.abreviations.etc",
        pattern=re.compile(r"etc(?:" + ELLIP + r"\.*|\.{2,})"),
        replacement="etc.",
        description="etc… → etc.",
    ))

    # 14. Espace fine insécable après abréviations de pagination
    #     p. 3, pp. 3-5, vol. II, t. I, f. 12, n° 5, fig. 2, art. cit., chap. 4
    #     On cible uniquement quand ce qui suit est un chiffre ou numéral romain
    _abbr = r"\b(pp?|vol|t|f|fol|fig|chap|cat|pl|ms|Ms|n°|N°|col)\."
    rules.append(TypoRule(
        rule_id="purh.pagination.espace",
        pattern=re.compile(_abbr + r"\s+(?=[\dIVXLCivxlc])"),
        replacement=r"\1." + NNBSP,
        description="Espace fine insécable après abréviations de pagination",
    ))

    # 15. Espace fine insécable dans les numéros (n° 3, N° 12)
    rules.append(TypoRule(
        rule_id="purh.numero",
        pattern=re.compile(r"\b([Nn]°)\s+(?=\d)"),
        replacement=r"\1" + NNBSP,
        description="Espace fine insécable après n°",
    ))

    # 16. Séparateur de milliers : espace ordinaire entre groupes de chiffres
    #     1 000 → 1 000, 1 500 000 → 1 500 000
    _thousands_re = re.compile(r"(\d{1,3}) (\d{3})(?!\d)")
    def _fix_thousands(text: str) -> str:
        # Plusieurs passages pour couvrir tous les groupes (milliers, millions, etc.)
        prev = None
        while prev != text:
            prev = text
            text = _thousands_re.sub(r"\1" + NNBSP + r"\2", text)
        return text

    rules.append(TypoRule(
        rule_id="purh.nombres.milliers",
        pattern=re.compile(r"\b\d{1,3}(?: \d{3})+\b"),
        replacement=lambda m: _fix_thousands(m.group(0)),
        description="Espace fine insécable dans les nombres (milliers)",
    ))

    # 17. Tiret cadratin dans les incises : " - " entre mots → " — "
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

    def analyze_quote_punctuation(self, document: Document) -> list[Diagnostic]:
        """
        R-GQ-004 (A3): diagnostic prudent sur ponctuation autour des guillemets.
        Ne modifie pas le texte.
        """
        diagnostics: list[Diagnostic] = []
        for block in document.blocks:
            if block.block_type == "quote_block":
                continue
            text = "".join(span.text for span in block.inlines) if block.inlines else block.text
            if not text or _TECHNICAL_TEXT_RE.search(text):
                continue
            diagnostics.extend(self._diagnose_quote_punctuation(block.block_id, text))
        return diagnostics

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
            update_inlines=lambda spans: setattr(block, "inlines", spans),
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
            update_inlines=lambda spans: setattr(note, "inlines", spans),
        )

    def _diagnose_quote_punctuation(self, block_id: str, text: str) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for match in _QUOTE_PUNCT_SUSPECT_RE.finditer(text):
            inside = match.group(1).strip()
            if not inside:
                continue
            if any(q in inside for q in ("“", "”", "\"", "«", "»")):
                continue

            suspicious = False
            if inside[-1] in _QUOTE_STRONG_PUNCT:
                suspicious = True
            before_open = text[:match.start()].rstrip()
            if before_open.endswith(":"):
                suspicious = True

            if not suspicious:
                continue

            diagnostics.append(
                Diagnostic(
                    diagnostic_id=make_id("diag"),
                    module=self.module_name,
                    severity="warning",
                    category="quote_punctuation",
                    message=(
                        "Vérifier la ponctuation autour du guillemet fermant selon le type de citation."
                    ),
                    target_ref=block_id,
                    evidence=Evidence(excerpt=match.group(0)),
                    rule_id="R-GQ-004",
                    attributes={
                        "pattern": "closing_quote_followed_by_dot",
                        "match_text": match.group(0),
                    },
                )
            )
        return diagnostics

    def _process_inlines_owner(self, inlines, *, target_ref, update_text) -> list[Transformation]:
        original = "".join(s.text for s in inlines)
        corrected = self._apply_all_rules(original)
        if corrected == original:
            styled_inlines, century_styled = self._style_centuries_in_inlines(inlines)
            if century_styled:
                inlines[:] = styled_inlines
                styled_text = "".join(span.text for span in styled_inlines)
                update_text(styled_text)
                regions = _find_changed_regions(original, styled_text)
                return [Transformation(
                    transformation_id=make_id("tr"),
                    module=self.module_name,
                    target_ref=target_ref,
                    operation="orthotypo",
                    before=original,
                    after=styled_text,
                    rule_id="purh.orthotypo.batch",
                    applied=True,
                    attributes={
                        "highlight_regions": regions,
                        "color": self.color,
                        "century_styling": True,
                        "rule_id": "R-SO-001",
                    },
                )]
            return []

        new_inlines = self._rebuild_inlines(
            inlines,
            original,
            corrected,
            _find_changed_regions(original, corrected),
        )
        new_inlines, century_styled = self._style_centuries_in_inlines(new_inlines)
        final_text = "".join(span.text for span in new_inlines)
        regions = _find_changed_regions(original, final_text)
        inlines[:] = new_inlines
        update_text(final_text)
        return [Transformation(
            transformation_id=make_id("tr"),
            module=self.module_name,
            target_ref=target_ref,
            operation="orthotypo",
            before=original,
            after=final_text,
            rule_id="purh.orthotypo.batch",
            applied=True,
            attributes={
                "highlight_regions": regions,
                "color": self.color,
                "century_styling": century_styled,
                "rule_id": "R-SO-001" if century_styled else None,
            },
        )]

    def _process_flat(
        self,
        text,
        *,
        target_ref,
        update_text,
        update_color,
        update_inlines,
    ) -> list[Transformation]:
        corrected = self._apply_all_rules(text)
        inlines = [InlineSpan(text=corrected)]
        styled_inlines, century_styled = self._style_centuries_in_inlines(inlines)
        final_text = "".join(span.text for span in styled_inlines)

        if final_text == text:
            return []
        update_text(final_text)
        update_color()
        if century_styled:
            update_inlines(styled_inlines)
        return [Transformation(
            transformation_id=make_id("tr"),
            module=self.module_name,
            target_ref=target_ref,
            operation="orthotypo",
            before=text,
            after=final_text,
            rule_id="purh.orthotypo.batch",
            applied=True,
            attributes={
                "color": self.color,
                "century_styling": century_styled,
                "rule_id": "R-SO-001" if century_styled else None,
            },
        )]

    @staticmethod
    def _is_century_context(full_text: str, match_end: int) -> bool:
        lookahead = full_text[match_end: match_end + 32]
        return bool(_CENTURY_CONTEXT_RE.match(lookahead))

    def _style_centuries_in_inlines(self, inlines: list[InlineSpan]) -> tuple[list[InlineSpan], bool]:
        if not inlines:
            return inlines, False

        full_text = "".join(span.text for span in inlines)
        roman_positions: set[int] = set()
        exponent_positions: set[int] = set()
        for match in _CENTURY_TOKEN_RE.finditer(full_text):
            roman = match.group(1)
            if roman.lower() not in _VALID_CENTURIES:
                continue
            if not self._is_century_context(full_text, match.end()):
                continue
            roman_start = match.start(1)
            roman_end = match.end(1)
            roman_positions.update(range(roman_start, roman_end))
            exponent_positions.add(roman_end)

        if not roman_positions and not exponent_positions:
            return inlines, False

        changed = False
        result: list[InlineSpan] = []
        absolute_index = 0
        for span in inlines:
            if span.kind != "text" or not span.text:
                result.append(copy.deepcopy(span))
                absolute_index += len(span.text)
                continue

            for ch in span.text:
                new_span = copy.deepcopy(span)
                new_span.text = ch
                if absolute_index in roman_positions:
                    lowered = ch.lower()
                    if lowered != ch or not new_span.style.small_caps:
                        changed = True
                    new_span.text = lowered
                    new_span.style.small_caps = True
                elif absolute_index in exponent_positions:
                    if ch != "e" or not new_span.style.superscript:
                        changed = True
                    new_span.text = "e"
                    new_span.style.superscript = True
                result.append(new_span)
                absolute_index += 1

        if not changed:
            return inlines, False
        return self._merge_adjacent_spans(result), True

    @staticmethod
    def _merge_adjacent_spans(inlines: list[InlineSpan]) -> list[InlineSpan]:
        if not inlines:
            return inlines

        merged: list[InlineSpan] = []
        for span in inlines:
            if not span.text:
                continue
            if not merged:
                merged.append(span)
                continue
            last = merged[-1]
            if (
                last.kind == span.kind
                and last.note_ref == span.note_ref
                and last.style == span.style
                and last.attributes == span.attributes
            ):
                last.text += span.text
            else:
                merged.append(span)
        return merged

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
