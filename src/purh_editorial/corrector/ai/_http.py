from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> Any | None:
    """POST JSON et retourne le corps décodé, ou `None` sur toute erreur.

    Partagé par les backends distants (Gemini, Groq) : centralise la seule
    règle qui compte pour la couche IA — un problème réseau, un timeout ou un
    corps non-JSON ne doit jamais remonter comme exception à l'appelant,
    seulement comme absence de résultat.
    """
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None
