from __future__ import annotations

from typing import Sequence

from purh_editorial.corrector.ai._http import post_json
from purh_editorial.corrector.ai.client import AISuggestion, parse_ai_response
from purh_editorial.corrector.ai.prompts import build_system_prompt, build_user_prompt

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiAIClient:
    """Backend distant via l'API Gemini (palier gratuit Google AI Studio).

    Choisi en premier parmi les options distantes de la proposition
    d'architecture : à la différence de Claude (pas de palier gratuit
    exploitable) et de xAI Grok (à ne pas confondre avec Groq, l'accélérateur
    matériel — voir l'avis critique du 2026-08-01), Gemini offre un vrai
    quota gratuit utilisable pour un usage d'édition ponctuel.

    La clé API n'est jamais lue depuis une variable d'environnement ici :
    elle est injectée par l'appelant (voir `.env.example` pour le nom de
    variable conventionnel `GEMINI_API_KEY`), pour garder ce client agnostique
    du mécanisme de configuration — le câblage revient à l'étape 7 (UI).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def is_available(self) -> bool:
        """Vérifie qu'une clé API a été fournie.

        N'effectue volontairement aucun appel réseau de vérification : un
        aller-retour de test consommerait inutilement du quota gratuit pour
        une simple question de disponibilité. Une clé invalide se traduira
        par une liste vide renvoyée par `analyze_paragraph`, pas par un
        crash.
        """
        return bool(self._api_key.strip())

    def analyze_paragraph(
        self, text: str, rule_ids: Sequence[str]
    ) -> list[AISuggestion]:
        if not text.strip() or not rule_ids or not self._api_key.strip():
            return []

        payload = {
            "system_instruction": {"parts": [{"text": build_system_prompt(rule_ids)}]},
            "contents": [{"parts": [{"text": build_user_prompt(text)}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        url = f"{_API_BASE}/{self._model}:generateContent?key={self._api_key}"
        body = post_json(url, payload, headers={}, timeout=self._timeout)
        raw_text = _extract_text(body)
        if raw_text is None:
            return []

        rule_id_set = set(rule_ids)
        return [s for s in parse_ai_response(raw_text) if s.rule_id in rule_id_set]


def _extract_text(body: object) -> str | None:
    if not isinstance(body, dict):
        return None
    try:
        candidates = body["candidates"]
        text = candidates[0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return None
    return text if isinstance(text, str) else None
