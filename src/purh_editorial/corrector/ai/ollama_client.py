from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Sequence

from purh_editorial.corrector.ai.client import AISuggestion, parse_ai_response
from purh_editorial.corrector.ai.prompts import build_system_prompt, build_user_prompt

# Délai court : `is_available` est interrogé avant chaque paragraphe candidat
# par le runner (étape 6) pour décider, sans bloquer, de sauter la passe IA.
_AVAILABILITY_TIMEOUT_SECONDS = 2.0

# Basse par defaut : cette tache est un jugement structure (repondre dans un
# schema JSON strict, s'abstenir si de doute), pas une generation creative -
# une temperature elevee (defaut du modele, souvent ~0.7-0.8) favorise la
# sur-confiance et l'invention constatees sur corpus reel (etape 9).
_DEFAULT_TEMPERATURE = 0.2


def list_ollama_models(
    base_url: str = "http://localhost:11434",
    timeout: float = _AVAILABILITY_TIMEOUT_SECONDS,
) -> list[str]:
    """Liste les modèles installés dans Ollama (équivalent de `ollama list`).

    Retourne une liste vide sur toute erreur (serveur injoignable, réponse
    inattendue) plutôt que de lever une exception — cette fonction alimente
    une liste déroulante d'interface, jamais un chemin critique.
    """
    request = urllib.request.Request(f"{base_url.rstrip('/')}/api/tags", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(body, dict):
        return []
    models = body.get("models")
    if not isinstance(models, list):
        return []
    return sorted(
        name
        for item in models
        if isinstance(item, dict) and isinstance(name := item.get("name"), str)
    )


def active_ollama_model(
    base_url: str = "http://localhost:11434",
    timeout: float = _AVAILABILITY_TIMEOUT_SECONDS,
) -> str | None:
    """Nom du modèle actuellement chargé en mémoire par Ollama (équivalent de
    `ollama ps`), ou `None` si aucun modèle n'est chargé ou si le serveur est
    injoignable.

    Sert uniquement à préremplir un choix par défaut dans l'interface ; ne
    remplace jamais la nécessité de préciser un modèle explicite pour
    `OllamaAIClient` lui-même (voir sa docstring).
    """
    request = urllib.request.Request(f"{base_url.rstrip('/')}/api/ps", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(body, dict):
        return None
    models = body.get("models")
    if not isinstance(models, list) or not models:
        return None
    first = models[0]
    if not isinstance(first, dict):
        return None
    name = first.get("name")
    return name if isinstance(name, str) else None


class OllamaAIClient:
    """Backend local via l'API REST d'Ollama (http://localhost:11434 par
    défaut). Aucune bibliothèque HTTP tierce : `urllib` de la bibliothèque
    standard suffit et évite d'alourdir `requirements.txt` pour un simple
    appel POST/GET JSON.

    Le nom du modèle n'a pas de valeur par défaut implicite : le laisser
    deviner masquerait une erreur de configuration (mauvais modèle chargé)
    au lieu de la signaler à l'appelant.
    """

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0,
        temperature: float = _DEFAULT_TEMPERATURE,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._temperature = temperature

    def is_available(self) -> bool:
        """Vérifie que le serveur Ollama répond.

        Ne vérifie PAS que `self._model` est effectivement chargé : Ollama
        télécharge/charge les modèles à la demande, et une vérification
        stricte imposerait un appel `/api/tags` plus lourd à interpréter.
        Une erreur de nom de modèle se traduira par une liste vide renvoyée
        par `analyze_paragraph`, pas par un crash.
        """
        request = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
        try:
            with urllib.request.urlopen(
                request, timeout=_AVAILABILITY_TIMEOUT_SECONDS
            ) as response:
                return response.status == 200
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def analyze_paragraph(
        self, text: str, rule_ids: Sequence[str]
    ) -> list[AISuggestion]:
        if not text.strip() or not rule_ids:
            return []

        payload = {
            "model": self._model,
            "system": build_system_prompt(rule_ids),
            "prompt": build_user_prompt(text),
            "format": "json",
            "stream": False,
            "options": {"temperature": self._temperature},
        }
        request = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
            return []

        raw_text = body.get("response") if isinstance(body, dict) else None
        if not isinstance(raw_text, str):
            return []

        rule_id_set = set(rule_ids)
        return [s for s in parse_ai_response(raw_text) if s.rule_id in rule_id_set]
