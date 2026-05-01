from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias


@dataclass(slots=True)
class TextRun:
    text: str


@dataclass(slots=True)
class Italic:
    children: list["InlineNode"] = field(default_factory=list)


@dataclass(slots=True)
class Bold:
    children: list["InlineNode"] = field(default_factory=list)


@dataclass(slots=True)
class SmallCaps:
    children: list["InlineNode"] = field(default_factory=list)


@dataclass(slots=True)
class Superscript:
    children: list["InlineNode"] = field(default_factory=list)


@dataclass(slots=True)
class Subscript:
    children: list["InlineNode"] = field(default_factory=list)


@dataclass(slots=True)
class FootnoteRef:
    content: list["InlineNode"] = field(default_factory=list)


InlineNode: TypeAlias = TextRun | Italic | Bold | SmallCaps | Superscript | Subscript | FootnoteRef


@dataclass(slots=True)
class Paragraph:
    content: list[InlineNode] = field(default_factory=list)


@dataclass(slots=True)
class Division:
    title: str
    paragraphs: list[Paragraph] = field(default_factory=list)


@dataclass(slots=True)
class BookMetadata:
    title: str
    contributors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Book:
    metadata: BookMetadata
    divisions: list[Division] = field(default_factory=list)
