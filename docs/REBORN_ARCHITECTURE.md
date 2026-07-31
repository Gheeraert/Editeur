# Architecture minimaliste du correcteur `reborn`

## 1. Objet

Ce document fixe l’architecture du nouveau chemin d’exécution du correcteur
éditorial.

Le but est de produire rapidement un correcteur lisible, testable et utilisable
sur des documents Word réels.

Le redémarrage est technique. Il ne réduit pas le périmètre éditorial déjà
recensé.

## 2. Périmètre fonctionnel conservé

Le catalogue et le registre définissent un périmètre de **61 règles**.

| Famille | Nombre de règles |
|---|---:|
| `orthotypography` | 23 |
| `footnote` | 10 |
| `bibliography` | 7 |
| `structure` | 21 |
| **Total** | **61** |

La répartition par nature est la suivante :

| Nature | Nombre |
|---|---:|
| `deterministic` | 30 |
| `heuristic` | 31 |

La répartition par type d’action est la suivante :

| Type d’action | Nombre |
|---|---:|
| `text_transform` | 26 |
| `style_transform` | 2 |
| `structure_transform` | 21 |
| `diagnostic` | 8 |
| `pipeline_control` | 4 |

Les 61 règles restent documentées et conservent leurs identifiants.

Aucune règle ne disparaît du catalogue du seul fait du redémarrage technique.

Ce maintien ne signifie pas que les 61 règles sont :

- des expressions régulières ;
- automatiques ;
- déjà implémentées dans le nouveau chemin ;
- applicables sans vérification.

La nature et le type d’action de chaque règle restent ceux du registre.

### 2.1 État réel d’implémentation dans le chemin `reborn`

Le périmètre déclaré (61 règles) et le périmètre effectivement exécuté par
`corrector/word_document.py` ne coïncident pas encore. L'écart est explicite
et suivi dans `corrector/runner.py` (`RULE_IDS` pour ce qui est câblé,
`NOT_YET_IMPLEMENTED_RULE_IDS` pour ce qui reste à concevoir), plutôt que
silencieux.

| Famille | Câblées (`RULE_IDS`) | Restant à concevoir |
|---|---:|---:|
| `orthotypography` | 22 | 1 |
| `footnote` | 10 | 0 |
| `bibliography` | 3 | 4 |
| `structure` | 3 | 18 |
| **Total** | **38** | **23** |

`purh.tiret.incise` (famille orthotypographie) est marquée `disabled` par le
catalogue lui-même — jamais fonctionnelle, y compris dans la voie legacy — et
n'a aucun détecteur dans `corrector/rules/`. Elle a été retirée de `RULE_IDS`
(elle y figurait par erreur) et déplacée dans `NOT_YET_IMPLEMENTED_RULE_IDS`.

`purh.biblio.ponctuation_finale` est désormais câblée : la section
bibliographique est repérée par le style de titre Word (Titre/Heading 1-4)
associé au titre de section reconnu (Bibliographie, Sources, Références
bibliographiques...) — une condition déterministe fondée sur le style réel du
document, pas un score. Voir `_apply_bibliography_entry` et
`BIBLIOGRAPHY_SECTION_HEADING_RE` dans `word_document.py` /
`rules/bibliography.py`. Les 4 règles bibliographie restantes
(`structure.bibliography.section.start`/`.end`/`.item.promote`,
`bibliography.entry.detect`) sont marquées `planned`/`dormant` dans le
catalogue lui-même — jamais fonctionnelles, y compris dans la voie legacy.

Les 3 règles de frontmatter (`structure.frontmatter.abstract`/`keywords`/
`acknowledgment`) sont câblées comme **diagnostics** (surlignage turquoise
sur la ligne détectée), pas comme transformations structurelles silencieuses :
le catalogue ne précise pas quel style Word cible appliquer, et l'inventer
aurait été une invention normative non sourcée. `structure.frontmatter.
circuit_breaker` et les 17 autres règles de structure (détection de titres,
de poésie, de citations comme structure) restent hors périmètre : elles
reposent, dans la voie legacy, sur le moteur de score/seuil
(`structure_service`, score `heading`/`poetry`/`quote_structure`/
`bibliography_structure`) que le nouveau chemin d'exécution exclut
explicitement (§7 ci-dessous), et leur redéfinir un déclencheur explicite sans
score est un vrai travail éditorial — pas une simple portation.
`corrector/rules/structure.py` contient le détecteur de frontmatter
(`detect_frontmatter_rule`), maintenant branché.

**Ces 18 règles de structure ne sont pas prioritaires pour l'instant.** La
valeur immédiate de l'outil pour les éditrices tient d'abord aux corrections
ortho-typographiques et bibliographiques déterministes, qui couvrent la
majorité des interventions réellement chronophages sur un manuscrit. La
détection de structure (titres, poésie, citations) est un chantier à part
entière, avec un vrai risque éditorial si elle est mal calibrée (ex. : un vers
de poésie promu à tort en titre) — elle sera reprise après consolidation du
périmètre ortho-typo/notes/bibliographie, pas avant. Voir §13 « Faisabilité
d'une automatisation bibliographique plus poussée » pour la suite jugée la
plus utile à court terme.

Un identifiant absent de `RULE_IDS` n'apparaît pas dans le décompte renvoyé
par `correct_docx` : cela évite qu'un compte à 0 soit confondu avec « règle
exécutée, aucune occurrence trouvée ».

## 3. Nouveau chemin d’exécution

Le nouveau correcteur est construit dans un chemin isolé.

Son exécution ne dépend d’aucune notion de :

- legacy ;
- native ;
- shadow ;
- parité ;
- compatibilité entre moteurs ;
- seuil de migration ;
- adaptateur de comparaison.

Ces notions ne font pas partie du nouveau noyau.

L’ancien code pourra être consulté ultérieurement pour récupérer des éléments
utiles et circonscrits :

- expressions régulières ;
- listes lexicales ;
- garde-fous ;
- exceptions ;
- cas de test ;
- connaissances éditoriales.

Il ne constitue pas l’architecture du nouveau programme.

## 4. Finalité concrète

Le programme cible suit ce parcours :

```text
ouvrir un DOCX
→ travailler sur une copie
→ détecter les cas prévus par les règles
→ appliquer les corrections déterministes
→ surligner les modifications
→ enregistrer un nouveau DOCX
```

Le document original n’est jamais écrasé.

Le fichier de sortie est une copie du manuscrit ouverte et modifiée directement
dans Microsoft Word.

Le nouveau chemin ne reconstruit pas le manuscrit à partir :

- d’un modèle intermédiaire ;
- d’un gabarit ;
- d’un export complet ;
- d’une nouvelle représentation globale du document.

Il modifie uniquement les plages concernées par les règles.

Chaque modification automatique est surlignée pour rester immédiatement visible
à la relecture.

## 5. Premier backend : Microsoft Word

Le premier backend utilise Microsoft Word sous Windows, piloté depuis Python.

Une automatisation directe avec `pywin32` est le choix initial.

Cette approche doit préserver le document existant, notamment :

- les styles ;
- les notes ;
- les tableaux ;
- les images ;
- les sections ;
- les champs ;
- les en-têtes et pieds de page ;
- la mise en page ;
- les objets Word non concernés.

Cette étape ne définit ni backend abstrait, ni solution multiplateforme, ni
implémentations concurrentes.

## 6. Règles déterministes

Les **30 règles déterministes** sont prioritaires.

Une règle déterministe repose sur :

- une condition explicite ;
- un motif ou un état observable ;
- des garde-fous explicites ;
- des exceptions explicites ;
- une action prévisible ;
- des tests positifs ;
- des tests négatifs.

Une condition satisfaite produit toujours la même décision.

Une condition non satisfaite ne produit aucune modification.

Les garde-fous empêchent les transformations hors du domaine exact de la règle.

Les exceptions sont écrites à proximité immédiate de la règle concernée.

Elles ne sont pas déplacées dans un moteur général d’exceptions.

Une nouvelle exception doit pouvoir être ajoutée en modifiant uniquement :

- la règle concernée ;
- ses tests.

## 7. Règles heuristiques

Les **31 règles heuristiques** restent dans le catalogue.

Une heuristique peut appliquer une transformation lorsque son comportement est
explicitement défini par le code et les tests existants. Toute transformation
reste visible par surlignage jaune et doit être testée contre les faux positifs.
Les diagnostics restent non destructifs.

Les diagnostics heuristiques conservent le texte et utilisent un surlignage
turquoise distinct des transformations.

Le nouveau noyau ne contient :

- aucun score ;
- aucun seuil ;
- aucune décision probabiliste ;
- aucune calibration de migration.

## 8. Forme minimale d’une règle

Une règle est représentée par :

- une petite fonction Python ;
- ou une donnée simple associée à une fonction de remplacement.

Elle possède au minimum les éléments suivants :

```text
rule_id
description
scope
detector
action
guards
exceptions
```

`rule_id` conserve l’identifiant stable du registre.

`description` expose la fonction éditoriale en français clair.

`scope` indique les parties du document où la règle peut intervenir.

`detector` constate la condition observable.

`action` décrit la modification ou le signalement attendu.

`guards` rassemble les conditions qui bloquent une application trop large.

`exceptions` rend les exclusions explicites et locales.

La représentation n’impose pas :

- de protocole complexe ;
- de hiérarchie de classes ;
- d’injection de dépendances ;
- de registre dynamique ;
- de système de plugins ;
- d’événements ;
- de sérialisation intermédiaire ;
- de moteur de décision générique.

## 9. Organisation cible minimale

L’organisation indicative est volontairement petite :

```text
src/purh_editorial/corrector/
    runner.py
    word_document.py
    cli.py

    rules/
        orthotypography.py
        footnotes.py
        bibliography.py
        structure.py
```

Les responsabilités sont limitées à ceci :

- `word_document.py` ouvre la copie du DOCX, parcourt les contenus concernés,
  modifie les plages, applique le surlignage et sauvegarde le résultat ;
- `runner.py` applique les règles dans un ordre explicite ;
- `cli.py` reçoit les chemins d’entrée et de sortie, puis lance le traitement ;
- `rules/*.py` contient les règles lisibles, regroupées par famille.

Aucune autre couche n’est prévue à ce stade.

## 10. Politique de réutilisation

### Conserver

Les éléments suivants restent des actifs du projet :

- le catalogue des 61 règles ;
- les identifiants stables ;
- les descriptions éditoriales ;
- les sources normatives ;
- les expressions régulières utiles ;
- les exceptions déjà découvertes ;
- les fixtures éditoriales pertinentes ;
- les tests de cas positifs ;
- les tests de faux positifs ;
- les composants simples d’automatisation Word réutilisables.

Toute réutilisation doit rester locale, compréhensible et couverte par les tests
de la règle concernée.

### Ne pas réutiliser dans le nouveau chemin

Le nouveau chemin ne reprend pas :

- l’orchestration legacy/native/shadow ;
- les comparateurs de parité ;
- les adaptateurs de migration ;
- les seuils de décision ;
- les rapports shadow ;
- les modèles intermédiaires servant à reconstruire entièrement le DOCX ;
- les tests dont l’unique finalité est la parité entre anciens moteurs.

L’ancien code reste temporairement dans le dépôt tant que le nouveau chemin
n’est pas validé.

Il n’est pas supprimé pendant les premières étapes.

## 11. Stratégie de développement

### 1. Tranche verticale

Construire une première tranche avec trois règles représentatives :

- une correction textuelle simple ;
- une correction avec garde-fou ou exception ;
- une correction située dans une note.

Cette tranche ouvre un DOCX, travaille sur une copie, applique les trois règles,
surligne les changements et produit immédiatement un DOCX utilisable.

### 2. Préservation du DOCX

Vérifier dans Word que le fichier de sortie s’ouvre normalement et que les
éléments non concernés sont conservés.

### 3. Migration des règles déterministes

Migrer progressivement les règles déterministes, avec leurs garde-fous,
exceptions et tests positifs et négatifs.

### 4. Règles heuristiques

Ajouter les règles heuristiques dont le comportement est établi, avec un
surlignage jaune pour chaque transformation et turquoise pour chaque
diagnostic.

### 5. Validation réelle

Valider le comportement et la préservation documentaire sur des manuscrits
réels, sans écraser les originaux.

### 6. Retrait de l’ancienne machinerie

Supprimer l’ancienne machinerie uniquement lorsque le nouveau chemin est validé
et couvre les besoins retenus.

### 7. Interface

Ajouter éventuellement une interface simple après stabilisation du traitement.

## 12. Critères de réussite

Le redémarrage est réussi lorsque les critères suivants sont vérifiés :

- les 61 règles restent documentées ;
- les corrections déterministes sont explicites ;
- les transformations heuristiques établies sont explicites et surlignées ;
- les diagnostics heuristiques restent non destructifs ;
- chaque modification automatique est surlignée ;
- le fichier original reste intact ;
- le DOCX de sortie s’ouvre normalement dans Word ;
- les éléments non concernés restent inchangés ;
- un second passage ne répète pas les mêmes corrections ;
- ajouter une exception ne nécessite pas de modifier le moteur ;
- ajouter une règle ne nécessite pas de créer une nouvelle couche
  architecturale ;
- le nouveau chemin n’importe aucun composant shadow.

Ces critères sont vérifiables sur les tests ciblés et sur les documents Word de
validation.

## 13. Faisabilité d'une automatisation bibliographique plus poussée

### 13.1 Les 4 règles déclarées ne sont pas ce qui apporterait le plus de valeur

Les 4 règles bibliographie encore hors périmètre —
`structure.bibliography.section.start`, `structure.bibliography.section.end`,
`structure.bibliography.item.promote`, `bibliography.entry.detect` — sont
marquées `planned` ou `disabled`/`dormant` dans le catalogue : **aucune n'a de
comportement établi à porter**, y compris dans la voie legacy. Les concevoir
de zéro n'est pas une portation mais une conception complète, et leur nature
(délimiter une section, promouvoir un bloc en « entrée bibliographique »,
découper une entrée en champs auteur/titre/année/éditeur) appartenait à
l'architecture pivot : ce sont des opérations de classification structurelle,
pas des corrections de texte visibles.

Or la détection de section bibliographique (l'équivalent fonctionnel de
`section.start`/`.end`) **existe déjà** dans `reborn` : c'est exactement ce
que fait `_apply_bibliography_entry` / `BIBLIOGRAPHY_SECTION_HEADING_RE` dans
`word_document.py` pour scoper `purh.biblio.ponctuation_finale` (§2.1). Le
formaliser en rule_ids séparés n'ajouterait rien d'observable dans le DOCX de
sortie, puisque reborn n'a pas de pivot où « marquer » un bloc — seulement des
actions Word visibles (surlignage jaune/turquoise). Quant à
`bibliography.entry.detect` (parser une entrée en champs), c'est un problème
de reconnaissance d'entités bien plus dur que le reste du catalogue : les
citations d'auteurs sont notoirement mal formatées et hétérogènes (ordre des
champs, virgules vs points, initiales vs prénoms complets, années entre
parenthèses ou non), ce qui rend une extraction par regex fragile et à haut
risque de faux positifs silencieux.

**Conclusion : implémenter littéralement ces 4 règles n'est pas la voie à
suivre.** Elles peuvent rester dans `NOT_YET_IMPLEMENTED_RULE_IDS`
indéfiniment sans perte réelle — leur fonction utile (délimiter la section)
est déjà couverte autrement.

### 13.2 Ce qui apporterait réellement du temps gagné : étendre les corrections *dans* la zone déjà détectée

L'objectif énoncé — automatiser le formatage bibliographique parce que les
auteurs sont négligents sur le respect du gabarit attendu — est déjà
partiellement atteint : `reborn` détecte la section bibliographique de façon
déterministe (style de titre Word) et y corrige la ponctuation finale. Cette
même zone détectée est le point d'ancrage naturel pour des règles
supplémentaires, **sans transformation structurelle du document** — uniquement
des corrections de texte localisées, dans l'esprit des règles
ortho-typographiques déjà en place. Candidats plausibles, par ordre de
facilité technique décroissante :

1. **Espace avant/après séparateurs d'entrée** (virgules, points, tirets entre
   éléments d'une référence) — même famille technique que
   `purh.biblio.pagination_nnbsp`/`numero_nnbsp`, faisabilité élevée.
2. **Normalisation des espaces autour du tiret de plage de pages** (« p.
   12-25 » → tiret et espacement PURH) — regex ciblée, faisabilité élevée.
3. **Casse du nom d'auteur** (petites capitales, tout en majuscules, ou
   Nom/Prénom standard PURH) — faisabilité moyenne : nécessite de savoir
   distinguer de façon fiable le segment « auteur » du reste de l'entrée, ce
   qui suppose une convention de ponctuation stable en début d'entrée
   (ex. : toujours suivie d'une virgule).
4. **Normalisation de « et al. »**, des initiales de prénom, des abréviations
   d'éditeur — faisabilité moyenne, dépend de la variabilité réelle observée
   dans les manuscrits.
5. **Mise en italique du titre** — faisabilité plus faible dans le modèle
   actuel : `reborn` corrige du texte, pas la mise en forme d'une plage
   délimitée par des règles de citation (contrairement au stylage des
   siècles/numéros, qui s'appuie sur un motif textuel fixe) ; il faudrait
   d'abord définir comment délimiter le titre dans une entrée à la
   ponctuation hétérogène.

### 13.3 Ce qu'il faut pour lancer ce chantier

Chacune des règles candidates ci-dessus doit être ancrée sur une **source
normative PURH concrète** avant d'être codée — pas inventée (cf. AGENTS.md
§2.4). Le préalable concret :

1. Obtenir 10 à 20 entrées bibliographiques réelles de manuscrits déjà
   corrigés par une éditrice PURH (avant/après), pour caractériser les
   erreurs réellement fréquentes plutôt que d'en supposer.
2. Obtenir la référence du gabarit PURH pour la bibliographie (page du guide
   de préparation éditoriale, comme pour les règles déjà sourcées
   `purh.guide.p10`–`p12` dans le catalogue).
3. Pour chaque règle candidate retenue, l'ajouter au catalogue
   (`docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md`) avec un `rule_id` explicite
   (`purh.biblio.xxx`), sa source normative, puis l'implémenter dans
   `corrector/rules/bibliography.py` en suivant le même patron que
   `find_bibliography_pagination_edits` (garde-fous locaux, tests positifs et
   négatifs, idempotence).

Sans ce matériau (exemples réels + référence PURH), toute règle supplémentaire
serait une hypothèse non vérifiée risquant de « corriger » vers une norme
incorrecte — silencieusement, sur un document destiné à l'impression.
