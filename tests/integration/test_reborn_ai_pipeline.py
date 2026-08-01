from __future__ import annotations

from pathlib import Path
from typing import Any

from purh_editorial.corrector import correct_docx
from purh_editorial.corrector.ai import AISuggestion, FakeAIClient

WD_NO_HIGHLIGHT = 0
WD_DARK_YELLOW = 14

HEADING_TEXT = "Un titre anormalement bavard sujet a discussion possible ici"
# Sans contraction ni guillemet : evite que purh.apostrophe (ou toute autre
# regle deterministe qui s'execute avant l'IA, dans la meme boucle par
# paragraphe) ne modifie ce texte avant que le faux client ne le recoive -
# l'IA analyse volontairement le texte deja corrige par le moteur
# deterministe, jamais le texte brut d'origine.
MAIN_TEXT = (
    "Ce paragraphe repete de maniere redondante et lourde la meme idee, "
    "encore et encore, sans jamais varier la formulation employee."
)
SHORT_TEXT = "Un court paragraphe."
BIBLIOGRAPHY_HEADING = "Bibliographie"
BIBLIOGRAPHY_ENTRY = "Dupont, 2020."


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
            f"{HEADING_TEXT}\r"
            f"{MAIN_TEXT}\r"
            f"{SHORT_TEXT}\r"
            f"{BIBLIOGRAPHY_HEADING}\r"
            f"{BIBLIOGRAPHY_ENTRY}\r"
        )
        document.Paragraphs(1).Range.Style = "Titre 1"
        document.Paragraphs(2).Range.Style = "Normal"
        document.Paragraphs(3).Range.Style = "Normal"
        document.Paragraphs(4).Range.Style = "Titre 1"
        document.Paragraphs(5).Range.Style = "Normal"
        document.SaveAs2(FileName=str(path), FileFormat=16)
    finally:
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def _read_paragraphs(path: Path) -> list[tuple[str, int, int]]:
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
            paragraphs.append(
                (text, paragraph.Range.HighlightColorIndex, paragraph.Range.Start)
            )
        return paragraphs
    finally:
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def _make_fake_client() -> FakeAIClient:
    return FakeAIClient(
        responses={
            HEADING_TEXT: [
                AISuggestion(
                    rule_id="ia.style.lourdeur",
                    original_text=HEADING_TEXT,
                    suggested_text="peu importe",
                    explanation="Ne devrait jamais être appliqué (paragraphe de titre).",
                )
            ],
            MAIN_TEXT: [
                AISuggestion(
                    rule_id="ia.style.lourdeur",
                    original_text="repete de maniere redondante et lourde",
                    suggested_text="exprime",
                    explanation="Répétition et lourdeur de style.",
                )
            ],
            SHORT_TEXT: [
                AISuggestion(
                    rule_id="ia.style.lourdeur",
                    original_text=SHORT_TEXT,
                    suggested_text="peu importe",
                    explanation="Ne devrait jamais être appliqué (paragraphe trop court).",
                )
            ],
            BIBLIOGRAPHY_ENTRY: [
                AISuggestion(
                    rule_id="ia.biblio.reference_incomplete",
                    original_text=BIBLIOGRAPHY_ENTRY,
                    suggested_text="Dupont, 2020, Paris, PUF.",
                    explanation="Ville et éditeur manquants.",
                )
            ],
        }
    )


def test_ai_suggestions_are_applied_only_where_expected(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    corrected = tmp_path / "corrected.docx"
    _create_source(source)

    ai_client = _make_fake_client()
    counts = correct_docx(source, corrected, ai_client=ai_client)

    # Bibliographie : pas de seuil de longueur, une entree courte est bien
    # analysee et la suggestion appliquee.
    assert counts["ia.biblio.reference_incomplete"] == 1
    # Texte courant assez long : suggestion appliquee. Si le titre ou le
    # paragraphe trop court avaient ete interroges a tort, ce compte serait
    # de 2 (le faux client a une reponse prete pour les deux).
    assert counts["ia.style.lourdeur"] == 1

    paragraphs = _read_paragraphs(corrected)
    by_text = {text: highlight for text, highlight, _start in paragraphs}

    assert by_text[HEADING_TEXT] == WD_NO_HIGHLIGHT
    assert by_text[SHORT_TEXT] == WD_NO_HIGHLIGHT

    word = _word_application()
    document = None
    try:
        document = word.Documents.Open(
            FileName=str(corrected), ReadOnly=True, AddToRecentFiles=False, Visible=False
        )
        assert document.Comments.Count == 2
        comment_texts = [document.Comments(i + 1).Range.Text for i in range(2)]
        assert any("ia.style.lourdeur" in text for text in comment_texts)
        assert any("ia.biblio.reference_incomplete" in text for text in comment_texts)
    finally:
        if document is not None:
            document.Close(SaveChanges=False)
        document = None
        word.Quit()
        word = None


def test_ai_counters_are_absent_from_report_when_no_client_is_provided(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.docx"
    corrected = tmp_path / "corrected.docx"
    _create_source(source)

    counts = correct_docx(source, corrected)

    assert "ia.style.lourdeur" not in counts
    assert "ia.biblio.reference_incomplete" not in counts


def test_ai_is_skipped_without_crashing_when_client_reports_unavailable(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.docx"
    corrected = tmp_path / "corrected.docx"
    _create_source(source)

    unavailable_client = FakeAIClient(available=False)
    counts = correct_docx(source, corrected, ai_client=unavailable_client)

    assert counts["ia.style.lourdeur"] == 0
    assert counts["ia.biblio.reference_incomplete"] == 0
