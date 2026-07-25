from __future__ import annotations

import copy
import hashlib
import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from purh_editorial.io.importer_base import DocumentImporter
from purh_editorial.model import (
    Block,
    ComplexObjectOccurrence,
    Document,
    Heading,
    ImageAsset,
    ImageOccurrence,
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
NS_RELS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}

_IMAGE_CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".svg": "image/svg+xml",
    ".emf": "image/x-emf",
    ".wmf": "image/x-wmf",
}

# Sous-chaine du a:graphicData/@uri -> nature du graphique DrawingML.
_GRAPHIC_KIND_MARKERS = (
    ("picture", "picture"),
    ("chart", "chart"),
    ("diagram", "smartart"),
)

_CAPTION_STYLE_MARKERS = ("caption", "légende", "legende", "figure_caption")

# Reconnaît les niveaux dans les styles Word et Métopes :
# "Heading 1", "heading1", "Titre-1", "titre_2", "TEI_head3", "head3"
_HEADING_LEVEL_EXTRACT_RE = re.compile(
    r"(?:heading|tei_head|tei_titre|titre|head)[_\-\s]*([1-6])",
    re.IGNORECASE,
)


def _local_name_of(tag: str) -> str:
    return tag.split("}", 1)[-1]


@dataclass
class _MediaContext:
    """État mutable accumulé pendant l'import des médias d'un DOCX."""

    archive: zipfile.ZipFile
    rels_by_part: dict[str, dict[str, tuple[str, bool]]] = field(default_factory=dict)
    assets_by_sha: dict[str, ImageAsset] = field(default_factory=dict)
    occurrences: list[ImageOccurrence] = field(default_factory=list)
    complex_objects: list[ComplexObjectOccurrence] = field(default_factory=list)
    order_counter: int = 0
    header_footer_images_detected: int = 0

    def next_order(self) -> int:
        self.order_counter += 1
        return self.order_counter


class DocxImporter(DocumentImporter):
    supported_extensions = (".docx",)

    def load(self, path: Path) -> Document:
        with zipfile.ZipFile(path) as archive:
            document_root = ET.fromstring(archive.read("word/document.xml"))
            paragraph_style_names, run_style_defaults = self._load_style_data(archive)
            metadata = self._load_metadata(path, archive)
            media_ctx = _MediaContext(archive=archive)
            media_ctx.rels_by_part["word/document.xml"] = self._load_rels(archive, "word/document.xml")
            media_ctx.rels_by_part["word/footnotes.xml"] = self._load_rels(archive, "word/footnotes.xml")
            # Les labels de notes sont necessaires pour resoudre les appels de note
            # dans le corps ; on les charge d'abord, legerement, sans consommer de
            # numeros d'ordre d'occurrence d'image (le corps doit etre numerote avant
            # les notes pour respecter l'ordre logique de lecture, cf. ImageOccurrence.order).
            note_labels = self._load_note_labels(archive)

            blocks: list = []
            block_index = 1
            note_call_map: dict[str, list[str]] = {}
            table_count = 0
            blank_para_count = 0

            body = document_root.find(".//w:body", NS_WORD)
            body_children: list[ET.Element] = list(body) if body is not None else []

            for body_child in body_children:
                child_name = self._local_name(body_child.tag)
                if child_name == "tbl":
                    table_count += 1
                    table_block_id = f"b{block_index}"
                    table_image_refs = self._scan_table_image_refs(body_child, media_ctx)
                    blocks.append(
                        Block(
                            block_id=table_block_id,
                            block_type="table",
                            text="",
                            inlines=[],
                            note_refs=[],
                            attributes={
                                "protected_zone": "table",
                                "table_ooxml": ET.tostring(body_child, encoding="unicode"),
                                **({"table_image_refs": table_image_refs} if table_image_refs else {}),
                            },
                        )
                    )
                    for ref in table_image_refs:
                        media_ctx.occurrences.append(ImageOccurrence(
                            occurrence_id=make_id("imgocc"),
                            asset_ref=ref["asset_id"],
                            placement="table",
                            target_ref=table_block_id,
                            order=media_ctx.next_order(),
                            attributes={"rid": ref["rid"]},
                        ))
                    block_index += 1
                    blank_para_count = 0
                    continue
                if child_name != "p":
                    continue

                paragraph = body_child
                block_id = f"b{block_index}"
                inlines, note_refs = self._paragraph_inlines(
                    paragraph,
                    note_labels=note_labels,
                    paragraph_style_names=paragraph_style_names,
                    run_style_defaults=run_style_defaults,
                    media_ctx=media_ctx,
                    part_name="word/document.xml",
                    target_ref=block_id,
                )
                text = "".join(span.text for span in inlines)
                has_media = any(span.kind in {"image", "complex_object"} for span in inlines)
                if not text.strip() and not note_refs and not has_media:
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
                            block_id=block_id,
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
                    block_id=block_id,
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

            notes, _ = self._load_notes(
                archive,
                paragraph_style_names=paragraph_style_names,
                run_style_defaults=run_style_defaults,
                media_ctx=media_ctx,
            )

            header_footer_count = self._detect_header_footer_images(archive)

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

        self._associate_captions(blocks, media_ctx)

        if not metadata.title and blocks:
            metadata.title = blocks[0].text[:120]

        original_text = "\n\n".join(block.text for block in blocks)
        annotations = {
            "table_detected": table_count > 0,
            "table_preserved": table_count > 0,
            "table_protected": table_count > 0,
            "table_count": table_count,
            "header_footer_images_detected": header_footer_count > 0,
            "header_footer_images_count": header_footer_count,
        }
        image_assets = {asset.asset_id: asset for asset in media_ctx.assets_by_sha.values()}
        return Document(
            document_id=make_id("doc"),
            source_path=str(path),
            source_format="docx",
            metadata=metadata,
            blocks=blocks,
            notes=notes,
            annotations=annotations,
            original_text=original_text,
            image_assets=image_assets,
            image_occurrences=media_ctx.occurrences,
            complex_objects=media_ctx.complex_objects,
        )

    # -- Médias : relations, assets, occurrences --------------------------------

    @staticmethod
    def _rels_path_for(part_name: str) -> str:
        part_dir, part_file = part_name.rsplit("/", 1)
        return f"{part_dir}/_rels/{part_file}.rels"

    @staticmethod
    def _resolve_rel_target(part_name: str, target: str) -> str:
        if target.startswith("/"):
            return target.lstrip("/")
        part_dir = part_name.rsplit("/", 1)[0]
        return posixpath.normpath(f"{part_dir}/{target}").replace("\\", "/")

    def _load_rels(self, archive: zipfile.ZipFile, part_name: str) -> dict[str, tuple[str, bool]]:
        rels_path = self._rels_path_for(part_name)
        try:
            root = ET.fromstring(archive.read(rels_path))
        except KeyError:
            return {}
        rels: dict[str, tuple[str, bool]] = {}
        for rel in root.findall("r:Relationship", NS_RELS):
            rid = rel.attrib.get("Id")
            target = rel.attrib.get("Target")
            mode = rel.attrib.get("TargetMode", "Internal")
            if rid and target:
                rels[rid] = (target, mode == "External")
        return rels

    def _get_or_create_asset(
        self, media_ctx: _MediaContext, part_name: str, rid: str,
    ) -> tuple[ImageAsset | None, str | None]:
        """Retourne (asset, None) pour un média incorporé, ou (None, url) pour un lien externe."""
        rel = media_ctx.rels_by_part.get(part_name, {}).get(rid)
        if rel is None:
            return None, None
        target, is_external = rel
        if is_external:
            return None, target
        resolved = self._resolve_rel_target(part_name, target)
        try:
            data = media_ctx.archive.read(resolved)
        except KeyError:
            return None, None
        sha = hashlib.sha256(data).hexdigest()
        existing = media_ctx.assets_by_sha.get(sha)
        if existing is not None:
            return existing, None
        ext = Path(resolved).suffix.lower()
        content_type = _IMAGE_CONTENT_TYPES.get(ext, "application/octet-stream")
        asset = ImageAsset(
            asset_id=make_id("img"),
            filename=Path(resolved).name,
            content_type=content_type,
            data=data,
            sha256=sha,
            source_part=part_name,
        )
        media_ctx.assets_by_sha[sha] = asset
        return asset, None

    def _scan_table_image_refs(self, tbl_element: ET.Element, media_ctx: _MediaContext) -> list[dict]:
        """Repère les rIds d'image référencés dans le XML opaque d'un tableau et
        s'assure que leurs assets sont extraits, sans décomposer le tableau."""
        refs: list[dict] = []
        seen_rids: set[str] = set()
        for el in tbl_element.iter():
            for attr_name, attr_val in el.attrib.items():
                if not (attr_name.endswith("}embed") or attr_name.endswith("}id") or attr_name.endswith("}link")):
                    continue
                if not attr_val.startswith("rId") or attr_val in seen_rids:
                    continue
                asset, external_url = self._get_or_create_asset(media_ctx, "word/document.xml", attr_val)
                if asset is not None:
                    seen_rids.add(attr_val)
                    refs.append({"rid": attr_val, "asset_id": asset.asset_id, "external": None})
                elif external_url is not None:
                    seen_rids.add(attr_val)
                    refs.append({"rid": attr_val, "asset_id": None, "external": external_url})
        return refs

    def _detect_header_footer_images(self, archive: zipfile.ZipFile) -> int:
        """Détecte (sans les modéliser) les images d'en-tête/pied de page : hors
        périmètre de rendu pour cette passe, mais jamais ignorées silencieusement."""
        count = 0
        for name in archive.namelist():
            if not re.match(r"^word/(header|footer)\d*\.xml$", name):
                continue
            rels = self._load_rels(archive, name)
            for target, is_external in rels.values():
                if is_external:
                    continue
                if Path(target).suffix.lower() in _IMAGE_CONTENT_TYPES:
                    count += 1
        return count

    @staticmethod
    def _associate_captions(blocks: list, media_ctx: _MediaContext) -> None:
        """Associe la légende d'une figure au bloc de texte qui la suit immédiatement,
        quand ce bloc porte un style de légende reconnu (TEI_figure_caption, etc.)."""
        occurrences_by_block: dict[str, list[ImageOccurrence]] = {}
        for occ in media_ctx.occurrences:
            occurrences_by_block.setdefault(occ.target_ref, []).append(occ)
        for index, block in enumerate(blocks):
            occs = occurrences_by_block.get(block.block_id)
            if not occs:
                continue
            if index + 1 >= len(blocks):
                continue
            next_block = blocks[index + 1]
            style_ref = str(next_block.attributes.get("style_name") or next_block.attributes.get("style_id") or "").lower()
            if not any(marker in style_ref for marker in _CAPTION_STYLE_MARKERS):
                continue
            caption_text = next_block.text.strip()
            if not caption_text:
                continue
            for occ in occs:
                occ.caption = caption_text
            next_block.attributes["is_figure_caption"] = True
            next_block.attributes["caption_for_occurrences"] = [o.occurrence_id for o in occs]

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

    def _load_note_labels(self, archive: zipfile.ZipFile) -> dict[str, str]:
        """Charge uniquement les identifiants des notes (pas leur contenu), pour
        résoudre les appels de note du corps avant de traiter les notes elles-mêmes
        (le corps doit garder la priorité dans l'ordre logique des occurrences d'image)."""
        try:
            root = ET.fromstring(archive.read("word/footnotes.xml"))
        except KeyError:
            return {}
        note_labels: dict[str, str] = {}
        for footnote in root.findall(".//w:footnote", NS_WORD):
            footnote_type = footnote.attrib.get(f"{{{NS_WORD['w']}}}type", "")
            if footnote_type in {"separator", "continuationSeparator"}:
                continue
            note_id_raw = footnote.attrib.get(f"{{{NS_WORD['w']}}}id", "")
            note_labels[f"ftn{note_id_raw}"] = note_id_raw
        return note_labels

    def _load_notes(
        self,
        archive: zipfile.ZipFile,
        *,
        paragraph_style_names: dict[str, str],
        run_style_defaults: dict[str, InlineStyle],
        media_ctx: _MediaContext,
    ) -> tuple[list[Note], dict[str, str]]:
        try:
            root = ET.fromstring(archive.read("word/footnotes.xml"))
        except KeyError:
            return [], {}

        notes: list[Note] = []
        note_labels: dict[str, str] = {}
        for footnote in root.findall(".//w:footnote", NS_WORD):
            # Les marqueurs separator/continuationSeparator sont identifies par
            # w:type, pas par leur w:id : rien ne garantit que Word reserve les id
            # -1/0 a ces marqueurs (un document peut tres bien numeroter une vraie
            # note de contenu "0"). Filtrer sur l'id exclurait alors une note reelle.
            footnote_type = footnote.attrib.get(f"{{{NS_WORD['w']}}}type", "")
            if footnote_type in {"separator", "continuationSeparator"}:
                continue
            note_id_raw = footnote.attrib.get(f"{{{NS_WORD['w']}}}id", "")
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
                    media_ctx=media_ctx,
                    part_name="word/footnotes.xml",
                    target_ref=note_id,
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
        media_ctx: _MediaContext,
        part_name: str,
        target_ref: str,
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
                    media_ctx=media_ctx,
                    part_name=part_name,
                    target_ref=target_ref,
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
                        media_ctx=media_ctx,
                        part_name=part_name,
                        target_ref=target_ref,
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
        media_ctx: _MediaContext,
        part_name: str,
        target_ref: str,
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
            elif local_name == "drawing":
                span = self._extract_drawing_span(child, media_ctx, part_name, target_ref)
                if span is not None:
                    inlines.append(span)
            elif local_name == "pict":
                span = self._extract_vml_pict_span(child, media_ctx, part_name, target_ref)
                if span is not None:
                    inlines.append(span)
            elif local_name == "object":
                span = self._extract_ole_object_span(child, media_ctx, part_name, target_ref)
                if span is not None:
                    inlines.append(span)
            elif local_name in {"oMath", "oMathPara"}:
                media_ctx.complex_objects.append(ComplexObjectOccurrence(
                    occurrence_id=make_id("cobj"),
                    object_type="equation",
                    target_ref=target_ref,
                    order=media_ctx.next_order(),
                ))
                inlines.append(InlineSpan(
                    text="",
                    kind="complex_object",
                    attributes={"object_type": "equation"},
                ))
        return inlines, note_refs

    # -- DrawingML / VML / OLE ----------------------------------------------------

    def _extract_drawing_span(
        self, drawing_el: ET.Element, media_ctx: _MediaContext, part_name: str, target_ref: str,
    ) -> InlineSpan | None:
        info = self._parse_drawing(drawing_el)
        if info is None:
            return None

        placement = "note" if part_name == "word/footnotes.xml" else info["placement"]
        anchor_normalized = info["placement"] == "anchor"

        if info["kind"] != "picture":
            object_type = info["kind"]
            media_ctx.complex_objects.append(ComplexObjectOccurrence(
                occurrence_id=make_id("cobj"),
                object_type=object_type,
                target_ref=target_ref,
                order=media_ctx.next_order(),
                placement=placement,
                attributes={"name": info["name"]},
            ))
            return InlineSpan(
                text="",
                kind="complex_object",
                attributes={"object_type": object_type, "name": info["name"]},
            )

        asset = None
        external_url = None
        if info["embed_rid"]:
            asset, external_url = self._get_or_create_asset(media_ctx, part_name, info["embed_rid"])
        if asset is None and info["link_rid"]:
            _, external_url = self._get_or_create_asset(media_ctx, part_name, info["link_rid"])

        occurrence_id = make_id("imgocc")
        occurrence = ImageOccurrence(
            occurrence_id=occurrence_id,
            asset_ref=asset.asset_id if asset else "",
            placement=placement,
            target_ref=target_ref,
            order=media_ctx.next_order(),
            width_emu=info["cx"],
            height_emu=info["cy"],
            alt_text=info["descr"],
            title=info["title"],
            external_link=external_url,
            anchor_normalized_to_inline=anchor_normalized,
            attributes={"dml_container": info["placement"]},
        )
        media_ctx.occurrences.append(occurrence)
        return InlineSpan(
            text="",
            kind="image",
            attributes={"occurrence_id": occurrence_id},
        )

    @staticmethod
    def _parse_drawing(drawing_el: ET.Element) -> dict | None:
        container = None
        for child in drawing_el:
            ln = _local_name_of(child.tag)
            if ln in ("inline", "anchor"):
                container = child
                break
        if container is None:
            return None

        info = {
            "placement": "anchor" if _local_name_of(container.tag) == "anchor" else "inline",
            "cx": None, "cy": None, "name": "", "descr": "", "title": "",
            "embed_rid": None, "link_rid": None, "kind": "other_graphic",
        }
        for child in container:
            ln = _local_name_of(child.tag)
            if ln == "extent":
                for attr, key in (("cx", "cx"), ("cy", "cy")):
                    raw = child.attrib.get(attr)
                    if raw:
                        try:
                            info[key] = int(raw)
                        except ValueError:
                            pass
            elif ln == "docPr":
                info["name"] = child.attrib.get("name", "")
                info["descr"] = child.attrib.get("descr", "")
                info["title"] = child.attrib.get("title", "")

        for el in container.iter():
            if _local_name_of(el.tag) == "graphicData":
                uri = el.attrib.get("uri", "")
                for marker, kind in _GRAPHIC_KIND_MARKERS:
                    if marker in uri:
                        info["kind"] = kind
                        break
                break

        for el in container.iter():
            if _local_name_of(el.tag) != "blip":
                continue
            for attr_name, attr_val in el.attrib.items():
                if attr_name.endswith("}embed"):
                    info["embed_rid"] = attr_val
                elif attr_name.endswith("}link"):
                    info["link_rid"] = attr_val
            break

        return info

    def _extract_vml_pict_span(
        self, pict_el: ET.Element, media_ctx: _MediaContext, part_name: str, target_ref: str,
    ) -> InlineSpan | None:
        imagedata = None
        for el in pict_el.iter():
            if _local_name_of(el.tag) == "imagedata":
                imagedata = el
                break
        if imagedata is None:
            return None

        rid = None
        for attr_name, attr_val in imagedata.attrib.items():
            if attr_name.endswith("}id"):
                rid = attr_val
                break
        if not rid:
            return None

        asset, external_url = self._get_or_create_asset(media_ctx, part_name, rid)
        occurrence_id = make_id("imgocc")
        occurrence = ImageOccurrence(
            occurrence_id=occurrence_id,
            asset_ref=asset.asset_id if asset else "",
            placement="note" if part_name == "word/footnotes.xml" else "inline",
            target_ref=target_ref,
            order=media_ctx.next_order(),
            external_link=external_url,
            attributes={"legacy_vml": True},
        )
        media_ctx.occurrences.append(occurrence)
        return InlineSpan(text="", kind="image", attributes={"occurrence_id": occurrence_id})

    def _extract_ole_object_span(
        self, object_el: ET.Element, media_ctx: _MediaContext, part_name: str, target_ref: str,
    ) -> InlineSpan | None:
        prog_id = ""
        for el in object_el.iter():
            if _local_name_of(el.tag) == "OLEObject":
                prog_id = el.attrib.get("ProgID", "")
                break

        fallback_asset_ref = None
        imagedata = None
        for el in object_el.iter():
            if _local_name_of(el.tag) == "imagedata":
                imagedata = el
                break
        if imagedata is not None:
            rid = None
            for attr_name, attr_val in imagedata.attrib.items():
                if attr_name.endswith("}id"):
                    rid = attr_val
                    break
            if rid:
                asset, _ = self._get_or_create_asset(media_ctx, part_name, rid)
                if asset is not None:
                    fallback_asset_ref = asset.asset_id

        media_ctx.complex_objects.append(ComplexObjectOccurrence(
            occurrence_id=make_id("cobj"),
            object_type="ole_object",
            target_ref=target_ref,
            order=media_ctx.next_order(),
            fallback_asset_ref=fallback_asset_ref,
            attributes={"prog_id": prog_id},
        ))
        return InlineSpan(
            text="",
            kind="complex_object",
            attributes={"object_type": "ole_object", "prog_id": prog_id},
        )

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
