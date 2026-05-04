from __future__ import annotations

from purh_editorial.model import BlockSemantics, Document, Transformation
from purh_editorial.model.semantics import (
    extract_verse_lines,
    read_block_semantics,
    semantics_to_dict,
    write_block_semantics,
)
from purh_editorial.utils import make_id


class PivotCanonicalizer:
    module_name = "pivot_canonicalizer"
    rule_id = "pivot.semantic.canonicalize"

    def apply(self, document: Document) -> list[Transformation]:
        transformations: list[Transformation] = []
        for block in document.blocks:
            current = read_block_semantics(block)
            canonical = self._canonical_semantics_for_block(block, current)
            before_payload = semantics_to_dict(current)
            after_payload = semantics_to_dict(canonical)
            if before_payload == after_payload:
                continue

            write_block_semantics(block, canonical)
            transformations.append(
                Transformation(
                    transformation_id=make_id("tr"),
                    module=self.module_name,
                    target_ref=block.block_id,
                    operation="canonicalize_semantics",
                    before=str(before_payload),
                    after=str(after_payload),
                    rule_id=self.rule_id,
                    applied=True,
                    attributes={
                        "before_semantic": before_payload,
                        "after_semantic": after_payload,
                    },
                )
            )
        return transformations

    @staticmethod
    def _canonical_semantics_for_block(
        block,
        current: BlockSemantics,
    ) -> BlockSemantics:
        role = current.role
        layout_kind = current.layout_kind
        quote_kind = current.quote_kind
        lineation = current.lineation
        lines = list(current.lines)
        genre_hint = current.genre_hint
        genre_confidence = current.genre_confidence
        genre_source = current.genre_source
        poetry_group_id = current.poetry_group_id
        poetry_line_index = current.poetry_line_index

        if block.block_type == "heading":
            role = "heading"
            layout_kind = None
            quote_kind = None
            lineation = None
            lines = []
            genre_hint = None
            genre_confidence = None
            genre_source = None
            poetry_group_id = None
            poetry_line_index = None
        elif block.block_type == "paragraph":
            role = "paragraph"
            layout_kind = None
            quote_kind = None
            lineation = None
            lines = []
            genre_hint = None
            genre_confidence = None
            genre_source = None
            poetry_group_id = None
            poetry_line_index = None
        elif block.block_type == "quote_block":
            role = "quote"
        elif block.block_type == "lineated_block":
            role = "lineated_block"
            layout_kind = "lineated_block"
            lineation = "lineated"
            quote_kind = None
            if not lines:
                lines = extract_verse_lines(block)
            poetry_group_id = None
            poetry_line_index = None
        elif block.block_type == "table":
            role = "table"
            layout_kind = None
            quote_kind = None
            lineation = None
            lines = []
            genre_hint = None
            genre_confidence = None
            genre_source = None
            poetry_group_id = None
            poetry_line_index = None
        else:
            # Unknown block types: avoid inventing rich semantics; drop quote
            # semantics unless this is an explicit quote block.
            layout_kind = None
            quote_kind = None
            lineation = None
            lines = []
            genre_hint = None
            genre_confidence = None
            genre_source = None
            poetry_group_id = None
            poetry_line_index = None

        if block.block_type == "quote_block":
            quote_kind = "prose"
            lineation = "prose"
            layout_kind = None
            lines = []
            genre_hint = None
            genre_confidence = None
            genre_source = None
            poetry_group_id = None
            poetry_line_index = None

        return BlockSemantics(
            role=role,
            layout_kind=layout_kind,
            quote_kind=quote_kind,
            lineation=lineation,
            lines=lines,
            genre_hint=genre_hint,
            genre_confidence=genre_confidence,
            genre_source=genre_source,
            poetry_group_id=poetry_group_id,
            poetry_line_index=poetry_line_index,
        )
