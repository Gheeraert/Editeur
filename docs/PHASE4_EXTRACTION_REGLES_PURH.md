# Phase 4 — Extraction des règles PURH réelles

Rapport diagnostique et journal des décisions. Complète `docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md`
(Phase 3), où les fiches de règles concernées ont été mises à jour directement.

## Sources dépouillées

- **`sources/editorial_rules/CONSIGNES_AUTEURS_PURH_2025 (1).pdf`** — le guide réel des
  PURH, 16 pages. Dépouillé intégralement (texte extrait via `pypdf`). C'est la source
  la plus directement autorisante pour ce projet : c'est le document que les PURH
  remettent eux-mêmes à leurs auteurs.
- **`sources/editorial_rules/Lexique des règles typographiques… Imprimerie nationale.epub`**
  — dictionnaire général de référence (35 chapitres alphabétiques + index, ~500 pages
  équivalent). Dépouillement ciblé uniquement : le chapitre « Cit. » (Citations), le plus
  directement pertinent pour les gaps identifiés en Phase 3. Le reste du lexique n'a pas
  été lu intégralement — ce n'est pas un guide PURH mais une référence nationale
  générale, à consulter au cas par cas si un point précis reste incertain.

## Ce que le dépouillement confirme (mise à jour des fiches, Phase 3)

Huit des dix-sept règles ont désormais une source directement citée dans le guide PURH
ou le Lexique, au lieu de « non confronté au guide PURH » :

| Règle | Confirmation |
|---|---|
| `purh.guillemets.droits` | p. 12 : guillemets français exclusifs en texte courant, espace insécable, guillemets anglais réservés au second niveau sans espace interne — exactement le comportement de la règle. |
| `purh.siecles` | p. 10 : « Les siècles sont toujours composés en chiffres romains et en petites capitales » ; le tableau donne explicitement `Ier` → `Ier` (inchangé), qui valide directement le correctif de Phase 1. |
| `purh.ordinaux` | p. 10 : « on abrège "e" et non pas "ème", "re" et non pas "ère" » — correspond exactement. |
| `purh.abreviations.etc` | p. 10 : « etc. Jamais en italique. Toujours suivi d'un point abréviatif… » — correspond exactement. |
| `purh.pagination.espace` | p. 11-12 : espace insécable explicitement requise pour `loc. cit.`, `op. cit.`, `s. d.`, `s. l.`. |
| `R-GQ-004` (diagnostic guillemets/ponctuation) | Le guide (p. 12) et le Lexique (chap. « Cit. ») confirment que la position de la ponctuation dépend d'une distinction structurelle (citation fondue ou non) qu'aucun des deux documents ne réduit à une règle mécanique — validation du choix de rester en diagnostic plutôt que correction automatique. |
| `R-AN-002`/`R-AN-003` (diagnostics appel de note) | p. 11 : « L'appel de note se place toujours avant la ponctuation… Il ne doit pas être précédé d'une espace… » — correspond exactement à ce que ces diagnostics signalent. |
| `purh.numero` | **Contredite** (voir plus bas). |

## Ce que le dépouillement corrige : le trou du redoublement d'abréviations

Le guide PURH (p. 11) est explicite et sans ambiguïté :

> « Ne jamais redoubler tout ou partie d'une abréviation française pour indiquer le
> pluriel. »
>
> `pp. 53-84` → `p. 53-84` ; `vv. 122-128` → `v. 122-128` ; `ll. 5 et 12` → `l. 5 et 12` ;
> `§§ 5-9` → `§ 5-9`

Nouvelle règle implémentée : **`purh.abreviations.redoublement`**
(`src/purh_editorial/services/orthotypo_service.py`), avec fiche complète dans le
catalogue. Comble exactement le trou identifié par l'audit initial : seule la *création*
de nouveaux redoublements était jusqu'ici empêchée par construction (aucune règle n'en
produit), mais un redoublement déjà présent dans le manuscrit brut n'était pas
normalisé. 2 tests de non-régression ajoutés
(`tests/unit/test_orthotypo_service_guardrails.py`).

## Vérification du prompt `ai_editorial_service.py`

Demandée explicitement par la feuille de route : le prompt système contient déjà la
ligne « Abréviations normalisées : p. XX (**pas pp.**), n° X (pas no.), art. cit.,
op. cit. » (`src/purh_editorial/services/ai_editorial_service.py:24`).

**Vérifié cohérent** avec la nouvelle règle déterministe : les deux disent la même
chose (jamais `pp.`, toujours `p.`). Aucune double source de vérité à corriger. Note
en passant : ce même prompt écrit `« n° X (pas no.) »`, alors que la p. 12 du guide PURH
demande l'inverse — voir ci-dessous.

## Écart réel découvert : `purh.numero` va à l'encontre du guide PURH

Le guide (p. 12, tableau des abréviations) est explicite : « numéro » s'abrège **`no`**,
avec la lettre `o` en exposant — pas le symbole degré `n°` que produit la règle actuelle
`purh.numero` (et que suppose aussi, à tort dans le sens inverse, le prompt IA cité
ci-dessus, qui écrit littéralement « n° X »). C'est un écart réel entre la pratique
actuelle du projet (code et prompt IA) et le guide PURH.

**Non corrigé dans cette phase.** Implémenter `no` avec un `o` en exposant demande le
même mécanisme que le stylage des siècles (`R-SO-001`) : éclater le texte en spans
séparés pour appliquer un style à un seul caractère, pas une simple substitution regex
sur une chaîne. C'est un changement de nature différente des corrections regex qui
composent le reste du catalogue — je le signale comme trouvaille de cette phase plutôt
que de l'implémenter à la hâte dans le même mouvement que le redoublement d'abréviations
(qui, lui, est une substitution texte pure, sans risque de régression comparable).

Le même constat s'applique à `fol.`/`fo` (folio) et `ro`/`vo` (recto/verso), également
demandés avec un `o` en exposant par le guide et non couverts aujourd'hui.

## Éléments identifiés mais non implémentés : citations, bibliographie, index

La feuille de route demandait d'extraire quatre éléments repérés à l'avance. Les quatre
sont bien documentés dans le guide PURH réel (et, pour les citations, très précisément
dans le Lexique Imprimerie nationale) — mais aucun n'est implémentable comme simple
règle regex, et aucun n'a donc été ajouté au catalogue de Phase 3 :

### Composition des citations (4 cas)

Confirmés textuellement, guide PURH p. 12-13 :

1. citation en langue étrangère **non fondue** → italique, traduction en romain entre
   guillemets ou renvoyée en note ;
2. citation en français **non fondue** (qui n'est pas la traduction d'une citation
   précédente) → romain, **sans guillemets** ;
3. citation en langue étrangère **fondue** → italique **et** guillemets ;
4. citation en français **fondue** → romain **et** guillemets.

Le Lexique Imprimerie nationale (chapitre « Cit. ») détaille encore la position de la
ponctuation finale par rapport au guillemet fermant selon que la citation forme une
phrase complète ou est fondue dans la phrase, le traitement des citations de second
rang, les incises à l'intérieur d'une citation, les citations abrégées, etc. — matière
riche mais entièrement conditionnée à des décisions qu'aucune regex ne peut prendre de
façon fiable : est-ce une citation ? une traduction ? en quelle langue ? fondue ou non ?
Selon `AGENTS.md` (« aucune invention normative silencieuse », « préférer un
comportement conservateur ») ce genre de décision relève d'une reconnaissance
structurelle (proche des « zones protégées » déjà existantes pour la poésie ou le code),
pas d'`OrthotypoService`. Non implémenté ; à concevoir comme un module à part, avec
diagnostic prudent avant toute correction automatique.

### Modèles bibliographiques

Le guide PURH (p. 8-9) propose deux modèles au choix de l'auteur : « Modèle 1 »
(Imprimerie nationale, référence complète en note avec `ibid.`/`op. cit.`) et
« Modèle 2 » (auteur-date entre parenthèses dans le texte, avec `ibid.` aussi). Le choix
du modèle est une décision d'auteur/ouvrage, pas une propriété déductible du texte —
relève de `bibliography_normalizer.py`, hors périmètre d'une règle `OrthotypoService`.
Non implémenté.

### Format des entrées d'index

Guide PURH p. 10 : entrée type `NOM Prénom.` (nom en capitales, point final), au moins
deux occurrences requises, jamais d'indexation automatique. Aucune fonctionnalité
d'index n'existe aujourd'hui dans le pipeline (`Step1Pipeline` ne produit pas d'index) —
il n'y a pas de règle à corriger, seulement une fonctionnalité absente à concevoir le
jour où l'index entre dans le périmètre du projet. Non implémenté.

## Trouvaille non demandée mais significative : espace insécable nom + numéral dynastique

Déjà identifiée en Phase 3 (via le corpus H&P2, 784 occurrences) comme la candidate de
règle la plus rentable. Le Lexique Imprimerie nationale la confirme indépendamment, dans
sa section sur la coupure des mots : « Les initiales de prénoms et les particules ne
seront pas séparées du nom de famille, de même que les noms de souverains de leur
numéro dynastique. On ne coupera pas : […] Louis/XIV. » Deux sources indépendantes
(pratique éditoriale observée + référence typographique nationale) convergent
maintenant vers la même règle. Elle n'était pas dans la liste de gaps que cette phase
devait combler ; je ne l'ai donc pas implémentée, mais elle mérite d'être la première
candidate d'une prochaine extension du catalogue.

## Récapitulatif des changements de code de cette phase

- Nouvelle règle `purh.abreviations.redoublement` (+ fiche catalogue, + 2 tests).
- Aucune autre modification de code : les écarts identifiés (`purh.numero`, `fol.`/`ro`/`vo`
  en exposant, citations, bibliographie, index) sont documentés mais pas corrigés, pour
  les raisons données ci-dessus (nécessitent soit un éclatement en spans, soit une
  reconnaissance structurelle — pas une substitution regex isolée).
- `docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md` mis à jour : 8 sources confirmées avec
  citation précise, 1 nouvelle fiche, 3 écarts documentés dans les fiches concernées.

Suite complète : voir commit de cette phase pour le résultat des tests.
