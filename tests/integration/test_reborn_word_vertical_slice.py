from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from purh_editorial.corrector import correct_docx
from purh_editorial.corrector.runner import RULE_IDS

WD_FORMAT_DOCUMENT_DEFAULT = 16
WD_YELLOW = 7
WD_TURQUOISE = 3


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
    bold_range = None
    first_anchor = None
    second_anchor = None
    first_note = None
    table_anchor = None
    table = None
    try:
        document = word.Documents.Add()
        body = (
            "L'auteur... boeuf « Bonjour » Voici: mot , double  espace "
            "M. Dupont XVIème siècle, la vie continue, 1ère partie etc... p. 12 n° 5 "
            "pp. 53 1 000 mot - mot, “citation” avant--après, "
            "« Que faire ? »."
        )
        document.Content.Text = (
            "Résumé\r"
            "Keywords\r"
            "Acknowledgments\r"
            f"{body}\r"
            "Élément préservé\r"
            "Appel espacé "
        )

        bold_range = document.Paragraphs(5).Range
        bold_range.Font.Bold = True

        first_anchor = document.Paragraphs(4).Range.Duplicate
        first_anchor.SetRange(
            document.Paragraphs(4).Range.End - 1,
            document.Paragraphs(4).Range.End - 1,
        )
        first_note = document.Footnotes.Add(
            Range=first_anchor,
            Text="\tvoir op. cit. et s. l., Voir Ibid., fragment",
        )

        second_anchor = document.Paragraphs(6).Range.Duplicate
        second_anchor.SetRange(
            document.Paragraphs(6).Range.End - 1,
            document.Paragraphs(6).Range.End - 1,
        )
        document.Footnotes.Add(
            Range=second_anchor,
            Text="https://exemple.org/ressource",
        )

        table_anchor = document.Range(
            Start=document.Content.End - 1,
            End=document.Content.End - 1,
        )
        table = document.Tables.Add(Range=table_anchor, NumRows=1, NumColumns=1)
        table.Cell(1, 1).Range.Text = "Tableau préservé"

        document.SaveAs2(
            FileName=str(path),
            FileFormat=WD_FORMAT_DOCUMENT_DEFAULT,
            AddToRecentFiles=False,
        )
    finally:
        table = None
        table_anchor = None
        first_note = None
        second_anchor = None
        first_anchor = None
        bold_range = None
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def _clean_main_text(text: str) -> str:
    return text.replace("\x02", "").replace("\r", "\n").replace("\x07", "")


def _find_paragraph(document: Any, fragment: str) -> Any:
    for paragraph in document.Paragraphs:
        if fragment in paragraph.Range.Text:
            return paragraph
    raise AssertionError(f"Paragraphe introuvable : {fragment}")


def _range_for(paragraph: Any, fragment: str, offset: int = 0, length: int | None = None) -> Any:
    paragraph_text = paragraph.Range.Text
    index = paragraph_text.index(fragment) + offset
    size = len(fragment) - offset if length is None else length
    target = paragraph.Range.Duplicate
    target.SetRange(
        paragraph.Range.Start + index,
        paragraph.Range.Start + index + size,
    )
    return target


def _assert_corrected_document(path: Path) -> None:
    word = _word_application()
    document = None
    body_paragraph = None
    ellipsis = None
    roman = None
    suffix = None
    century = None
    numero_o = None
    numero = None
    incise = None
    straight_quote = None
    double_dash = None
    quote_punctuation = None
    first_note = None
    abbreviation = None
    capital = None
    latin = None
    final_point = None
    first_note_start = None
    first_reference = None
    first_preceding = None
    second_reference = None
    second_preceding = None
    second_start = None
    second_end = None
    bold_paragraph = None
    table_range = None
    try:
        document = word.Documents.Open(
            FileName=str(path),
            ReadOnly=True,
            AddToRecentFiles=False,
            Visible=False,
        )
        main_text = _clean_main_text(document.StoryRanges(1).Text)
        assert "Résumé\nKeywords\nAcknowledgments" in main_text
        assert (
            "L’auteur… bœuf «\u00a0Bonjour\u00a0» Voici\u00a0: mot, double espace "
            "M.\u00a0Dupont xvie siècle, la vie continue, 1re partie etc. p.\u00a012 "
            "no\u00a05 p.\u00a053 1\u00a0000 mot - mot, “citation” avant--après, "
            "«\u00a0Que faire\u00a0?\u00a0»."
        ) in main_text
        assert "Appel espacé " in main_text

        body_paragraph = _find_paragraph(document, "L’auteur")
        ellipsis = _range_for(body_paragraph, "…")
        assert ellipsis.HighlightColorIndex == WD_YELLOW

        roman = _range_for(body_paragraph, "xvie", length=3)
        suffix = _range_for(body_paragraph, "xvie", offset=3, length=1)
        century = _range_for(body_paragraph, "xvie")
        assert roman.Font.SmallCaps == -1
        assert roman.Font.Superscript == 0
        assert suffix.Font.SmallCaps == 0
        assert suffix.Font.Superscript == -1
        assert century.HighlightColorIndex == WD_YELLOW
        assert "la vie continue" in body_paragraph.Range.Text

        numero_o = _range_for(body_paragraph, "no\u00a05", offset=1, length=1)
        numero = _range_for(body_paragraph, "no\u00a05", length=3)
        assert numero_o.Font.Superscript == -1
        assert numero.HighlightColorIndex == WD_YELLOW

        incise = _range_for(body_paragraph, "mot - mot", offset=3, length=3)
        assert incise.Text == " - "
        assert incise.HighlightColorIndex == WD_TURQUOISE

        straight_quote = _range_for(body_paragraph, "“citation”")
        assert straight_quote.HighlightColorIndex == WD_TURQUOISE
        double_dash = _range_for(body_paragraph, "--")
        assert double_dash.HighlightColorIndex == WD_TURQUOISE
        quote_punctuation = _range_for(
            body_paragraph,
            "«\u00a0Que faire\u00a0?\u00a0».",
        )
        assert quote_punctuation.HighlightColorIndex == WD_TURQUOISE

        first_note = document.Footnotes(1).Range
        assert first_note.Text.startswith("Voir")
        assert f"op.\u00a0cit." in first_note.Text
        assert f"s.\u00a0l." in first_note.Text
        assert "Voir ibid., fragment." in first_note.Text
        abbreviation = first_note.Duplicate
        abbreviation_index = first_note.Text.index("op.\u00a0cit.")
        abbreviation.SetRange(
            first_note.Start + abbreviation_index,
            first_note.Start + abbreviation_index + len("op.\u00a0cit."),
        )
        assert abbreviation.HighlightColorIndex == WD_YELLOW
        capital = first_note.Duplicate
        capital.SetRange(first_note.Start, first_note.Start + 1)
        assert capital.Text == "V"
        assert capital.HighlightColorIndex == WD_YELLOW
        latin = first_note.Duplicate
        latin_index = first_note.Text.index("ibid.")
        latin.SetRange(
            first_note.Start + latin_index,
            first_note.Start + latin_index + len("ibid."),
        )
        assert latin.HighlightColorIndex == WD_YELLOW
        final_point = first_note.Duplicate
        final_index = first_note.Text.rstrip("\r").rfind(".")
        final_point.SetRange(
            first_note.Start + final_index,
            first_note.Start + final_index + 1,
        )
        assert final_point.HighlightColorIndex == WD_YELLOW
        first_note_start = first_note.Duplicate
        first_note_start.SetRange(first_note.Start, first_note.Start + 1)
        assert first_note_start.HighlightColorIndex == WD_YELLOW

        first_reference = document.Footnotes(1).Reference
        first_preceding = first_reference.Duplicate
        first_preceding.SetRange(first_reference.Start - 1, first_reference.Start)
        assert first_preceding.Text == "."
        assert first_preceding.HighlightColorIndex == WD_TURQUOISE

        second_reference = document.Footnotes(2).Reference
        second_preceding = second_reference.Duplicate
        second_preceding.SetRange(second_reference.Start - 1, second_reference.Start)
        assert second_preceding.Text == " "
        assert second_preceding.HighlightColorIndex == WD_TURQUOISE
        assert document.Footnotes(2).Range.Text.startswith("https://")
        second_start = document.Footnotes(2).Range.Duplicate
        second_start.SetRange(second_start.Start, second_start.Start + 1)
        assert second_start.HighlightColorIndex == WD_TURQUOISE
        second_end = document.Footnotes(2).Range.Duplicate
        second_text = document.Footnotes(2).Range.Text.rstrip("\r")
        second_end.SetRange(
            second_end.Start + len(second_text) - 1,
            second_end.Start + len(second_text),
        )
        assert second_end.HighlightColorIndex == WD_TURQUOISE

        bold_paragraph = _find_paragraph(document, "Élément préservé")
        assert bold_paragraph.Range.Font.Bold == -1
        assert document.Tables.Count == 1
        table_range = document.Tables(1).Cell(1, 1).Range
        assert "Tableau préservé" in table_range.Text
    finally:
        table_range = None
        bold_paragraph = None
        second_end = None
        second_start = None
        second_preceding = None
        second_reference = None
        first_preceding = None
        first_reference = None
        first_note_start = None
        final_point = None
        latin = None
        capital = None
        abbreviation = None
        first_note = None
        quote_punctuation = None
        double_dash = None
        straight_quote = None
        incise = None
        numero = None
        numero_o = None
        century = None
        suffix = None
        roman = None
        ellipsis = None
        body_paragraph = None
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def _expected_first_counts() -> dict[str, int]:
    counts = {rule_id: 0 for rule_id in RULE_IDS}
    counts.update(
        {
            "purh.apostrophe": 1,
            "purh.points_suspension": 2,
            "purh.ligature.oe": 1,
            "purh.guillemets.espace_apres_ouvrant": 2,
            "purh.guillemets.espace_avant_fermant": 2,
            "purh.espaces.avant_ponct_forte": 2,
            "purh.espaces.avant_ponct_faible": 1,
            "purh.espaces.double": 1,
            "purh.civilite": 1,
            "purh.siecles": 1,
            "purh.ordinaux": 1,
            "purh.abreviations.etc": 1,
            "purh.pagination.espace": 2,
            "purh.numero": 1,
            "purh.abreviations.redoublement": 1,
            "purh.nombres.milliers": 1,
            "purh.siecles.style": 1,
            "purh.numero.style": 1,
            "purh.ordinaux.style": 1,
            "purh.note.espace_initiale": 1,
            "purh.note.espace_op_cit": 1,
            "purh.note.espace_sans_lieu_date": 1,
            "purh.note.italique_latin": 2,
            "purh.tiret.incise.diagnostic": 1,
            "purh.note.appel.placement": 1,
            "purh.note.appel.espace_avant": 1,
            "purh.guillemets.droits": 1,
            "purh.tiret.double": 1,
            "purh.guillemets.ponctuation_fermante": 1,
            "purh.note.majuscule_initiale": 1,
            "purh.note.abreviation_latine": 1,
            "purh.note.ponctuation_finale": 1,
            "purh.note.diagnostic.debut_minuscule": 1,
            "purh.note.diagnostic.ponctuation_finale_ambigue": 1,
            "structure.frontmatter.abstract": 1,
            "structure.frontmatter.keywords": 1,
            "structure.frontmatter.acknowledgment": 1,
        }
    )
    return counts


def test_reborn_word_vertical_slice(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    corrected = tmp_path / "corrected.docx"
    corrected_twice = tmp_path / "corrected_twice.docx"

    _create_source(source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()

    first_counts = correct_docx(source, corrected)
    assert first_counts == _expected_first_counts()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    _assert_corrected_document(corrected)

    second_counts = correct_docx(corrected, corrected_twice)
    automatic_ids = set(RULE_IDS) - {
        "purh.tiret.incise.diagnostic",
        "purh.note.appel.placement",
        "purh.note.appel.espace_avant",
        "purh.guillemets.droits",
        "purh.tiret.double",
        "purh.guillemets.ponctuation_fermante",
        "purh.note.diagnostic.debut_minuscule",
        "purh.note.diagnostic.ponctuation_finale_ambigue",
        "structure.frontmatter.abstract",
        "structure.frontmatter.keywords",
        "structure.frontmatter.acknowledgment",
    }
    assert all(second_counts[rule_id] == 0 for rule_id in automatic_ids)
    assert second_counts["purh.tiret.incise.diagnostic"] == 1
    assert second_counts["purh.note.appel.placement"] == 1
    assert second_counts["purh.note.appel.espace_avant"] == 1
    assert second_counts["purh.guillemets.droits"] == 1
    assert second_counts["purh.tiret.double"] == 1
    assert second_counts["purh.guillemets.ponctuation_fermante"] == 1
    assert second_counts["purh.note.diagnostic.debut_minuscule"] == 1
    assert second_counts["purh.note.diagnostic.ponctuation_finale_ambigue"] == 1
    assert second_counts["structure.frontmatter.abstract"] == 1
    assert second_counts["structure.frontmatter.keywords"] == 1
    assert second_counts["structure.frontmatter.acknowledgment"] == 1
    _assert_corrected_document(corrected_twice)
