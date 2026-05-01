from __future__ import annotations

from pathlib import Path

from lxml import etree


def load_tei_tree(input_xml: Path) -> etree._ElementTree:
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    return etree.parse(str(input_xml), parser)
