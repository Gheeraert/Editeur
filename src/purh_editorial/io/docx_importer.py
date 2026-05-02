from __future__ import annotations

import copy
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from purh_editorial.io.importer_base import DocumentImporter
from purh_editorial.model import (
    Block,
    Document,
    Heading,
    InlineSpan,
    InlineStyle,
    Metadata,
    Note,
    Paragraph,
    QuoteBlock,
)
from purh_editorial.utils import make_id

NS_WORD = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
NS_CORE = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
}

# Reconnaît les niveaux dans les styles Word et Métopes :
# "Heading 1", "heading1", "Titre-1", "titre_2", "TEI_head3", "head3"
_HEADING_LEVEL_EXTRACT_RE = re.compile(
    r"(?:heading|tei_head|tei_titre|titre|head)[_\-\s]*([1-6])",
    re.IGNORECASE,
)


class DocxImporter(DocumentImporter):
    supported_extensions = (".docx",)

    def load(self, path: Path) -> Document:
        with zipfile.ZipFile(path) as archive:
            document_root = ET.fromstring(archive.read("word/document.xml"))
            paragraph_style_names, run_style_defaults = self._load_style_data(archive)
            metadata = self._load_metadata(path, archive)
            notes, note_labels = self._load_notes(
                archive,
                paragraph_style_names=paragraph_style_names,
                run_style_defaults=run_style_defaults,
            )

        blocks = []
        block_index = 1
        note_call_map: dict[str, list[str]] = {}
        table_count = 0
        blank_para_count = 0

        body = document_root.find(".//w:body", NS_WORD)
        if body is None:
            body_children: list[ET.Element] = []
        else:
            body_children = list(body)

        for body_child in body_children:
            child_name = self._local_name(body_child.tag)
            if child_name == "tbl":
                table_count += 1
                blocks.append(
                    Block(
                        block_id=f"b{block_index}",
                        block_type="table",
                        text="",
                        inlines=[],
                        note_refs=[],
                        attributes={
                            "protected_zone": "table",
                            "table_ooxml": ET.tostring(body_child, encoding="unicode"),
                        },
                    )
                )
                block_index += 1
                blank_para_count = 0
                continue
            if child_name != "p":
                continue

            paragraph = body_child
            inlines, note_refs = self._paragraph_inlines(
                paragraph,
                note_labels=note_labels,
                paragraph_style_names=paragraph_style_names,
                run_style_defaults=run_style_defaults,
            )
            text = "".join(span.text for span in inlines)
            if not text.strip() and not note_refs:
                blank_para_count += 1
                # Conserver le paragraphe vide comme frontière matérielle.
                # Il ne porte aucun texte éditorial, mais il évite que la
                # structure visuelle du DOCX soit perdue avant les heuristiques.
                has_page_break = any(
                    br.get(f"{{{NS_WORD['w']}}}type") == "page"
                    for br in paragraph.findall(".//w:br", NS_WORD)
                )
                blank_attrs: dict = {
                    "is_blank_para": True,
                    "blank_para": True,
                    "blank_para_index": blank_para_count,
                }
                if has_page_break:
                    blank_attrs["page_break"] = True
                blocks.append(
                    Paragraph(
                        block_id=f"b{block_index}",
                        text="",
                        inlines=[],
                        note_refs=[],
                        attributes=blank_attrs,
                    )
                )
                block_index += 1
                continue

            style_id = self._paragraph_style(paragraph)
            style_name = paragraph_style_names.get(style_id, style_id or "")
            para_visual = self._paragraph_visual_props(paragraph, inlines)
            block = self._build_block(
                block_id=f"b{block_index}",
                text=text,
                inlines=inlines,
                note_refs=note_refs,
                style_id=style_id,
                style_name=style_name,
                visual=para_visual,
            )
            blank_para_count = 0
            blocks.append(block)
            for note_ref in note_refs:
                note_call_map.setdefault(note_ref, []).append(block.block_id)
            block_index += 1

        # Les paragraphes vides sont conservés comme blocs-frontières et
        # également projetés sous forme d'attributs before/after sur les
        # blocs textuels voisins. Cette double représentation rend le modèle
        # plus robuste : les heuristiques peuvent lire soit le vrai blanc,
        # soit sa trace attributaire.
        for index, block in enumerate(blocks):
            if not block.attributes.get("is_blank_para"):
                continue

            prev_index = index - 1
            while prev_index >= 0 and blocks[prev_index].attributes.get("is_blank_para"):
                prev_index -= 1
            next_index = index + 1
            while next_index < len(blocks) and blocks[next_index].attributes.get("is_blank_para"):
                next_index += 1

            if prev_index >= 0:
                blocks[prev_index].attributes["blank_para_after"] = True
                blocks[prev_index].attributes["blank_para_after_count"] = (
                    int(blocks[prev_index].attributes.get("blank_para_after_count", 0) or 0) + 1
                )
            if next_index < len(blocks):
                blocks[next_index].attributes["blank_para_before"] = True
                blocks[next_index].attributes["blank_para_before_count"] = (
                    int(blocks[next_index].attributes.get("blank_para_before_count", 0) or 0) + 1
                )
                if block.attributes.get("page_break"):
                    blocks[next_index].attributes["page_break_before"] = True

        for note in notes:
            call_refs = note_call_map.get(note.note_id, [])
            if call_refs:
                note.target_ref = call_refs[0]
                note.attributes["call_refs"] = call_refs

        if not metadata.title and blocks:
            metadata.title = blocks[0].text[:120]

        original_text = "\n\n".join(block.text for block in blocks)
        annotations = {
            "table_detected": table_count > 0,
            "table_preserved": table_count > 0,
            "table_protected": table_count > 0,
            "table_count": table_count,
        }
        return Document(
            document_id=make_id("doc"),
            source_path=str(path),
            source_format="docx",
            metadata=metadata,
            blocks=blocks,
            notes=notes,
            annotations=annotations,
            original_text=original_text,
        )

    def _load_metadata(self, path: Path, archive: zipfile.ZipFile) -> Metadata:
        metadata = Metadata(source_label=path.name)
        try:
            core_root = ET.fromstring(archive.read("docProps/core.xml"))
        except KeyError:
            return metadata

        title = core_root.findtext("dc:title", default="", namespaces=NS_CORE).strip()
        creator = core_root.findtext("dc:creator", default="", namespaces=NS_CORE).strip()
        language = core_root.findtext("dc:language", default="", namespaces=NS_CORE).strip()
        if title:
            metadata.title = title
        if creator:
            metadata.authors = [creator]
        if language:
            metadata.language = language
        return metadata

    def _load_style_data(self, archive: zipfile.ZipFile) -> tuple[dict[str, str], dict[str, InlineStyle]]:
        try:
            styles_root = ET.fromstring(archive.read("word/styles.xml"))
        except KeyError:
            return {}, {}

        paragraph_style_names: dict[str, str] = {}
        run_style_defaults: dict[str, InlineStyle] = {}

        for style in styles_root.findall(".//w:style", NS_WORD):
            style_id = style.attrib.get(f"{{{NS_WORD['w']}}}styleId")
            if not style_id:
                continue

            style_type = style.attrib.get(f"{{{NS_WORD['w']}}}type", "")
            name_node = style.find("w:name", NS_WORD)
            style_name = ""
            if name_node is not None:
                style_name = name_node.attrib.get(f"{{{NS_WORD['w']}}}val", "")
            paragraph_style_names[style_id] = style_name

            rpr = style.find("w:rPr", NS_WORD)
            if rpr is not None:
                run_style_defaults[style_id] = self._inline_style_from_rpr(rpr)
            elif style_type == "character":
                run_style_defaults[style_id] = InlineStyle()
        return paragraph_style_names, run_style_defaults

    def _load_notes(
        self,
        archive: zipfile.ZipFile,
        *,
        paragraph_style_names: dict[str, str],
        run_style_defaults: dict[str, InlineStyle],
    ) -> tuple[list[Note], dict[str, str]]:
        try:
            root = ET.fromstring(archive.read("word/footnotes.xml"))
        except KeyError:
            return [], {}

        notes: list[Note] = []
        note_labels: dict[str, str] = {}
        for footnote in root.findall(".//w:footnote", NS_WORD):
            note_id_raw = footnote.attrib.get(f"{{{NS_WORD['w']}}}id", "")
            if note_id_raw in {"-1", "0"}:
                continue
            note_id = f"ftn{note_id_raw}"
            inlines: list[InlineSpan] = []
            note_refs: list[str] = []
            paragraphs = footnote.findall("./w:p", NS_WORD)
            for p_index, paragraph in enumerate(paragraphs):
                para_inlines, para_note_refs = self._paragraph_inlines(
                    paragraph,
                    note_labels=note_labels,
                    paragraph_style_names=paragraph_style_names,
                    run_style_defaults=run_style_defaults,
                )
                inlines.extend(para_inlines)
                note_refs.extend(para_note_refs)
                if p_index < len(paragraphs) - 1:
                    inlines.append(InlineSpan(text="\n", kind="line_break"))

            text = "".join(span.text for span in inlines).strip()
            note = Note(
                note_id=note_id,
                label=note_id_raw,
                text=text,
                inlines=inlines,
                attributes={"source": "docx", "note_refs": note_refs},
            )
            notes.append(note)
            note_labels[note_id] = note_id_raw
        return notes, note_labels

    def _paragraph_inlines(
        self,
        paragraph: ET.Element,
        *,
        note_labels: dict[str, str],
        paragraph_style_names: dict[str, str],
        run_style_defaults: dict[str, InlineStyle],
    ) -> tuple[list[InlineSpan], list[str]]:
        inlines: list[InlineSpan] = []
        note_refs: list[str] = []

        for child in list(paragraph):
            local_name = self._local_name(child.tag)
            if local_name == "r":
                run_inlines, run_note_refs = self._run_inlines(
                    child,
                    note_labels=note_labels,
                    paragraph_style_names=paragraph_style_names,
                    run_style_defaults=run_style_defaults,
                )
                inlines.extend(run_inlines)
                note_refs.extend(run_note_refs)
                continue

            if local_name in {"hyperlink", "smartTag", "sdt", "ins"}:
                for run in child.findall(".//w:r", NS_WORD):
                    run_inlines, run_note_refs = self._run_inlines(
                        run,
                        note_labels=note_labels,
                        paragraph_style_names=paragraph_style_names,
                        run_style_defaults=run_style_defaults,
                    )
                    inlines.extend(run_inlines)
                    note_refs.extend(run_note_refs)

        return inlines, note_refs

    def _run_inlines(
        self,
        run: ET.Element,
        *,
        note_labels: dict[str, str],
        paragraph_style_names: dict[str, str],
        run_style_defaults: dict[str, InlineStyle],
    ) -> tuple[list[InlineSpan], list[str]]:
        inlines: list[InlineSpan] = []
        note_refs: list[str] = []

        style, run_style_id, run_style_name = self._resolve_run_style(
            run,
            paragraph_style_names=paragraph_style_names,
            run_style_defaults=run_style_defaults,
        )

        for child in list(run):
            local_name = self._local_name(child.tag)
            attributes = {}
            if run_style_id:
                attributes["run_style_id"] = run_style_id
            if run_style_name:
                attributes["run_style_name"] = run_style_name

            if local_name == "t":
                inlines.append(
                    InlineSpan(
                        text=child.text or "",
                        style=copy.deepcopy(style),
                        attributes=attributes,
                    )
                )
            elif local_name == "tab":
                inlines.append(
                    InlineSpan(
                        text="\t",
                        style=copy.deepcopy(style),
                        kind="tab",
                        attributes=attributes,
                    )
                )
            elif local_name in {"br", "cr"}:
                inlines.append(
                    InlineSpan(
                        text="\n",
                        style=copy.deepcopy(style),
                        kind="line_break",
                        attributes=attributes,
                    )
                )
            elif local_name in {"footnoteReference", "endnoteReference"}:
                raw_id = child.attrib.get(f"{{{NS_WORD['w']}}}id")
                if not raw_id:
                    continue
                note_ref = f"ftn{raw_id}"
                note_refs.append(note_ref)
                note_label = note_labels.get(note_ref, raw_id)
                call_style = copy.deepcopy(style)
                call_style.superscript = True
                inlines.append(
                    InlineSpan(
                        text=f"[{note_label}]",
                        style=call_style,
                        kind="note_call",
                        note_ref=note_ref,
                        attributes=attributes,
                    )
                )
            elif local_name == "footnoteRef":
                continue
        return inlines, note_refs

    def _resolve_run_style(
        self,
        run: ET.Element,
        *,
        paragraph_style_names: dict[str, str],
        run_style_defaults: dict[str, InlineStyle],
    ) -> tuple[InlineStyle, str | None, str]:
        rpr = run.find("w:rPr", NS_WORD)
        if rpr is None:
            return InlineStyle(), None, ""

        run_style_id_node = rpr.find("w:rStyle", NS_WORD)
        run_style_id = None
        if run_style_id_node is not None:
            run_style_id = run_style_id_node.attrib.get(f"{{{NS_WORD['w']}}}val")
        run_style_name = paragraph_style_names.get(run_style_id, "") if run_style_id else ""

        base_style = copy.deepcopy(run_style_defaults.get(run_style_id, InlineStyle()))
        direct_style = self._inline_style_from_rpr(rpr)
        style = InlineStyle(
            bold=base_style.bold or direct_style.bold,
            italic=base_style.italic or direct_style.italic,
            small_caps=base_style.small_caps or direct_style.small_caps,
            subscript=base_style.subscript or direct_style.subscript,
            superscript=base_style.superscript or direct_style.superscript,
        )
        return style, run_style_id, run_style_name

    @staticmethod
    def _inline_style_from_rpr(rpr: ET.Element) -> InlineStyle:
        vert_align = rpr.find("w:vertAlign", NS_WORD)
        vert_val = vert_align.attrib.get(f"{{{NS_WORD['w']}}}val", "") if vert_align is not None else ""
        return InlineStyle(
            bold=DocxImporter._bool_prop(rpr, "b"),
            italic=DocxImporter._bool_prop(rpr, "i"),
            small_caps=DocxImporter._bool_prop(rpr, "smallCaps"),
            subscript=vert_val == "subscript",
            superscript=vert_val == "superscript",
        )

    @staticmethod
    def _bool_prop(rpr: ET.Element, prop_name: str) -> bool:
        node = rpr.find(f"w:{prop_name}", NS_WORD)
        if node is None:
            return False
        value = node.attrib.get(f"{{{NS_WORD['w']}}}val")
        if value is None:
            return True
        return value.lower() not in {"0", "false", "off", "no"}

    @staticmethod
    def _paragraph_style(paragraph: ET.Element) -> str | None:
        node = paragraph.find("./w:pPr/w:pStyle", NS_WORD)
        if node is None:
            return None
        return node.attrib.get(f"{{{NS_WORD['w']}}}val")

    @staticmethod
    def _paragraph_visual_props(paragraph: ET.Element, inlines: list[InlineSpan]) -> dict:
        props: dict = {}
        ppr = paragraph.find("w:pPr", NS_WORD)
        if ppr is not None:
            ind = ppr.find("w:ind", NS_WORD)
            if ind is not None:
                left = ind.get(f"{{{NS_WORD['w']}}}left")
                fl   = ind.get(f"{{{NS_WORD['w']}}}firstLine")
                if left:
                    try: props["ind_left"] = int(left)
                    except ValueError: pass
                if fl:
                    try: props["ind_first_line"] = int(fl)
                    except ValueError: pass

            spacing = ppr.find("w:spacing", NS_WORD)
            if spacing is not None:
                for key, attr in (("space_before", "before"), ("space_after", "after")):
                    val = spacing.get(f"{{{NS_WORD['w']}}}{attr}")
                    if val:
                        try: props[key] = int(val)
                        except ValueError: pass

            jc = ppr.find("w:jc", NS_WORD)
            if jc is not None:
                jc_val = jc.get(f"{{{NS_WORD['w']}}}val")
                if jc_val:
                    props["jc"] = jc_val

            for tag, key in (("keepNext", "keep_with_next"), ("keepLines", "keep_lines")):
                node = ppr.find(f"w:{tag}", NS_WORD)
                if node is not None:
                    val = node.get(f"{{{NS_WORD['w']}}}val")
                    props[key] = val is None or val.lower() not in {"0", "false", "off", "no"}

        text_spans = [s for s in inlines if s.kind == "text" and s.text.strip()]
        if text_spans:
            props["all_runs_bold"]   = all(s.style.bold   for s in text_spans)
            props["all_runs_italic"] = all(s.style.italic for s in text_spans)
            props["any_run_bold"]    = any(s.style.bold   for s in text_spans)
            props["any_run_italic"]  = any(s.style.italic for s in text_spans)
        return props

    def _build_block(
        self,
        *,
        block_id: str,
        text: str,
        inlines: list[InlineSpan],
        note_refs: list[str],
        style_id: str | None,
        style_name: str,
        visual: dict | None = None,
    ):
        style_ref   = (style_name or style_id or "").lower()
        stripped    = text.strip()
        attributes  = {"style_id": style_id or "", "style_name": style_name}
        if visual:
            attributes.update(visual)

        if any(token in style_ref for token in ("heading", "titre", "title", "chapter", "head")):
            level = DocxImporter._extract_heading_level(style_name, style_id)
            if level is not None:
                attributes["heading_level"] = level
            return Heading(block_id=block_id, text=text, inlines=inlines,
                           note_refs=note_refs, attributes=attributes)
        if any(token in style_ref for token in ("quote", "citation", "epigraphe")):
            return QuoteBlock(block_id=block_id, text=text, inlines=inlines,
                              note_refs=note_refs, attributes=attributes)
        if stripped and stripped.isupper() and 4 < len(stripped) < 140:
            attributes["heading_level"] = 1
            return Heading(block_id=block_id, text=text, inlines=inlines,
                           note_refs=note_refs, attributes=attributes)
        return Paragraph(block_id=block_id, text=text, inlines=inlines,
                         note_refs=note_refs, attributes=attributes)

    @staticmethod
    def _extract_heading_level(style_name: str, style_id: str | None) -> int | None:
        for value in (style_name, style_id or ""):
            m = _HEADING_LEVEL_EXTRACT_RE.search(value)
            if m:
                return int(m.group(1))
        return None

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.split("}", 1)[-1]
