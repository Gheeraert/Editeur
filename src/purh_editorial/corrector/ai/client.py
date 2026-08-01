from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from purh_editorial.corrector.ai.rules import AI_RULE_ID_SET

# Garde-fou deterministe contre une deviation observee en pratique (etape 9,
# corpus reel PURH, Mistral Small 3.2) : le modele invoque "tournure passive"
# comme justification par defaut, y compris sur des phrases qui ne sont pas
# grammaticalement passives (ex. "qui regna de 1758 a 1769", un verbe simple
# actif). Plutot que de faire confiance a l'explication du modele, on verifie
# la presence d'au moins une forme conjuguee de l'auxiliaire "etre" dans le
# texte cite - une approximation volontairement large (pas un vrai parseur
# grammatical) qui suffit a rejeter les cas les plus flagrants sans risquer
# de rejeter un vrai passif.
_ETRE_FORM_RE = re.compile(
    r"\b(suis|es|est|sommes|êtes|sont|étais|était|étions|étiez|étaient|"
    r"fus|fut|fûmes|fûtes|furent|serai|seras|sera|serons|serez|seront|"
    r"serais|serait|serions|seriez|seraient|sois|soit|soyons|soyez|soient|"
    r"étant|été)\b",
    re.IGNORECASE,
)
_EXPLANATION_CLAIMS_PASSIVE_RE = re.compile(r"passi[fv]", re.IGNORECASE)


def _is_unsubstantiated_passive_claim(original_text: str, explanation: str) -> bool:
    if not _EXPLANATION_CLAIMS_PASSIVE_RE.search(explanation):
        return False
    return not _ETRE_FORM_RE.search(original_text)


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
    # 1 (preference de style mineure) a 5 (gene serieuse) : evaluee par le
    # modele lui-meme (voir prompts.py), sert de filtre deterministe reglable
    # par l'editrice (curseur de sensibilite, gui.py) plutot que de compter
    # sur l'auto-limitation du modele - constate peu efficace en pratique
    # (etape 9 bis : le taux de declenchement variait peu malgre des
    # consignes de prompt plus severes). Defaut 3 (moyen) pour les
    # suggestions construites sans cette information (tests, FakeAIClient).
    severity: int = 3


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
    severity: int = 3


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
        severity=suggestion.severity,
    )


_REQUIRED_STRING_FIELDS = ("rule_id", "original_text", "suggested_text", "explanation")


def _extract_severity(item: dict) -> int | None:
    """Valide le champ optionnel `severity` d'une entrée JSON.

    Absent -> 3 (moyen), par tolérance envers un backend qui omettrait le
    champ. Présent mais hors de l'intervalle [1, 5] ou de type invalide
    (`bool` explicitement exclu : `isinstance(True, int)` vaut `True` en
    Python) -> `None`, pour que l'appelant rejette l'entrée entière plutôt
    que d'inventer une sévérité arbitraire.
    """
    if "severity" not in item:
        return 3
    value = item["severity"]
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and 1 <= value <= 5:
        return value
    if isinstance(value, float) and value.is_integer() and 1 <= value <= 5:
        return int(value)
    return None


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

    Rejette aussi toute suggestion dont l'explication invoque une « tournure
    passive » sans qu'une forme de l'auxiliaire être n'apparaisse dans la
    citation (voir `_is_unsubstantiated_passive_claim`) : constaté en
    pratique sur corpus réel (étape 9), le modèle invoque parfois ce
    diagnostic par défaut sur des phrases qui ne sont pas grammaticalement
    passives.

    Valide le champ optionnel `severity` (1 à 5, voir `_extract_severity`) :
    absent, il vaut 3 par défaut ; présent mais invalide, l'entrée entière
    est rejetée plutôt que d'inventer une valeur.
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
        original_text = item["original_text"]
        explanation = item["explanation"]
        if _is_unsubstantiated_passive_claim(original_text, explanation):
            continue
        severity = _extract_severity(item)
        if severity is None:
            continue
        suggestions.append(
            AISuggestion(
                rule_id=rule_id,
                original_text=original_text,
                suggested_text=item["suggested_text"],
                explanation=explanation,
                severity=severity,
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
