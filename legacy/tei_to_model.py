from __future__ import annotations

"""Parseur TEI normalisé -> modèle sémantique minimal.

Ce module lit le ``book.normalized.xml`` produit par Impressions et le convertit
vers la représentation intermédiaire définie dans ``semantic_model.py``.

Objectifs de la V1
-----------------
- rester simple et lisible ;
- couvrir les cas les plus fréquents des livres PURH ;
- éviter toute génération LaTeX à ce stade ;
- produire une structure stable pour le renderer PDF.

Hypothèses principales
----------------------
- le fichier XML a déjà été normalisé ;
- les ``xi:include`` ont déjà été résolus ;
- le document relève du sous-ensemble TEI/Métopes observé dans les corpus ;
- les niveaux de sections utiles en V1 sont 1 à 3.
"""

from dataclasses import replace
import itertools
import re
from pathlib import Path

from lxml import etree as ET

from .semantic_model import (
    BibliographyBlock,
    BibliographyItem,
    Book,
    BookMetadata,
    Bold,
    Contributor,
    Division,
    DivisionType,
    FigureBlock,
    Footnote,
    InlineNode,
    InlineQuote,
    Italic,
    Link,
    ListBlock,
    ListItem,
    ListKind,
    Paragraph,
    PublicationInfo,
    QuoteBlock,
    Section,
    SmallCaps,
    Subscript,
    Superscript,
    TextRun,
    TitlePageBlock,
    VerseBlock,
    VerseLine,
    NoteRef,
)


TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}
WHITESPACE_RE = re.compile(r"\s+")
SECTION_TYPE_RE = re.compile(r"^section([1-9])$")


class TeiToModelParser:
    """Convertisseur TEI normalisé -> modèle sémantique minimal."""

    def __init__(self) -> None:
        self._generated_note_counter = itertools.count(1)
        self._generated_div_counter = itertools.count(1)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def parse(self, xml_path: str | Path) -> Book:
        """Parse un fichier TEI normalisé et retourne un objet ``Book``."""

        parser = ET.XMLParser(remove_blank_text=False, recover=True)
        tree = ET.parse(str(xml_path), parser=parser)
        root = tree.getroot()

        metadata = self._parse_book_metadata(root)
        book = Book(metadata=metadata)

        text_el = root.find("./tei:text", namespaces=NS)
        if text_el is None:
            return book

        book.front_divisions.extend(self._parse_volume_front_divisions(text_el))
        book.body_divisions.extend(self._parse_grouped_body_divisions(text_el))

        if not book.body_divisions:
            book.body_divisions.extend(self._parse_ungrouped_body_divisions(text_el))

        book.back_divisions.extend(self._parse_volume_back_divisions(text_el))
        return book


# ----------------------------------------------------------------------
# Métadonnées globales
# ----------------------------------------------------------------------

    def _parse_book_metadata(self, root: ET._Element) -> BookMetadata:
        header = root.find("./tei:teiHeader", namespaces=NS)
        if header is None:
            return BookMetadata(title="Sans titre")

        title_stmt = header.find("./tei:fileDesc/tei:titleStmt", namespaces=NS)
        profile_desc = header.find("./tei:profileDesc", namespaces=NS)
        publication_stmt = header.find("./tei:fileDesc/tei:publicationStmt", namespaces=NS)

        title = self._first_text(
            title_stmt,
            "./tei:title[@type='main']",
            default="Sans titre",
        )
        subtitle = self._first_text(title_stmt, "./tei:title[@type='sub']")
        language = self._first_attr(profile_desc, "./tei:langUsage/tei:language", "ident")

        contributors = self._parse_header_contributors(title_stmt)
        publication = self._parse_publication_info(publication_stmt)
        abstract = self._extract_abstract(profile_desc)
        back_cover = self._extract_back_cover(profile_desc)

        return BookMetadata(
            title=title,
            subtitle=subtitle,
            language=language,
            contributors=contributors,
            publication=publication,
            abstract=abstract,
            back_cover=back_cover,
        )

    def _parse_header_contributors(self, title_stmt: ET._Element | None) -> list[Contributor]:
        contributors: list[Contributor] = []
        if title_stmt is None:
            return contributors

        for author in title_stmt.findall("./tei:author", namespaces=NS):
            contributors.append(self._parse_header_person(author, role="author"))

        for editor in title_stmt.findall("./tei:editor", namespaces=NS):
            role = editor.get("role") or "editor"
            contributors.append(self._parse_header_person(editor, role=role))

        return contributors

    def _parse_header_person(self, node: ET._Element, role: str) -> Contributor:
        full_name = self._compose_pers_name(node.find("./tei:persName", namespaces=NS))
        if not full_name:
            full_name = self._normalized_text(node)

        affiliation = self._first_text(node, "./tei:affiliation/tei:orgName")
        email = self._first_text(node, "./tei:affiliation/tei:email")
        return Contributor(full_name=full_name, role=role, affiliation=affiliation, email=email)

    def _parse_publication_info(self, publication_stmt: ET._Element | None) -> PublicationInfo:
        if publication_stmt is None:
            return PublicationInfo()

        info = PublicationInfo()
        info.publisher = self._first_text(publication_stmt, ".//tei:publisher")
        info.publication_place = self._first_text(publication_stmt, ".//tei:pubPlace")

        book_ab = publication_stmt.find("./tei:ab[@type='book']", namespaces=NS)
        pdf_ab = publication_stmt.find("./tei:ab[@type='digital_download'][@subtype='PDF']", namespaces=NS)

        info.publication_year = (
            self._first_text(book_ab, ".//tei:date[@type='publishing']")
            or self._first_text(pdf_ab, ".//tei:date[@type='publishing']")
        )
        info.isbn_print = self._first_text(book_ab, ".//tei:idno[@type='ISBN-13']")
        info.isbn_pdf = (
            self._first_text(pdf_ab, ".//tei:idno[@type='ISBN']")
            or self._first_text(pdf_ab, ".//tei:idno[@type='ISBN-13']")
        )
        info.issn = self._first_text(book_ab, ".//tei:idno[@type='ISSN']")
        info.doi = (
            self._first_text(pdf_ab, ".//tei:idno[@type='DOI']")
            or self._first_text(pdf_ab, ".//tei:ref[@type='DOI']")
        )
        return info

    def _extract_abstract(self, profile_desc: ET._Element | None) -> str | None:
        if profile_desc is None:
            return None
        return (
            self._first_text(profile_desc, "./tei:abstract[@rend='resume']/tei:p")
            or self._first_text(profile_desc, "./tei:abstract[@rend='abstract']/tei:p")
        )

    def _extract_back_cover(self, profile_desc: ET._Element | None) -> str | None:
        if profile_desc is None:
            return None
        return self._first_text(profile_desc, "./tei:abstract[@rend='4e-couv']/tei:p")


# ----------------------------------------------------------------------
# Découpage du livre
# ----------------------------------------------------------------------

    def _parse_volume_front_divisions(self, text_el: ET._Element) -> list[Division]:
        front = text_el.find("./tei:front", namespaces=NS)
        if front is None:
            return []

        divisions: list[Division] = []
        for child in front:
            if self._local_name(child) != "div":
                continue
            if child.get("type") == "titlePage":
                continue
            divisions.append(self._parse_standalone_division(child))
        return divisions

    def _parse_grouped_body_divisions(self, text_el: ET._Element) -> list[Division]:
        group_book = text_el.find("./tei:group[@type='book']", namespaces=NS)
        if group_book is None:
            return []
        return list(self._iter_group_divisions(group_book))

    def _parse_ungrouped_body_divisions(self, text_el: ET._Element) -> list[Division]:
        body = text_el.find("./tei:body", namespaces=NS)
        if body is None:
            return []

        division = Division(
            div_id="body-1",
            div_type=DivisionType.OTHER,
            title=self._first_text(body, "./tei:head") or "Corps du texte",
        )
        division.blocks.extend(self._parse_container_blocks(body, division.notes))
        division.sections.extend(self._parse_direct_sections(body, division.notes))
        return [division]

    def _parse_volume_back_divisions(self, text_el: ET._Element) -> list[Division]:
        back = text_el.find("./tei:back", namespaces=NS)
        if back is None:
            return []

        divisions: list[Division] = []
        for child in back:
            if self._local_name(child) != "div":
                continue
            divisions.append(self._parse_standalone_division(child))
        return divisions

    def _iter_group_divisions(self, group_book: ET._Element):
        for child in group_book:
            if self._local_name(child) != "group":
                continue

            group_type = (child.get("type") or "").strip()

            # Cas important : les parties d'un volume collectif.
            if SECTION_TYPE_RE.match(group_type):
                part_title = self._first_text(child, "./tei:head") or self._first_text(
                    child,
                    ".//tei:head[@subtype='level1']",
                )
                yield Division(
                    div_id=child.get("{http://www.w3.org/XML/1998/namespace}id")
                    or f"part-{next(self._generated_div_counter)}",
                    div_type=DivisionType.PART,
                    title=part_title or "Partie",
                )
                yield from self._iter_group_divisions(child)
                continue

            yield self._parse_group_division(child)

    def _parse_group_division(self, group_el: ET._Element) -> Division:
        div_type = self._map_division_type(group_el.get("type"))
        division = Division(
            div_id=group_el.get("{http://www.w3.org/XML/1998/namespace}id")
            or f"div-{next(self._generated_div_counter)}",
            div_type=div_type,
        )

        front = self._find_structural_child(group_el, "front")
        body = self._find_structural_child(group_el, "body")
        back = self._find_structural_child(group_el, "back")

        if front is not None:
            division.title_page = self._parse_title_page(front)
            division.contributors.extend(self._parse_title_page_contributors(front))
            division.blocks.extend(self._parse_front_special_blocks(front, division.notes))

        if body is not None:
            division.blocks.extend(self._parse_container_blocks(body, division.notes))
            division.sections.extend(self._parse_direct_sections(body, division.notes))

        if back is not None:
            division.blocks.extend(self._parse_container_blocks(back, division.notes))
            division.sections.extend(self._parse_direct_sections(back, division.notes))

        division.title = (
            (division.title_page.title if division.title_page else None)
            or self._first_text(body, "./tei:head")
            or self._first_text(front, ".//tei:head")
        )

        return division

    def _parse_standalone_division(self, div_el: ET._Element) -> Division:
        div_type = self._map_division_type(div_el.get("type"))
        division = Division(
            div_id=div_el.get("{http://www.w3.org/XML/1998/namespace}id")
            or f"div-{next(self._generated_div_counter)}",
            div_type=div_type,
            title=self._first_text(div_el, "./tei:head") or self._guess_division_title_from_type(div_type),
        )
        division.blocks.extend(self._parse_container_blocks(div_el, division.notes))
        division.sections.extend(self._parse_direct_sections(div_el, division.notes))
        return division


# ----------------------------------------------------------------------
# Parsing des sections
# ----------------------------------------------------------------------

    def _parse_direct_sections(
        self,
        parent: ET._Element,
        notes_store: dict[str, Footnote],
    ) -> list[Section]:
        sections: list[Section] = []
        for child in parent:
            if self._local_name(child) != "div":
                continue
            if not self._is_section_div(child):
                continue
            sections.append(self._parse_section(child, notes_store))
        return sections

    def _parse_section(
        self,
        div_el: ET._Element,
        notes_store: dict[str, Footnote],
    ) -> Section:
        level = self._section_level(div_el)
        section = Section(
            title=self._first_text(div_el, "./tei:head") or "Sans titre",
            level=level,
        )
        section.blocks.extend(self._parse_container_blocks(div_el, notes_store))
        section.sections.extend(self._parse_direct_sections(div_el, notes_store))
        return section


# ----------------------------------------------------------------------
# Parsing des blocs
# ----------------------------------------------------------------------

    def _parse_front_special_blocks(
        self,
        front_el: ET._Element,
        notes_store: dict[str, Footnote],
    ) -> list:
        blocks: list = []
        for child in front_el:
            local = self._local_name(child)
            if local == "div" and child.get("type") == "titlePage":
                continue
            if local == "note":
                # Notes liminaires éventuelles : on les traite comme paragraphes.
                content = self._parse_inline_children(child, notes_store)
                if content:
                    blocks.append(Paragraph(content=content, render_hint=child.get("type")))
                continue
            if local == "argument":
                content = self._parse_inline_children(child, notes_store)
                if content:
                    blocks.append(Paragraph(content=content, render_hint="lead"))
                continue
            if local == "epigraph":
                quote = child.find("./tei:cit/tei:quote", namespaces=NS)
                source = child.find("./tei:cit/tei:bibl", namespaces=NS)
                if quote is not None:
                    blocks.append(
                        QuoteBlock(
                            blocks=[Paragraph(content=self._parse_inline_children(quote, notes_store))],
                            source=self._parse_inline_children(source, notes_store) if source is not None else None,
                        )
                    )
                continue
            block = self._parse_block(child, notes_store)
            if block is not None:
                blocks.append(block)
        return blocks

    def _parse_container_blocks(
        self,
        parent: ET._Element,
        notes_store: dict[str, Footnote],
    ) -> list:
        blocks: list = []
        children = list(parent)
        i = 0

        while i < len(children):
            child = children[i]
            local = self._local_name(child)

            if local == "head":
                i += 1
                continue

            if local == "div" and self._is_section_div(child):
                i += 1
                continue

            if local == "div" and child.get("type") == "titlePage":
                i += 1
                continue

            if local == "bibl":
                items: list[BibliographyItem] = []
                while i < len(children) and self._local_name(children[i]) == "bibl":
                    items.append(self._parse_bibliography_item(children[i], notes_store))
                    i += 1
                blocks.append(BibliographyBlock(items=items))
                continue

            if local == "listBibl":
                items = [
                    self._parse_bibliography_item(bibl_el, notes_store)
                    for bibl_el in child.findall("./tei:bibl", namespaces=NS)
                ]
                blocks.append(BibliographyBlock(title=self._first_text(child, "./tei:head"), items=items))
                i += 1
                continue

            block = self._parse_block(child, notes_store)
            if block is not None:
                blocks.append(block)
            i += 1

        return blocks

    def _parse_block(
        self,
        element: ET._Element,
        notes_store: dict[str, Footnote],
    ):
        local = self._local_name(element)

        if local == "p":
            return Paragraph(
                content=self._parse_inline_children(element, notes_store),
                render_hint=element.get("rend"),
            )

        if local == "cit" and self._is_block_quote(element):
            return self._parse_quote_block(element, notes_store)

        if local == "figure":
            return self._parse_figure_block(element, notes_store)

        if local == "list":
            return self._parse_list_block(element, notes_store)

        if local == "lg":
            return self._parse_verse_block(element, notes_store)

        if local == "div":
            # Div non sectionnel : on aplatit ses blocs pour la V1.
            inner_blocks = self._parse_container_blocks(element, notes_store)
            if len(inner_blocks) == 1:
                return inner_blocks[0]
            if inner_blocks:
                return QuoteBlock(blocks=inner_blocks) if element.get("type") == "blockquote" else Paragraph(
                    content=[TextRun(text=self._normalized_text(element))]
                )
            return None

        if local == "argument":
            content = self._parse_inline_children(element, notes_store)
            return Paragraph(content=content, render_hint="lead") if content else None

        if local == "epigraph":
            quote = element.find("./tei:cit/tei:quote", namespaces=NS)
            source = element.find("./tei:cit/tei:bibl", namespaces=NS)
            if quote is None:
                return None
            return QuoteBlock(
                blocks=[Paragraph(content=self._parse_inline_children(quote, notes_store))],
                source=self._parse_inline_children(source, notes_store) if source is not None else None,
            )

        return None

    def _parse_quote_block(
        self,
        cit_el: ET._Element,
        notes_store: dict[str, Footnote],
    ) -> QuoteBlock:
        quote_el = cit_el.find("./tei:quote", namespaces=NS)
        source_el = cit_el.find("./tei:bibl", namespaces=NS)

        if quote_el is None:
            return QuoteBlock()

        blocks: list = []
        paragraph_children = quote_el.findall("./tei:p", namespaces=NS)
        if paragraph_children:
            for p_el in paragraph_children:
                blocks.append(Paragraph(content=self._parse_inline_children(p_el, notes_store)))
        else:
            blocks.append(Paragraph(content=self._parse_inline_children(quote_el, notes_store)))

        source = self._parse_inline_children(source_el, notes_store) if source_el is not None else None
        return QuoteBlock(blocks=blocks, source=source)

    def _parse_figure_block(
        self,
        figure_el: ET._Element,
        notes_store: dict[str, Footnote],
    ) -> FigureBlock:
        graphic_el = figure_el.find("./tei:graphic", namespaces=NS)
        alt_graphic_el = figure_el.find("./tei:graphic[@type='alternative']", namespaces=NS)

        image_path = ""
        if graphic_el is not None:
            image_path = (
                graphic_el.get("url")
                or graphic_el.get("target")
                or graphic_el.get("n")
                or ""
            )

        alt_image_path = None
        if alt_graphic_el is not None:
            alt_image_path = (
                alt_graphic_el.get("url")
                or alt_graphic_el.get("target")
                or alt_graphic_el.get("n")
            )

        title = None
        title_el = figure_el.find("./tei:head", namespaces=NS)
        if title_el is not None:
            title = self._parse_inline_children(title_el, notes_store)

        caption = None
        caption_el = figure_el.find("./tei:p[@rend='caption']", namespaces=NS)
        if caption_el is not None:
            caption = self._parse_inline_children(caption_el, notes_store)

        credits = None
        credits_el = figure_el.find("./tei:p[@rend='credits']", namespaces=NS)
        if credits_el is not None:
            credits = self._parse_inline_children(credits_el, notes_store)

        return FigureBlock(
            image_path=image_path,
            title=title,
            caption=caption,
            credits=credits,
            alt_image_path=alt_image_path,
            inline=(figure_el.get("rend") == "inline"),
        )

    def _parse_list_block(
        self,
        list_el: ET._Element,
        notes_store: dict[str, Footnote],
    ) -> ListBlock:
        kind = ListKind.ORDERED if list_el.get("type") == "ordered" else ListKind.UNORDERED
        items: list[ListItem] = []
        for item_el in list_el.findall("./tei:item", namespaces=NS):
            blocks = self._parse_container_blocks(item_el, notes_store)
            if not blocks:
                blocks = [Paragraph(content=self._parse_inline_children(item_el, notes_store))]
            items.append(ListItem(blocks=blocks))
        return ListBlock(kind=kind, items=items, rendition=list_el.get("rendition"))

    def _parse_verse_block(
        self,
        lg_el: ET._Element,
        notes_store: dict[str, Footnote],
    ) -> VerseBlock:
        lines: list[VerseLine] = []
        for line_el in lg_el.findall("./tei:l", namespaces=NS):
            lines.append(
                VerseLine(
                    content=self._parse_inline_children(line_el, notes_store),
                    number=self._first_text(line_el, "./tei:num") or line_el.get("n"),
                )
            )
        return VerseBlock(lines=lines)

    def _parse_bibliography_item(
        self,
        bibl_el: ET._Element,
        notes_store: dict[str, Footnote],
    ) -> BibliographyItem:
        return BibliographyItem(content=self._parse_inline_children(bibl_el, notes_store))


# ----------------------------------------------------------------------
# Parsing des pages de titre et des contributeurs locaux
# ----------------------------------------------------------------------

    def _parse_title_page(self, front_el: ET._Element) -> TitlePageBlock | None:
        title_page = front_el.find("./tei:div[@type='titlePage']", namespaces=NS)
        if title_page is None:
            return None

        title = self._text_of_first_p_by_rend(title_page, "title-main") or "Sans titre"
        subtitle = self._text_of_first_p_by_rend(title_page, "title-sub")
        contributors = self._parse_title_page_contributors(front_el)

        extra_lines: list[str] = []
        for p_el in title_page.findall("./tei:p", namespaces=NS):
            rend = p_el.get("rend") or ""
            if rend.startswith("title-"):
                continue
            if rend.startswith("author") or rend.startswith("editor") or rend.startswith("authority_"):
                continue
            text = self._normalized_text(p_el)
            if text:
                extra_lines.append(text)

        return TitlePageBlock(
            title=title,
            subtitle=subtitle,
            contributors=contributors,
            extra_lines=extra_lines,
        )

    def _parse_title_page_contributors(self, front_el: ET._Element) -> list[Contributor]:
        title_page = front_el.find("./tei:div[@type='titlePage']", namespaces=NS)
        if title_page is None:
            return []

        contributors: list[Contributor] = []
        for p_el in title_page.findall("./tei:p", namespaces=NS):
            rend = (p_el.get("rend") or "").strip()
            content = self._normalized_text(p_el)
            if not content:
                continue

            if rend.startswith("author"):
                contributors.append(Contributor(full_name=content, role="author"))
                continue

            if rend.startswith("editor"):
                contributors.append(Contributor(full_name=content, role="editor"))
                continue

            if rend == "authority_affiliation" and contributors:
                last = contributors[-1]
                if not last.affiliation:
                    contributors[-1] = replace(last, affiliation=content)
                continue

            if rend == "authority_mail" and contributors:
                last = contributors[-1]
                if not last.email:
                    contributors[-1] = replace(last, email=content)
                continue

        return contributors


# ----------------------------------------------------------------------
# Parsing des inline et des notes
# ----------------------------------------------------------------------

    def _parse_inline_children(
        self,
        element: ET._Element | None,
        notes_store: dict[str, Footnote],
    ) -> list[InlineNode]:
        if element is None:
            return []

        nodes: list[InlineNode] = []

        if element.text:
            nodes.extend(self._text_node_from_raw(element.text))

        for child in element:
            nodes.extend(self._parse_inline_element(child, notes_store))
            if child.tail:
                nodes.extend(self._text_node_from_raw(child.tail))

        return self._merge_adjacent_text_runs(nodes)

    def _parse_inline_element(
        self,
        element: ET._Element,
        notes_store: dict[str, Footnote],
    ) -> list[InlineNode]:
        local = self._local_name(element)

        if local == "hi":
            children = self._parse_inline_children(element, notes_store)
            return self._apply_hi_rend(element.get("rend"), children)

        if local == "ref":
            return [
                Link(
                    target=element.get("target") or "",
                    children=self._parse_inline_children(element, notes_store),
                    link_type=element.get("type"),
                )
            ]

        if local == "note" and (element.get("place") == "foot" or element.get("type") == "standard"):
            note_id = element.get("{http://www.w3.org/XML/1998/namespace}id") or f"note-{next(self._generated_note_counter)}"
            if note_id not in notes_store:
                notes_store[note_id] = self._parse_footnote(element, note_id)
            return [NoteRef(note_id=note_id)]

        if local == "cit":
            quote = element.find("./tei:quote", namespaces=NS)
            if quote is not None:
                return [InlineQuote(children=self._parse_inline_children(quote, notes_store))]
            return self._parse_inline_children(element, notes_store)

        if local == "quote":
            return [InlineQuote(children=self._parse_inline_children(element, notes_store))]

        if local in {"bibl", "name", "num", "seg", "label", "term", "title"}:
            return self._parse_inline_children(element, notes_store)

        if local == "lb":
            return [TextRun(text=" ")]

        if local == "graphic":
            return []

        # Repli souple : on descend récursivement sans perdre le texte.
        return self._parse_inline_children(element, notes_store)

    def _parse_footnote(self, note_el: ET._Element, note_id: str) -> Footnote:
        note_number = note_el.get("n")
        blocks = self._parse_container_blocks(note_el, notes_store={})
        if not blocks:
            content = self._parse_inline_children(note_el, notes_store={})
            if content:
                blocks = [Paragraph(content=content)]
        return Footnote(note_id=note_id, blocks=blocks, number=note_number)

    def _apply_hi_rend(self, rend: str | None, children: list[InlineNode]) -> list[InlineNode]:
        if not children:
            return []

        rend_tokens = self._normalize_rend_tokens(rend)
        node: InlineNode | None = None

        # Ordre choisi : d'abord les transformations de casse/position,
        # puis emphase typographique. Cela reste simple et stable pour la V1.
        current: list[InlineNode] = children

        if "small-caps" in rend_tokens:
            current = [SmallCaps(children=current)]
        if "sup" in rend_tokens:
            current = [Superscript(children=current)]
        if "sub" in rend_tokens:
            current = [Subscript(children=current)]
        if "bold" in rend_tokens:
            current = [Bold(children=current)]
        if "italic" in rend_tokens:
            current = [Italic(children=current)]

        return current


# ----------------------------------------------------------------------
# Utilitaires de structure TEI
# ----------------------------------------------------------------------

    def _find_structural_child(self, group_el: ET._Element, name: str) -> ET._Element | None:
        direct = group_el.find(f"./tei:{name}", namespaces=NS)
        if direct is not None:
            return direct

        text_child = group_el.find(f"./tei:text/tei:{name}", namespaces=NS)
        if text_child is not None:
            return text_child

        return group_el.find(f".//tei:{name}", namespaces=NS)

    def _map_division_type(self, raw_type: str | None) -> DivisionType:
        if not raw_type:
            return DivisionType.OTHER

        normalized = raw_type.strip().lower()
        mapping = {
            "dedication": DivisionType.DEDICATION,
            "acknowledgments": DivisionType.ACKNOWLEDGMENTS,
            "foreword": DivisionType.FOREWORD,
            "preface": DivisionType.PREFACE,
            "introduction": DivisionType.INTRODUCTION,
            "chapter": DivisionType.CHAPTER,
            "conclusion": DivisionType.CONCLUSION,
            "bibliography": DivisionType.BIBLIOGRAPHY,
            "appendix": DivisionType.APPENDIX,
            "section1": DivisionType.PART,
            "part": DivisionType.PART,
        }
        return mapping.get(normalized, DivisionType.OTHER)

    def _guess_division_title_from_type(self, div_type: DivisionType) -> str | None:
        labels = {
            DivisionType.DEDICATION: "Dédicace",
            DivisionType.ACKNOWLEDGMENTS: "Remerciements",
            DivisionType.FOREWORD: "Avant-propos",
            DivisionType.PREFACE: "Préface",
            DivisionType.INTRODUCTION: "Introduction",
            DivisionType.CONCLUSION: "Conclusion",
            DivisionType.BIBLIOGRAPHY: "Bibliographie",
            DivisionType.APPENDIX: "Annexe",
            DivisionType.PART: "Partie",
        }
        return labels.get(div_type)

    def _is_section_div(self, div_el: ET._Element) -> bool:
        raw_type = div_el.get("type") or ""
        return SECTION_TYPE_RE.match(raw_type) is not None

    def _section_level(self, div_el: ET._Element) -> int:
        raw_type = div_el.get("type") or "section1"
        match = SECTION_TYPE_RE.match(raw_type)
        if not match:
            return 1
        return int(match.group(1))

    def _is_block_quote(self, cit_el: ET._Element) -> bool:
        parent = cit_el.getparent()
        if parent is None:
            return True
        return self._local_name(parent) not in {"p", "item"}


# ----------------------------------------------------------------------
# Utilitaires texte / XML
# ----------------------------------------------------------------------

    def _first_text(self, context: ET._Element | None, xpath: str, default: str | None = None) -> str | None:
        if context is None:
            return default
        node = context.find(xpath, namespaces=NS)
        if node is None:
            return default
        text = self._normalized_text(node)
        return text or default

    def _first_attr(
        self,
        context: ET._Element | None,
        xpath: str,
        attr_name: str,
        default: str | None = None,
    ) -> str | None:
        if context is None:
            return default
        node = context.find(xpath, namespaces=NS)
        if node is None:
            return default
        return node.get(attr_name) or default

    def _text_of_first_p_by_rend(self, parent: ET._Element, rend_value: str) -> str | None:
        for p_el in parent.findall("./tei:div[@type='titlePage']/tei:p", namespaces=NS):
            if (p_el.get("rend") or "").strip() == rend_value:
                text = self._normalized_text(p_el)
                if text:
                    return text
        return None

    def _compose_pers_name(self, pers_name_el: ET._Element | None) -> str:
        if pers_name_el is None:
            return ""
        parts: list[str] = []
        for child in pers_name_el:
            text = self._normalized_text(child)
            if text:
                parts.append(text)
        if parts:
            return " ".join(parts)
        return self._normalized_text(pers_name_el)

    def _normalized_text(self, element: ET._Element | None) -> str:
        if element is None:
            return ""
        raw = "".join(element.itertext())
        return self._normalize_text(raw)

    def _normalize_text(self, text: str | None) -> str:
        if not text:
            return ""
        text = WHITESPACE_RE.sub(" ", text)
        return text.strip()

    def _text_node_from_raw(self, raw: str) -> list[InlineNode]:
        if not raw:
            return []
        cleaned = WHITESPACE_RE.sub(" ", raw)
        if not cleaned.strip():
            return []
        return [TextRun(text=cleaned)]

    def _merge_adjacent_text_runs(self, nodes: list[InlineNode]) -> list[InlineNode]:
        if not nodes:
            return []

        merged: list[InlineNode] = []
        for node in nodes:
            if isinstance(node, TextRun) and merged and isinstance(merged[-1], TextRun):
                merged[-1] = TextRun(text=merged[-1].text + node.text)
            else:
                merged.append(node)
        return merged

    def _normalize_rend_tokens(self, rend: str | None) -> set[str]:
        if not rend:
            return set()
        normalized = rend.lower().replace("_", " ").replace("-", " ")
        tokens = {token.strip() for token in normalized.split() if token.strip()}

        result: set[str] = set()
        if "italic" in tokens:
            result.add("italic")
        if "bold" in tokens or "gras" in tokens:
            result.add("bold")
        if "small" in tokens and "caps" in tokens:
            result.add("small-caps")
        if "sup" in tokens or "exposant" in tokens:
            result.add("sup")
        if "sub" in tokens or "indice" in tokens:
            result.add("sub")
        return result

    def _local_name(self, element: ET._Element) -> str:
        return ET.QName(element).localname


def parse_normalized_tei(xml_path: str | Path) -> Book:
    """Fonction de confort pour parser un TEI normalisé en une ligne."""

    return TeiToModelParser().parse(xml_path)
