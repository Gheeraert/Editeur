from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from purh_editorial.corrector.ai.rules import AI_RULE_ID_SET


@dataclass(frozen=True)
class AISuggestion:
    """Suggestion brute renvoyée par un modèle, avant localisation dans le texte.

    Ne porte jamais de position : `original_text` est une citation exacte que
    le modèle affirme avoir vue dans le paragraphe fourni. Rien ne garantit
    qu'elle s'y trouve réellement (hallucination, troncature) — voir
    `locate_suggestion`, qui est le seul point de passage vers un surlignage
    Word.
    """

    rule_id: str
    original_text: str
    suggested_text: str
    explanation: str


@dataclass(frozen=True)
class LocatedAISuggestion:
    """Une `AISuggestion` dont `original_text` a été retrouvée dans le
    paragraphe source, avec les décalages de caractères correspondants.

    Seule une instance de ce type peut être transmise à l'étape de surlignage
    Word (étape 5 du plan) : c'est la garantie qu'aucune suggestion
    inventée par le modèle sur un texte qu'il n'a pas vu ne produit
    d'annotation.
    """

    rule_id: str
    start: int
    end: int
    original_text: str
    suggested_text: str
    explanation: str


def locate_suggestion(
    paragraph_text: str, suggestion: AISuggestion
) -> LocatedAISuggestion | None:
    """Retrouve `suggestion.original_text` dans `paragraph_text`.

    Retourne `None` si la citation est absente (au lieu de lever une
    exception) : conformément au principe de tolérance aux pannes de la
    couche IA, une suggestion non localisable est silencieusement ignorée
    par l'appelant plutôt que de faire échouer tout le traitement.
    """
    if not suggestion.original_text:
        return None
    index = paragraph_text.find(suggestion.original_text)
    if index == -1:
        return None
    return LocatedAISuggestion(
        rule_id=suggestion.rule_id,
        start=index,
        end=index + len(suggestion.original_text),
        original_text=suggestion.original_text,
        suggested_text=suggestion.suggested_text,
        explanation=suggestion.explanation,
    )


_REQUIRED_STRING_FIELDS = ("rule_id", "original_text", "suggested_text", "explanation")


def parse_ai_response(raw: str) -> list[AISuggestion]:
    """Convertit la réponse JSON brute d'un backend (local ou distant) en
    suggestions validées.

    Format attendu : un tableau JSON d'objets `{rule_id, original_text,
    suggested_text, explanation}` (voir docs/CATALOGUE_REGLES_IA.md). Chaque
    entrée est validée indépendamment ; une entrée malformée ou portant un
    `rule_id` hors catalogue est ignorée sans faire échouer les autres —
    aucune exception n'est jamais levée par cette fonction, y compris sur un
    JSON invalide ou une racine qui n'est pas un tableau.

    Tolère deux déviations observées en pratique (constaté avec Mistral
    Small 3.2 en local, malgré une consigne de prompt explicite demandant un
    tableau) : une unique suggestion renvoyée comme objet nu plutôt que
    tableau à un élément, ou un objet enveloppant le tableau sous une clé
    quelconque (ex. `{"suggestions": [...]}`). Toute autre forme d'objet
    (sans `rule_id` ni valeur de type liste) est traitée comme « aucune
    suggestion », par prudence plutôt que de deviner davantage.
    """
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if isinstance(payload, dict):
        if "rule_id" in payload:
            payload = [payload]
        else:
            list_values = [v for v in payload.values() if isinstance(v, list)]
            payload = list_values[0] if list_values else []
    if not isinstance(payload, list):
        return []

    suggestions: list[AISuggestion] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        if any(not isinstance(item.get(field), str) for field in _REQUIRED_STRING_FIELDS):
            continue
        rule_id = item["rule_id"]
        if rule_id not in AI_RULE_ID_SET:
            continue
        suggestions.append(
            AISuggestion(
                rule_id=rule_id,
                original_text=item["original_text"],
                suggested_text=item["suggested_text"],
                explanation=item["explanation"],
            )
        )
    return suggestions


class AIClient(Protocol):
    """Interface commune aux backends IA (Ollama local, API distante).

    Ne couvre que l'analyse paragraphe par paragraphe : 8 des 9 règles du
    catalogue s'y prêtent. `ia.terminologie.incoherence`, à portée document
    entier, nécessitera une méthode distincte lorsqu'elle sera implémentée
    (étape 6 du plan) — ne pas l'anticiper ici tant que sa conception n'est
    pas arrêtée.
    """

    def is_available(self) -> bool:
        """Indique si le backend peut être sollicité maintenant.

        Doit être bon marché (pas d'appel réseau bloquant coûteux) : c'est ce
        que le runner interroge pour décider, silencieusement, de sauter la
        passe IA plutôt que de planter le traitement déterministe.
        """
        ...

    def analyze_paragraph(
        self, text: str, rule_ids: Sequence[str]
    ) -> list[AISuggestion]:
        """Analyse un paragraphe pour les règles demandées.

        Doit retourner une liste vide (jamais lever d'exception) si le
        backend est indisponible, si la réponse est malformée, ou si aucune
        suggestion ne s'applique.
        """
        ...


class FakeAIClient:
    """Client de test : aucun appel réseau, réponses préprogrammées.

    `responses` associe un texte de paragraphe exact aux suggestions à
    renvoyer ; tout paragraphe absent de la table renvoie une liste vide,
    comme le ferait un vrai backend qui n'a rien à signaler.
    """

    def __init__(
        self,
        responses: Mapping[str, list[AISuggestion]] | None = None,
        available: bool = True,
    ) -> None:
        self._responses = dict(responses or {})
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def analyze_paragraph(
        self, text: str, rule_ids: Sequence[str]
    ) -> list[AISuggestion]:
        if not self._available:
            return []
        candidates = self._responses.get(text, [])
        return [s for s in candidates if s.rule_id in rule_ids]
