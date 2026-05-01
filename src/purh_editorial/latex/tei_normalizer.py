from __future__ import annotations

from collections import defaultdict

from lxml import etree

XML_NS = "http://www.w3.org/XML/1998/namespace"
TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}


def normalize_tei_tree(tree: etree._ElementTree) -> None:
    _ensure_xml_ids(tree)
    _merge_adjacent_hi(tree)
    _number_notes(tree)


def _ensure_xml_ids(tree: etree._ElementTree) -> None:
    seen: set[str] = set()
    counters: defaultdict[str, int] = defaultdict(int)
    candidates = tree.xpath(
        "//*[@xml:id] | //tei:div | //tei:head | //tei:p | //tei:note | //tei:list | //tei:item | //tei:listBibl | //tei:bibl",
        namespaces=NS,
    )
    for element in candidates:
        current = element.get(f"{{{XML_NS}}}id")
        if current and current not in seen:
            seen.add(current)
            continue
        base = etree.QName(element).localname
        while True:
            counters[base] += 1
            candidate = f"{base}-{counters[base]:03d}"
            if candidate not in seen:
                break
        element.set(f"{{{XML_NS}}}id", candidate)
        seen.add(candidate)


def _merge_adjacent_hi(tree: etree._ElementTree) -> None:
    changed = True
    while changed:
        changed = False
        for first in list(tree.xpath("//tei:hi[@rend]", namespaces=NS)):
            parent = first.getparent()
            if parent is None:
                continue
            second = first.getnext()
            if second is None:
                continue
            qname = etree.QName(second)
            if qname.namespace != TEI_NS or qname.localname != "hi":
                continue
            if (first.get("rend") or "").strip() != (second.get("rend") or "").strip():
                continue
            if first.tail and first.tail.strip():
                continue
            if len(first):
                first[-1].tail = (first[-1].tail or "") + (first.tail or "") + (second.text or "")
            else:
                first.text = (first.text or "") + (first.tail or "") + (second.text or "")
            for child in list(second):
                second.remove(child)
                first.append(child)
            first.tail = second.tail
            parent.remove(second)
            changed = True
            break


def _number_notes(tree: etree._ElementTree) -> None:
    for idx, note in enumerate(tree.xpath("//tei:note", namespaces=NS), start=1):
        note.set("n", str(idx))
