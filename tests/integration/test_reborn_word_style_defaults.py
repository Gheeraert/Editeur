from __future__ import annotations

from pathlib import Path
from typing import Any

from purh_editorial.corrector import correct_docx

WD_ALIGN_PARAGRAPH_LEFT = 0
WD_ALIGN_PARAGRAPH_CENTER = 1
WD_ALIGN_PARAGRAPH_JUSTIFY = 3
WD_YELLOW = 7
CM_TO_POINTS = 72.0 / 2.54


def _word_application() -> Any:
    try:
        from win32com.client import DispatchEx
    except ImportError as exc:
        raise AssertionError("pywin32 n'est pas importable.") from exc
    try:
        word = DispatchEx("Word.Application")
    except Exception as exc:
        raise AssertionError(
            "Microsoft Word ne peut pas être lancé pour le test d'intégration."
        ) from exc
    word.Visible = False
    word.DisplayAlerts = 0
    return word


def _create_source(path: Path) -> None:
    word = _word_application()
    document = None
    try:
        document = word.Documents.Add()
        document.Content.Text = (
            "Un titre de chapitre\r"
            "Une phrase citée en bloc.\r"
            "Un vers de poésie\r"
            "Un paragraphe normal.\r"
            "Un paragraphe de corps de texte.\r"
        )
        document.Paragraphs(1).Range.Style = "Titre"
        document.Paragraphs(2).Range.Style = "Citation"
        document.Paragraphs(3).Range.Style = "Citation intense"
        document.Paragraphs(4).Range.Style = "Normal"
        document.Paragraphs(5).Range.Style = "Corps de texte"
        # Retrait non nul force explicitement sur le style lui-meme, pour
        # verifier que purh.style.corps_de_texte le ramene bien a zero -
        # sinon ce style herite deja de "Normal" (Times New Roman 12 apres
        # correction, retrait 0 par defaut) et le test ne verifierait rien
        # de plus que purh.style.normal.
        document.Styles("Corps de texte").ParagraphFormat.LeftIndent = 20

        anchor = document.Paragraphs(4).Range.Duplicate
        anchor.SetRange(
            document.Paragraphs(4).Range.End - 1,
            document.Paragraphs(4).Range.End - 1,
        )
        document.Footnotes.Add(Range=anchor, Text="Une note de bas de page.")
        # Ecart force explicitement sur le style lui-meme (au lieu de
        # dependre du gabarit par defaut, qui herite deja de "Normal" une
        # fois celui-ci corrige et se retrouverait conforme sans que la
        # regle n'ait rien eu a faire) : verifie que purh.style.note_bas_de_page
        # corrige bien un ecart qui lui est propre.
        document.Styles("Note de bas de page").Font.Name = "Arial"
        document.Styles("Note de bas de page").Font.Size = 9
        document.Styles("Appel note de bas de p.").Font.Name = "Arial"
        document.Styles("Appel note de bas de p.").Font.Italic = True

        document.SaveAs2(FileName=str(path), FileFormat=16)
    finally:
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def _read_style_properties(path: Path) -> dict[str, dict[str, Any]]:
    word = _word_application()
    document = None
    try:
        document = word.Documents.Open(
            FileName=str(path), ReadOnly=True, AddToRecentFiles=False, Visible=False
        )
        result: dict[str, dict[str, Any]] = {}
        for name in (
            "Titre",
            "Citation",
            "Citation intense",
            "Normal",
            "Corps de texte",
            "Note de bas de page",
        ):
            style = document.Styles(name)
            font = style.Font
            paragraph_format = style.ParagraphFormat
            result[name] = {
                "font_name": font.Name,
                "font_size": font.Size,
                "bold": font.Bold,
                "alignment": paragraph_format.Alignment,
                "left_indent": paragraph_format.LeftIndent,
                "first_line_indent": paragraph_format.FirstLineIndent,
            }
        reference_style = document.Styles("Appel note de bas de p.")
        result["Appel note de bas de p."] = {
            "font_name": reference_style.Font.Name,
            "superscript": reference_style.Font.Superscript,
            "italic": reference_style.Font.Italic,
            "bold": reference_style.Font.Bold,
        }
        return result
    finally:
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def _read_main_text_highlight_indexes(path: Path) -> set[int]:
    # Lecture caractere par caractere (pas paragraphe.Range.HighlightColorIndex,
    # qui renvoie une valeur "indefinie" des qu'un paragraphe melange deux
    # couleurs, ex. un diagnostic turquoise legitime a cote du texte) : on
    # veut verifier precisement l'absence du jaune (marqueur de stylage
    # retire), sans se laisser perturber par d'autres surlignages valides
    # deja presents pour d'autres regles (ex. purh.note.appel.placement).
    word = _word_application()
    document = None
    try:
        document = word.Documents.Open(
            FileName=str(path), ReadOnly=True, AddToRecentFiles=False, Visible=False
        )
        indexes: set[int] = set()
        for paragraph in document.Paragraphs:
            for offset in range(paragraph.Range.Start, paragraph.Range.End):
                character = document.Range(offset, offset + 1)
                indexes.add(character.HighlightColorIndex)
        return indexes
    finally:
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def test_purh_style_defaults_are_applied_and_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    corrected = tmp_path / "corrected.docx"
    corrected_twice = tmp_path / "corrected_twice.docx"

    _create_source(source)

    first_counts = correct_docx(source, corrected, reapply_normal_style=True)
    assert first_counts["purh.style.titre"] == 1
    assert first_counts["purh.style.citation"] == 1
    assert first_counts["purh.style.citation_intense"] == 1
    # 2 paragraphes "Normal" : celui du corps explicitement style, plus le
    # paragraphe vide final implicite laisse par Content.Text se terminant
    # par un retour a la ligne.
    assert first_counts["purh.style.normal"] == 2
    assert first_counts["purh.style.corps_de_texte"] == 1
    assert first_counts["purh.style.note_bas_de_page"] == 1
    assert first_counts["purh.style.appel_de_note"] == 1
    # Reapplication du style "Normal" sur les 2 memes paragraphes (cf.
    # commentaire ci-dessus) : contournement d'un artefact de rendu Word,
    # pas une correction editoriale - toujours appliquee, meme quand la
    # definition du style n'a pas change (donc pas comptee comme "0" au
    # deuxieme passage, contrairement aux autres regles de stylage).
    assert first_counts["purh.style.normal_refresh"] == 2

    # Mise en forme des styles (police, casse, attributs de caractere) :
    # aucune modification de texte, donc aucun surlignage - la doctrine de
    # tracabilite (AGENTS.md 2.6) ne vise que les modifications qui touchent
    # le texte. Le marqueur jaune pose auparavant sur le premier caractere de
    # chaque paragraphe stylise a ete retire.
    assert WD_YELLOW not in _read_main_text_highlight_indexes(corrected)

    properties = _read_style_properties(corrected)

    for name in (
        "Titre",
        "Citation",
        "Citation intense",
        "Normal",
        "Corps de texte",
        "Note de bas de page",
    ):
        assert properties[name]["font_name"] == "Times New Roman"

    assert properties["Titre"]["font_size"] == 14
    assert properties["Titre"]["bold"] == -1
    assert properties["Titre"]["alignment"] == WD_ALIGN_PARAGRAPH_CENTER

    assert properties["Citation"]["font_size"] == 10
    assert properties["Citation"]["alignment"] == WD_ALIGN_PARAGRAPH_JUSTIFY
    # Word arrondit LeftIndent au vingtieme de point (twip) le plus proche :
    # tolerance large pour absorber cette imprecision, pas la nostre.
    assert abs(properties["Citation"]["left_indent"] - CM_TO_POINTS) < 0.5

    assert properties["Citation intense"]["font_size"] == 10
    assert properties["Citation intense"]["alignment"] == WD_ALIGN_PARAGRAPH_LEFT
    assert abs(properties["Citation intense"]["left_indent"] - CM_TO_POINTS) < 0.5

    assert properties["Normal"]["font_size"] == 12

    assert properties["Corps de texte"]["font_size"] == 12
    assert properties["Corps de texte"]["left_indent"] == 0.0
    assert properties["Corps de texte"]["first_line_indent"] == 0.0

    assert properties["Note de bas de page"]["font_size"] == 10

    reference = properties["Appel note de bas de p."]
    assert reference["font_name"] == "Times New Roman"
    assert reference["superscript"] == -1
    assert reference["italic"] == 0
    assert reference["bold"] == 0

    second_counts = correct_docx(corrected, corrected_twice, reapply_normal_style=True)
    for rule_id in (
        "purh.style.titre",
        "purh.style.citation",
        "purh.style.citation_intense",
        "purh.style.normal",
        "purh.style.corps_de_texte",
        "purh.style.note_bas_de_page",
        "purh.style.appel_de_note",
    ):
        assert second_counts[rule_id] == 0
    # A l'inverse des autres regles de stylage, purh.style.normal_refresh
    # n'est pas conditionnee par un ecart de definition de style : elle
    # reapplique le style a chaque passage, silencieusement.
    assert second_counts["purh.style.normal_refresh"] == 2


def test_normal_style_reapplication_is_opt_in_and_disabled_by_default(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.docx"
    corrected = tmp_path / "corrected.docx"

    _create_source(source)

    # Case a cocher decochee par defaut dans l'interface (gui.py) : sans
    # argument explicite, correct_docx ne doit pas reappliquer "Normal".
    counts = correct_docx(source, corrected)
    assert counts["purh.style.normal_refresh"] == 0
