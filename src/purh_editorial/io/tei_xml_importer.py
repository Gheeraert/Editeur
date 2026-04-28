from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from purh_editorial.io.importer_base import DocumentImporter
from purh_editorial.model import Document, Heading, Metadata, Note, Paragraph, QuoteBlock
from purh_editorial.utils import make_id


class TeiXmlImporter(DocumentImporter):
    supported_extensions = (".xml",)

    def load(self, path: Path) -> Document:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
        ns = self._build_namespace(root)
        metadata = Metadata(
            title=self._find_title(root, ns) or path.stem,
            source_label=path.name,
            language=self._find_language(root, ns),
        )

        blocks = []
        block_index = 1
        body = root.find(".//tei:text/tei:body", ns)
        if body is None:
            body = root
        for node in body.iter():
            local_name = self._local_name(node.tag)
            if local_name not in {"head", "p", "quote"}:
                continue
            text = self._text_without_notes(node).strip()
            if not text:
                continue
            attributes = {"xml_tag": local_name}
            if local_name == "head":
                blocks.append(Heading(block_id=f"h{block_index}", text=text, attributes=attributes))
            elif local_name == "quote":
                blocks.append(QuoteBlock(block_id=f"q{block_index}", text=text, attributes=attributes))
            else:
                blocks.append(Paragraph(block_id=f"p{block_index}", text=text, attributes=attributes))
            block_index += 1

        notes = self._extract_notes(root, ns)
        original_text = "\n\n".join(block.text for block in blocks)
        return Document(
            document_id=make_id("doc"),
            source_path=str(path),
            source_format="xml",
            metadata=metadata,
            blocks=blocks,
            notes=notes,
            original_text=original_text,
        )

    def _find_title(self, root: ET.Element, ns: dict[str, str]) -> str | None:
        candidates = [
            ".//tei:titleStmt/tei:title[@type='main']",
            ".//tei:titleStmt/tei:title",
            ".//tei:title",
        ]
        for xpath in candidates:
            node = root.find(xpath, ns)
            if node is not None:
                text = "".join(node.itertext()).strip()
                if text:
                    return text
        return None

    def _find_language(self, root: ET.Element, ns: dict[str, str]) -> str | None:
        lang = root.find(".//tei:langUsage/tei:language", ns)
        if lang is None:
            return None
        return lang.attrib.get("ident")

    def _extract_notes(self, root: ET.Element, ns: dict[str, str]) -> list[Note]:
        notes: list[Note] = []
        for index, note_node in enumerate(root.findall(".//tei:note", ns), start=1):
            text = "".join(note_node.itertext()).strip()
            if not text:
                continue
            note_id = note_node.attrib.get("{http://www.w3.org/XML/1998/namespace}id", f"note{index}")
            label = note_node.attrib.get("n")
            notes.append(
                Note(
                    note_id=note_id,
                    label=label,
                    text=text,
                    attributes={"xml_tag": "note"},
                )
            )
        return notes

    @staticmethod
    def _build_namespace(root: ET.Element) -> dict[str, str]:
        if root.tag.startswith("{"):
            uri = root.tag.split("}", 1)[0][1:]
            return {"tei": uri}
        return {"tei": ""}

    def _text_without_notes(self, element: ET.Element) -> str:
        chunks: list[str] = []

        def visit(node: ET.Element) -> None:
            if self._local_name(node.tag) == "note":
                return
            if node.text:
                chunks.append(node.text)
            for child in list(node):
                visit(child)
                if child.tail:
                    chunks.append(child.tail)

        visit(element)
        return "".join(chunks)

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.split("}", 1)[-1]
