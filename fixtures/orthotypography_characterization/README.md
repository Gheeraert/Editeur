# Corpus de caractérisation — orthotypographie

Un fichier JSON par règle de `OrthotypoService` (`src/purh_editorial/services/orthotypo_service.py`),
consommé par `tests/unit/test_orthotypo_characterization_corpus.py`. Voir
`docs/CORPUS_ET_FIXTURES.md` pour la distinction entre corpus de caractérisation et
corpus d'or normatif — **ce corpus est de la première catégorie, jamais de la seconde.**

## Ce que ce corpus répond

*Que produit le programme actuellement ?* — pas *que doit-il produire ?*

Chaque cas est vérifié en exécutant le pipeline `OrthotypoService` réel (pas la règle en
isolation) : un cas de caractérisation enregistre fidèlement le comportement observable,
y compris quand une règle est volontairement désactivée (`"automatic": false`, voir
`purh_tiret_incise.json`) ou quand son comportement est connu comme discutable.

**Aucun cas de ce corpus ne doit être interprété comme une validation éditoriale.**

## Origine des cas

Tous les cas sont **synthétiques** (`origin: "synthétique"` ou
`"synthétique (garde-fou)"`) — construits pour illustrer chaque règle et ses
garde-fous, jamais extraits d'un manuscrit réel. Avant la passe d'assainissement, ce
corpus contenait des extraits réels du corpus éditorial privé ; ils ont été retirés de
l'historique public et remplacés par ces cas synthétiques équivalents. Les cas réels
d'origine restent disponibles dans l'espace privé local
(`C:\Editeur-private\private_fixtures\orthotypography\`) pour qui dispose du corpus
privé.

## Format

```json
{
  "rule_id": "purh.xxx.yyy",
  "automatic": true,
  "positive_cases": [{"input": "...", "expected_output": "...", "origin": "synthétique"}],
  "negative_cases": [{"input": "...", "expected_output": "...", "origin": "synthétique (garde-fou)"}],
  "note": "précision optionnelle, ex. statut d'abstention"
}
```

- **`automatic`** reflète l'attribut `TypoRule.auto` réel : `false` uniquement pour
  `purh.tiret.incise` à ce jour (abstention, voir
  `docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md`).
- **`positive_cases`** / **`negative_cases`** : vérifiés via le pipeline complet
  (`OrthotypoService().apply(document)`), pas via `TypoRule.apply()` isolé — important
  pour les règles non automatiques, dont l'effet isolé ne reflète pas le comportement
  réel du logiciel.
