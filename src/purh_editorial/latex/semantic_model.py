from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
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
class QuoteBlock:
    paragraphs: list[Paragraph] = field(default_factory=list)


@dataclass(slots=True)
class VerseLine:
    content: list[InlineNode] = field(default_factory=list)


@dataclass(slots=True)
class VerseBlock:
    lines: list[VerseLine] = field(default_factory=list)


@dataclass(slots=True)
class ListItem:
    content: list[InlineNode] = field(default_factory=list)


@dataclass(slots=True)
class ListBlock:
    ordered: bool
    items: list[ListItem] = field(default_factory=list)


@dataclass(slots=True)
class BibliographyItem:
    content: list[InlineNode] = field(default_factory=list)


@dataclass(slots=True)
class BibliographyBlock:
    items: list[BibliographyItem] = field(default_factory=list)


BlockNode: TypeAlias = Paragraph | QuoteBlock | VerseBlock | ListBlock | BibliographyBlock


class DivisionKind(str, Enum):
    FRONT = "front"
    INTRODUCTION = "introduction"
    CHAPTER = "chapter"
    CONCLUSION = "conclusion"
    BIBLIOGRAPHY = "bibliography"
    APPENDIX = "appendix"
    BACK = "back"
    OTHER = "other"


@dataclass(slots=True)
class Division:
    title: str
    kind: DivisionKind = DivisionKind.OTHER
    blocks: list[BlockNode] = field(default_factory=list)


@dataclass(slots=True)
class BookMetadata:
    title: str
    contributors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Book:
    metadata: BookMetadata
    divisions: list[Division] = field(default_factory=list)
