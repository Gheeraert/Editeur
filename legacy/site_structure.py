from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from lxml import etree

from .utils import NSMAP, slugify, short_text, xml_id

PAGE_TYPES = {
    "chapter",
    "article",
    "introduction",
    "conclusion",
    "bibliography",
    "foreword",
    "acknowledgments",
    "preface",
    "postface",
    "appendix",
    "dedication",
    "afterword",
}


@dataclass(slots=True)
class AuthorEntry:
    name: str
    affiliations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SiteMeta:
    title: str
    subtitle: str = ""
    creators: list[str] = field(default_factory=list)
    creator_role_label: str = "Responsabilité du volume"
    publisher: str = ""
    publication_year: str = ""
    doi: str = ""
    site_url: str = ""
    collection_title: str = ""
    collection_number: str = ""
    collection_issn: str = ""
    isbn: str = ""
    issn: str = ""


@dataclass(slots=True)
class PageDef:
    node_id: str
    file_name: str
    title: str
    subtitle: str = ""
    authors: list[str] = field(default_factory=list)
    author_entries: list[AuthorEntry] = field(default_factory=list)
    group_type: str = "chapter"
    page_kind: str = "chapter"
    section_chain: list[str] = field(default_factory=list)
    sequence: int = 0


@dataclass(slots=True)
class NavItem:
    title: str
    href: str | None = None
    children: list["NavItem"] = field(default_factory=list)
    is_current: bool = False
    page_kind: str = ""


class SiteStructureBuilder:
    """Construit l'arborescence du livre et les pages à générer."""

    def build(self, tree: etree._ElementTree) -> tuple[SiteMeta, list[PageDef], list[NavItem]]:
        site_meta = self._extract_site_meta(tree)
        root_group = self._find_root_group(tree)
        if root_group is None:
            return site_meta, [], []

        pages: list[PageDef] = []
        nav: list[NavItem] = []
        slug_counts: dict[str, int] = {}
        sequence = 0
        for child in self._iter_group_children(root_group):
            nav_item, new_pages, sequence = self._walk_group(
                child,
                slug_counts=slug_counts,
                sequence=sequence,
                section_chain=[],
            )
            if nav_item is not None:
                nav.append(nav_item)
            pages.extend(new_pages)
        return site_meta, pages, nav

    def build_nav_for_page(self, nav: Iterable[NavItem], current_file_name: str | None) -> list[NavItem]:
        return [self._clone_nav_item(item, current_file_name) for item in nav]

    def _clone_nav_item(self, item: NavItem, current_file_name: str | None) -> NavItem:
        cloned = NavItem(
            title=item.title,
            href=item.href,
            page_kind=item.page_kind,
            is_current=item.href == current_file_name,
            children=[self._clone_nav_item(child, current_file_name) for child in item.children],
        )
        if any(child.is_current for child in cloned.children):
            cloned.is_current = True
        return cloned

    def _extract_site_meta(self, tree: etree._ElementTree) -> SiteMeta:
        title = tree.xpath(
            "normalize-space((/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@type='main'])[1])",
            namespaces=NSMAP,
        )
        subtitle = tree.xpath(
            "normalize-space((/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@type='sub'])[1])",
            namespaces=NSMAP,
        )

        editor_nodes = tree.xpath(
            "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:editor",
            namespaces=NSMAP,
        )
        director_author_nodes = tree.xpath(
            "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:author[translate(normalize-space(@role), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='pbd']",
            namespaces=NSMAP,
        )
        author_nodes = tree.xpath(
            "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:author",
            namespaces=NSMAP,
        )

        if editor_nodes:
            creator_nodes = editor_nodes
            creator_role_label = "Dir."
        elif director_author_nodes:
            creator_nodes = director_author_nodes
            creator_role_label = "Dir."
        else:
            creator_nodes = author_nodes
            creators_preview = [self._personish_text(node) for node in creator_nodes if self._personish_text(node)]
            if len(creators_preview) == 1:
                creator_role_label = "Auteur·rice du volume"
            else:
                creator_role_label = "Responsabilité du volume"

        creators = [self._personish_text(node) for node in creator_nodes if self._personish_text(node)]

        publisher = tree.xpath(
            "normalize-space((/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt//tei:publisher[normalize-space(.) != ''])[1])",
            namespaces=NSMAP,
        )
        publication_date_raw = tree.xpath(
            "normalize-space((/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt//tei:date[@type='publishing']/@when)[1])",
            namespaces=NSMAP,
        )
        if not publication_date_raw:
            publication_date_raw = tree.xpath(
                "normalize-space((/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt//tei:date[@type='publishing'][normalize-space(.) != ''])[1])",
                namespaces=NSMAP,
            )
        if not publication_date_raw:
            publication_date_raw = tree.xpath(
                "normalize-space((/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt//tei:date/@when)[1])",
                namespaces=NSMAP,
            )
        if not publication_date_raw:
            publication_date_raw = tree.xpath(
                "normalize-space((/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt//tei:date[normalize-space(.) != ''])[1])",
                namespaces=NSMAP,
            )
        publication_year = self._extract_year(publication_date_raw)

        doi = tree.xpath(
            "normalize-space((/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt//tei:idno[translate(@type, 'doi', 'DOI')='DOI' and normalize-space(.) != ''])[1])",
            namespaces=NSMAP,
        )
        if not doi:
            doi = tree.xpath(
                "normalize-space((/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt//tei:ref[translate(@type, 'doi', 'DOI')='DOI' and normalize-space(@target) != '']/@target)[1])",
                namespaces=NSMAP,
            )
        doi = "" if doi in {"#", "-", "##"} else doi

        site_url = tree.xpath(
            "normalize-space((/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt/tei:ab[@type='digital_online']//tei:ref[@type='site' and normalize-space(@target) != '']/@target)[1])",
            namespaces=NSMAP,
        )
        if not site_url:
            site_url = tree.xpath(
                "normalize-space((/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt//tei:ref[@type='site' and normalize-space(@target) != '']/@target)[1])",
                namespaces=NSMAP,
            )
        site_url = "" if site_url in {"#", "-", "##"} else site_url

        collection_title = self._first_nonempty(
            tree,
            [
                "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:seriesStmt/tei:title[@level='s'][1]",
                "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:seriesStmt/tei:title[1]",
                "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@type='collection'][1]",
            ],
        )
        collection_number_raw = self._first_nonempty(
            tree,
            [
                "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:seriesStmt/tei:biblScope[@unit='volume'][1]",
                "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:seriesStmt/tei:biblScope[@unit='number'][1]",
                "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:seriesStmt/tei:biblScope[@unit='issue'][1]",
            ],
        )
        collection_number = self._normalize_collection_number(collection_number_raw)
        collection_issn = self._extract_identifier(
            tree,
            [
                "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:seriesStmt//tei:idno[@type='ISSN'][1]",
            ],
        )
        isbn = self._extract_identifier(
            tree,
            [
                "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt/tei:ab[@type='book']//tei:idno[@type='ISBN-13'][1]",
                "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt/tei:ab[@type='book']//tei:idno[@type='ISBN'][1]",
            ],
        )
        issn = self._extract_identifier(
            tree,
            [
                "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:publicationStmt/tei:ab[@type='book']//tei:idno[@type='ISSN'][1]",
                "/tei:TEI/tei:teiHeader/tei:fileDesc/tei:seriesStmt//tei:idno[@type='ISSN'][1]",
            ],
        )

        return SiteMeta(
            title=title or "Livre PURH",
            subtitle=subtitle,
            creators=creators,
            creator_role_label=creator_role_label,
            publisher=publisher,
            publication_year=publication_year,
            doi=doi,
            site_url=site_url,
            collection_title=collection_title,
            collection_number=collection_number,
            collection_issn=collection_issn,
            isbn=isbn,
            issn=issn,
        )

    def _first_nonempty(self, tree: etree._ElementTree, xpaths: list[str]) -> str:
        for xpath in xpaths:
            value = tree.xpath(f"normalize-space(({xpath}) )", namespaces=NSMAP)
            if isinstance(value, list):
                value = " ".join(str(v) for v in value).strip()
            if value:
                return str(value).strip()
        return ""

    def _extract_identifier(self, tree: etree._ElementTree, xpaths: list[str]) -> str:
        value = self._first_nonempty(tree, xpaths)
        return "" if value in {"#", "-", "##"} else value

    def _normalize_collection_number(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            return ""
        match = re.search(r"(\d+)", value)
        return match.group(1) if match else value

    def _personish_text(self, node: etree._Element) -> str:
        text = " ".join(node.xpath('.//tei:persName//text() | .//tei:name//text()', namespaces=NSMAP)).strip()
        if not text:
            text = " ".join(node.xpath('.//text()')).strip()
        return short_text(text, 200) if text else ""

    def _extract_year(self, value: str) -> str:
        match = re.search(r"(1\d{3}|20\d{2}|21\d{2})", value or "")
        return match.group(1) if match else (value or "")

    def _find_root_group(self, tree: etree._ElementTree) -> etree._Element | None:
        groups = tree.xpath("/tei:TEI/tei:text/tei:group[@type='book'][1]", namespaces=NSMAP)
        if groups:
            return groups[0]
        groups = tree.xpath("/tei:TEI/tei:text/tei:group[1]", namespaces=NSMAP)
        return groups[0] if groups else None

    def _iter_group_children(self, group: etree._Element) -> list[etree._Element]:
        return [child for child in group if isinstance(child.tag, str) and etree.QName(child).localname == "group"]

    def _walk_group(
        self,
        group: etree._Element,
        slug_counts: dict[str, int],
        sequence: int,
        section_chain: list[str],
    ) -> tuple[NavItem | None, list[PageDef], int]:
        if self._is_page_group(group):
            sequence += 1
            page = self._make_page(group, slug_counts, sequence, section_chain)
            nav_item = NavItem(title=page.title, href=page.file_name, page_kind=page.page_kind)
            return nav_item, [page], sequence

        title = self._group_title(group)
        current_section_chain = [*section_chain, title] if title else list(section_chain)
        nav_item = NavItem(title=title or self._label_for_group(group.get("type", "")), page_kind=group.get("type", ""))
        pages: list[PageDef] = []
        for child in self._iter_group_children(group):
            child_nav, child_pages, sequence = self._walk_group(
                child,
                slug_counts=slug_counts,
                sequence=sequence,
                section_chain=current_section_chain,
            )
            if child_nav is not None:
                nav_item.children.append(child_nav)
            pages.extend(child_pages)
        if not nav_item.children:
            return None, pages, sequence
        return nav_item, pages, sequence

    def _is_page_group(self, group: etree._Element) -> bool:
        group_type = group.get("type", "")
        return group_type in PAGE_TYPES or (group_type == "chapter" and bool(group.get("data-page-authors")))

    def _make_page(
        self,
        group: etree._Element,
        slug_counts: dict[str, int],
        sequence: int,
        section_chain: list[str],
    ) -> PageDef:
        title = self._group_title(group) or self._label_for_group(group.get("type", ""))
        subtitle = (group.get("data-page-subtitle") or "").strip()
        author_entries = self._split_author_entries(group.get("data-page-authors", ""))
        authors = [entry.name for entry in author_entries]
        group_type = group.get("type", "chapter")
        page_kind = "article" if authors and group_type == "chapter" else group_type
        if page_kind not in {"article", "chapter"}:
            page_kind = "article" if authors else page_kind
        base_slug = slugify(title, fallback=group_type or "page")
        count = slug_counts.get(base_slug, 0) + 1
        slug_counts[base_slug] = count
        suffix = f"-{count}" if count > 1 else ""
        file_name = f"{sequence:02d}-{base_slug}{suffix}.html"
        return PageDef(
            node_id=xml_id(group) or "",
            file_name=file_name,
            title=title,
            subtitle=subtitle,
            authors=authors,
            author_entries=author_entries,
            group_type=group_type,
            page_kind=page_kind,
            section_chain=section_chain,
            sequence=sequence,
        )

    def _group_title(self, group: etree._Element) -> str:
        for attr in ("data-page-title", "data-article-title", "n"):
            value = (group.get(attr) or "").strip()
            if value:
                return value
        head_text = " ".join(group.xpath("./tei:head[1]//text()", namespaces=NSMAP)).strip()
        if head_text:
            return short_text(head_text, 300)
        text_head = " ".join(group.xpath("./tei:body/tei:div[1]/tei:head[1]//text()", namespaces=NSMAP)).strip()
        return short_text(text_head, 300)

    def _split_author_entries(self, value: str) -> list[AuthorEntry]:
        entries: list[AuthorEntry] = []
        for raw_entry in value.split("||"):
            raw_entry = raw_entry.strip()
            if not raw_entry:
                continue
            parts = [part.strip() for part in raw_entry.split("@@")]
            name = parts[0] if parts else raw_entry
            affiliations = [part for part in parts[1:] if part]
            entries.append(AuthorEntry(name=name, affiliations=affiliations))
        return entries

    def _label_for_group(self, group_type: str) -> str:
        labels = {
            "dedication": "Dédicace",
            "introduction": "Introduction",
            "chapter": "Chapitre",
            "conclusion": "Conclusion",
            "bibliography": "Bibliographie",
            "foreword": "Avant-propos",
            "acknowledgments": "Remerciements",
            "preface": "Préface",
            "postface": "Postface",
            "appendix": "Annexe",
            "part": "Partie",
            "section": "Section",
            "section1": "Section",
            "section2": "Sous-section",
            "section3": "Sous-section",
        }
        return labels.get(group_type, group_type or "Section")
