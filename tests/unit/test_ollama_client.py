from __future__ import annotations

import json
import urllib.error
from typing import Any
from unittest.mock import patch

from purh_editorial.corrector.ai import (
    OllamaAIClient,
    active_ollama_model,
    list_ollama_models,
)


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


def test_analyze_paragraph_sends_configured_temperature() -> None:
    client = OllamaAIClient(model="mistral-small3.2", temperature=0.2)
    body = json.dumps({"response": "[]"}).encode("utf-8")
    captured: dict[str, object] = {}

    def _fake_urlopen(request, timeout=None):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(200, body)

    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        side_effect=_fake_urlopen,
    ):
        client.analyze_paragraph("un paragraphe assez long pour etre analyse", ["ia.style.lourdeur"])

    assert captured["payload"]["options"]["temperature"] == 0.2


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


def test_list_ollama_models_returns_names_from_tags_endpoint() -> None:
    body = json.dumps(
        {"models": [{"name": "mistral-small3.2:latest"}, {"name": "llama3.1:8b"}]}
    ).encode("utf-8")
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        return_value=_FakeResponse(200, body),
    ):
        assert list_ollama_models() == ["llama3.1:8b", "mistral-small3.2:latest"]


def test_list_ollama_models_returns_empty_list_on_connection_error() -> None:
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        assert list_ollama_models() == []


def test_list_ollama_models_returns_empty_list_on_unexpected_shape() -> None:
    body = json.dumps({"unexpected": "shape"}).encode("utf-8")
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        return_value=_FakeResponse(200, body),
    ):
        assert list_ollama_models() == []


def test_active_ollama_model_returns_first_loaded_model_name() -> None:
    body = json.dumps({"models": [{"name": "mistral-small3.2:latest"}]}).encode("utf-8")
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        return_value=_FakeResponse(200, body),
    ):
        assert active_ollama_model() == "mistral-small3.2:latest"


def test_active_ollama_model_returns_none_when_no_model_loaded() -> None:
    body = json.dumps({"models": []}).encode("utf-8")
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        return_value=_FakeResponse(200, body),
    ):
        assert active_ollama_model() is None


def test_active_ollama_model_returns_none_on_connection_error() -> None:
    with patch(
        "purh_editorial.corrector.ai.ollama_client.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        assert active_ollama_model() is None
