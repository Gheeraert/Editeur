from __future__ import annotations

from xml.etree import ElementTree as ET

from purh_editorial.model import Document, InlineSpan, InlineStyle, Note
from purh_editorial.model.semantics import (
    extract_verse_lines,
    is_canonical_poetry_block,
    read_block_semantics,
)

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


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
        table_diagnostics: list[dict[str, object]] = []
        active_poetry_group_id: str | None = None
        active_poetry_lg: ET.Element | None = None
        for block in document.blocks:
            semantics = read_block_semantics(block, allow_legacy_inference=False)
            is_poetry_block = is_canonical_poetry_block(block)
            poetry_group_id = (semantics.poetry_group_id or "").strip()
            effective_group_id = poetry_group_id or (block.block_id if is_poetry_block else "")
            if not is_poetry_block:
                active_poetry_group_id = None
                active_poetry_lg = None

            if block.block_type == "heading":
                level = self._heading_level(block.attributes.get("heading_level"))
                while len(section_stack) >= level:
                    section_stack.pop()
                parent = section_stack[-1] if section_stack else body_el
                div_el = ET.SubElement(parent, self._q("div"), {"type": f"section{level}"})
                head_el = ET.SubElement(div_el, self._q("head"))
                self._append_block_content(head_el, block.text, block.inlines, note_by_id)
                section_stack.append(div_el)
            elif is_poetry_block:
                parent = section_stack[-1] if section_stack else body_el
                if active_poetry_group_id != effective_group_id or active_poetry_lg is None:
                    cit_el = ET.SubElement(parent, self._q("cit"))
                    quote_el = ET.SubElement(cit_el, self._q("quote"))
                    active_poetry_lg = ET.SubElement(quote_el, self._q("lg"))
                    active_poetry_group_id = effective_group_id
                if block.inlines:
                    inline_lines = self._split_inlines_on_line_break(block.inlines)
                    if not inline_lines:
                        l_el = ET.SubElement(active_poetry_lg, self._q("l"))
                        self._append_block_content(l_el, block.text, block.inlines, note_by_id)
                    for line_inlines in inline_lines:
                        l_el = ET.SubElement(active_poetry_lg, self._q("l"))
                        self._append_inline_sequence(l_el, line_inlines, note_by_id)
                else:
                    verse_lines = semantics.lines or extract_verse_lines(block)
                    if not verse_lines:
                        l_el = ET.SubElement(active_poetry_lg, self._q("l"))
                        self._append_block_content(l_el, block.text, block.inlines, note_by_id)
                    else:
                        for verse_line in verse_lines:
                            l_el = ET.SubElement(active_poetry_lg, self._q("l"))
                            l_el.text = verse_line
            elif block.block_type == "quote_block":
                parent = section_stack[-1] if section_stack else body_el
                cit_el = ET.SubElement(parent, self._q("cit"))
                quote_el = ET.SubElement(cit_el, self._q("quote"))
                self._append_block_content(quote_el, block.text, block.inlines, note_by_id)
            elif block.block_type == "table":
                parent = section_stack[-1] if section_stack else body_el
                table_diag = self._append_table_block(parent, block)
                table_diagnostics.append(table_diag)
            else:
                parent = section_stack[-1] if section_stack else body_el
                p_el = ET.SubElement(parent, self._q("p"))
                self._append_block_content(p_el, block.text, block.inlines, note_by_id)

        annotations = document.annotations
        annotations["tei_table_diagnostics"] = table_diagnostics
        annotations["tei_table_exported_count"] = sum(
            1 for item in table_diagnostics if item.get("code") == "table_exported_to_tei"
        )
        annotations["tei_table_not_exported_count"] = sum(
            1 for item in table_diagnostics if item.get("code") != "table_exported_to_tei"
        )
        return ET.tostring(root, encoding="unicode")

    def _append_table_block(self, parent: ET.Element, block) -> dict[str, object]:
        raw_ooxml = str(block.attributes.get("table_ooxml", "") or "").strip()
        if not raw_ooxml:
            ET.SubElement(parent, self._q("p")).text = "[Table not exported: missing OOXML]"
            return {
                "code": "table_not_exported_to_tei",
                "block_id": block.block_id,
                "reason": "missing_table_ooxml",
                "rows": 0,
                "cells": 0,
            }

        try:
            table_root = ET.fromstring(raw_ooxml)
        except ET.ParseError:
            ET.SubElement(parent, self._q("p")).text = "[Table not exported: invalid OOXML]"
            return {
                "code": "table_not_exported_to_tei",
                "block_id": block.block_id,
                "reason": "invalid_table_ooxml",
                "rows": 0,
                "cells": 0,
            }

        tr_nodes = table_root.findall(f"./{{{WORD_NS}}}tr")
        if not tr_nodes:
            ET.SubElement(parent, self._q("p")).text = "[Table not exported: no rows]"
            return {
                "code": "table_export_fallback",
                "block_id": block.block_id,
                "reason": "no_rows",
                "rows": 0,
                "cells": 0,
            }

        table_el = ET.SubElement(parent, self._q("table"))
        row_count = 0
        cell_count = 0
        for tr in tr_nodes:
            row_el = ET.SubElement(table_el, self._q("row"))
            row_count += 1
            tc_nodes = tr.findall(f"./{{{WORD_NS}}}tc")
            for tc in tc_nodes:
                cell_el = ET.SubElement(row_el, self._q("cell"))
                cell_count += 1
                text_parts: list[str] = []
                for p_node in tc.findall(f"./{{{WORD_NS}}}p"):
                    paragraph_text = "".join(
                        t.text or ""
                        for t in p_node.findall(f".//{{{WORD_NS}}}t")
                    ).strip()
                    if paragraph_text:
                        text_parts.append(paragraph_text)
                if text_parts:
                    cell_el.text = "\n".join(text_parts)

        return {
            "code": "table_exported_to_tei",
            "block_id": block.block_id,
            "rows": row_count,
            "cells": cell_count,
        }

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

    @staticmethod
    def _split_inlines_on_line_break(inlines: list[InlineSpan]) -> list[list[InlineSpan]]:
        lines: list[list[InlineSpan]] = []
        current: list[InlineSpan] = []
        for span in inlines:
            if span.kind == "line_break":
                if current:
                    lines.append(current)
                current = []
                continue
            current.append(span)
        if current:
            lines.append(current)
        return lines
