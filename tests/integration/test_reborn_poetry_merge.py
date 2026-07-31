from __future__ import annotations

from pathlib import Path
from typing import Any

from purh_editorial.corrector import correct_docx

MANUAL_LINE_BREAK = "\v"
WD_BRIGHT_GREEN = 4


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
            "Un paragraphe normal.\r"
            "Premier vers\r"
            "Deuxième vers\r"
            "Troisième vers\r"
            "Un paragraphe de prose citée.\r"
            "Un vers isolé\r"
            "Un autre paragraphe normal.\r"
        )
        document.Paragraphs(1).Range.Style = "Normal"
        document.Paragraphs(2).Range.Style = "Citation intense"
        document.Paragraphs(3).Range.Style = "Citation intense"
        document.Paragraphs(4).Range.Style = "Citation intense"
        document.Paragraphs(5).Range.Style = "Citation"
        document.Paragraphs(6).Range.Style = "Citation intense"
        document.Paragraphs(7).Range.Style = "Normal"
        document.SaveAs2(FileName=str(path), FileFormat=16)
    finally:
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def _read_paragraphs(path: Path) -> list[tuple[str, int]]:
    word = _word_application()
    document = None
    try:
        document = word.Documents.Open(
            FileName=str(path), ReadOnly=True, AddToRecentFiles=False, Visible=False
        )
        paragraphs = []
        for paragraph in document.Paragraphs:
            text = paragraph.Range.Text
            while text.endswith(("\r", "\x07")):
                text = text[:-1]
            paragraphs.append((text, paragraph.Range.HighlightColorIndex))
        return paragraphs
    finally:
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def test_poetry_citation_block_is_merged_into_a_single_paragraph(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.docx"
    corrected = tmp_path / "corrected.docx"
    corrected_twice = tmp_path / "corrected_twice.docx"

    _create_source(source)

    first_counts = correct_docx(source, corrected)
    # 3 vers consécutifs "Citation intense" -> 2 jonctions fusionnées ; le
    # vers isolé plus loin (paragraphe 6) n'a pas de voisin "Citation
    # intense" de part et d'autre, donc aucune fusion supplémentaire.
    assert first_counts["structure.poetry.heuristique"] == 2

    paragraphs = _read_paragraphs(corrected)
    texts = [text for text, _highlight in paragraphs]
    expected_poem = (
        f"Premier vers{MANUAL_LINE_BREAK}"
        f"Deuxième vers{MANUAL_LINE_BREAK}"
        "Troisième vers"
    )
    assert expected_poem in texts
    assert "Premier vers" not in texts
    assert "Deuxième vers" not in texts
    assert "Troisième vers" not in texts
    # La prose citée ("Citation", pas "Citation intense") et le vers isolé
    # restent des paragraphes distincts, non fusionnés.
    assert "Un paragraphe de prose citée." in texts
    assert "Un vers isolé" in texts

    highlights = dict(paragraphs)
    # Le paragraphe poetique fusionne est surligne en vert clair, uniformement
    # sur tout le bloc - une couleur distincte du jaune (edition de texte) et
    # du turquoise (diagnostic), pour signaler une fusion structurelle a
    # l'editrice.
    assert highlights[expected_poem] == WD_BRIGHT_GREEN
    # Un vers isole (aucune fusion, un seul paragraphe "Citation intense") et
    # la prose citee ne sont pas concernes par le vert : leur premier
    # caractere peut rester marque en jaune par purh.style.citation_intense /
    # purh.style.citation (marqueur de tracabilite du stylage), mais jamais
    # en vert.
    assert highlights["Un vers isolé"] != WD_BRIGHT_GREEN
    assert highlights["Un paragraphe de prose citée."] != WD_BRIGHT_GREEN

    second_counts = correct_docx(corrected, corrected_twice)
    assert second_counts["structure.poetry.heuristique"] == 0
    second_texts = [text for text, _highlight in _read_paragraphs(corrected_twice)]
    assert second_texts == texts
