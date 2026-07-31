# Corpus de caractérisation orthotypographique — rapport public

Ce document remplace `docs/PHASE5_CORPUS_OR.md`, retiré de l'historique public lors de
la passe d'assainissement (voir `docs/PHASE6BIS_ASSAINISSEMENT.md`). Le rapport complet
d'origine, qui citait des extraits du corpus éditorial privé, reste disponible dans
`C:\Editeur-private\private_reports\` pour un usage strictement local.

## Ce que ce document décrit

`fixtures/orthotypography_characterization/` contient un fichier par règle de
`OrthotypoService`, avec des cas positifs et négatifs vérifiant **ce que le programme
produit actuellement**. Voir `docs/CORPUS_ET_FIXTURES.md` pour la définition exacte de
« corpus de caractérisation » et sa différence avec un corpus d'or normatif.

## Méthode publique

Contrairement à la version initiale de ce corpus (constituée en extrayant des exemples
réels d'un corpus privé local, désigné ici uniquement par l'identifiant générique
`private_corpus_a`), la version publique actuelle est **entièrement synthétique** :
chaque cas est construit à la main pour illustrer une règle ou un de ses garde-fous, puis
vérifié en exécutant le pipeline réel. Aucun extrait de manuscrit, aucun titre d'ouvrage,
aucun nom d'auteur n'apparaît dans ce dépôt public.

La méthode originale (extraction automatique de cas positifs réels depuis un corpus
privé) reste documentée et utilisable localement : voir
`C:\Editeur-private\private_reports\PHASE5_CORPUS_OR.md` pour qui dispose du corpus
privé installé.

## Résultat

- 19 règles de `OrthotypoService` couvertes par le corpus de caractérisation public
  (`fixtures/orthotypography_characterization/`), toutes avec au moins un cas négatif ou
  positif synthétique et vérifié.
- 2 règles ont, en plus, un cas véritablement **normatif** et public
  (`fixtures/orthotypography_gold/`) : `purh.abreviations.redoublement` et
  `purh.ordinaux`, toutes deux sourcées par une citation courte et non ambiguë du guide
  PURH réel (`validation_source.type: "guide_purh"`).
- `purh.tiret.incise` est marquée `"automatic": false` dans le corpus de
  caractérisation : ses cas ne sont que des négatifs (les trois formes de tiret restent
  inchangées), reflétant honnêtement l'abstention décidée en Phase 6 bis (voir
  `docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md`).

## Ce que ce corpus ne prouve toujours pas

Repris tel quel de la version originale, toujours vrai : un cas de caractérisation
n'est pas une preuve de correction éditoriale. Sur `private_corpus_a` (identifiant
générique, corpus privé local), plusieurs règles n'avaient encore aucun exemple positif
réel trouvé — `purh.ordinaux`, `purh.tiret.double`, `purh.abreviations.etc`,
`purh.abreviations.redoublement`, `purh.nombres.milliers`. Cette information reste
pertinente pour qui dispose du corpus privé et souhaite l'étendre ; voir
`C:\Editeur-private\private_reports\PHASE5_CORPUS_OR.md` pour le détail complet
(non publié ici).
