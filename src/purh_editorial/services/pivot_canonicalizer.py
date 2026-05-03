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
            needs_legacy_cleanup = self._has_stale_legacy_semantic_keys(block, canonical)
            if before_payload == after_payload and not needs_legacy_cleanup:
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
    def _has_stale_legacy_semantic_keys(block, canonical: BlockSemantics) -> bool:
        attributes = block.attributes

        if canonical.role == "quote":
            if canonical.quote_kind:
                if attributes.get("quote_kind") != canonical.quote_kind:
                    return True
            elif "quote_kind" in attributes:
                return True

            if canonical.lineation:
                if attributes.get("lineation") != canonical.lineation:
                    return True
            elif "lineation" in attributes:
                return True

            if canonical.quote_kind == "poetry":
                if canonical.poetry_group_id is not None and attributes.get("poetry_group_id") != canonical.poetry_group_id:
                    return True
                if canonical.poetry_group_id is None and "poetry_group_id" in attributes:
                    return True
                if canonical.poetry_line_index is not None and attributes.get("poetry_line_index") != canonical.poetry_line_index:
                    return True
                if canonical.poetry_line_index is None and "poetry_line_index" in attributes:
                    return True
            else:
                if "poetry_group_id" in attributes or "poetry_line_index" in attributes:
                    return True
            return False

        return any(
            key in attributes
            for key in ("quote_kind", "lineation", "poetry_group_id", "poetry_line_index")
        )

    @staticmethod
    def _canonical_semantics_for_block(
        block,
        current: BlockSemantics,
    ) -> BlockSemantics:
        role = current.role
        quote_kind = current.quote_kind
        lineation = current.lineation
        lines = list(current.lines)
        poetry_group_id = current.poetry_group_id
        poetry_line_index = current.poetry_line_index

        if block.block_type == "heading":
            role = "heading"
            quote_kind = None
            lineation = None
            lines = []
            poetry_group_id = None
            poetry_line_index = None
        elif block.block_type == "paragraph":
            role = "paragraph"
            quote_kind = None
            lineation = None
            lines = []
            poetry_group_id = None
            poetry_line_index = None
        elif block.block_type == "quote_block":
            role = "quote"
        elif block.block_type == "table":
            role = "table"
            quote_kind = None
            lineation = None
            lines = []
            poetry_group_id = None
            poetry_line_index = None
        else:
            # Unknown block types: avoid inventing rich semantics; drop quote
            # semantics unless this is an explicit quote block.
            quote_kind = None
            lineation = None
            lines = []
            poetry_group_id = None
            poetry_line_index = None

        if block.block_type == "quote_block":
            if quote_kind == "poetry" or lineation == "verse":
                quote_kind = "poetry"
                lineation = "verse"
                if not lines:
                    lines = extract_verse_lines(block)
            else:
                quote_kind = "prose"
                lineation = "prose"
                lines = []
                poetry_group_id = None
                poetry_line_index = None

        return BlockSemantics(
            role=role,
            quote_kind=quote_kind,
            lineation=lineation,
            lines=lines,
            poetry_group_id=poetry_group_id,
            poetry_line_index=poetry_line_index,
        )
