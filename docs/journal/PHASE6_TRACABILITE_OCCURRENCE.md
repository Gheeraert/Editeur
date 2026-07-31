# Phase 6 — Traçabilité par occurrence

Rapport de la refonte. Périmètre : `OrthotypoService`
(`src/purh_editorial/services/orthotypo_service.py`), qui produit la grande majorité des
corrections du pipeline.

## Défaut corrigé

Avant cette phase, `OrthotypoService` produisait **une seule `Transformation` par bloc
ou par note**, quel que soit le nombre de règles qui avaient réellement corrigé quelque
chose à l'intérieur : `rule_id` était systématiquement la valeur générique
`"purh.orthotypo.batch"`, et `before`/`after` contenaient le texte **entier** du bloc,
avant et après l'ensemble des corrections.

Concrètement, un paragraphe contenant une correction de guillemets, une correction
d'espace avant ponctuation et un siècle stylé produisait **une seule** transformation
« fourre-tout », impossible à décomposer pour savoir quelle règle avait fait quoi à quel
endroit précis. Ce n'était pas exploitable pour générer, plus tard, des révisions Word
commentées par règle appliquée (`w:ins`/`w:del` + commentaire citant le `rule_id`), qui
est l'objectif final envisagé pour l'interface éditrice.

## Ce qui a changé

`OrthotypoService` produit désormais **une `Transformation` distincte par occurrence
corrigée**, avec le `rule_id` réel de la règle qui l'a produite, et `before`/`after`
limités au fragment concerné (pas le bloc entier).

Vérifié sur un exemple réel combinant plusieurs règles dans un seul bloc :

```
Il dit "bonjour": "au revoir" du xviie au xixe siècles, sans doute...
```

produit désormais 5 transformations distinctes :

| rule_id | avant | après |
|---|---|---|
| `purh.points_suspension` | `...` | `…` |
| `purh.guillemets.droits` | `"au revoir"` | `« au revoir »` |
| `purh.espaces.avant_ponct_forte` | `:` | ` :` |
| `purh.siecles` | `xixe` | `XIXe` |
| `R-SO-001` | `XIXe` | `xixe` |

(Le premier `"bonjour"` n'est pas converti : un garde-fou préexistant de
`purh.guillemets.droits`, `_is_technical_quote_context`, traite un texte entre
guillemets immédiatement suivi de `:` comme un contexte technique — comportement
inchangé par cette phase, simplement rendu visible parce que chaque occurrence est
maintenant individuellement traçable.)

## Comment

- Nouveau `_apply_rule_with_occurrences(rule, text)` : reconstruit le texte occurrence
  par occurrence via `pattern.finditer` plutôt que `pattern.sub`, en capturant chaque
  fragment (avant, après) individuellement modifié. Produit exactement le même texte
  que `TypoRule.apply` (utilisé tel quel par le corpus d'or de Phase 5, non modifié).
- Nouveau `_apply_all_rules_tracked(text)` : chaîne les 17 règles comme avant, mais
  retourne en plus la liste `(rule_id, avant, après)` de toutes les occurrences, tous
  règles confondues, dans l'ordre d'application.
- `_style_centuries_in_inlines` retourne désormais aussi la liste des siècles
  individuellement stylés (un bloc peut en contenir plusieurs, ex. « xviie au xixe
  siècles » — un seul des deux était auparavant visible dans le before/after agrégé).
- Nouveau `_build_transformations(...)` : construit une `Transformation` par occurrence
  (règles + siècles), chacune avec son propre `rule_id`.
- Le garde-fou anti-transformation-fantôme de la Phase 1 (comparaison de signature
  caractère par caractère avant/après) est conservé **inchangé** au niveau du bloc : il
  continue de décider si on retourne quelque chose ou une liste vide, avant que le détail
  par occurrence n'entre en jeu. Un bloc qui reconverge exactement vers son état de
  départ (le cas siècle déjà traité en Phase 1) continue de ne rien journaliser du tout.
- Le mécanisme de surlignage du DOCX exporté (`_rebuild_inlines`, calcul des régions
  colorées) est **inchangé** : il continue d'utiliser le diff agrégé de tout le bloc,
  qui pilote correctement le rendu visuel indépendamment du nombre de `Transformation`
  désormais journalisées. Seul le journal des transformations devient plus fin ; rien
  ne change dans le texte produit ni dans son surlignage.

## Limite assumée : cas mixte réel + annulation de siècle dans un même bloc

Le garde-fou de signature agit au niveau du **bloc entier** : si un bloc contient à la
fois une correction réelle (qui force `after_signature != before_signature`) et un
siècle qui se serait normalement annulé (cas Phase 1), les deux occurrences sont
journalisées — y compris celle du siècle qui, prise isolément, n'aurait rien changé de
permanent. C'est une limite connue et mineure : elle ne peut se produire que dans un
bloc qui contient encore une correction réelle à faire, donc jamais sur un document déjà
entièrement traité (le cas qui motivait le correctif de Phase 1). Vérifié : le test
d'intégration d'idempotence (`tests/integration/test_real_manuscript_fixtures.py`)
continue de passer sans modification — sur un document déjà traité, plus aucune
correction réelle ne reste à faire, donc plus aucun bloc mixte de ce type n'apparaît.

## Hors périmètre de cette phase

- `FootnoteNormalizer` (`rule_id="purh.note.batch"`) et `BibliographyNormalizer`
  produisent encore une transformation agrégée par note/entrée. Même limite que
  `OrthotypoService` avant cette phase, non corrigée ici : le périmètre de la feuille de
  route portait sur le catalogue de règles typographiques (Phases 3-5), qui ne couvre
  que `OrthotypoService`. Candidat naturel pour une prochaine extension si la
  traçabilité par occurrence doit s'étendre aux notes et à la bibliographie.
- Aucune génération de révisions Word (`w:ins`/`w:del` + commentaire) n'est implémentée
  dans cette phase : elle prépare seulement la condition nécessaire (un `rule_id` fiable
  par occurrence corrigée), pas la fonctionnalité elle-même.

## Tests

`tests/unit/test_orthotypo_traceability.py` (4 tests, nouveau) : plusieurs règles dans
un bloc produisent des transformations distinctes correctement taguées ; chaque
transformation ne porte que son propre fragment (pas tout le bloc) ; une même règle qui
se déclenche deux fois produit deux transformations ; les notes sont aussi couvertes.

Suite complète : voir le commit de cette phase pour le résultat des tests.
