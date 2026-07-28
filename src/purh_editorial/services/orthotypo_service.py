from __future__ import annotations

import copy
import difflib
import re
from dataclasses import dataclass
from typing import Callable

from purh_editorial.model import Diagnostic, Document, Evidence, InlineSpan, Transformation
from purh_editorial.utils import make_id
from purh_editorial.utils.protection import is_protected_block, is_protected_note

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
_NUMERO_STYLE_RE = re.compile(r"\b[Nn](o)" + NNBSP + r"(?=\d)")
_INCISE_DASH_RE = re.compile(r"(?<=\w) [-–—] (?=\w)")
_QUOTE_PUNCT_SUSPECT_RE = re.compile(r"«([^»]+)»\.")
_QUOTE_STRONG_PUNCT = {".", ";", ":", "?", "!", "…"}
_TECHNICAL_TEXT_RE = re.compile(r"<[^>]+>|[\w:-]+\s*=\s*\"[^\"]*\"")
_CENTURY_CONTEXT_RE = re.compile(r"^\s*(si[eè]cles?|s\.)\b", re.IGNORECASE | re.UNICODE)
# Connecteur d'énumération entre deux siècles ("XVIe, XVIIe et XVIIIe siècles",
# "du XVIe au XVIIIe siècle", "XVIe-XVIIIe siècles") : permet de reconnaître le
# contexte "siècle(s)" même quand il ne suit pas immédiatement CE numéro-ci.
_CENTURY_ENUM_CONNECTOR_RE = re.compile(
    r"^(?:[,\-]\s*|\s*(?:et|ou|au|à)\s+)([IVXLCDMivxlcdm]{1,8}[eè][rm]?[eé]?)\b",
    re.IGNORECASE | re.UNICODE,
)


def _has_century_context(lookahead: str) -> bool:
    """True si `lookahead` (texte suivant un numéro de siècle) mène à "siècle(s)"/
    "s.", en traversant d'éventuels autres numéros d'une même énumération."""
    remaining = lookahead
    for _ in range(6):  # borne défensive, une énumération réaliste est courte
        if _CENTURY_CONTEXT_RE.match(remaining):
            return True
        m = _CENTURY_ENUM_CONNECTOR_RE.match(remaining)
        if not m:
            return False
        remaining = remaining[m.end():]
    return False
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

# ── Localisation par occurrence (Phase 6 bis) ─────────────────────────────────

@dataclass
class RuleOccurrence:
    """Une correction individuellement localisée, avant regroupement en Transformation.

    Convention d'offsets (voir docs/PHASE6BIS_ASSAINISSEMENT.md) : `offset_start` et
    `offset_end` sont relatifs au texte tel qu'il existe juste avant l'application de
    CETTE règle précise — pas au texte original du bloc, qui peut déjà avoir été modifié
    par des règles précédentes dans la chaîne. `coordinate_space="pre_rule_text"` rend
    ce référentiel explicite plutôt qu'implicite.
    """

    rule_id: str
    before: str
    after: str
    offset_start: int
    offset_end: int
    coordinate_space: str = "pre_rule_text"


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
    #     Contexte "siècle(s)"/"s." obligatoire : sans lui, le motif capture aussi des
    #     mots ordinaires (ex. "vie" -> roman "vi" valide) ou des ordinaux de prénom
    #     déjà corrects (ex. "Jules Ier"), qu'il ne faut pas toucher (R-SO-001-BIS).
    def _fix_siecle(m: re.Match) -> str:
        roman = m.group(1)
        if roman.lower() not in _VALID_CENTURIES:
            return m.group(0)   # pas un siècle connu, pas de remplacement
        lookahead = m.string[m.end():m.end() + 64]
        if not _has_century_context(lookahead):
            return m.group(0)   # pas de contexte "siècle" proche, pas de remplacement
        if roman.lower() == "i":
            return "Ier"        # le Ier siècle, jamais "Ie siècle"
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

    # 15. Numéro : normalise n°/N°/nº/Nº/no/No devant un chiffre vers la forme canonique
    #     "n"/"N" + o + espace fine insécable + chiffre. Le "o" est ensuite mis en
    #     exposant par _style_numero_in_inlines (même mécanisme que le stylage des
    #     siècles) — remplace le symbole degré "n°" par la forme demandée par le guide
    #     PURH (CONSIGNES_AUTEURS_PURH_2025.pdf, p. 12 : "numéro -> no, lettre o en
    #     exposant"). Voir docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md.
    rules.append(TypoRule(
        rule_id="purh.numero",
        pattern=re.compile(r"\b([Nn])[°ºoO]\.?[ \t  ]*(?=\d)"),
        replacement=lambda m: m.group(1) + "o" + NNBSP,
        description="Numéro -> \"o\" en exposant + espace fine insécable (n° 5 -> no 5)",
    ))

    # 15b. Redoublement fautif d'une abréviation pour marquer le pluriel : le français
    #      ne redouble jamais une abréviation (pp./vv./ll./§§), contrairement à l'anglais.
    #      Source : CONSIGNES_AUTEURS_PURH_2025.pdf, p. 11 — "Ne jamais redoubler tout ou
    #      partie d'une abréviation française pour indiquer le pluriel."
    #      (pp. 53-84 -> p. 53-84 ; vv. 122-128 -> v. 122-128 ; ll. 5 et 12 -> l. 5 et 12 ;
    #      §§ 5-9 -> § 5-9). Seule la création de nouveaux redoublements était jusqu'ici
    #      empêchée (purh.pagination.espace n'espace que la forme déjà présente) ; cette
    #      règle normalise les redoublements déjà présents dans le manuscrit.
    rules.append(TypoRule(
        rule_id="purh.abreviations.redoublement",
        pattern=re.compile(r"\b(pp|vv|ll)\.|§§"),
        replacement=lambda m: (m.group(1)[0] + "." if m.group(1) else "§"),
        description="Abréviation redoublée -> forme simple (pp./vv./ll./§§)",
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

    # 17. Tiret d'incise : abstention (auto=False), diagnostic seul.
    #     La normalisation automatique vers le cadratin a été retirée : elle allait à
    #     l'encontre de la pratique éditoriale observée (le corpus de caractérisation
    #     privé montre les éditrices convertissant systématiquement vers le
    #     demi-cadratin, l'inverse de ce que cette règle produisait), et le guide PURH
    #     ne tranche pas explicitement la convention attendue. Une règle connue comme
    #     probablement contraire à la pratique ne doit pas rester une correction
    #     automatique silencieuse. Voir docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md et
    #     analyze_incise_dash ci-dessous (diagnostic R-TI-001).
    rules.append(TypoRule(
        rule_id="purh.tiret.incise",
        pattern=re.compile(r"(?<=\w) – (?=\w)|(?<=\w) - (?=[A-Za-zÀ-ÿA-Z])"),
        replacement=" " + EMDASH + " ",
        description="Tiret d'incise — abstention, voir analyze_incise_dash",
        auto=False,
    ))

    # Only rules explicitly supported by a PURH source may alter the document.
    # All other rules remain detectable review material until their source is
    # documented; this is deliberately stricter than general French practice.
    purh_validated_rule_ids = {
        "purh.siecles",
        "purh.ordinaux",
        "purh.abreviations.etc",
        "purh.pagination.espace",
        "purh.numero",
        "purh.abreviations.redoublement",
    }
    for rule in rules:
        rule.auto = rule.auto and rule.rule_id in purh_validated_rule_ids
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


def _apply_rule_with_occurrences(rule: "TypoRule", text: str) -> tuple[str, list[RuleOccurrence]]:
    """
    Applique une règle et retourne, en plus du texte corrigé, une RuleOccurrence par
    occurrence individuellement modifiée — condition nécessaire à la traçabilité par
    occurrence (Phase 6/6 bis) : une même règle peut corriger plusieurs endroits d'un
    même bloc, chacun doit rester distinguable et localisable dans le journal.
    Reconstruit le texte occurrence par occurrence plutôt que via pattern.sub() pour
    pouvoir capturer chaque fragment et sa position ; produit exactement le même texte
    que `TypoRule.apply`. `offset_start`/`offset_end` sont les positions du fragment
    *avant* dans `text` tel que reçu en paramètre (donc "pre_rule_text" pour cette
    règle précise, pas pour le bloc d'origine).
    """
    occurrences: list[RuleOccurrence] = []
    parts: list[str] = []
    last_end = 0
    for match in rule.pattern.finditer(text):
        before_fragment = match.group(0)
        after_fragment = (
            rule.replacement(match) if callable(rule.replacement) else match.expand(rule.replacement)
        )
        parts.append(text[last_end:match.start()])
        parts.append(after_fragment)
        last_end = match.end()
        if after_fragment != before_fragment:
            occurrences.append(RuleOccurrence(
                rule_id=rule.rule_id,
                before=before_fragment,
                after=after_fragment,
                offset_start=match.start(),
                offset_end=match.end(),
            ))
    parts.append(text[last_end:])
    return "".join(parts), occurrences


# ── Service principal ─────────────────────────────────────────────────────────

class OrthotypoService:
    """Applique les règles typographiques PURH avec surlignage localisé."""

    module_name = "orthotypo"
    color = COLOR_ORTHOTYPO

    def apply(self, document: Document) -> tuple[Document, list[Transformation]]:
        doc = copy.deepcopy(document)
        transformations: list[Transformation] = []
        for block in doc.blocks:
            if is_protected_block(block):
                continue
            transformations.extend(self._process_block(block))
        protected_target_refs = {
            block.block_id for block in doc.blocks if is_protected_block(block)
        }
        for note in doc.notes:
            if is_protected_note(note, protected_target_refs=protected_target_refs):
                continue
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
            if is_protected_block(block):
                continue
            text = "".join(span.text for span in block.inlines) if block.inlines else block.text
            if not text or _TECHNICAL_TEXT_RE.search(text):
                continue
            diagnostics.extend(self._diagnose_quote_punctuation(block.block_id, text))
        return diagnostics

    def analyze_unvalidated_rules(self, document: Document) -> list[Diagnostic]:
        """Report non-PURH rules as review items without changing the text."""
        diagnostics: list[Diagnostic] = []
        for block in document.blocks:
            if is_protected_block(block):
                continue
            text = "".join(span.text for span in block.inlines) if block.inlines else block.text
            for rule in TYPO_RULES:
                if rule.auto or not rule.pattern.search(text):
                    continue
                diagnostics.append(
                    Diagnostic(
                        diagnostic_id=make_id("diag"),
                        module=self.module_name,
                        severity="info",
                        category="orthotypo_unvalidated_rule",
                        message="Règle non validée par une source PURH : correction non appliquée.",
                        target_ref=block.block_id,
                        evidence=Evidence(excerpt=rule.pattern.search(text).group(0)),
                        rule_id=rule.rule_id,
                        status="open",
                        attributes={"status": "pending_human_review", "description": rule.description},
                    )
                )
        return diagnostics

    def analyze_incise_dash(self, document: Document) -> list[Diagnostic]:
        """
        R-TI-001 (diagnostic seul, A3) : signale un tiret d'incise (-, – ou —) sans le
        normaliser automatiquement. purh.tiret.incise (auto=False) ne corrige plus ce
        motif : la convention attendue (cadratin ou demi-cadratin) n'est pas tranchée
        avec certitude — voir docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md.
        """
        diagnostics: list[Diagnostic] = []
        for block in document.blocks:
            if is_protected_block(block):
                continue
            text = "".join(span.text for span in block.inlines) if block.inlines else block.text
            if not text:
                continue
            for match in _INCISE_DASH_RE.finditer(text):
                diagnostics.append(
                    Diagnostic(
                        diagnostic_id=make_id("diag"),
                        module=self.module_name,
                        severity="info",
                        category="incise_dash",
                        message=(
                            "Convention du tiret d’incise à vérifier : aucune "
                            "normalisation automatique n’a été appliquée."
                        ),
                        target_ref=block.block_id,
                        evidence=Evidence(excerpt=match.group(0)),
                        rule_id="R-TI-001",
                    )
                )
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

    def _apply_special_stylings(
        self, inlines: list[InlineSpan]
    ) -> tuple[list[InlineSpan], bool, list[RuleOccurrence], list[RuleOccurrence]]:
        """Enchaîne le stylage des siècles (petites capitales + exposant) et celui du
        "o" de "no" (exposant) produit par purh.numero, dans cet ordre. Retourne les
        occurrences de chacun séparément pour conserver un rule_id distinct par
        transformation (Phase 6/6 bis)."""
        styled, century_changed, century_occurrences = self._style_centuries_in_inlines(inlines)
        styled, numero_changed, numero_occurrences = self._style_numero_in_inlines(styled)
        return styled, century_changed or numero_changed, century_occurrences, numero_occurrences

    def _build_transformations(
        self,
        target_ref: str,
        rule_occurrences: list[RuleOccurrence],
        century_occurrences: list[RuleOccurrence],
        numero_occurrences: list[RuleOccurrence] | None = None,
        highlight_regions: list[tuple[int, int]] | None = None,
    ) -> list[Transformation]:
        """Une Transformation distincte par occurrence corrigée, taguée par son propre
        rule_id et localisée par offsets (Phase 6/6 bis) — plutôt qu'une seule
        transformation "purh.orthotypo.batch" agrégeant tout un bloc, qui empêchait de
        savoir quelle règle avait fait quoi à quel endroit. `sequence` numérote l'ordre
        réel d'application (règles de texte, puis stylage des siècles, puis du numéro)."""
        all_occurrences = [
            *rule_occurrences,
            *century_occurrences,
            *(numero_occurrences or []),
        ]
        extra_attrs = {id(occ): {} for occ in all_occurrences}
        for occ in century_occurrences:
            extra_attrs[id(occ)]["century_styling"] = True
        for occ in numero_occurrences or []:
            extra_attrs[id(occ)]["numero_styling"] = True
        for occ in all_occurrences:
            # Une occurrence dont le texte est inchangé (before == after) n'est
            # pas une correction textuelle mais un changement de style (petites
            # capitales, exposant...) : le marquer évite de laisser croire à une
            # transformation textuelle vide (Partie F1).
            if occ.before == occ.after:
                extra_attrs[id(occ)]["style_only"] = True

        return [
            Transformation(
                transformation_id=make_id("tr"),
                module=self.module_name,
                target_ref=target_ref,
                operation="orthotypo",
                before=occ.before,
                after=occ.after,
                rule_id=occ.rule_id,
                applied=True,
                attributes={
                    "highlight_regions": highlight_regions or [],
                    "color": self.color,
                    "offset_start": occ.offset_start,
                    "offset_end": occ.offset_end,
                    "sequence": sequence,
                    "coordinate_space": occ.coordinate_space,
                    **extra_attrs[id(occ)],
                },
            )
            for sequence, occ in enumerate(all_occurrences)
        ]

    def _process_inlines_owner(self, inlines, *, target_ref, update_text) -> list[Transformation]:
        original = "".join(s.text for s in inlines)
        corrected, rule_occurrences = self._apply_all_rules_tracked(original)
        if corrected == original:
            styled_inlines, any_styled, century_occurrences, numero_occurrences = (
                self._apply_special_stylings(inlines)
            )
            if any_styled:
                inlines[:] = styled_inlines
                styled_text = "".join(span.text for span in styled_inlines)
                update_text(styled_text)
                regions = _find_changed_regions(original, styled_text)
                return self._build_transformations(
                    target_ref, [], century_occurrences, numero_occurrences, regions
                )
            return []

        # Signature caractère par caractère (texte + petites capitales + exposant) de
        # l'état de départ, capturée avant toute reconstruction : purh.siecles peut
        # mettre un siècle en majuscules puis le stylage des siècles le repasse en
        # minuscules stylées juste après, ce qui fait apparaître un "changement" pour
        # _style_centuries_in_inlines (son entrée intermédiaire diffère) sans que le
        # bloc ait réellement changé de bout en bout. Comparer les signatures de départ
        # et d'arrivée est le seul moyen fiable de détecter ce cas et d'éviter de
        # journaliser une fausse transformation (before == after) à chaque nouveau
        # passage sur un document déjà traité.
        before_signature = self._char_style_signature(inlines)

        new_inlines = self._rebuild_inlines(
            inlines,
            original,
            corrected,
            _find_changed_regions(original, corrected),
        )
        new_inlines, _any_styled, century_occurrences, numero_occurrences = (
            self._apply_special_stylings(new_inlines)
        )
        final_text = "".join(span.text for span in new_inlines)
        after_signature = self._char_style_signature(new_inlines)
        inlines[:] = new_inlines
        update_text(final_text)
        if after_signature == before_signature:
            return []
        regions = _find_changed_regions(original, final_text)
        return self._build_transformations(
            target_ref, rule_occurrences, century_occurrences, numero_occurrences, regions
        )

    def _process_flat(
        self,
        text,
        *,
        target_ref,
        update_text,
        update_color,
        update_inlines,
    ) -> list[Transformation]:
        corrected, rule_occurrences = self._apply_all_rules_tracked(text)
        inlines = [InlineSpan(text=corrected)]
        styled_inlines, any_styled, century_occurrences, numero_occurrences = (
            self._apply_special_stylings(inlines)
        )
        final_text = "".join(span.text for span in styled_inlines)

        if final_text == text:
            return []
        update_text(final_text)
        update_color()
        if any_styled:
            update_inlines(styled_inlines)
        return self._build_transformations(
            target_ref, rule_occurrences, century_occurrences, numero_occurrences
        )

    @staticmethod
    def _is_century_context(full_text: str, match_end: int) -> bool:
        lookahead = full_text[match_end: match_end + 64]
        return _has_century_context(lookahead)

    @staticmethod
    def _char_style_signature(inlines: list[InlineSpan]) -> list[tuple[str, bool, bool]]:
        """Empreinte caractère par caractère (texte, petites capitales, exposant)."""
        return [
            (ch, span.style.small_caps, span.style.superscript)
            for span in inlines
            for ch in span.text
        ]

    def _style_centuries_in_inlines(
        self, inlines: list[InlineSpan]
    ) -> tuple[list[InlineSpan], bool, list[RuleOccurrence]]:
        """Retourne aussi, pour la traçabilité par occurrence (Phase 6/6 bis), une
        RuleOccurrence localisée par siècle individuellement stylé — un même bloc peut
        en contenir plusieurs (ex. "xviie au xixe siècles")."""
        if not inlines:
            return inlines, False, []

        full_text = "".join(span.text for span in inlines)
        century_matches: list[re.Match] = []
        for match in _CENTURY_TOKEN_RE.finditer(full_text):
            roman = match.group(1)
            if roman.lower() not in _VALID_CENTURIES:
                continue
            if not self._is_century_context(full_text, match.end()):
                continue
            century_matches.append(match)

        if not century_matches:
            return inlines, False, []

        roman_positions: dict[int, int] = {}
        exponent_positions: dict[int, int] = {}
        for match_index, match in enumerate(century_matches):
            roman_start, roman_end = match.start(1), match.end(1)
            for pos in range(roman_start, roman_end):
                roman_positions[pos] = match_index
            exponent_positions[roman_end] = match_index

        changed_by_match = [False] * len(century_matches)
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
                    match_index = roman_positions[absolute_index]
                    lowered = ch.lower()
                    if lowered != ch or not new_span.style.small_caps:
                        changed_by_match[match_index] = True
                    new_span.text = lowered
                    new_span.style.small_caps = True
                elif absolute_index in exponent_positions:
                    match_index = exponent_positions[absolute_index]
                    if ch != "e" or not new_span.style.superscript:
                        changed_by_match[match_index] = True
                    new_span.text = "e"
                    new_span.style.superscript = True
                result.append(new_span)
                absolute_index += 1

        if not any(changed_by_match):
            return inlines, False, []
        occurrences = [
            RuleOccurrence(
                rule_id="R-SO-001",
                before=match.group(0),
                after=match.group(1).lower() + "e",
                offset_start=match.start(),
                offset_end=match.end(),
            )
            for match, changed in zip(century_matches, changed_by_match)
            if changed
        ]
        return self._merge_adjacent_spans(result), True, occurrences

    def _style_numero_in_inlines(
        self, inlines: list[InlineSpan]
    ) -> tuple[list[InlineSpan], bool, list[RuleOccurrence]]:
        """Met en exposant le "o" de "no"/"No" produit par la règle purh.numero, quand
        il est immédiatement suivi de l'espace fine insécable puis d'un chiffre (forme
        canonique produite par cette règle). Même mécanisme que le stylage des siècles."""
        if not inlines:
            return inlines, False, []

        full_text = "".join(span.text for span in inlines)
        numero_matches = list(_NUMERO_STYLE_RE.finditer(full_text))
        if not numero_matches:
            return inlines, False, []

        exponent_positions: dict[int, int] = {}
        for match_index, match in enumerate(numero_matches):
            exponent_positions[match.start(1)] = match_index

        changed_by_match = [False] * len(numero_matches)
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
                if absolute_index in exponent_positions:
                    match_index = exponent_positions[absolute_index]
                    if not new_span.style.superscript:
                        changed_by_match[match_index] = True
                    new_span.style.superscript = True
                result.append(new_span)
                absolute_index += 1

        if not any(changed_by_match):
            return inlines, False, []
        occurrences = [
            RuleOccurrence(
                rule_id="R-NO-001",
                before=match.group(0),
                after=match.group(0),
                offset_start=match.start(),
                offset_end=match.end(),
            )
            for match, changed in zip(numero_matches, changed_by_match)
            if changed
        ]
        return self._merge_adjacent_spans(result), True, occurrences

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

    @staticmethod
    def _apply_all_rules_tracked(text: str) -> tuple[str, list[RuleOccurrence]]:
        """Comme `_apply_all_rules`, mais retourne aussi une RuleOccurrence localisée
        pour chaque occurrence corrigée, toutes règles confondues, dans l'ordre
        d'application."""
        occurrences: list[RuleOccurrence] = []
        for rule in TYPO_RULES:
            if not rule.auto:
                continue
            text, rule_occurrences = _apply_rule_with_occurrences(rule, text)
            occurrences.extend(rule_occurrences)
        return text, occurrences

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
