from __future__ import annotations

from typing import Sequence

from purh_editorial.corrector.ai._http import post_json
from purh_editorial.corrector.ai.client import AISuggestion, parse_ai_response
from purh_editorial.corrector.ai.prompts import build_system_prompt, build_user_prompt

_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqAIClient:
    """Backend distant via l'API Groq (accélérateur matériel, palier gratuit
    rapide sur des modèles ouverts — à ne pas confondre avec xAI Grok, voir
    `GeminiAIClient`). Option de secours si Gemini est indisponible ou si son
    quota est épuisé.

    Interface OpenAI-compatible (`/chat/completions`). Pas de mode JSON forcé
    ici (`response_format`) : ce mode impose chez la plupart des fournisseurs
    compatibles OpenAI une racine objet, alors que le contrat de la couche IA
    attend un tableau (voir docs/CATALOGUE_REGLES_IA.md) — les instructions du
    prompt système suffisent, et `parse_ai_response` tolère déjà une réponse
    imparfaite en n'en retenant que les entrées valides.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.1-8b-instant",
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def is_available(self) -> bool:
        """Vérifie qu'une clé API a été fournie, sans appel réseau — même
        raisonnement que `GeminiAIClient.is_available`."""
        return bool(self._api_key.strip())

    def analyze_paragraph(
        self, text: str, rule_ids: Sequence[str]
    ) -> list[AISuggestion]:
        if not text.strip() or not rule_ids or not self._api_key.strip():
            return []

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": build_system_prompt(rule_ids)},
                {"role": "user", "content": build_user_prompt(text)},
            ],
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        body = post_json(_API_URL, payload, headers=headers, timeout=self._timeout)
        raw_text = _extract_text(body)
        if raw_text is None:
            return []

        rule_id_set = set(rule_ids)
        return [s for s in parse_ai_response(raw_text) if s.rule_id in rule_id_set]


def _extract_text(body: object) -> str | None:
    if not isinstance(body, dict):
        return None
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    return content if isinstance(content, str) else None
