from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from docx import Document as DocxDoc
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm

from purh_editorial.model import Document, InlineSpan, Note

# ── Gabarit Métopes ───────────────────────────────────────────────────────────
_DEFAULT_TEMPLATE = Path(__file__).parent.parent.parent.parent / (
    "sources/editorial_rules/metopes_template_word/Commons-publishing-Metopes.dotm"
)

# Content-type .dotm → .docx (python-docx refuse les templates macro)
_CT_DOTM = b"application/vnd.ms-word.template.macroEnabledTemplate.main+xml"
_CT_DOCX = b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"

# Fichiers VBA à exclure lors de la conversion
_VBA_FILES = frozenset({"word/vbaProject.bin", "word/vbaData.xml", "word/_rels/vbaProject.bin.rels"})
# Retire les entrées <Override> VBA dans [Content_Types].xml
_VBA_CT_RE = re.compile(rb'<Override[^>]+/word/vba[^>]+/>')
# Retire les relations vbaProject dans *.rels
_VBA_REL_RE = re.compile(rb'<Relationship[^>]+vbaProject[^>]+/>')

# Namespaces OOXML
W  = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML = "http://www.w3.org/XML/1998/namespace"

# ── Correspondance couleurs de surlignage ─────────────────────────────────────
_HIGHLIGHT_MAP: dict[str, WD_COLOR_INDEX] = {
    "orthotypo": WD_COLOR_INDEX.YELLOW,
    "footnote":  WD_COLOR_INDEX.BRIGHT_GREEN,
    "biblio":    WD_COLOR_INDEX.TURQUOISE,
    "ai":        WD_COLOR_INDEX.PINK,
}

# ── Polices PURH (substituts des polices InDesign) ───────────────────────────
# Corps du texte → Garamond (empattement, analogue Chaparral Pro)
# Titraille      → Calibri  (sans empattement, analogue Josefin Sans)
_FONT_BODY = "Garamond"
_FONT_HEAD = "Calibri"

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


# ── Conversion .dotm → flux .docx ────────────────────────────────────────────

def _dotm_to_docx_bytes(dotm_path: Path) -> io.BytesIO:
    """Retourne le contenu du .dotm converti en .docx sans macros."""
    buf = io.BytesIO()
    with zipfile.ZipFile(dotm_path, "r") as src, \
         zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            if item.filename in _VBA_FILES:
                continue
            data = src.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(_CT_DOTM, _CT_DOCX)
                data = _VBA_CT_RE.sub(b"", data)
            elif item.filename.endswith(".rels"):
                data = _VBA_REL_RE.sub(b"", data)
            dst.writestr(item, data)
    buf.seek(0)
    return buf


# ── Helpers python-docx ───────────────────────────────────────────────────────

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

    # Retrait suspendu pour les entrées bibliographiques (≈ 5 mm, charte PURH)
    if style_name == "TEI_bibl_reference":
        para.paragraph_format.left_indent = Cm(0.5)
        para.paragraph_format.first_line_indent = Cm(-0.5)

    if block.inlines:
        for span in block.inlines:
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
                )
    else:
        hl = _HIGHLIGHT_MAP.get(block.attributes.get("highlight_color", ""), None)
        _add_run_with_style(para, block.text, highlight=hl)


# ── Injection des notes de bas de page (post-sauvegarde) ─────────────────────

def _build_footnote_element(note: Note, footnote_id: int) -> ET.Element:
    """Construit l'élément XML <w:footnote> pour une note."""
    ftn = ET.Element(f"{{{W}}}footnote")
    ftn.set(f"{{{W}}}type", "normal")
    ftn.set(f"{{{W}}}id", str(footnote_id))

    p = ET.SubElement(ftn, f"{{{W}}}p")
    ppr = ET.SubElement(p, f"{{{W}}}pPr")
    pstyle = ET.SubElement(ppr, f"{{{W}}}pStyle")
    pstyle.set(f"{{{W}}}val", "Notedebasdepage")

    # Marqueur footnoteRef — superscript + espace insécable après le numéro
    r_ref = ET.SubElement(p, f"{{{W}}}r")
    rpr_ref = ET.SubElement(r_ref, f"{{{W}}}rPr")
    rstyle_ref = ET.SubElement(rpr_ref, f"{{{W}}}rStyle")
    rstyle_ref.set(f"{{{W}}}val", "NotedebasdepageCar")
    vert = ET.SubElement(rpr_ref, f"{{{W}}}vertAlign")
    vert.set(f"{{{W}}}val", "superscript")
    ET.SubElement(r_ref, f"{{{W}}}footnoteRef")
    # Espace insécable après le numéro de note
    r_sp = ET.SubElement(p, f"{{{W}}}r")
    rpr_sp = ET.SubElement(r_sp, f"{{{W}}}rPr")
    rstyle_sp = ET.SubElement(rpr_sp, f"{{{W}}}rStyle")
    rstyle_sp.set(f"{{{W}}}val", "NotedebasdepageCar")
    t_sp = ET.SubElement(r_sp, f"{{{W}}}t")
    t_sp.text = " "
    t_sp.set(f"{{{XML}}}space", "preserve")

    # Contenu de la note — rendu span par span si disponible (préserve les surlignages)
    if note.inlines:
        for span in note.inlines:
            if span.kind == "note_call":
                continue
            if not span.text:
                continue
            r = ET.SubElement(p, f"{{{W}}}r")
            rpr = ET.SubElement(r, f"{{{W}}}rPr")
            rstyle = ET.SubElement(rpr, f"{{{W}}}rStyle")
            rstyle.set(f"{{{W}}}val", "NotedebasdepageCar")
            if span.style.bold:
                ET.SubElement(rpr, f"{{{W}}}b")
            if span.style.italic:
                ET.SubElement(rpr, f"{{{W}}}i")
            if span.style.small_caps:
                sc_el = ET.SubElement(rpr, f"{{{W}}}smallCaps")
                sc_el.set(f"{{{W}}}val", "true")
            # Surlignage de correction dans les notes
            hl_key = span.attributes.get("highlight_color")
            if hl_key:
                _HL_TO_WVAL = {
                    "orthotypo": "yellow",
                    "footnote":  "green",
                    "biblio":    "cyan",
                    "ai":        "magenta",
                }
                hl_val = _HL_TO_WVAL.get(hl_key)
                if hl_val:
                    hl_el = ET.SubElement(rpr, f"{{{W}}}highlight")
                    hl_el.set(f"{{{W}}}val", hl_val)
            t = ET.SubElement(r, f"{{{W}}}t")
            t.text = span.text
            t.set(f"{{{XML}}}space", "preserve")
    elif note.text:
        r_txt = ET.SubElement(p, f"{{{W}}}r")
        rpr_txt = ET.SubElement(r_txt, f"{{{W}}}rPr")
        rstyle_txt = ET.SubElement(rpr_txt, f"{{{W}}}rStyle")
        rstyle_txt.set(f"{{{W}}}val", "NotedebasdepageCar")
        t = ET.SubElement(r_txt, f"{{{W}}}t")
        t.text = note.text
        t.set(f"{{{XML}}}space", "preserve")

    return ftn


def _inject_footnotes(output_path: Path, notes: list[Note], note_id_map: dict[str, int]) -> None:
    """
    Post-traitement : injecte le contenu des notes dans word/footnotes.xml
    du DOCX déjà sauvegardé.  Reécrit le zip en conservant tous les autres fichiers.
    """
    # Lire le zip existant
    with zipfile.ZipFile(output_path, "r") as z:
        all_files = {name: z.read(name) for name in z.namelist()}

    # Parser footnotes.xml existant (contient déjà les séparateurs -1 et 0)
    ET.register_namespace("w", W)
    ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")
    ET.register_namespace("xml", XML)
    fn_xml = all_files.get("word/footnotes.xml", b"")
    if fn_xml:
        root = ET.fromstring(fn_xml)
    else:
        root = ET.Element(f"{{{W}}}footnotes")

    # Ajouter les entrées de notes
    for note in notes:
        fn_id = note_id_map.get(note.note_id)
        if fn_id is None:
            continue
        root.append(_build_footnote_element(note, fn_id))

    all_files["word/footnotes.xml"] = ET.tostring(root, encoding="unicode").encode("utf-8")

    # Réécrire le zip
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
            _add_paragraph(doc, block, note_id_map)

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
        # Word requiert au moins un paragraphe dans le corps
        if not body.findall(qn("w:p")):
            body.insert(0, OxmlElement("w:p"))
