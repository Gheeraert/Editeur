# Schéma du corpus d'or normatif

Voir `docs/CORPUS_ET_FIXTURES.md` pour la définition complète. Un cas normatif répond à
la question *que doit produire le programme ?*, avec une réponse établie
**indépendamment du code**.

## Format d'un cas

```json
{
  "rule_id": "purh.exemple",
  "input": "forme source",
  "expected_output": "forme validée",
  "validation_source": {
    "type": "guide_purh | editorial_copy | human_validation",
    "reference": "référence précise"
  },
  "validated": true
}
```

- **`validation_source.type`** :
  - `guide_purh` — prescription non ambiguë du guide typographique PURH réel
    (`CONSIGNES_AUTEURS_PURH_2025.pdf`), avec `reference` citant la page et si possible
    une courte citation ;
  - `editorial_copy` — correspondance exacte, vérifiée mot pour mot, avec une copie
    corrigée par une éditrice PURH (le document source reste privé ; `reference` pointe
    vers son identifiant générique dans le corpus privé, ex. `private_corpus_a#p12`) ;
  - `human_validation` — validation explicite d'une éditrice sur un cas précis, hors
    correspondance à un document complet (`reference` décrit les circonstances, ex.
    « validé par [initiales], 2026-07-25, voir private_reports/ »).
- **`validated`** doit être `true` pour qu'un cas soit effectivement considéré comme
  normatif par le chargeur (voir ci-dessous). Un cas à `false` n'est qu'un brouillon.

## Un fichier par règle

Même convention de nommage que `fixtures/orthotypography_characterization/` :
`<rule_id_normalisé>.json`, contenant `{"rule_id": ..., "gold_cases": [...]}`.

## Ce que le dépôt public contient, et ce qu'il ne contient pas

Le dépôt public contient ce schéma, le chargeur (`loader.py`) et uniquement les cas dont
la norme est **explicitement publique et non ambiguë** (typiquement `guide_purh`, quand
la citation elle-même est courte et non sensible). Les cas de type `editorial_copy` ou
`human_validation` référencent un document du corpus privé : leurs données complètes
restent dans `C:\Editeur-private\private_fixtures\` et ne sont jamais publiées ici, seule
leur référence générique peut apparaître dans un fichier de suivi privé.

**Aucun cas ne doit être ajouté à ce corpus sans satisfaire réellement l'une des trois
sources de validation ci-dessus.** Une sortie simplement produite par le code, même
plausible, n'est jamais un cas d'or — c'est un cas de caractérisation
(`fixtures/orthotypography_characterization/`).
