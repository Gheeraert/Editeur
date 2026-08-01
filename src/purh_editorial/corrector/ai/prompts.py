from __future__ import annotations

from typing import Sequence

# Instructions condensées à partir de docs/CATALOGUE_REGLES_IA.md. Le
# catalogue reste la source de vérité éditoriale ; ce dictionnaire n'est
# qu'une reformulation orientée prompt, à tenir manuellement synchronisée
# (pas de test de garde ici : la reformulation n'est pas censée être un
# copier-coller littéral du catalogue).
_RULE_INSTRUCTIONS: dict[str, str] = {
    "ia.style.lourdeur": (
        "ia.style.lourdeur : pléonasme, verbosité ou accumulation excessive "
        "de subordonnées qui alourdit réellement la phrase, en tenant compte "
        "du registre soutenu normal d'une édition universitaire (une phrase "
        "longue et savante n'est pas en soi un défaut). N'invoque une "
        "\"tournure passive\" que si la phrase contient effectivement une "
        "forme conjuguée de l'auxiliaire être suivie d'un participe passé "
        "(ex. \"fut modifié\", \"sont célébrées\") : ne l'invoque jamais par "
        "défaut ou par habitude sur une phrase qui n'est pas grammaticalement "
        "passive."
    ),
    "ia.style.repetition": (
        "ia.style.repetition : répétition rapprochée d'un même mot ou d'une "
        "même tournure, hors répétition volontaire (anaphore rhétorique, "
        "terme technique répété à dessein)."
    ),
    "ia.syntaxe.construction": (
        "ia.syntaxe.construction : rupture de construction grammaticale "
        "(anacoluthe), incohérence de temps ou de mode dans une même phrase."
    ),
    "ia.syntaxe.accord": (
        "ia.syntaxe.accord : accord douteux dépendant du sens (participe "
        "passé avec un COD éloigné, syllepse) que corrigeraient mal les "
        "correcteurs grammaticaux automatiques classiques."
    ),
    "ia.morphologie.forme_douteuse": (
        "ia.morphologie.forme_douteuse : forme fléchie douteuse ou "
        "archaïsante, employée de façon incorrecte, non couverte par un "
        "correcteur orthographique standard."
    ),
    "ia.biblio.reference_incomplete": (
        "ia.biblio.reference_incomplete : référence bibliographique à "
        "laquelle il manque un élément identifiable (auteur, titre, "
        "éditeur, année, ville, pagination)."
    ),
    "ia.biblio.structure_atypique": (
        "ia.biblio.structure_atypique : référence bibliographique complète "
        "mais dont la forme s'écarte fortement d'un ordre canonique "
        "auteur/titre/éditeur/année/ville."
    ),
    "ia.terminologie.incoherence": (
        "ia.terminologie.incoherence : à ne signaler que si tu disposes du "
        "document entier — inapplicable à un paragraphe isolé, ne "
        "l'utilise pas ici."
    ),
    "ia.clarte.ambiguite": (
        "ia.clarte.ambiguite : formulation dont le référent ou le sens est "
        "ambigu (pronom équivoque, rattachement syntaxique incertain)."
    ),
}

_JSON_SCHEMA_INSTRUCTIONS = """\
Réponds UNIQUEMENT avec un tableau JSON, sans aucun texte autour, même vide \
(par exemple : []). Chaque élément du tableau est un objet avec exactement \
ces clés, toutes des chaînes de caractères :
- "rule_id" : un des identifiants listés ci-dessus, jamais un autre.
- "original_text" : une citation EXACTE et VERBATIM du paragraphe fourni \
(ne paraphrase jamais ce champ, sous peine que la suggestion soit rejetée \
automatiquement).
- "suggested_text" : la reformulation ou correction proposée.
- "explanation" : une phrase brève expliquant le problème identifié.

Sois exigeante : la plupart des paragraphes d'un manuscrit déjà relu ne \
méritent AUCUNE remarque. Ne signale que ce qui gênerait réellement la \
lecture d'un lecteur académique exigeant, jamais une préférence de style \
mineure ou discutable. En cas de doute, ne signale rien. Un paragraphe bien \
écrit, même long ou syntaxiquement complexe, appelle un tableau vide.

Exemple de paragraphe qui n'appelle AUCUNE remarque (réponse attendue : []) :
"Le recueil s'organise en deux parties égales de six articles chacune : \
l'une se consacre à des pontificats spécifiques, l'autre à la \
monumentalisation de l'héraldique."

Exemple de paragraphe qui appelle une remarque justifiée :
"Il s'avère avéré que ce fait, qui a été observé, qui a été noté, et qui a \
été confirmé, demeure un fait avéré." → réponse attendue (un seul élément, \
pléonasme et répétition réelles, pas une invocation de voix passive) :
[{"rule_id": "ia.style.lourdeur", "original_text": "Il s'avère avéré que ce \
fait", "suggested_text": "Il est avéré que ce fait", "explanation": \
"Pléonasme : \\"s'avérer avéré\\" est redondant."}]

Si le paragraphe n'appelle aucune remarque parmi les points demandés, \
réponds par un tableau vide []. Ne modifie jamais le texte toi-même : tu es \
en train de préparer des annotations soumises à la relecture d'une \
éditrice, pas d'appliquer des corrections."""


def build_system_prompt(rule_ids: Sequence[str]) -> str:
    """Construit le prompt système restreint aux règles demandées.

    Les identifiants absents de `_RULE_INSTRUCTIONS` (erreur d'appel côté
    runner) sont silencieusement ignorés ici : c'est `parse_ai_response`,
    en aval, qui reste responsable de rejeter toute suggestion hors
    catalogue si le modèle en invente une malgré tout.
    """
    known = [_RULE_INSTRUCTIONS[r] for r in rule_ids if r in _RULE_INSTRUCTIONS]
    points = "\n".join(f"- {line}" for line in known)
    return (
        "Tu assistes une éditrice des Presses universitaires de Rouen et du "
        "Havre dans la relecture d'un tapuscrit. Analyse le paragraphe fourni "
        "uniquement selon les points suivants :\n"
        f"{points}\n\n"
        f"{_JSON_SCHEMA_INSTRUCTIONS}"
    )


def build_user_prompt(paragraph_text: str) -> str:
    return f'Paragraphe à analyser :\n"""\n{paragraph_text}\n"""'
