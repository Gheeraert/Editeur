from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET

from purh_editorial.latex.semantic_model import (
    Bold,
    Book,
    BookMetadata,
    Division,
    FootnoteRef,
    InlineNode,
    Italic,
    Paragraph,
    SmallCaps,
    Subscript,
    Superscript,
    TextRun,
)

XML_NS = "http://www.w3.org/XML/1998/namespace"
WS_RE = re.compile(r"\s+")


def parse_tei_to_semantic(input_xml: Path) -> Book:
    root = ET.fromstring(input_xml.read_text(encoding="utf-8"))
    ns = _build_ns(root)

    title = _find_text(
        root,
        ns,
        (
            ".//tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[@type='main']",
            ".//tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title",
        ),
    ) or input_xml.stem
    contributors = _collect_contributors(root, ns)
    metadata = BookMetadata(title=title, contributors=contributors)

    body = root.find(".//tei:text/tei:body", ns)
    if body is None:
        return Book(metadata=metadata, divisions=[])

    divisions: list[Division] = []
    for div in body.findall("./tei:div", ns):
        div_title = _find_text(div, ns, ("./tei:head",)) or "Section"
        paragraphs: list[Paragraph] = []
        for p in div.findall(".//tei:p", ns):
            content = _parse_inline_children(p, ns)
            if content:
                paragraphs.append(Paragraph(content=content))
        if paragraphs:
            divisions.append(Division(title=div_title, paragraphs=paragraphs))

    if not divisions:
        paragraphs = []
        for p in body.findall(".//tei:p", ns):
            content = _parse_inline_children(p, ns)
            if content:
                paragraphs.append(Paragraph(content=content))
        if paragraphs:
            divisions.append(Division(title="Texte", paragraphs=paragraphs))

    return Book(metadata=metadata, divisions=divisions)


def _build_ns(root: ET.Element) -> dict[str, str]:
    if root.tag.startswith("{"):
        return {"tei": root.tag.split("}", 1)[0][1:]}
    return {"tei": ""}


def _find_text(context: ET.Element, ns: dict[str, str], xpaths: tuple[str, ...]) -> str | None:
    for xpath in xpaths:
        node = context.find(xpath, ns)
        if node is None:
            continue
        value = _normalize("".join(node.itertext()))
        if value:
            return value
    return None


def _collect_contributors(root: ET.Element, ns: dict[str, str]) -> list[str]:
    contributors: list[str] = []
    for xpath in (
        ".//tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:author",
        ".//tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:editor",
    ):
        for node in root.findall(xpath, ns):
            text = _normalize("".join(node.itertext()))
            if text:
                contributors.append(text)
    return contributors


def _parse_inline_children(element: ET.Element, ns: dict[str, str]) -> list[InlineNode]:
    nodes: list[InlineNode] = []
    if element.text:
        text = _normalize(element.text)
        if text:
            nodes.append(TextRun(text=text))

    for child in list(element):
        nodes.extend(_parse_inline_element(child, ns))
        if child.tail:
            tail = _normalize(child.tail)
            if tail:
                nodes.append(TextRun(text=tail))

    return _merge_text_runs(nodes)


def _parse_inline_element(element: ET.Element, ns: dict[str, str]) -> list[InlineNode]:
    local = _local_name(element.tag)
    if local == "hi":
        children = _parse_inline_children(element, ns)
        rend = (element.attrib.get("rend") or "").lower()
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

    if local == "note":
        note_content = _parse_inline_children(element, ns)
        return [FootnoteRef(content=note_content)] if note_content else []

    return _parse_inline_children(element, ns)


def _merge_text_runs(nodes: list[InlineNode]) -> list[InlineNode]:
    merged: list[InlineNode] = []
    for node in nodes:
        if isinstance(node, TextRun) and merged and isinstance(merged[-1], TextRun):
            merged[-1] = TextRun(text=f"{merged[-1].text} {node.text}".strip())
            continue
        merged.append(node)
    return merged


def _normalize(text: str) -> str:
    return WS_RE.sub(" ", text).strip()


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag
