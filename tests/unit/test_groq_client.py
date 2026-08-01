from __future__ import annotations

import json
from unittest.mock import patch

from purh_editorial.corrector.ai import GroqAIClient


def test_is_available_true_when_key_present() -> None:
    assert GroqAIClient(api_key="fake-key").is_available() is True


def test_is_available_false_when_key_blank() -> None:
    assert GroqAIClient(api_key="").is_available() is False


def _groq_body(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_analyze_paragraph_parses_valid_response() -> None:
    client = GroqAIClient(api_key="fake-key")
    inner_json = json.dumps(
        [
            {
                "rule_id": "ia.biblio.reference_incomplete",
                "original_text": "Dupont, 2020",
                "suggested_text": "Dupont, 2020, Paris, PUF",
                "explanation": "Ville et éditeur manquants.",
            }
        ]
    )
    with patch(
        "purh_editorial.corrector.ai.groq_client.post_json",
        return_value=_groq_body(inner_json),
    ):
        result = client.analyze_paragraph(
            "Dupont, 2020", ["ia.biblio.reference_incomplete"]
        )
    assert len(result) == 1
    assert result[0].rule_id == "ia.biblio.reference_incomplete"


def test_analyze_paragraph_returns_empty_list_when_post_json_fails() -> None:
    client = GroqAIClient(api_key="fake-key")
    with patch(
        "purh_editorial.corrector.ai.groq_client.post_json", return_value=None
    ):
        result = client.analyze_paragraph("paragraphe", ["ia.style.lourdeur"])
    assert result == []


def test_analyze_paragraph_returns_empty_list_on_unexpected_body_shape() -> None:
    client = GroqAIClient(api_key="fake-key")
    with patch(
        "purh_editorial.corrector.ai.groq_client.post_json",
        return_value={"unexpected": "shape"},
    ):
        result = client.analyze_paragraph("paragraphe", ["ia.style.lourdeur"])
    assert result == []


def test_analyze_paragraph_skips_call_without_api_key() -> None:
    client = GroqAIClient(api_key="")
    with patch("purh_editorial.corrector.ai.groq_client.post_json") as mocked:
        result = client.analyze_paragraph("paragraphe", ["ia.style.lourdeur"])
    mocked.assert_not_called()
    assert result == []


def test_analyze_paragraph_filters_out_rule_ids_not_requested() -> None:
    client = GroqAIClient(api_key="fake-key")
    inner_json = json.dumps(
        [
            {
                "rule_id": "ia.biblio.reference_incomplete",
                "original_text": "x",
                "suggested_text": "y",
                "explanation": "z",
            }
        ]
    )
    with patch(
        "purh_editorial.corrector.ai.groq_client.post_json",
        return_value=_groq_body(inner_json),
    ):
        result = client.analyze_paragraph("paragraphe", ["ia.style.lourdeur"])
    assert result == []
