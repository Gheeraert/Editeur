from __future__ import annotations

import json
import urllib.error
from typing import Any
from unittest.mock import patch

from purh_editorial.corrector.ai import OllamaAIClient


class _FakeResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        return None


def test_is_available_returns_true_on_http_200() -> None:
    client = OllamaAIClient(model="mistral-small3.2")
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        return_value=_FakeResponse(200, b"{}"),
    ):
        assert client.is_available() is True


def test_is_available_returns_false_on_connection_error() -> None:
    client = OllamaAIClient(model="mistral-small3.2")
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        assert client.is_available() is False


def test_analyze_paragraph_parses_valid_response() -> None:
    client = OllamaAIClient(model="mistral-small3.2")
    inner_json = json.dumps(
        [
            {
                "rule_id": "ia.style.lourdeur",
                "original_text": "il s'avère avéré",
                "suggested_text": "il est avéré",
                "explanation": "Pléonasme.",
            }
        ]
    )
    body = json.dumps({"response": inner_json}).encode("utf-8")
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        return_value=_FakeResponse(200, body),
    ):
        result = client.analyze_paragraph(
            "il s'avère avéré que...", ["ia.style.lourdeur"]
        )
    assert len(result) == 1
    assert result[0].rule_id == "ia.style.lourdeur"


def test_analyze_paragraph_filters_out_rule_ids_not_requested() -> None:
    client = OllamaAIClient(model="mistral-small3.2")
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
    body = json.dumps({"response": inner_json}).encode("utf-8")
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        return_value=_FakeResponse(200, body),
    ):
        result = client.analyze_paragraph("paragraphe", ["ia.style.lourdeur"])
    assert result == []


def test_analyze_paragraph_returns_empty_list_on_network_error() -> None:
    client = OllamaAIClient(model="mistral-small3.2")
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        result = client.analyze_paragraph("paragraphe", ["ia.style.lourdeur"])
    assert result == []


def test_analyze_paragraph_returns_empty_list_on_malformed_json_body() -> None:
    client = OllamaAIClient(model="mistral-small3.2")
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        return_value=_FakeResponse(200, b"ceci n'est pas du JSON"),
    ):
        result = client.analyze_paragraph("paragraphe", ["ia.style.lourdeur"])
    assert result == []


def test_analyze_paragraph_returns_empty_list_when_response_field_missing() -> None:
    client = OllamaAIClient(model="mistral-small3.2")
    body = json.dumps({"other_field": "sans intérêt"}).encode("utf-8")
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        return_value=_FakeResponse(200, body),
    ):
        result = client.analyze_paragraph("paragraphe", ["ia.style.lourdeur"])
    assert result == []


def test_analyze_paragraph_skips_network_call_for_empty_text() -> None:
    client = OllamaAIClient(model="mistral-small3.2")
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen"
    ) as mocked:
        result = client.analyze_paragraph("   ", ["ia.style.lourdeur"])
    mocked.assert_not_called()
    assert result == []


def test_analyze_paragraph_skips_network_call_for_empty_rule_ids() -> None:
    client = OllamaAIClient(model="mistral-small3.2")
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen"
    ) as mocked:
        result = client.analyze_paragraph("un paragraphe", [])
    mocked.assert_not_called()
    assert result == []
