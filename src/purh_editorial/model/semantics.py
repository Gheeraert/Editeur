from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from purh_editorial.model.document import Block, InlineSpan


@dataclass(slots=True)
class BlockSemantics:
    role: str | None = None
    quote_kind: str | None = None
    lineation: str | None = None
    lines: list[str] = field(default_factory=list)
    poetry_group_id: str | None = None
    poetry_line_index: int | None = None


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _inline_lines(inlines: list[InlineSpan]) -> list[str]:
    if not inlines:
        return []
    lines: list[str] = []
    current: list[str] = []
    for span in inlines:
        if span.kind == "line_break":
            candidate = "".join(current).strip()
            if candidate:
                lines.append(candidate)
            current = []
            continue
        if span.kind == "note_call":
            continue
        if span.text:
            current.append(span.text)
    candidate = "".join(current).strip()
    if candidate:
        lines.append(candidate)
    return lines


def extract_verse_lines(block: Block) -> list[str]:
    attributes = block.attributes or {}
    semantic = attributes.get("semantic")
    if isinstance(semantic, dict):
        lines = semantic.get("lines")
        if isinstance(lines, list):
            cleaned = [str(line).strip() for line in lines if str(line).strip()]
            if cleaned:
                return cleaned

    inline_lines = _inline_lines(block.inlines)
    if inline_lines:
        return inline_lines

    text = block.text or ""
    if "\n" in text:
        return [line.strip() for line in text.split("\n") if line.strip()]
    if text.strip():
        return [text.strip()]
    return []


def _semantic_lines_from_payload(semantic_raw: dict[str, Any]) -> list[str]:
    raw_lines = semantic_raw.get("lines")
    if not isinstance(raw_lines, list):
        return []
    return [str(line).strip() for line in raw_lines if str(line).strip()]


def read_block_semantics(
    block: Block,
    *,
    allow_legacy_inference: bool = True,
) -> BlockSemantics:
    attributes = block.attributes or {}
    semantic_raw = attributes.get("semantic")

    role: str | None = None
    quote_kind: str | None = None
    lineation: str | None = None
    lines: list[str] = []
    poetry_group_id: str | None = None
    poetry_line_index: int | None = None

    if isinstance(semantic_raw, dict):
        role = _as_text(semantic_raw.get("role"))
        quote_kind = _as_text(semantic_raw.get("quote_kind"))
        lineation = _as_text(semantic_raw.get("lineation"))
        lines = _semantic_lines_from_payload(semantic_raw)
        poetry_group_id = _as_text(semantic_raw.get("poetry_group_id"))
        poetry_line_index = _as_int(semantic_raw.get("poetry_line_index"))

    if allow_legacy_inference:
        if role is None:
            role = _as_text(attributes.get("semantic_role"))
        if poetry_group_id is None:
            poetry_group_id = _as_text(attributes.get("poetry_group_id"))
        if poetry_line_index is None:
            poetry_line_index = _as_int(attributes.get("poetry_line_index"))

        allow_legacy_quote_fields = block.block_type == "quote_block" or role == "quote"
        if allow_legacy_quote_fields:
            if quote_kind is None:
                quote_kind = _as_text(attributes.get("quote_kind"))
            if lineation is None:
                lineation = _as_text(attributes.get("lineation"))

        if role is None:
            if block.block_type == "heading":
                role = "heading"
            elif block.block_type == "quote_block":
                role = "quote"
            elif block.block_type == "paragraph":
                role = "paragraph"

        if quote_kind == "poetry" and lineation is None:
            lineation = "verse"
        if lineation == "verse" and not lines:
            lines = extract_verse_lines(block)
        if role == "quote" and block.block_type == "quote_block":
            if quote_kind is None:
                quote_kind = "prose"
            if lineation is None:
                lineation = "prose"

    return BlockSemantics(
        role=role,
        quote_kind=quote_kind,
        lineation=lineation,
        lines=lines,
        poetry_group_id=poetry_group_id,
        poetry_line_index=poetry_line_index,
    )


def semantics_to_dict(semantics: BlockSemantics) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if semantics.role:
        payload["role"] = semantics.role
    if semantics.quote_kind:
        payload["quote_kind"] = semantics.quote_kind
    if semantics.lineation:
        payload["lineation"] = semantics.lineation
    if semantics.lines:
        payload["lines"] = semantics.lines
    if semantics.poetry_group_id:
        payload["poetry_group_id"] = semantics.poetry_group_id
    if semantics.poetry_line_index is not None:
        payload["poetry_line_index"] = semantics.poetry_line_index
    return payload


def write_block_semantics(block: Block, semantics: BlockSemantics) -> None:
    payload = semantics_to_dict(semantics)
    block.attributes["semantic"] = payload

    if semantics.role:
        block.attributes["semantic_role"] = semantics.role

    if semantics.quote_kind:
        block.attributes["quote_kind"] = semantics.quote_kind
    if semantics.lineation:
        block.attributes["lineation"] = semantics.lineation

    if semantics.poetry_group_id:
        block.attributes["poetry_group_id"] = semantics.poetry_group_id
    if semantics.poetry_line_index is not None:
        block.attributes["poetry_line_index"] = semantics.poetry_line_index


def is_canonical_poetry_block(block: Block) -> bool:
    semantics = read_block_semantics(block, allow_legacy_inference=False)
    return (
        block.block_type == "quote_block"
        and semantics.role == "quote"
        and semantics.quote_kind == "poetry"
        and semantics.lineation == "verse"
        and bool(semantics.lines)
    )
