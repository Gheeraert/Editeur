from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from xml.etree import ElementTree as ET

from docx import Document as DocxDoc
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from purh_editorial.model import Document, InlineSpan, Note
from purh_editorial.model.semantics import extract_verse_lines, is_canonical_lineated_block

# ── Gabarit Métopes ───────────────────────────────────────────────────────────
_DEFAULT_TEMPLATE = Path(__file__).parent.parent.parent.parent / (
    "sources/editorial_rules/metopes_template_word/Commons-publishing-Metopes.dotm"
)

# Content-type .dotm → .docx (python-docx refuse les templates macro)
_CT_DOTM = b"application/vnd.ms-word.template.macroEnabledTemplate.main+xml"
_CT_DOCX = b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"

# Fichiers VBA à exclure lors de la conversion .dotm -> .docx.
_VBA_FILES = frozenset({"word/vbaProject.bin", "word/vbaData.xml", "word/_rels/vbaProject.bin.rels"})
# Le ruban Métopes appelle des callbacks VBA : il faut le retirer avec les macros.
_CUSTOM_UI_PREFIXES = ("customUI/",)

# Retire les entrées VBA dans [Content_Types].xml.
_VBA_CT_RE = re.compile(rb'<Override[^>]+/word/vba[^>]+/>')
_VBA_DEFAULT_CT_RE = re.compile(
    rb'<Default\b(?=[^>]*\bExtension="bin")'
    rb'(?=[^>]*\bContentType="application/vnd\.ms-office\.vbaProject")[^>]*/>'
)
# Retire les relations vers le projet VBA ou vers le ruban customUI.
_VBA_REL_RE = re.compile(rb'<Relationship[^>]+vbaProject[^>]*/>')
_CUSTOM_UI_REL_RE = re.compile(rb'<Relationship[^>]+(?:customUI|ui/extensibility)[^>]*/>')

# Namespaces OOXML
W  = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML = "http://www.w3.org/XML/1998/namespace"

# ── Correspondance couleurs de surlignage ─────────────────────────────────────
_HIGHLIGHT_MAP: dict[str, WD_COLOR_INDEX] = {
    "orthotypo":             WD_COLOR_INDEX.YELLOW,
    "footnote":              WD_COLOR_INDEX.BRIGHT_GREEN,
    "biblio":                WD_COLOR_INDEX.TURQUOISE,
    "ai":                    WD_COLOR_INDEX.PINK,
    "ai_structure":          WD_COLOR_INDEX.VIOLET,
    "exploratory_structure": WD_COLOR_INDEX.DARK_YELLOW,
}

# ── Polices PURH (substituts des polices InDesign) ───────────────────────────
# Corps du texte → Garamond (empattement, analogue Chaparral Pro)
# Titraille      → Calibri  (sans empattement, analogue Josefin Sans)
_FONT_BODY = "Garamond"
_FONT_HEAD = "Calibri"
_HEADING_FONT_SIZES_PT: dict[int, int] = {1: 16, 2: 14, 3: 13}
_QUOTE_FONT_SIZE_PT = 11
_QUOTE_LEFT_INDENT_CM = 0.7

# Styles de corps (reçoivent Garamond)
_BODY_STYLE_NAMES: frozenset[str] = frozenset({
    "Normal", "footnote text", "endnote text",
    "TEI_quote", "TEI_quote2", "TEI_quote_nested", "TEI_quote_continuation",
    "TEI_bibl_reference", "TEI_epigraph", "TEI_acknowledgment",
    "TEI_dedication", "TEI_paragraph_lead", "TEI_paragraph_consecutive",
    "TEI_abstract", "TEI_keywords", "TEI_verse", "TEI_figure_caption",
    "TEI_figure_credits", "TEI_figure_alternative", "TEI_aut:",
    "TEI_note:", "TEI_localpara",
})

# Styles de titre (reçoivent Calibri)
_HEAD_STYLE_NAMES: frozenset[str] = frozenset({
    "Heading 1", "Heading 2", "Heading 3", "Heading 4", "Heading 5",
    "heading 1", "heading 2", "heading 3", "heading 4", "heading 5",
    "TEI_bibl_start", "TEI_appendix_start",
})
_FIRST_LINE_INDENT_CM = 0.5


# ── Conversion .dotm → flux .docx ────────────────────────────────────────────

def _dotm_to_docx_bytes(dotm_path: Path) -> io.BytesIO:
    """Retourne le contenu du .dotm converti en .docx sans macros ni ruban VBA."""
    buf = io.BytesIO()
    with zipfile.ZipFile(dotm_path, "r") as src, \
         zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            if item.filename in _VBA_FILES or item.filename.startswith(_CUSTOM_UI_PREFIXES):
                continue
            data = src.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(_CT_DOTM, _CT_DOCX)
                data = _VBA_CT_RE.sub(b"", data)
                data = _VBA_DEFAULT_CT_RE.sub(b"", data)
            elif item.filename.endswith(".rels"):
                data = _VBA_REL_RE.sub(b"", data)
                data = _CUSTOM_UI_REL_RE.sub(b"", data)
            dst.writestr(item, data)
    buf.seek(0)
    return buf


# ── Helpers python-docx ───────────────────────────────────────────────────────

def _add_line_break(paragraph) -> None:
    """Insère un saut de ligne manuel (Shift+Entrée) dans un paragraphe Word."""
    r = OxmlElement("w:r")
    br = OxmlElement("w:br")
    r.append(br)
    paragraph._p.append(r)


def _add_page_break(doc: DocxDoc) -> None:
    """Insère un saut de page (paragraphe vide avec <w:br w:type='page'>)."""
    p = OxmlElement("w:p")
    r = OxmlElement("w:r")
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    r.append(br)
    p.append(r)
    _insert_body_element(doc, p)


def _add_footnote_reference(paragraph, footnote_id: int) -> None:
    """Insère un appel de note (renvoi superscript) dans un paragraphe."""
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    rstyle = OxmlElement("w:rStyle")
    rstyle.set(qn("w:val"), "Appelnotedebasdep")
    rpr.append(rstyle)
    r.append(rpr)
    ref = OxmlElement("w:footnoteReference")
    ref.set(qn("w:id"), str(footnote_id))
    r.append(ref)
    paragraph._p.append(r)


def _add_run_with_style(
    paragraph,
    text: str,
    *,
    bold: bool = False,
    italic: bool = False,
    small_caps: bool = False,
    superscript: bool = False,
    subscript: bool = False,
    highlight: WD_COLOR_INDEX | None = None,
    font_name: str | None = None,
    font_size_pt: int | None = None,
) -> None:
    if not text:
        return
    run = paragraph.add_run(text)
    if bold:
        run.bold = True
    if italic:
        run.italic = True
    if small_caps:
        run.font.small_caps = True
    if superscript:
        run.font.superscript = True
    if subscript:
        run.font.subscript = True
    if highlight is not None:
        run.font.highlight_color = highlight
    if font_name:
        run.font.name = font_name
    if font_size_pt is not None:
        run.font.size = Pt(font_size_pt)


def _inline_highlight(span: InlineSpan) -> WD_COLOR_INDEX | None:
    key = span.attributes.get("highlight_color")
    return _HIGHLIGHT_MAP.get(key) if key else None


def _add_paragraph(doc: DocxDoc, block, note_id_map: dict[str, int]) -> None:
    """Ajoute un paragraphe au document Word avec son style Métopes."""
    style_name = block.attributes.get("metopes_style", "Normal")
    try:
        para = doc.add_paragraph(style=style_name)
    except (KeyError, ValueError):
        para = doc.add_paragraph(style="Normal")

    if style_name == "Normal":
        para.paragraph_format.first_line_indent = Cm(_FIRST_LINE_INDENT_CM)

    # Retrait suspendu pour les entrées bibliographiques (≈ 5 mm, charte PURH)
    if style_name == "TEI_bibl_reference":
        para.paragraph_format.left_indent = Cm(0.5)
        para.paragraph_format.first_line_indent = Cm(-0.5)

    heading_level = 0
    if block.block_type == "heading":
        raw_level = block.attributes.get("heading_level", 0)
        try:
            heading_level = int(raw_level or 0)
        except (TypeError, ValueError):
            heading_level = 1
    heading_size = _HEADING_FONT_SIZES_PT.get(min(max(heading_level, 1), 3)) if heading_level else None
    is_lineated_block = is_canonical_lineated_block(block)
    is_quote_block = block.block_type == "quote_block"
    if is_quote_block or block.block_type == "lineated_block":
        para.paragraph_format.left_indent = Cm(_QUOTE_LEFT_INDENT_CM)
        para.paragraph_format.first_line_indent = None
        para.paragraph_format.line_spacing = 1.0
        para.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT if is_lineated_block else WD_PARAGRAPH_ALIGNMENT.JUSTIFY

    if block.inlines:
        for span in block.inlines:
            if span.kind == "line_break":
                _add_line_break(para)
                continue
            if span.kind == "note_call" and span.note_ref:
                fn_id = note_id_map.get(span.note_ref)
                if fn_id is not None:
                    _add_footnote_reference(para, fn_id)
            else:
                _add_run_with_style(
                    para,
                    span.text,
                    bold=span.style.bold,
                    italic=span.style.italic,
                    small_caps=span.style.small_caps,
                    superscript=span.style.superscript,
                    subscript=span.style.subscript,
                    highlight=_inline_highlight(span),
                    font_size_pt=_QUOTE_FONT_SIZE_PT if (is_quote_block or is_lineated_block) else heading_size,
                )
    else:
        hl = _HIGHLIGHT_MAP.get(block.attributes.get("highlight_color", ""), None)
        if is_lineated_block:
            lines = extract_verse_lines(block)
            for i, line in enumerate(lines):
                if i > 0:
                    _add_line_break(para)
                _add_run_with_style(
                    para,
                    line.strip(),
                    highlight=hl,
                    font_size_pt=_QUOTE_FONT_SIZE_PT,
                )
        else:
            _add_run_with_style(
                para,
                block.text,
                highlight=hl,
                font_size_pt=_QUOTE_FONT_SIZE_PT if is_quote_block else heading_size,
            )


def _insert_body_element(doc: DocxDoc, element) -> None:
    body = doc.element.body
    sect_pr = body.find(qn("w:sectPr"))
    if sect_pr is None:
        body.append(element)
        return
    body.insert(body.index(sect_pr), element)


def _add_raw_table(doc: DocxDoc, block) -> None:
    raw_ooxml = str(block.attributes.get("table_ooxml", "") or "").strip()
    if not raw_ooxml:
        return
    table_element = parse_xml(raw_ooxml.encode("utf-8"))
    _insert_body_element(doc, table_element)


# ── Injection des notes de bas de page (post-sauvegarde) ─────────────────────

_HL_TO_WVAL = {
    "orthotypo":             "yellow",
    "footnote":              "green",
    "biblio":                "cyan",
    "ai":                    "magenta",
    "exploratory_structure": "darkYellow",
}

_FOOTNOTES_XML_DECL = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
_FOOTNOTES_FALLBACK_ROOT = (
    '<w:footnotes '
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:xml="http://www.w3.org/XML/1998/namespace">'
    '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
    '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
    '</w:footnotes>'
).encode("utf-8")


def _xml_text(value: str) -> str:
    return xml_escape(value, {"\r": "&#13;"})


def _xml_attr(value: object) -> str:
    return xml_escape(str(value), {'"': '&quot;', "'": '&apos;'})


def _note_rpr_xml(
    *,
    superscript: bool = False,
    bold: bool = False,
    italic: bool = False,
    small_caps: bool = False,
    highlight_key: str | None = None,
) -> str:
    parts = [
        '<w:rPr>',
        '<w:rStyle w:val="NotedebasdepageCar"/>',
        f'<w:rFonts w:ascii="{_xml_attr(_FONT_BODY)}" w:hAnsi="{_xml_attr(_FONT_BODY)}"/>',
    ]
    if bold:
        parts.append('<w:b/>')
    if italic:
        parts.append('<w:i/>')
    if small_caps:
        parts.append('<w:smallCaps w:val="true"/>')
    if superscript:
        parts.append('<w:vertAlign w:val="superscript"/>')
    hl_val = _HL_TO_WVAL.get(highlight_key or "")
    if hl_val:
        parts.append(f'<w:highlight w:val="{_xml_attr(hl_val)}"/>')
    parts.append('</w:rPr>')
    return "".join(parts)


def _note_text_run_xml(
    text: str,
    *,
    bold: bool = False,
    italic: bool = False,
    small_caps: bool = False,
    highlight_key: str | None = None,
) -> str:
    if not text:
        return ""
    return (
        '<w:r>'
        + _note_rpr_xml(
            bold=bold,
            italic=italic,
            small_caps=small_caps,
            highlight_key=highlight_key,
        )
        + f'<w:t xml:space="preserve">{_xml_text(text)}</w:t>'
        + '</w:r>'
    )


def _build_footnote_xml(note: Note, footnote_id: int) -> str:
    """Construit un fragment OOXML <w:footnote> sans re-sérialiser tout footnotes.xml."""
    parts = [
        f'<w:footnote w:type="normal" w:id="{_xml_attr(footnote_id)}">',
        '<w:p>',
        '<w:pPr><w:pStyle w:val="Notedebasdepage"/></w:pPr>',
        '<w:r>',
        _note_rpr_xml(superscript=True),
        '<w:footnoteRef/>',
        '</w:r>',
        '<w:r>',
        _note_rpr_xml(),
        '<w:t xml:space="preserve">&#160;</w:t>',
        '</w:r>',
    ]

    if note.inlines:
        for span in note.inlines:
            if span.kind == "note_call" or not span.text:
                continue
            parts.append(
                _note_text_run_xml(
                    span.text,
                    bold=span.style.bold,
                    italic=span.style.italic,
                    small_caps=span.style.small_caps,
                    highlight_key=span.attributes.get("highlight_color"),
                )
            )
    elif note.text:
        parts.append(_note_text_run_xml(note.text))

    parts.extend(['</w:p>', '</w:footnote>'])
    return "".join(parts)


def _inject_footnotes(output_path: Path, notes: list[Note], note_id_map: dict[str, int]) -> None:
    """
    Injecte les notes dans word/footnotes.xml sans re-sérialiser le fichier entier.

    On préserve ainsi les déclarations XML, les namespaces et les attributs mc:Ignorable
    du gabarit Métopes. C'est plus robuste que ElementTree.tostring(root), qui renomme
    les préfixes w14/w15/wp14 en ns1/ns2 et peut déclencher la réparation de Word.
    """
    with zipfile.ZipFile(output_path, "r") as z:
        all_files = {name: z.read(name) for name in z.namelist()}

    fn_xml = all_files.get("word/footnotes.xml") or (_FOOTNOTES_XML_DECL + _FOOTNOTES_FALLBACK_ROOT)
    closing_tag = b"</w:footnotes>"
    if closing_tag not in fn_xml:
        raise ValueError("word/footnotes.xml ne contient pas de balise </w:footnotes> reconnaissable")

    fragments: list[str] = []
    for note in notes:
        fn_id = note_id_map.get(note.note_id)
        if fn_id is None:
            continue
        fragments.append(_build_footnote_xml(note, fn_id))

    insertion = "".join(fragments).encode("utf-8")
    all_files["word/footnotes.xml"] = fn_xml.replace(closing_tag, insertion + closing_tag, 1)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in all_files.items():
            z.writestr(name, data)


# ── Application des polices PURH sur les styles du document ──────────────────

def _apply_purh_fonts(doc: DocxDoc) -> None:
    """Remplace les polices du gabarit Métopes par les substituts PURH.

    Corps → Garamond (empattement)   |   Titraille → Calibri (sans empattement)
    """
    for style in doc.styles:
        if style.name in _BODY_STYLE_NAMES:
            style.font.name = _FONT_BODY
        elif style.name in _HEAD_STYLE_NAMES:
            style.font.name = _FONT_HEAD


# ── Exporteur principal ───────────────────────────────────────────────────────

class DocxExporter:
    """
    Exporte un Document (modèle interne) vers un fichier .docx :
    - styles de paragraphes Métopes appliqués ;
    - corrections surlignées en couleur selon leur type ;
    - notes de bas de page reconstruites.
    """

    def __init__(self, template_path: Path | None = None) -> None:
        self.template_path = template_path or _DEFAULT_TEMPLATE

    def export(self, document: Document, output_path: Path) -> Path:
        """Génère le fichier .docx et retourne son chemin."""
        template_buf = _dotm_to_docx_bytes(self.template_path)
        doc = DocxDoc(template_buf)
        self._clear_body(doc)
        _apply_purh_fonts(doc)

        # Carte note_id → entier (IDs numériques Word des footnotes)
        note_id_map: dict[str, int] = {
            note.note_id: i for i, note in enumerate(document.notes, start=1)
        }

        for block in document.blocks:
            if block.attributes.get("page_break_before"):
                _add_page_break(doc)
            if block.block_type == "table":
                _add_raw_table(doc, block)
            else:
                _add_paragraph(doc, block, note_id_map)

        if not document.blocks:
            doc.add_paragraph("")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))

        # Injection des notes de bas de page en post-traitement
        if document.notes:
            _inject_footnotes(output_path, document.notes, note_id_map)

        return output_path

    @staticmethod
    def _clear_body(doc: DocxDoc) -> None:
        """Supprime le contenu du gabarit pour le remplacer par le document."""
        body = doc.element.body
        to_remove = [c for c in body if c.tag != qn("w:sectPr")]
        for el in to_remove:
            body.remove(el)
