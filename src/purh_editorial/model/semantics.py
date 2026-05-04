from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from purh_editorial.model.document import Block, InlineSpan


@dataclass(slots=True)
class BlockSemantics:
    role: str | None = None
    layout_kind: str | None = None
    quote_kind: str | None = None
    lineation: str | None = None
    lines: list[str] = field(default_factory=list)
    genre_hint: str | None = None
    genre_confidence: float | None = None
    genre_source: str | None = None
    poetry_group_id: str | None = None
    poetry_line_index: int | None = None

    @property
    def is_lineated(self) -> bool:
        return self.lineation == "lineated" and bool(self.lines)


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


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
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


def read_block_semantics(block: Block) -> BlockSemantics:
    semantic_raw = (block.attributes or {}).get("semantic")
    if not isinstance(semantic_raw, dict):
        return BlockSemantics()
    return BlockSemantics(
        role=_as_text(semantic_raw.get("role")),
        layout_kind=_as_text(semantic_raw.get("layout_kind")),
        quote_kind=_as_text(semantic_raw.get("quote_kind")),
        lineation=_as_text(semantic_raw.get("lineation")),
        lines=_semantic_lines_from_payload(semantic_raw),
        genre_hint=_as_text(semantic_raw.get("genre_hint")),
        genre_confidence=_as_float(semantic_raw.get("genre_confidence")),
        genre_source=_as_text(semantic_raw.get("genre_source")),
        poetry_group_id=_as_text(semantic_raw.get("poetry_group_id")),
        poetry_line_index=_as_int(semantic_raw.get("poetry_line_index")),
    )


def semantics_to_dict(semantics: BlockSemantics) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if semantics.role:
        payload["role"] = semantics.role
    if semantics.layout_kind:
        payload["layout_kind"] = semantics.layout_kind
    if semantics.quote_kind and semantics.role != "lineated_block":
        payload["quote_kind"] = semantics.quote_kind
    if semantics.lineation:
        payload["lineation"] = semantics.lineation
    if semantics.lines:
        payload["lines"] = semantics.lines
    if semantics.genre_hint:
        payload["genre_hint"] = semantics.genre_hint
    if semantics.genre_confidence is not None:
        payload["genre_confidence"] = semantics.genre_confidence
    if semantics.genre_source:
        payload["genre_source"] = semantics.genre_source
    if semantics.poetry_group_id and semantics.role != "lineated_block":
        payload["poetry_group_id"] = semantics.poetry_group_id
    if semantics.poetry_line_index is not None and semantics.role != "lineated_block":
        payload["poetry_line_index"] = semantics.poetry_line_index
    return payload


def write_block_semantics(block: Block, semantics: BlockSemantics) -> None:
    block.attributes["semantic"] = semantics_to_dict(semantics)


def is_canonical_lineated_block(block: Block) -> bool:
    semantics = read_block_semantics(block)
    has_lineated_payload = (
        semantics.layout_kind == "lineated_block"
        and semantics.lineation == "lineated"
        and bool(semantics.lines)
    )
    if not has_lineated_payload:
        return False
    return (
        (block.block_type == "lineated_block" and semantics.role == "lineated_block")
        or (block.block_type == "quote_block" and semantics.role == "quote")
    )


def is_canonical_poetry_block(block: Block) -> bool:
    semantics = read_block_semantics(block)
    return is_canonical_lineated_block(block) and (
        semantics.genre_hint == "poetry"
        or (semantics.role == "quote" and semantics.quote_kind == "poetry")
    )
