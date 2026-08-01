from __future__ import annotations

# Identifiants stables des règles IA, en miroir de
# docs/CATALOGUE_REGLES_IA.md (source de vérité éditoriale : toute règle
# ajoutée ou retirée ici doit d'abord être reflétée dans ce catalogue).
#
# `ia.terminologie.incoherence` est présente dans la liste pour la
# validation des identifiants, mais sa portée document entier (et non
# paragraphe) la rend inutilisable avec `AIClient.analyze_paragraph` : voir
# la fiche correspondante dans le catalogue avant de la brancher (étape 6 du
# plan de travail sur la branche `ia`).
AI_RULE_IDS = (
    "ia.style.lourdeur",
    "ia.style.repetition",
    "ia.syntaxe.construction",
    "ia.syntaxe.accord",
    "ia.morphologie.forme_douteuse",
    "ia.biblio.reference_incomplete",
    "ia.biblio.structure_atypique",
    "ia.terminologie.incoherence",
    "ia.clarte.ambiguite",
)

AI_RULE_ID_SET = frozenset(AI_RULE_IDS)
