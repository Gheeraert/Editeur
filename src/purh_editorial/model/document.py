from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Metadata:
    title: str | None = None
    subtitle: str | None = None
    authors: list[str] = field(default_factory=list)
    language: str | None = None
    collection: str | None = None
    publication_type: str | None = None
    source_label: str | None = None


@dataclass(slots=True)
class InlineStyle:
    bold: bool = False
    italic: bool = False
    small_caps: bool = False
    subscript: bool = False
    superscript: bool = False


@dataclass(slots=True)
class InlineSpan:
    text: str
    style: InlineStyle = field(default_factory=InlineStyle)
    kind: str = "text"
    note_ref: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Block:
    block_id: str
    block_type: str
    text: str = ""
    inlines: list[InlineSpan] = field(default_factory=list)
    note_refs: list[str] = field(default_factory=list)
    children: list["Block"] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    source_span: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Paragraph(Block):
    block_type: str = "paragraph"


@dataclass(slots=True)
class Heading(Block):
    block_type: str = "heading"


@dataclass(slots=True)
class QuoteBlock(Block):
    block_type: str = "quote_block"


@dataclass(slots=True)
class Note:
    note_id: str
    label: str | None = None
    text: str = ""
    inlines: list[InlineSpan] = field(default_factory=list)
    target_ref: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BibliographyItem:
    item_id: str
    raw_text: str
    parsed_fields: dict[str, str] = field(default_factory=dict)
    item_type: str = "unknown"
    source_span: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Document:
    document_id: str
    source_path: str
    source_format: str
    metadata: Metadata = field(default_factory=Metadata)
    blocks: list[Block] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)
    bibliography: list[BibliographyItem] = field(default_factory=list)
    annotations: dict[str, Any] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)
    original_text: str = ""

    def block_by_id(self, block_id: str) -> Block | None:
        for block in self.blocks:
            if block.block_id == block_id:
                return block
        return None
