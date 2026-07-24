# Phase 1 — Fiabilité du pipeline (idempotence + conservation documentaire)

Rapport diagnostique. Aucune correction de code appliquée dans le cadre de cette phase.

## Méthode

Pour deux manuscrits réels de `sources/manuscripts_raw/` (`dissimuler_original.docx`,
1 Mo, 1107 paragraphes, 505 notes ; `iphigenie_original.docx`, 5,7 Mo, 1151 paragraphes,
590 notes) :

1. passe 1 : `Step1Pipeline.run()` (mode `deterministic`) sur le document original →
   DOCX de sortie, rapport, transformations ;
2. passe 2 : `Step1Pipeline.run()` sur le DOCX produit par la passe 1 (le pipeline
   traite sa propre sortie comme une nouvelle entrée) ;
3. comparaison du texte de sortie passe 1 vs passe 2 (idempotence textuelle) et des
   compteurs de blocs/notes/bibliographie/transformations par module.

`heraldique_original.docx` (85 Mo) n'a pas été testé en double passe dans cette
itération pour des raisons de temps ; les deux manuscrits testés suffisent à mettre en
évidence des défauts reproductibles et généralisables. À inclure si une vérification
plus large est jugée utile.

## Résultat principal : le texte de sortie est idempotent

Sur les deux manuscrits, le texte du DOCX de sortie de la passe 2 est **strictement
identique**, paragraphe par paragraphe, à celui de la passe 1. Aucune sur-correction en
boucle, aucune dérive du texte visible n'a été observée. C'est le résultat attendu et
il est confirmé.

Mais l'exercice a mis en évidence **trois défauts réels**, deux invisibles au niveau du
texte final (donc non détectés par la seule comparaison textuelle) et un troisième qui
est une perte de contenu.

---

## Défaut 1 — Régression réelle : la casse de « Ibid. » se dégrade à la deuxième passe

**Confirmé, reproductible, corrige du texte déjà correct en texte incorrect.**

`FootnoteNormalizer._apply_rules` applique trois règles en séquence sur le texte d'une
note (`src/purh_editorial/services/footnote_normalizer.py:204-223`) :
- R1 : `text.lstrip(" \t")` — retire un espace de tête parasite (séparateur entre le
  numéro d'appel de note et le texte) ;
- R2 : majuscule en début de note ;
- R3 : `(?<!^)\bIbid\b` → minuscule, **sauf en tout début de note** (pour ne pas
  changer une casse de début de phrase légitime).

`DocxExporter._build_footnote_xml` (`src/purh_editorial/io/docx_exporter.py:378`) insère
un séparateur **codé en dur en espace insécable** (`&#160;`) entre le numéro d'appel de
note et le texte : `<w:t xml:space="preserve">&#160;</w:t>`.

Au réimport, ce caractère insécable devient le premier caractère du texte de la note
(`note.inlines[0]`). Or R1 (`lstrip(" \t")`) ne retire que l'espace normal et la
tabulation — **pas l'espace insécable**. Résultat : après un aller-retour
export → réimport, « Ibid. » n'est plus détecté comme étant en tout début de note par
R3, et se retrouve mis en minuscule à tort.

Preuve directe (`dissimuler_original.docx`) :
- import brut, une seule passe de `FootnoteNormalizer` : 76 notes commençant par
  « Ibid. » restent inchangées (protection R3 correcte, le séparateur d'origine est un
  espace normal) ;
- après export puis réimport (état réel de tout document qui repasserait dans le
  pipeline, y compris via l'export DOCX de relecture) : le séparateur est devenu une
  espace insécable, R3 ne protège plus, et une nouvelle passe transforme « Ibid. » en
  « ibid. » pour ces mêmes notes — une dégradation, pas une correction.

**Portée** : ce défaut touche toute réouverture d'un document déjà exporté par l'outil
(relecture, corrections manuelles suivies d'un nouveau passage), pas seulement un
« double-clic accidentel ». Il touche aussi les autres abréviations couvertes par la
même règle (`Id`, `Idem`, `Op. cit.`, `Art. cit.`, `Loc. cit.`).

---

## Défaut 2 — Traçabilité non fiable : des « corrections » de siècle sont journalisées sans rien changer

**Confirmé. N'abîme pas le texte final, mais fausse le journal des transformations.**

Sur `dissimuler_original.docx`, la passe 2 journalise 68 transformations
`orthotypo.batch` avec l'attribut `century_styling: True`, dont le `before` et le
`after` sont **rigoureusement identiques** (vérifié caractère pour caractère).

Cause : deux étapes de `OrthotypoService` se neutralisent mutuellement sans jamais
atteindre un point fixe détecté comme tel.
- La règle `purh.siecles` (normalisation du texte) met le chiffre romain en
  **majuscules** (`roman.upper() + "e"`) ;
- `_style_centuries_in_inlines` (stylage visuel) remet ensuite ces mêmes caractères en
  **minuscules** et leur applique le style petites capitales (le texte stocké est en bas
  de casse, l'apparence visuelle en capitales vient du style Word, pas du texte).

À l'export, le texte est donc en minuscules avec le style petites capitales. Au
réimport puis au retraitement, `purh.siecles` s'applique de nouveau à ce texte déjà
minuscule et le repasse en majuscules ; `_style_centuries_in_inlines` le repasse
ensuite en minuscules stylées — le texte final reconverge exactement vers son état de
départ. Mais `OrthotypoService._process_inlines_owner`
(`src/purh_editorial/services/orthotypo_service.py:497-551`) ne vérifie l'égalité
`corrected == original` **qu'à l'étape intermédiaire** (juste après `_apply_all_rules`),
pas après le second passage de stylage. Comme le texte intermédiaire diffère du texte de
départ (même si le texte final n'en diffère pas), une `Transformation` est créée et
journalisée avec `before == after`.

**Pourquoi c'est important malgré l'absence d'impact visible** : la Phase 6 prévoit de
générer des révisions Word (`w:ins`/`w:del`) commentées par `rule_id` à partir de ce
journal. Si le journal contient de fausses corrections (rien n'a changé, mais une entrée
dit le contraire), toute fonctionnalité de traçabilité ou de relecture construite dessus
sera trompeuse dès le premier réexamen d'un document déjà traité.

Un phénomène du même ordre (transformations `structure: 4` identiques entre passe 1 et
passe 2) a été observé sur `iphigenie_original.docx` sans être creusé plus avant — à
vérifier si la Phase 6 est engagée.

---

## Défaut 3 — Conservation documentaire : une note perdue sur `dissimuler_original.docx`

**Confirmé, cause non identifiée dans le temps imparti à cette phase.**

| | original | après passe 1 |
|---|---:|---:|
| notes de bas de page (`word/footnotes.xml`, type normal, IDs uniques) | 505 | 504 |

Une note disparaît entre l'import et l'export sur ce manuscrit. Sur
`iphigenie_original.docx`, en comparaison, le compte de notes est stable (590 → 590).
Cause non déterminée : pourrait être une note dupliquée à l'import, une note orpheline
sans appel dans le texte, ou une perte lors de l'injection XML des notes à l'export. À
creuser avant toute correction.

Autres écarts numériques observés, de moindre gravité mais à garder en tête :
- `dissimuler` : longueur de texte 351 917 → 351 919 caractères (+2, cohérent avec des
  normalisations orthotypographiques mineures) ;
- `iphigenie` : longueur de texte 417 318 → 417 162 caractères (**-156**), écart plus
  significatif, non expliqué ici — probablement une combinaison de suppressions
  d'espaces et de fusions de paragraphes, mais mérite une vérification dédiée avant de
  considérer la conservation comme acquise sur ce manuscrit.

Le nombre de blocs structurels change fortement entre le DOCX original et la sortie
(ex. `dissimuler` : 1107 paragraphes bruts → 752 blocs pivot → 765 paragraphes DOCX
réexportés) : ceci reflète la restructuration du pivot (fusion de runs, regroupement en
blocs sémantiques) et n'est pas en soi un signe de perte — mais ce rapport n'a pas
vérifié un-à-un que chaque paragraphe source retrouve son contenu dans la sortie. Ce
serait la vérification naturelle d'une Phase 1bis si l'on souhaite aller plus loin.

---

## Ce qui n'a pas été trouvé cassé

- Idempotence **textuelle** du DOCX de sortie : confirmée sur les deux manuscrits.
- Le stylage petites capitales / exposant des siècles survit correctement à l'aller-retour
  export → réimport (vérifié directement sur les runs Word du fichier réel) — ce n'est
  **pas** une perte de style, contrairement à l'hypothèse initiale ; c'est un problème de
  détection de non-changement (Défaut 2), pas de persistance.
- Pas de plantage, pas d'exception, pas de warning levé sur aucune des deux passes, sur
  aucun des deux manuscrits.

## Décision à prendre avant la suite

Conformément au mode d'exécution demandé : ces trois défauts sont réels mais d'ampleur
différente.
- Le **Défaut 1** (régression de casse « Ibid. ») est une vraie corruption de contenu à
  la relecture d'un document déjà traité — pertinent de corriger rapidement,
  indépendamment du reste de la feuille de route.
- Le **Défaut 2** (journal non fiable) ne casse rien aujourd'hui mais compromet
  directement l'objectif de la Phase 6 (traçabilité par occurrence) si non traité avant
  d'y arriver.
- Le **Défaut 3** (note perdue) est confirmé mais pas encore expliqué ; nécessite une
  investigation supplémentaire, pas nécessairement un correctif immédiat.

Je m'arrête ici, dans l'attente d'une décision : corriger ces défauts maintenant (hors
catalogue de règles, puisqu'il s'agit de fiabilité du pipeline et non de nouvelles
règles typographiques), les documenter et les reporter, ou approfondir d'abord le
Défaut 3 avant de statuer.
