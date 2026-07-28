from __future__ import annotations

from copy import deepcopy

from purh_editorial.model import Document, Transformation
from purh_editorial.model.semantics import is_canonical_lineated_block, read_block_semantics
from purh_editorial.utils import make_id


METOPES_STYLES: dict[str, str] = {
    "paragraph": "Normal",
    "paragraph_lead": "TEI_paragraph_consecutive",
    "heading_1": "Heading 1", "heading_2": "Heading 2", "heading_3": "Heading 3",
    "heading_4": "Heading 4", "heading_5": "Heading 5",
    "quote_block": "TEI_quote", "bibliography_item": "TEI_bibl_reference",
    "acknowledgment": "TEI_acknowledgment", "abstract": "TEI_abstract",
    "keywords": "TEI_keywords", "author": "TEI_aut:", "epigraph": "TEI_epigraph",
    "verse": "TEI_verse",
}


class MetopesMapper:
    """Optional, projective mapping from canonical pivot semantics to Metopes styles."""

    module_name = "metopes_mapper"

    def apply(self, document: Document) -> tuple[Document, list[Transformation]]:
        doc = deepcopy(document)
        transformations: list[Transformation] = []
        previous_role: str | None = None
        for block in doc.blocks:
            style = self._resolve_style(block, previous_role)
            if style is None:
                previous_role = read_block_semantics(block).role
                continue
            block.attributes["metopes_style"] = style
            transformations.append(Transformation(
                transformation_id=make_id("tr"), module=self.module_name,
                target_ref=block.block_id, operation="assign_metopes_style",
                before=block.attributes.get("style_id", "Normal"), after=style,
                rule_id="metopes.style_mapping", applied=True,
            ))
            previous_role = read_block_semantics(block).role
        if transformations:
            doc.history.append(f"{self.module_name}: {len(transformations)} style(s) assigned.")
        return doc, transformations

    def _resolve_style(self, block, previous_role: str | None) -> str | None:
        semantic = read_block_semantics(block)
        role = semantic.role
        if role in {"abstract", "keywords", "acknowledgment", "author", "epigraph", "bibliography_item"}:
            return METOPES_STYLES[role]
        if role == "heading":
            semantic_data = block.attributes.get("semantic", {})
            level = semantic_data.get("heading_level", 1) if isinstance(semantic_data, dict) else 1
            return METOPES_STYLES.get(f"heading_{level}", "Heading 1")
        if role in {"quote", "lineated_block"}:
            return METOPES_STYLES["verse"] if is_canonical_lineated_block(block) else METOPES_STYLES["quote_block"]
        if role == "paragraph":
            return METOPES_STYLES["paragraph_lead"] if previous_role in {"quote", "lineated_block"} else METOPES_STYLES["paragraph"]
        return None
