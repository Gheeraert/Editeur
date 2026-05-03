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
            inferred = read_block_semantics(block, allow_legacy_inference=True)
            stored = read_block_semantics(block, allow_legacy_inference=False)
            canonical = self._canonical_semantics_for_block(block, inferred)
            before_payload = semantics_to_dict(stored)
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
        quote_kind = current.quote_kind
        lineation = current.lineation
        lines = list(current.lines)

        if block.block_type == "heading":
            role = "heading"
        elif block.block_type == "paragraph":
            role = "paragraph"
        elif block.block_type == "quote_block":
            role = "quote"

        if block.block_type == "quote_block":
            if quote_kind == "poetry" or lineation == "verse":
                quote_kind = "poetry"
                lineation = "verse"
                if not lines:
                    lines = extract_verse_lines(block)
            else:
                quote_kind = quote_kind or "prose"
                lineation = lineation or "prose"
                if lineation != "verse":
                    lines = []

        if quote_kind == "poetry" and lineation is None:
            lineation = "verse"

        return BlockSemantics(
            role=role,
            quote_kind=quote_kind,
            lineation=lineation,
            lines=lines,
            poetry_group_id=current.poetry_group_id,
            poetry_line_index=current.poetry_line_index,
        )
