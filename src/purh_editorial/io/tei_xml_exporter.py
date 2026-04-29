from __future__ import annotations

from xml.etree import ElementTree as ET

from purh_editorial.model import Document, InlineSpan, Note

TEI_NS = "http://www.tei-c.org/ns/1.0"


class TeiXmlExporter:
    """Export minimal du modèle interne vers XML-TEI."""

    def export_document(self, document: Document) -> str:
        ET.register_namespace("", TEI_NS)
        root = ET.Element(self._q("TEI"))

        self._build_header(root, document)
        text_el = ET.SubElement(root, self._q("text"))
        body_el = ET.SubElement(text_el, self._q("body"))

        note_by_id = {note.note_id: note for note in document.notes}

        for block in document.blocks:
            if block.block_type == "heading":
                container = ET.SubElement(body_el, self._q("head"))
                self._append_block_content(container, block.text, block.inlines, note_by_id)
            elif block.block_type == "quote_block":
                quote_el = ET.SubElement(body_el, self._q("quote"))
                p_el = ET.SubElement(quote_el, self._q("p"))
                self._append_block_content(p_el, block.text, block.inlines, note_by_id)
            else:
                p_el = ET.SubElement(body_el, self._q("p"))
                self._append_block_content(p_el, block.text, block.inlines, note_by_id)

        return ET.tostring(root, encoding="unicode")

    def _build_header(self, root: ET.Element, document: Document) -> None:
        tei_header = ET.SubElement(root, self._q("teiHeader"))
        file_desc = ET.SubElement(tei_header, self._q("fileDesc"))

        title_stmt = ET.SubElement(file_desc, self._q("titleStmt"))
        title_el = ET.SubElement(title_stmt, self._q("title"))
        title_el.text = document.metadata.title or "Untitled"

        publication_stmt = ET.SubElement(file_desc, self._q("publicationStmt"))
        p_pub = ET.SubElement(publication_stmt, self._q("p"))
        p_pub.text = "Publication metadata not set."

        source_desc = ET.SubElement(file_desc, self._q("sourceDesc"))
        p_src = ET.SubElement(source_desc, self._q("p"))
        p_src.text = document.source_path or "Unknown source"

    def _append_block_content(
        self,
        parent: ET.Element,
        fallback_text: str,
        inlines: list[InlineSpan],
        note_by_id: dict[str, Note],
    ) -> None:
        if not inlines:
            parent.text = fallback_text
            return
        self._append_inline_sequence(parent, inlines, note_by_id)

    def _append_inline_sequence(
        self,
        parent: ET.Element,
        inlines: list[InlineSpan],
        note_by_id: dict[str, Note],
    ) -> None:
        last_node: ET.Element | None = None
        for span in inlines:
            if span.kind == "note_call" and span.note_ref:
                note = note_by_id.get(span.note_ref)
                if note is None:
                    # Comportement conservateur: ignorer sans planter.
                    continue
                note_el = ET.SubElement(parent, self._q("note"), {"place": "foot"})
                self._append_note_content(note_el, note, note_by_id)
                last_node = note_el
                continue

            text = span.text or ""
            if not text:
                continue
            target = self._wrap_with_style_if_needed(parent, span)
            self._append_text(target, last_node, text)
            last_node = target

    def _append_note_content(
        self,
        note_el: ET.Element,
        note: Note,
        note_by_id: dict[str, Note],
    ) -> None:
        if note.inlines:
            self._append_inline_sequence(note_el, note.inlines, note_by_id)
        else:
            note_el.text = note.text

    def _wrap_with_style_if_needed(self, parent: ET.Element, span: InlineSpan) -> ET.Element:
        style = span.style
        # Minimalisme: on privilégie un seul rendu à la fois pour éviter une complexité
        # de nesting dans cette première passe.
        if style.italic:
            return ET.SubElement(parent, self._q("hi"), {"rend": "italic"})
        if style.bold:
            return ET.SubElement(parent, self._q("hi"), {"rend": "bold"})
        if style.small_caps:
            return ET.SubElement(parent, self._q("hi"), {"rend": "small-caps"})
        if style.superscript:
            return ET.SubElement(parent, self._q("hi"), {"rend": "sup"})
        if style.subscript:
            return ET.SubElement(parent, self._q("hi"), {"rend": "sub"})
        return parent

    @staticmethod
    def _append_text(target: ET.Element, last_node: ET.Element | None, text: str) -> None:
        if target is last_node or target is not None and target.tag.endswith("}hi"):
            if target.text is None:
                target.text = text
            else:
                target.text += text
            return

        if last_node is None:
            if target.text is None:
                target.text = text
            else:
                target.text += text
        else:
            if last_node.tail is None:
                last_node.tail = text
            else:
                last_node.tail += text

    @staticmethod
    def _q(local_name: str) -> str:
        return f"{{{TEI_NS}}}{local_name}"

