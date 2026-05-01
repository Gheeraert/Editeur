from __future__ import annotations

"""Modèle sémantique minimal pour la chaîne PDF d'Impressions.

Ce module définit une représentation intermédiaire volontairement légère
entre :

1. le XML TEI normalisé ;
2. le rendu typographique (LaTeX/PDF) ;
3. d'éventuels autres rendus futurs.

Le principe est simple :
- le parseur TEI construit des objets sémantiques ;
- le moteur de rendu décide ensuite comment les convertir en LaTeX.

On évite ainsi deux écueils :
- transformer trop tôt le TEI en chaînes LaTeX fragiles ;
- construire un modèle trop vaste et abstrait pour une V1.

Le périmètre de cette V1 correspond aux livres PURH les plus courants :
monographies, recueils d'articles, volumes collectifs, avec titres,
liminaires, paragraphes, notes, citations, figures et bibliographie.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias


# ---------------------------------------------------------------------------
# Énumérations et alias de type
# ---------------------------------------------------------------------------


class DivisionType(str, Enum):
    """Grandes unités éditoriales du livre."""

    DEDICATION = "dedication"
    ACKNOWLEDGMENTS = "acknowledgments"
    FOREWORD = "foreword"
    PREFACE = "preface"
    INTRODUCTION = "introduction"
    CHAPTER = "chapter"
    CONCLUSION = "conclusion"
    BIBLIOGRAPHY = "bibliography"
    APPENDIX = "appendix"
    PART = "part"
    OTHER = "other"


class SectionLevel(int, Enum):
    """Niveaux de sections pris en charge en V1."""

    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3


class ListKind(str, Enum):
    """Types de listes gérées en V1."""

    ORDERED = "ordered"
    UNORDERED = "unordered"


# ---------------------------------------------------------------------------
# Inline nodes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class TextRun:
    """Texte brut.

    Le rendu final (espaces typographiques, guillemets, commandes LaTeX,
    etc.) sera décidé plus tard.
    """

    text: str


@dataclass(slots=True)
class Italic:
    """Segment en italique."""

    children: list["InlineNode"] = field(default_factory=list)


@dataclass(slots=True)
class Bold:
    """Segment en gras."""

    children: list["InlineNode"] = field(default_factory=list)


@dataclass(slots=True)
class SmallCaps:
    """Segment en petites capitales."""

    children: list["InlineNode"] = field(default_factory=list)


@dataclass(slots=True)
class Superscript:
    """Segment en exposant."""

    children: list["InlineNode"] = field(default_factory=list)


@dataclass(slots=True)
class Subscript:
    """Segment en indice."""

    children: list["InlineNode"] = field(default_factory=list)


@dataclass(slots=True)
class Link:
    """Lien hypertexte."""

    target: str
    children: list["InlineNode"] = field(default_factory=list)
    link_type: str | None = None


@dataclass(slots=True)
class InlineQuote:
    """Citation courte intégrée au fil du texte."""

    children: list["InlineNode"] = field(default_factory=list)


@dataclass(slots=True)
class NoteRef:
    """Appel de note dans le flux du texte.

    Le contenu de la note est stocké séparément dans un objet ``Footnote``.
    """

    note_id: str


InlineNode: TypeAlias = (
    TextRun
    | Italic
    | Bold
    | SmallCaps
    | Superscript
    | Subscript
    | Link
    | InlineQuote
    | NoteRef
)


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Paragraph:
    """Paragraphe standard."""

    content: list[InlineNode] = field(default_factory=list)
    render_hint: str | None = None


@dataclass(slots=True)
class QuoteBlock:
    """Citation en retrait.

    ``blocks`` contient le corps de la citation.
    ``source`` permet d'encoder une source ou une référence bibliographique
    liée à la citation.
    """

    blocks: list["BlockNode"] = field(default_factory=list)
    source: list[InlineNode] | None = None


@dataclass(slots=True)
class FigureBlock:
    """Figure bloc avec image et éléments de paratexte."""

    image_path: str
    title: list[InlineNode] | None = None
    caption: list[InlineNode] | None = None
    credits: list[InlineNode] | None = None
    alt_image_path: str | None = None
    inline: bool = False


@dataclass(slots=True)
class BibliographyItem:
    """Entrée bibliographique déjà formulée dans le XML."""

    content: list[InlineNode] = field(default_factory=list)


@dataclass(slots=True)
class BibliographyBlock:
    """Bloc de bibliographie, généralement en fin d'unité."""

    title: str | None = None
    items: list[BibliographyItem] = field(default_factory=list)


@dataclass(slots=True)
class ListItem:
    """Élément de liste."""

    blocks: list["BlockNode"] = field(default_factory=list)


@dataclass(slots=True)
class ListBlock:
    """Liste ordonnée ou non ordonnée."""

    kind: ListKind
    items: list[ListItem] = field(default_factory=list)
    rendition: str | None = None


@dataclass(slots=True)
class VerseLine:
    """Vers individuel, numéroté ou non."""

    content: list[InlineNode] = field(default_factory=list)
    number: str | None = None


@dataclass(slots=True)
class VerseBlock:
    """Bloc de vers."""

    lines: list[VerseLine] = field(default_factory=list)


@dataclass(slots=True)
class TitlePageBlock:
    """Page de titre sémantique d'une unité ou du volume."""

    title: str
    subtitle: str | None = None
    contributors: list["Contributor"] = field(default_factory=list)
    extra_lines: list[str] = field(default_factory=list)


BlockNode: TypeAlias = (
    Paragraph
    | QuoteBlock
    | FigureBlock
    | BibliographyBlock
    | ListBlock
    | VerseBlock
    | TitlePageBlock
)


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Footnote:
    """Note de bas de page.

    Une note contient des blocs, et non une simple chaîne, afin de tolérer
    un minimum de richesse interne (italiques, références, paragraphes brefs,
    etc.).
    """

    note_id: str
    blocks: list[BlockNode] = field(default_factory=list)
    number: str | None = None


# ---------------------------------------------------------------------------
# Métadonnées éditoriales
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Contributor:
    """Personne intervenant dans le volume ou dans une unité."""

    full_name: str
    role: str = "author"
    affiliation: str | None = None
    email: str | None = None


@dataclass(slots=True)
class PublicationInfo:
    """Métadonnées de publication utiles au rendu éditorial."""

    publisher: str | None = None
    publication_year: str | None = None
    publication_place: str | None = None
    isbn_print: str | None = None
    isbn_pdf: str | None = None
    issn: str | None = None
    doi: str | None = None
    collection_name: str | None = None
    collection_number: str | None = None


@dataclass(slots=True)
class BookMetadata:
    """Métadonnées globales du livre."""

    title: str
    subtitle: str | None = None
    language: str | None = None
    contributors: list[Contributor] = field(default_factory=list)
    publication: PublicationInfo = field(default_factory=PublicationInfo)
    abstract: str | None = None
    back_cover: str | None = None


# ---------------------------------------------------------------------------
# Nœuds de structure
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Section:
    """Section hiérarchique interne à une division."""

    title: str
    level: int
    blocks: list[BlockNode] = field(default_factory=list)
    sections: list["Section"] = field(default_factory=list)


@dataclass(slots=True)
class Division:
    """Grande unité éditoriale du livre.

    Exemples : introduction, chapitre, conclusion, bibliographie, etc.
    """

    div_id: str
    div_type: DivisionType = DivisionType.OTHER
    title: str | None = None
    contributors: list[Contributor] = field(default_factory=list)
    title_page: TitlePageBlock | None = None
    blocks: list[BlockNode] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    notes: dict[str, Footnote] = field(default_factory=dict)


@dataclass(slots=True)
class Book:
    """Livre complet.

    Le partage front/body/back reste volontairement simple et orienté rendu.
    """

    metadata: BookMetadata
    front_divisions: list[Division] = field(default_factory=list)
    body_divisions: list[Division] = field(default_factory=list)
    back_divisions: list[Division] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Petites fonctions utilitaires
# ---------------------------------------------------------------------------


def text(value: str) -> TextRun:
    """Raccourci pratique pour construire un ``TextRun``."""

    return TextRun(text=value)


def paragraph_from_text(value: str) -> Paragraph:
    """Construit rapidement un paragraphe simple à partir d'une chaîne."""

    return Paragraph(content=[TextRun(text=value)])
