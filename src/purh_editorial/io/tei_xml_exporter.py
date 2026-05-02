from __future__ import annotations

from xml.etree import ElementTree as ET

from purh_editorial.model import Document, InlineSpan, InlineStyle, Note

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"


class TeiXmlExporter:
    """Export minimal du modèle interne vers XML-TEI."""

    def export_document(self, document: Document) -> str:
        ET.register_namespace("", TEI_NS)
        root = ET.Element(self._q("TEI"))

        self._build_header(root, document)
        text_el = ET.SubElement(root, self._q("text"))
        body_el = ET.SubElement(text_el, self._q("body"))

        note_by_id = {note.note_id: note for note in document.notes}
        section_stack: list[ET.Element] = []
        for block in document.blocks:
            if block.block_type == "heading":
                level = self._heading_level(block.attributes.get("heading_level"))
                while len(section_stack) >= level:
                    section_stack.pop()
                parent = section_stack[-1] if section_stack else body_el
                div_el = ET.SubElement(parent, self._q("div"), {"type": f"section{level}"})
                head_el = ET.SubElement(div_el, self._q("head"))
                self._append_block_content(head_el, block.text, block.inlines, note_by_id)
                section_stack.append(div_el)
            elif block.block_type == "quote_block":
                parent = section_stack[-1] if section_stack else body_el
                cit_el = ET.SubElement(parent, self._q("cit"))
                quote_el = ET.SubElement(cit_el, self._q("quote"))
                self._append_block_content(quote_el, block.text, block.inlines, note_by_id)
            else:
                parent = section_stack[-1] if section_stack else body_el
                p_el = ET.SubElement(parent, self._q("p"))
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
                note_attrs = {"place": "foot"}
                note_attrs[f"{{{XML_NS}}}id"] = note.note_id
                note_attrs["n"] = note.label if note.label else note.note_id
                note_el = ET.SubElement(parent, self._q("note"), note_attrs)
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
        rend_values = self._rend_values_for_style(span.style)
        if rend_values:
            return ET.SubElement(parent, self._q("hi"), {"rend": " ".join(rend_values)})
        return parent

    @staticmethod
    def _rend_values_for_style(style: InlineStyle) -> list[str]:
        values: list[str] = []
        if style.italic:
            values.append("italic")
        if style.bold:
            values.append("bold")
        if style.small_caps:
            values.append("small-caps")
        if style.superscript:
            values.append("sup")
        if style.subscript:
            values.append("sub")
        return values

    @staticmethod
    def _append_text(target: ET.Element, last_node: ET.Element | None, text: str) -> None:
        # Écriture dans un élément de style (<hi>) : le texte va à l'intérieur.
        if target is not None and target.tag.endswith("}hi"):
            if target.text is None:
                target.text = text
            else:
                target.text += text
            return

        # Texte brut vers l'élément parent.
        if last_node is None:
            # Rien encore écrit : va dans parent.text.
            if target.text is None:
                target.text = text
            else:
                target.text += text
        elif target is last_node:
            # Deux runs bruts consécutifs : last_node == parent.
            # Si l'élément a déjà des enfants, le texte doit aller dans la
            # queue (tail) du dernier enfant — pas dans parent.text qui
            # s'affiche avant tous les enfants en XML.
            children = list(target)
            if children:
                last_child = children[-1]
                if last_child.tail is None:
                    last_child.tail = text
                else:
                    last_child.tail += text
            else:
                if target.text is None:
                    target.text = text
                else:
                    target.text += text
        else:
            # Texte brut après un élément de style : va dans sa queue (tail).
            if last_node.tail is None:
                last_node.tail = text
            else:
                last_node.tail += text

    @staticmethod
    def _q(local_name: str) -> str:
        return f"{{{TEI_NS}}}{local_name}"

    @staticmethod
    def _heading_level(raw_level: object) -> int:
        if isinstance(raw_level, int):
            value = raw_level
        else:
            try:
                value = int(raw_level)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                value = 1
        if value < 1:
            return 1
        if value > 3:
            return 3
        return value
