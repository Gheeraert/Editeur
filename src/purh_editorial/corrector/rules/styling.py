from __future__ import annotations

from dataclasses import dataclass

# Noms locaux (français) des styles Word natifs vises par la maquette PURH.
# Un nom de style seul est ambigu (un document peut contenir un style
# personnalise portant le meme nom) : la garde "style natif" se fait via
# Style.BuiltIn au moment de l'application (word_document.py), pas ici.
STYLE_TITRE = "Titre"
STYLE_CITATION = "Citation"
STYLE_CITATION_INTENSE = "Citation intense"
STYLE_NORMAL = "Normal"
STYLE_CORPS_DE_TEXTE = "Corps de texte"
STYLE_NOTE_BAS_DE_PAGE = "Note de bas de page"
STYLE_APPEL_NOTE = "Appel note de bas de p."

WD_ALIGN_PARAGRAPH_LEFT = 0
WD_ALIGN_PARAGRAPH_CENTER = 1
WD_ALIGN_PARAGRAPH_JUSTIFY = 3

# 1 pouce = 72 points = 2,54 cm (unite native de ParagraphFormat.LeftIndent).
CM_TO_POINTS = 72.0 / 2.54

PURH_FONT_NAME = "Times New Roman"


@dataclass(frozen=True)
class ParagraphStyleSpec:
    rule_id: str
    style_name: str
    font_size: float
    bold: bool | None = None
    alignment: int | None = None
    left_indent_points: float | None = None
    first_line_indent_points: float | None = None


# Gabarit minimal PURH confirme par l'editrice le 2026-07-31 (cf. echange
# autour de la branche "stylage") : Times New Roman partout, tailles et
# alignements par style ci-dessous. "Citation" est justifiee (bloc de prose
# cite) ; "Citation intense" reprend la meme mise en forme mais sans
# justification, car utilisee pour la poesie (des vers justifies deformeraient
# la mise en page du poeme). "Corps de texte" est identique a "Normal" a
# l'exception du retrait, mis a zero explicitement.
PARAGRAPH_STYLE_SPECS = (
    ParagraphStyleSpec(
        rule_id="purh.style.titre",
        style_name=STYLE_TITRE,
        font_size=14,
        bold=True,
        alignment=WD_ALIGN_PARAGRAPH_CENTER,
    ),
    ParagraphStyleSpec(
        rule_id="purh.style.citation",
        style_name=STYLE_CITATION,
        font_size=10,
        alignment=WD_ALIGN_PARAGRAPH_JUSTIFY,
        left_indent_points=CM_TO_POINTS,
    ),
    ParagraphStyleSpec(
        rule_id="purh.style.citation_intense",
        style_name=STYLE_CITATION_INTENSE,
        font_size=10,
        alignment=WD_ALIGN_PARAGRAPH_LEFT,
        left_indent_points=CM_TO_POINTS,
    ),
    ParagraphStyleSpec(
        rule_id="purh.style.normal",
        style_name=STYLE_NORMAL,
        font_size=12,
    ),
    ParagraphStyleSpec(
        rule_id="purh.style.corps_de_texte",
        style_name=STYLE_CORPS_DE_TEXTE,
        font_size=12,
        left_indent_points=0.0,
        first_line_indent_points=0.0,
    ),
    ParagraphStyleSpec(
        rule_id="purh.style.note_bas_de_page",
        style_name=STYLE_NOTE_BAS_DE_PAGE,
        font_size=10,
    ),
)

FOOTNOTE_REFERENCE_STYLE_RULE_ID = "purh.style.appel_de_note"

PARAGRAPH_STYLE_RULE_IDS = tuple(spec.rule_id for spec in PARAGRAPH_STYLE_SPECS)
STYLING_RULE_IDS = PARAGRAPH_STYLE_RULE_IDS + (FOOTNOTE_REFERENCE_STYLE_RULE_ID,)


def _is_true(value: object) -> bool:
    return value is True or value == -1


def _is_false(value: object) -> bool:
    return value is False or value == 0


def paragraph_style_needs_change(style: object, spec: ParagraphStyleSpec) -> bool:
    font = style.Font  # type: ignore[attr-defined]
    if font.Name != PURH_FONT_NAME:
        return True
    if round(float(font.Size), 1) != spec.font_size:
        return True
    if spec.bold is not None and _is_true(font.Bold) != spec.bold:
        return True
    paragraph_format = style.ParagraphFormat  # type: ignore[attr-defined]
    if spec.alignment is not None and paragraph_format.Alignment != spec.alignment:
        return True
    # Tolerance large (0,5 pt) sur les retraits : Word arrondit LeftIndent/
    # FirstLineIndent au vingtieme de point (twip) le plus proche a
    # l'enregistrement, donc une comparaison stricte ou au dixieme de point
    # peut osciller entre deux runs pour la meme valeur cible et casser
    # l'idempotence (un deuxieme passage recompterait une correction).
    if spec.left_indent_points is not None and abs(
        float(paragraph_format.LeftIndent) - spec.left_indent_points
    ) >= 0.5:
        return True
    if spec.first_line_indent_points is not None and abs(
        float(paragraph_format.FirstLineIndent) - spec.first_line_indent_points
    ) >= 0.5:
        return True
    return False


def apply_paragraph_style_spec(style: object, spec: ParagraphStyleSpec) -> None:
    font = style.Font  # type: ignore[attr-defined]
    font.Name = PURH_FONT_NAME
    font.Size = spec.font_size
    if spec.bold is not None:
        font.Bold = spec.bold
    paragraph_format = style.ParagraphFormat  # type: ignore[attr-defined]
    if spec.alignment is not None:
        paragraph_format.Alignment = spec.alignment
    if spec.left_indent_points is not None:
        paragraph_format.LeftIndent = spec.left_indent_points
    if spec.first_line_indent_points is not None:
        paragraph_format.FirstLineIndent = spec.first_line_indent_points


def footnote_reference_style_needs_change(style: object) -> bool:
    font = style.Font  # type: ignore[attr-defined]
    return bool(
        font.Name != PURH_FONT_NAME
        or not _is_true(font.Superscript)
        or not _is_false(font.Italic)
        or not _is_false(font.Bold)
    )


def apply_footnote_reference_style(style: object) -> None:
    font = style.Font  # type: ignore[attr-defined]
    font.Name = PURH_FONT_NAME
    font.Superscript = True
    font.Italic = False
    font.Bold = False
