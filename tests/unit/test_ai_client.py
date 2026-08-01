from __future__ import annotations

import re
from pathlib import Path

from purh_editorial.corrector.ai import (
    AI_BIBLIOGRAPHY_RULE_IDS,
    AI_MAIN_TEXT_RULE_IDS,
    AI_PARAGRAPH_RULE_IDS,
    AI_RULE_IDS,
    AI_RULE_ID_SET,
    AISuggestion,
    FakeAIClient,
    locate_suggestion,
    parse_ai_response,
)

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE_PATH = ROOT / "docs" / "CATALOGUE_REGLES_IA.md"


def test_ai_rule_ids_match_catalogue_document() -> None:
    catalogue_text = CATALOGUE_PATH.read_text(encoding="utf-8")
    documented_ids = set(re.findall(r"### `(ia\.[a-z_.]+)`", catalogue_text))
    assert documented_ids == AI_RULE_ID_SET


def test_paragraph_scoped_rule_ids_exclude_document_wide_terminology_rule() -> None:
    assert "ia.terminologie.incoherence" not in AI_MAIN_TEXT_RULE_IDS
    assert "ia.terminologie.incoherence" not in AI_BIBLIOGRAPHY_RULE_IDS


def test_main_text_and_bibliography_rule_ids_are_disjoint() -> None:
    assert set(AI_MAIN_TEXT_RULE_IDS).isdisjoint(AI_BIBLIOGRAPHY_RULE_IDS)


def test_ai_paragraph_rule_ids_is_union_of_main_text_and_bibliography() -> None:
    assert set(AI_PARAGRAPH_RULE_IDS) == set(AI_MAIN_TEXT_RULE_IDS) | set(
        AI_BIBLIOGRAPHY_RULE_IDS
    )
    assert set(AI_PARAGRAPH_RULE_IDS) == AI_RULE_ID_SET - {"ia.terminologie.incoherence"}
    # Le catalogue liste les identifiants dans le même ordre que le code, pour
    # que la table de synthèse du document reste alignée visuellement.
    assert len(AI_RULE_IDS) == len(set(AI_RULE_IDS))


def test_locate_suggestion_finds_exact_substring() -> None:
    paragraph = "Il s'avère avéré que le style est lourd."
    suggestion = AISuggestion(
        rule_id="ia.style.lourdeur",
        original_text="Il s'avère avéré que",
        suggested_text="Il est avéré que",
        explanation="Pléonasme.",
    )
    located = locate_suggestion(paragraph, suggestion)
    assert located is not None
    assert located.start == 0
    assert located.end == len("Il s'avère avéré que")
    assert paragraph[located.start : located.end] == suggestion.original_text


def test_locate_suggestion_returns_none_when_text_absent() -> None:
    suggestion = AISuggestion(
        rule_id="ia.style.lourdeur",
        original_text="passage qui n'existe pas",
        suggested_text="peu importe",
        explanation="peu importe",
    )
    assert locate_suggestion("Un tout autre paragraphe.", suggestion) is None


def test_locate_suggestion_returns_none_for_empty_original_text() -> None:
    suggestion = AISuggestion(
        rule_id="ia.style.lourdeur",
        original_text="",
        suggested_text="x",
        explanation="x",
    )
    assert locate_suggestion("Un paragraphe.", suggestion) is None


def test_parse_ai_response_accepts_valid_payload() -> None:
    raw = (
        '[{"rule_id": "ia.biblio.reference_incomplete", '
        '"original_text": "Dupont, 2020", '
        '"suggested_text": "Dupont, 2020, Paris, PUF", '
        '"explanation": "Ville et éditeur manquants."}]'
    )
    suggestions = parse_ai_response(raw)
    assert len(suggestions) == 1
    assert suggestions[0].rule_id == "ia.biblio.reference_incomplete"


def test_parse_ai_response_ignores_unknown_rule_id() -> None:
    raw = (
        '[{"rule_id": "ia.inexistante", "original_text": "x", '
        '"suggested_text": "y", "explanation": "z"}]'
    )
    assert parse_ai_response(raw) == []


def test_parse_ai_response_ignores_entry_missing_field() -> None:
    raw = '[{"rule_id": "ia.style.lourdeur", "original_text": "x"}]'
    assert parse_ai_response(raw) == []


def test_parse_ai_response_keeps_valid_entries_and_drops_invalid_ones() -> None:
    raw = (
        "["
        '{"rule_id": "ia.style.lourdeur", "original_text": "a", '
        '"suggested_text": "b", "explanation": "c"},'
        '{"rule_id": "ia.inconnue", "original_text": "a", '
        '"suggested_text": "b", "explanation": "c"}'
        "]"
    )
    suggestions = parse_ai_response(raw)
    assert len(suggestions) == 1
    assert suggestions[0].rule_id == "ia.style.lourdeur"


def test_parse_ai_response_returns_empty_list_on_invalid_json() -> None:
    assert parse_ai_response("ceci n'est pas du JSON") == []


def test_parse_ai_response_wraps_bare_object_into_single_suggestion() -> None:
    # Constaté avec Mistral Small 3.2 en local : le modèle renvoie parfois
    # un objet nu au lieu d'un tableau à un élément, malgré la consigne.
    raw = (
        '{"rule_id": "ia.style.lourdeur", "original_text": "a", '
        '"suggested_text": "b", "explanation": "c"}'
    )
    suggestions = parse_ai_response(raw)
    assert len(suggestions) == 1
    assert suggestions[0].rule_id == "ia.style.lourdeur"


def test_parse_ai_response_unwraps_object_with_list_value() -> None:
    raw = (
        '{"suggestions": [{"rule_id": "ia.style.lourdeur", "original_text": "a", '
        '"suggested_text": "b", "explanation": "c"}]}'
    )
    suggestions = parse_ai_response(raw)
    assert len(suggestions) == 1
    assert suggestions[0].rule_id == "ia.style.lourdeur"


def test_parse_ai_response_returns_empty_list_for_object_without_list_or_rule_id() -> None:
    raw = '{"status": "no suggestions"}'
    assert parse_ai_response(raw) == []


def test_parse_ai_response_returns_empty_list_when_root_is_not_a_list() -> None:
    assert parse_ai_response('{"rule_id": "ia.style.lourdeur"}') == []


def test_fake_ai_client_returns_configured_suggestions_for_known_paragraph() -> None:
    suggestion = AISuggestion(
        rule_id="ia.style.lourdeur",
        original_text="lourdeur",
        suggested_text="légèreté",
        explanation="Style pesant.",
    )
    client = FakeAIClient(responses={"un paragraphe test": [suggestion]})
    assert client.is_available() is True
    result = client.analyze_paragraph("un paragraphe test", AI_RULE_IDS)
    assert result == [suggestion]


def test_fake_ai_client_returns_empty_list_for_unknown_paragraph() -> None:
    client = FakeAIClient()
    assert client.analyze_paragraph("paragraphe non configuré", AI_RULE_IDS) == []


def test_fake_ai_client_filters_by_requested_rule_ids() -> None:
    suggestion = AISuggestion(
        rule_id="ia.style.lourdeur",
        original_text="x",
        suggested_text="y",
        explanation="z",
    )
    client = FakeAIClient(responses={"p": [suggestion]})
    assert client.analyze_paragraph("p", ["ia.biblio.reference_incomplete"]) == []


def test_fake_ai_client_reports_unavailable_when_configured() -> None:
    client = FakeAIClient(available=False)
    assert client.is_available() is False
    assert client.analyze_paragraph("peu importe", AI_RULE_IDS) == []
