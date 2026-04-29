from __future__ import annotations

import re
from copy import deepcopy

from purh_editorial.model import Document, Transformation
from purh_editorial.utils import make_id

# ── Table de correspondance block_type → nom de style Métopes ────────────────
# Noms tels qu'ils apparaissent dans python-docx (pas les styleId XML).
# Source : Commons-publishing-Metopes.dotm

METOPES_STYLES: dict[str, str] = {
    "paragraph":             "Normal",
    "paragraph_lead":        "TEI_paragraph_consecutive",  # 1er § après titre (sans alinéa)
    "heading_1":             "Heading 1",
    "heading_2":             "Heading 2",
    "heading_3":             "Heading 3",
    "heading_4":             "Heading 4",
    "heading_5":             "Heading 5",
    "quote_block":           "TEI_quote",
    "quote_nested":          "TEI_quote_nested",
    "bibliography_item":     "TEI_bibl_reference",
    "bibliography_start":    "TEI_bibl_start",
    "epigraph":              "TEI_epigraph",
    "acknowledgment":        "TEI_acknowledgment",
    "abstract":              "TEI_abstract",
    "keywords":              "TEI_keywords",
    "author":                "TEI_aut:",
    "appendix_start":        "TEI_appendix_start",
    "footnote":              "footnote text",
    "dedication":            "TEI_dedication",
    "verse":                 "TEI_verse",
    "figure_title":          "TEI_figure_title",
    "figure_caption":        "TEI_figure_caption",
    "code":                  "TEI_code",
}

# Styles Word source → level d'intertitres dans Métopes
_HEADING_STYLE_IDS: dict[str, int] = {
    "Titre1": 1, "Titre2": 2, "Titre3": 3,
    "Titre4": 4, "Titre5": 5, "Titre6": 6,
    "heading1": 1, "heading2": 2, "heading3": 3,
    "Heading1": 1, "Heading2": 2, "Heading3": 3,
    "heading 1": 1, "heading 2": 2, "heading 3": 3,
}

# Regex pour détecter les sections spéciales dans les titres
_RE_ABSTRACT = re.compile(r"^(résumé|abstract|summary)", re.IGNORECASE)
_RE_KEYWORDS = re.compile(r"^(mots[- ]clés?|keywords?)", re.IGNORECASE)
_RE_ACKNOWLEDGMENT = re.compile(r"^(remerciements?|acknowledgments?)", re.IGNORECASE)


def _heading_level(block) -> int:
    """Détermine le niveau d'intertitre depuis le style source ou les attributs."""
    # Niveau explicitement stocké par le StructureService (formatage auteur)
    explicit = block.attributes.get("heading_level")
    if explicit and isinstance(explicit, int) and 1 <= explicit <= 6:
        return explicit
    style_id   = block.attributes.get("style_id", "")
    style_name = block.attributes.get("style_name", "")
    for key in (style_id, style_name):
        if key in _HEADING_STYLE_IDS:
            return _HEADING_STYLE_IDS[key]
    m = re.search(r"(\d)", style_id or style_name)
    if m:
        lvl = int(m.group(1))
        if 1 <= lvl <= 6:
            return lvl
    return 1


class MetopesMapper:
    """Attribue un style Métopes (nom python-docx) à chaque bloc du document."""

    module_name = "metopes_mapper"

    def apply(self, document: Document) -> tuple[Document, list[Transformation]]:
        doc = deepcopy(document)
        transformations: list[Transformation] = []
        prev_was_heading = False

        for block in doc.blocks:
            style = self._resolve_style(block, prev_was_heading)
            block.attributes["metopes_style"] = style
            transformations.append(Transformation(
                transformation_id=make_id("tr"),
                module=self.module_name,
                target_ref=block.block_id,
                operation="assign_metopes_style",
                before=block.attributes.get("style_id", "Normal"),
                after=style,
                rule_id="metopes.style_mapping",
                applied=True,
            ))
            prev_was_heading = (block.block_type == "heading")

        if transformations:
            doc.history.append(
                f"{self.module_name}: {len(transformations)} style(s) Métopes assigné(s)."
            )
        return doc, transformations

    def _resolve_style(self, block, prev_was_heading: bool) -> str:
        btype = block.block_type
        text  = block.text.strip()

        if btype == "heading":
            level = _heading_level(block)
            return METOPES_STYLES.get(f"heading_{level}", "Heading 1")

        if btype == "quote_block":
            return METOPES_STYLES["quote_block"]

        if btype == "bibliography_item":
            return METOPES_STYLES["bibliography_item"]

        if btype == "author":
            return METOPES_STYLES["author"]

        if btype == "epigraph":
            return METOPES_STYLES["epigraph"]

        if btype == "paragraph":
            if _RE_ABSTRACT.match(text):
                return METOPES_STYLES["abstract"]
            if _RE_KEYWORDS.match(text):
                return METOPES_STYLES["keywords"]
            if _RE_ACKNOWLEDGMENT.match(text):
                return METOPES_STYLES["acknowledgment"]
            if prev_was_heading:
                return METOPES_STYLES["paragraph_lead"]
            return METOPES_STYLES["paragraph"]

        return METOPES_STYLES.get(btype, "Normal")
