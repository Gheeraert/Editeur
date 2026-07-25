# Analyse du corpus de caractérisation privé — synthèse publique

Rapport diagnostique. Aucune règle ni fixture n'a été modifiée pour produire ce document.

**Confidentialité** : ce document est la version publique, expurgée, d'un rapport interne.
Il ne reproduit aucun extrait du manuscrit source (ni phrase, ni légende, ni crédit
photographique) — seulement des constats agrégés et des volumétries. La version complète
(avec citations exactes servant de preuve) est conservée exclusivement dans le corpus privé
local (voir `docs/CORPUS_ET_FIXTURES.md`), accessible via `PURH_PRIVATE_CORPUS_DIR`.

## Méthode

Sur un ouvrage complet du corpus privé (16 chapitres, manuscrit brut vs. version corrigée
par les éditrices) :

1. Extraction du texte brut de chaque chapitre depuis le manuscrit source ;
2. Passage de ce texte brut dans `OrthotypoService` (la couche déterministe réelle du
   pipeline, `src/purh_editorial/services/orthotypo_service.py`) pour obtenir un texte
   « auto-corrigé » ;
3. Comparaison mot à mot (`difflib`) : `brut → auto-corrigé` (ce que la règle actuelle fait
   réellement) et `auto-corrigé → corrigé par les éditrices` (l'écart restant) ;
4. Classement de l'écart restant en trois catégories.

**Limite connue** : la comparaison porte sur le texte brut des paragraphes. Les changements
de mise en forme pure (italique, gras, styles de caractère) ne sont pas visibles par cette
méthode et ne sont donc pas couverts par ce rapport.

## Catégorie 1 — corrections déjà couvertes par une règle existante (vérifiées)

Confirmé correct sur le corpus privé :

- guillemets droits → guillemets français + espaces fines insécables (`purh.guillemets.*`) ;
- espace insécable avant `: ; ? !` (`purh.espaces.avant_ponct_forte`) ;
- siècles en chiffres romains + « e » → petites capitales + exposant pour les cas standards
  (`purh.siecles`) ;
- suppression des espaces avant `,` et `.`, réduction des doubles espaces.

Aucune de ces corrections n'apparaît dans l'écart restant (« gap ») : le pipeline produit bien
ce que les éditrices ont produit sur ces points, sur l'ensemble des chapitres testés.

### Défaut identifié dans une règle « couverte » : `purh.siecles` corrompt les ordinaux « Ier »

Le manuscrit brut écrit correctement, à plusieurs reprises, des ordinaux masculins de la
forme « Ier » après un nom propre (ex. « <Nom> Ier »). La règle `purh.siecles`
(`orthotypo_service.py:274-282`) utilise un regex qui capture aussi ces occurrences (parce que
« I » est un chiffre romain valide pour un siècle) et les réécrit systématiquement en
`roman.upper() + "e"`, soit **« Ie »** — une forme incorrecte, ni un siècle valide ni un
ordinal valide.

**7 occurrences réelles de corruption sur ce seul corpus** (preuve détaillée dans le rapport
privé complet, avec citations exactes). Le pipeline actuel dégraderait un texte déjà correct
s'il était appliqué tel quel à ces passages — c'est un vrai défaut, pas une hypothèse.

## Catégorie 2 — corrections récurrentes non couvertes (candidates à une nouvelle fiche)

### 2a. Espace insécable entre un nom propre et le numéral romain qui le suit — motif le plus massif du corpus (784 occurrences)

Aucune règle actuelle ne le couvre (`purh.civilite` ne traite que M./Mme/Dr/Pr, pas les noms
de souverains suivis d'un chiffre romain). Le manuscrit brut utilise un espace normal ; les
éditrices y substituent systématiquement une espace insécable.

Motif également présent avant/après des références comme « fig. N », mais celui-ci est déjà en
grande partie couvert par `purh.pagination.espace` — la nouveauté concerne spécifiquement le
couple **nom propre + chiffre romain**.

### 2b. Expansion de l'abréviation ordinale brute « Ie » → « Ier » (~9 occurrences)

Distinct du bug de la catégorie 1 : ici, c'est le **manuscrit brut** qui abrège
« premier » en « Ie » (sans r) après un prénom de souverain, et les éditrices l'étendent en
« Ier ».

### 2c. Tiret d'incise : le brut utilise le cadratin, les éditrices imposent le demi-cadratin (50 occurrences)

Le manuscrit brut utilise systématiquement le tiret cadratin « — » (em dash) pour les incises ;
les éditrices le remplacent systématiquement par le tiret demi-cadratin « – » (en dash), avec un
espacement différent.

**Point d'attention** : la règle existante `purh.tiret.incise` (`orthotypo_service.py`) allait
dans le sens **inverse** avant sa correction en Passe 6 bis (voir
`docs/CORPUS_ET_FIXTURES.md` et le journal des règles) : elle convertissait un tiret simple ou
un demi-cadratin *vers* le cadratin — la convention opposée à celle réellement pratiquée par
les éditrices. Sur ce corpus elle ne s'activait jamais empiriquement (le brut n'utilise pas les
motifs qu'elle ciblait), mais le risque de contresens a motivé son passage en abstention
diagnostique (`analyze_incise_dash`, non automatique).

### 2d. Titres de section tout capitales → casse phrase

Récurrent dans les titres de chapitre/section du manuscrit brut (ex. bibliographie, table des
figures) : le tout-capitales est systématiquement ramené à la casse phrase par les éditrices.
Relève potentiellement autant de la reconnaissance de structure (`structure_service`) que de
l'orthotypographie — à arbitrer, mais le motif lui-même est net et récurrent.

### 2e. Légendes de figures : renumérotation et formule « Figure N. » (~200 légendes)

Le format brut « N-Description. » devient « Figure N. Description. » de façon systématique.
Cette partie strictement formelle est isolable, mais **elle est mêlée à des corrections de
contenu réel** (nouveaux crédits, années de copyright) qu'il ne faut pas confondre avec une
règle typographique — voir catégorie 3.

## Catégorie 3 — cas ponctuels ou de jugement éditorial (à ne pas automatiser)

### 3a. Virgule d'incise / de proposition subordonnée (275 occurrences)

Insertion d'une virgule avant une proposition relative, participiale, ou une apposition.
Fréquent, mais chaque cas dépend de l'analyse grammaticale de la phrase — aucune règle
positionnelle fiable ne peut le généraliser sans faux positifs massifs sur des virgules
légitimement absentes ailleurs.

### 3b. Corrections de contenu, non typographiques

Conventions de nommage (substitution d'un nom propre par un autre), renumérotations de
références de figures, réécritures de légendes avec de nouvelles informations factuelles
(crédits photographiques), ajouts éditoriaux de contenu (titre absent verbatim du brut) — tous
relèvent d'une décision éditoriale sur le fond, pas d'une transformation de surface
automatisable.

### 3c. Défaut isolé et trompeur du manuscrit brut

Le manuscrit brut contient, à plusieurs reprises, une confusion entre deux mots proches
(majuscules + suffixe vs. mot minuscule courant), corrigée par les éditrices au cas par cas.
Vraisemblablement un artefact d'une correction automatique antérieure mal maîtrisée sur le
manuscrit. **Ceci ne doit surtout pas devenir une règle générale** : une règle positionnelle
générique détruirait des occurrences légitimes de la forme majuscule ailleurs dans le texte.
Cas à diagnostiquer au coup par coup, jamais à corriger silencieusement.

### 3d. Casse dépendant du sens : points cardinaux

Majuscule quand il s'agit d'une région/aire géopolitique, minuscule pour une direction
commune, selon le sens de la phrase — jugement contextuel, non mécanisable par une règle
positionnelle.

## Synthèse

- **1 défaut réel confirmé** dans une règle existante (`purh.siecles` corrompt « Ier » → « Ie »,
  7 occurrences observées) — corrigé, voir historique du rapport privé complet.
- **1 candidate de règle à très fort volume** et faible risque apparent : espace insécable
  nom propre + chiffre romain (784 occurrences, aucune couverture actuelle).
- **4 autres candidates récurrentes** de volume moyen (expansion « Ie »→« Ier », convention de
  tiret d'incise — traitée en Passe 6 bis par le passage en abstention diagnostique —, casse
  des titres tout capitales, formule des légendes de figures).
- **4 familles de cas à ne jamais automatiser** en l'état : virgule d'incise (275 occurrences,
  mais jugement grammatical requis), corrections de contenu factuel, défaut isolé de confusion
  lexicale du manuscrit brut, casse contextuelle des points cardinaux.

Aucune règle ni fixture n'a été modifiée pour produire cette analyse. Ce corpus et ce rapport
constituent la base à partir de laquelle toute décision ultérieure (nouvelle fiche de règle,
correction de règle existante, constitution du corpus d'or normatif) devra être prise. La
version complète avec citations exactes, réservée à l'usage local, se trouve dans
`PURH_PRIVATE_CORPUS_DIR/../private_reports/ANALYSE_CORPUS_HP2.md` (hors dépôt Git).
