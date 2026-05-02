from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

from purh_editorial.latex.semantic_model import (
    BibliographyBlock,
    BibliographyItem,
    Bold,
    Book,
    BookMetadata,
    Division,
    DivisionKind,
    FootnoteRef,
    InlineNode,
    Italic,
    ListBlock,
    ListItem,
    Paragraph,
    QuoteBlock,
    SmallCaps,
    Subscript,
    Superscript,
    TableBlock,
    TableCell,
    TableRow,
    TextRun,
    VerseBlock,
    VerseLine,
)

TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}
WS_RE = re.compile(r"\s+")
INLINE_CONTAINER_TAGS = {
    "bibl",
    "biblScope",
    "citedRange",
    "ref",
    "seg",
    "abbr",
    "name",
    "persName",
    "placeName",
    "orgName",
    "date",
    "num",
    "term",
    "foreign",
    "quote",
}


def parse_tei_to_semantic(input_xml: Path) -> Book:
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    tree = etree.parse(str(input_xml), parser)
    return parse_tei_tree_to_semantic(tree, fallback_title=input_xml.stem)


def parse_tei_tree_to_semantic(tree: etree._ElementTree, fallback_title: str = "Sans titre") -> Book:
    root = tree.getroot()
    title = _xpath_text(
        root,
        (
            "normalize-space((.//tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@type='main'])[1])",
            "normalize-space((.//tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title)[1])",
        ),
    ) or fallback_title
    contributors = _collect_contributors(root)
    metadata = BookMetadata(title=title, contributors=contributors)

    divisions: list[Division] = []
    text = root.xpath("./tei:text", namespaces=NS)
    if not text:
        return Book(metadata=metadata, divisions=divisions)
    text_el = text[0]

    front = text_el.xpath("./tei:front", namespaces=NS)
    if front:
        divisions.extend(_parse_container_divisions(front[0], container_kind=DivisionKind.FRONT))

    body = text_el.xpath("./tei:body", namespaces=NS)
    if body:
        divisions.extend(_parse_container_divisions(body[0], container_kind=DivisionKind.OTHER))

    back = text_el.xpath("./tei:back", namespaces=NS)
    if back:
        divisions.extend(_parse_container_divisions(back[0], container_kind=DivisionKind.BACK))

    if not divisions and body:
        blocks = _parse_blocks(body[0])
        if blocks:
            divisions.append(Division(title="Texte", kind=DivisionKind.OTHER, blocks=blocks))

    return Book(metadata=metadata, divisions=divisions)


def _collect_contributors(root: etree._Element) -> list[str]:
    contributors: list[str] = []
    for xpath in (
        ".//tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:author",
        ".//tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:editor",
    ):
        for node in root.xpath(xpath, namespaces=NS):
            text = _normalize("".join(node.itertext()))
            if text:
                contributors.append(text)
    return contributors


def _parse_container_divisions(container: etree._Element, container_kind: DivisionKind) -> list[Division]:
    divisions: list[Division] = []
    divs = container.xpath("./tei:div", namespaces=NS)
    if not divs:
        blocks = _parse_blocks(container)
        if blocks:
            title = _first_child_head_text(container) or container_kind.value.capitalize()
            divisions.append(Division(title=title, kind=container_kind, blocks=blocks))
        return divisions

    for div in divs:
        kind = _map_division_kind(div.get("type"), container_kind)
        title = _first_child_head_text(div) or kind.value.capitalize()
        blocks = _parse_blocks(div)
        divisions.append(Division(title=title, kind=kind, blocks=blocks))
    return divisions


def _map_division_kind(raw_type: str | None, fallback: DivisionKind) -> DivisionKind:
    value = (raw_type or "").strip().lower()
    mapping = {
        "introduction": DivisionKind.INTRODUCTION,
        "chapter": DivisionKind.CHAPTER,
        "conclusion": DivisionKind.CONCLUSION,
        "bibliography": DivisionKind.BIBLIOGRAPHY,
        "appendix": DivisionKind.APPENDIX,
    }
    return mapping.get(value, fallback if fallback != DivisionKind.OTHER else DivisionKind.OTHER)


def _first_child_head_text(node: etree._Element) -> str | None:
    heads = node.xpath("./tei:head[1]", namespaces=NS)
    if not heads:
        return None
    return _normalize("".join(heads[0].itertext())) or None


def _parse_blocks(parent: etree._Element) -> list:
    blocks: list = []
    children = list(parent)
    i = 0
    while i < len(children):
        child = children[i]
        local = etree.QName(child).localname
        if local == "head":
            i += 1
            continue
        if local == "div":
            blocks.extend(_parse_blocks(child))
            i += 1
            continue
        if local == "p":
            content = _parse_inline_children(child)
            if content:
                blocks.append(Paragraph(content=content))
            i += 1
            continue
        if local == "cit":
            blocks.append(_parse_cit_block(child))
            i += 1
            continue
        if local == "quote":
            content = _parse_inline_children(child)
            blocks.append(QuoteBlock(paragraphs=[Paragraph(content=content)]))
            i += 1
            continue
        if local == "lg":
            blocks.append(_parse_verse_block(child))
            i += 1
            continue
        if local == "list":
            blocks.append(_parse_list_block(child))
            i += 1
            continue
        if local == "listBibl":
            blocks.append(_parse_list_bibl_block(child))
            i += 1
            continue
        if local == "table":
            blocks.append(_parse_table_block(child))
            i += 1
            continue
        if local == "bibl":
            items: list[BibliographyItem] = []
            while i < len(children) and etree.QName(children[i]).localname == "bibl":
                items.append(BibliographyItem(content=_parse_inline_children(children[i])))
                i += 1
            blocks.append(BibliographyBlock(items=items))
            continue
        i += 1
    return blocks


def _parse_cit_block(cit: etree._Element) -> QuoteBlock:
    quote_nodes = cit.xpath("./tei:quote", namespaces=NS)
    paragraphs: list[Paragraph] = []
    if quote_nodes:
        quote = quote_nodes[0]
        quote_ps = quote.xpath("./tei:p", namespaces=NS)
        if quote_ps:
            for p in quote_ps:
                content = _parse_inline_children(p)
                if content:
                    paragraphs.append(Paragraph(content=content))
        else:
            content = _parse_inline_children(quote)
            if content:
                paragraphs.append(Paragraph(content=content))
    return QuoteBlock(paragraphs=paragraphs)


def _parse_verse_block(lg: etree._Element) -> VerseBlock:
    lines: list[VerseLine] = []
    for line in lg.xpath("./tei:l", namespaces=NS):
        content = _parse_inline_children(line)
        lines.append(VerseLine(content=content))
    return VerseBlock(lines=lines)


def _parse_list_block(list_el: etree._Element) -> ListBlock:
    ordered = (list_el.get("type") or "").strip().lower() == "ordered"
    items: list[ListItem] = []
    for item in list_el.xpath("./tei:item", namespaces=NS):
        content = _parse_inline_children(item)
        items.append(ListItem(content=content))
    return ListBlock(ordered=ordered, items=items)


def _parse_list_bibl_block(list_bibl: etree._Element) -> BibliographyBlock:
    items: list[BibliographyItem] = []
    for bibl in list_bibl.xpath("./tei:bibl", namespaces=NS):
        items.append(BibliographyItem(content=_parse_inline_children(bibl)))
    return BibliographyBlock(items=items)


def _parse_table_block(table_el: etree._Element) -> TableBlock:
    # Complex tables (nested tables) are intentionally downgraded to a controlled
    # fallback comment to avoid exploding content into unrelated paragraphs.
    if table_el.xpath(".//tei:table", namespaces=NS):
        return TableBlock(
            rows=[],
            export_comment="table_export_fallback nested_table_not_supported",
        )

    rows: list[TableRow] = []
    row_nodes = table_el.xpath("./tei:row", namespaces=NS)
    for row_el in row_nodes:
        cells: list[TableCell] = []
        for cell_el in row_el.xpath("./tei:cell", namespaces=NS):
            paragraphs: list[Paragraph] = []
            p_nodes = cell_el.xpath("./tei:p", namespaces=NS)
            if p_nodes:
                for p_node in p_nodes:
                    paragraphs.append(Paragraph(content=_parse_inline_children(p_node)))
            else:
                paragraphs.append(Paragraph(content=_parse_inline_children(cell_el)))
            cells.append(TableCell(paragraphs=paragraphs))
        rows.append(TableRow(cells=cells))

    return TableBlock(rows=rows)


def _parse_inline_children(element: etree._Element) -> list[InlineNode]:
    nodes: list[InlineNode] = []
    if element.text:
        text = _normalize_inline_text(element.text)
        if text.strip():
            nodes.append(TextRun(text=text))
    for child in list(element):
        nodes.extend(_parse_inline_element(child))
        if child.tail:
            tail = _normalize_inline_text(child.tail)
            if tail.strip():
                nodes.append(TextRun(text=tail))
    return _merge_text_runs(nodes)


def _parse_inline_element(element: etree._Element) -> list[InlineNode]:
    local = etree.QName(element).localname
    if local == "hi":
        children = _parse_inline_children(element)
        rend = (element.get("rend") or "").lower()
        tokens = set(rend.replace("-", " ").replace("_", " ").split())
        if "italic" in tokens:
            return [Italic(children=children)]
        if "bold" in tokens or "gras" in tokens:
            return [Bold(children=children)]
        if "small" in tokens and "caps" in tokens:
            return [SmallCaps(children=children)]
        if "sup" in tokens:
            return [Superscript(children=children)]
        if "sub" in tokens:
            return [Subscript(children=children)]
        return children
    if local == "title":
        children = _parse_inline_children(element)
        rend = (element.get("rend") or "").lower()
        tokens = set(rend.replace("-", " ").replace("_", " ").split())
        if "bold" in tokens or "gras" in tokens:
            return [Bold(children=children)]
        if "small" in tokens and "caps" in tokens:
            return [SmallCaps(children=children)]
        if "sup" in tokens:
            return [Superscript(children=children)]
        if "sub" in tokens:
            return [Subscript(children=children)]
        # Default behavior for inline title in bibliographic notes.
        return [Italic(children=children)]
    if local == "note":
        content = _trim_boundary_text_runs(_parse_inline_children(element))
        return [FootnoteRef(content=content)] if content else []
    if local == "ptr":
        target = (element.get("target") or "").strip()
        return [TextRun(text=target)] if target else []
    if local in INLINE_CONTAINER_TAGS:
        return _parse_inline_children(element)
    return _parse_inline_children(element)


def _merge_text_runs(nodes: list[InlineNode]) -> list[InlineNode]:
    merged: list[InlineNode] = []
    for node in nodes:
        if isinstance(node, TextRun) and merged and isinstance(merged[-1], TextRun):
            merged[-1] = TextRun(text=f"{merged[-1].text}{node.text}")
        else:
            merged.append(node)
    return merged


def _trim_boundary_text_runs(nodes: list[InlineNode]) -> list[InlineNode]:
    if not nodes:
        return nodes
    trimmed = list(nodes)
    first = trimmed[0]
    if isinstance(first, TextRun):
        first_text = first.text.lstrip()
        if first_text:
            trimmed[0] = TextRun(text=first_text)
        else:
            trimmed = trimmed[1:]
    if not trimmed:
        return []
    last = trimmed[-1]
    if isinstance(last, TextRun):
        last_text = last.text.rstrip()
        if last_text:
            trimmed[-1] = TextRun(text=last_text)
        else:
            trimmed = trimmed[:-1]
    return trimmed


def _normalize(text: str) -> str:
    return WS_RE.sub(" ", text).strip()


def _normalize_inline_text(text: str) -> str:
    # Preserve leading/trailing spaces around inline tags while collapsing
    # excessive whitespace runs to a single space.
    return WS_RE.sub(" ", text)


def _xpath_text(node: etree._Element, expressions: tuple[str, ...]) -> str:
    for expression in expressions:
        value = node.xpath(expression, namespaces=NS)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""
