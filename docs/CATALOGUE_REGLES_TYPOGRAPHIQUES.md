# Catalogue des règles typographiques — document de référence unique

Ce document fusionne et remplace `/TYPO_RULES_PURH.md` (gabarit resté vide) et
`/docs/TYPO_RULES_PURH.md` (nomenclature `R-SP-xxx` incompatible avec le code). Les deux
anciens fichiers restent en place uniquement comme redirections courtes vers celui-ci.

## 1. Statut

Ce catalogue documente les règles **réellement implémentées et actives** dans
`OrthotypoService` (`src/purh_editorial/services/orthotypo_service.py`), telles
qu'elles fonctionnent aujourd'hui — pas des règles souhaitées ou à écrire.

Il ne s'agit toujours **pas** d'une validation contre le guide typographique réel des
PURH. Ce guide (`sources/editorial_rules/CONSIGNES_AUTEURS_PURH_2025 (1).pdf` et le
*Lexique des règles typographiques… Imprimerie nationale*) est présent dans le dépôt
mais n'a pas encore été dépouillé — c'est l'objet de la Phase 4. Le champ **Source** de
chaque fiche reflète honnêtement ce qui est validé aujourd'hui : soit une observation
directe sur le corpus réel H&P2 (`docs/ANALYSE_CORPUS_HP2.md`), soit une convention
typographique française générale non encore confrontée à une source PURH interne. Un
champ `Source: à confirmer contre le guide PURH (Phase 4)` n'est pas une lacune de ce
document : c'est un état de fait à ne pas masquer.

## 2. Nomenclature

Le code utilise le format `purh.<famille>.<précision>` (ex. `purh.espaces.avant_ponct_forte`)
pour 14 des 17 règles. Trois règles opérationnelles, écrites avant la stabilisation de
cette convention, portent un identifiant différent :

- `R-ORTHO-LIGATURE-OE-001` (ligatures œ) ;
- `R-GQ-004` (diagnostic ponctuation autour des guillemets, hors `OrthotypoService`
  au sens strict des règles de transformation mais rattaché au même service) ;
- `R-SO-001` (stylage petites capitales/exposant des siècles, appliqué en complément
  de `purh.siecles`).

Conformément au principe de cette phase (« faire converger la documentation vers la
nomenclature déjà utilisée dans le code, plutôt que renommer les règles opérationnelles »),
ces identifiants ne sont **pas** renommés ici. Un renommage éventuel vers `purh.xxx.yyy`
relèverait d'une décision de code à part entière, hors du périmètre de ce catalogue.

## 3. Échelle de niveaux

Reprise telle quelle du gabarit d'origine (`/TYPO_RULES_PURH.md`, section 6) :

- **Niveau 1 — Diagnostic seul** : le système signale, sans corriger automatiquement.
- **Niveau 2 — Correction locale proposée** : remplacement simple, réversible, appliqué
  automatiquement par le pipeline mais surligné (couleur `orthotypo`/`footnote`) pour
  rester visible et réversible à la relecture.
- **Niveau 3 — Abstention** : le système ne traite pas automatiquement, renvoie à la
  validation humaine.

Les 17 règles de `OrthotypoService` sont toutes de **Niveau 2** : aucune n'est un simple
diagnostic, toutes s'appliquent automatiquement dès l'étape 2 du pipeline
(`Step1Pipeline`), avec traçabilité par surlignage et par `Transformation` journalisée.

---

## 4. Catalogue — les 17 règles de `OrthotypoService`

### `purh.apostrophe`

- **Titre** : Apostrophe typographique
- **Description** : Convertit l'apostrophe droite (`'`) en apostrophe typographique
  (`’`, U+2019) entre deux caractères alphabétiques.
- **Exemple fautif** : `L'auteur`
- **Exemple attendu** : `L’auteur`
- **Niveau** : 2 — correction locale automatique
- **Source** : convention typographique française générale, non confrontée au guide PURH.
- **Remarques** : aucune exception connue à ce jour ; pas de garde-fou technique (un
  code source cité contenant un guillemet simple ASCII serait aussi converti — risque
  théorique non observé sur le corpus réel).

### `purh.points_suspension`

- **Titre** : Points de suspension
- **Description** : Remplace trois points consécutifs (`...`) par le caractère unique
  points de suspension (`…`, U+2026).
- **Exemple fautif** : `Attendez...`
- **Exemple attendu** : `Attendez…`
- **Niveau** : 2 — correction locale automatique
- **Source** : convention typographique française générale, non confrontée au guide PURH.
- **Remarques** : ne traite que trois points exacts ; `etc...` est repris séparément par
  `purh.abreviations.etc` en aval.

### `purh.guillemets.droits`

- **Titre** : Guillemets droits/anglais → guillemets français ou second niveau
- **Description** : Convertit `"texte"` ou `“texte”` en `« texte »` en texte
  courant. À l'intérieur de guillemets français déjà ouverts, convertit vers le second
  niveau `“texte”` (sans espace insécable). Contextes techniques détectés et exclus :
  attributs XML/HTML (`class="note"`), appels de fonction (`print("x")`), chemins avec
  antislash.
- **Exemple fautif** : `Il dit "bonjour".`
- **Exemple attendu** : `Il dit « bonjour ».`
- **Exemple second niveau** : `« Il dit "bonjour" puis se tut. »` →
  `« Il dit "bonjour" puis se tut. »` devient
  `« Il dit “bonjour” puis se tut. »`
- **Niveau** : 2 — correction locale automatique
- **Source** : **confirmée par observation directe** sur le corpus H&P2
  (`docs/ANALYSE_CORPUS_HP2.md`, catégorie 1) — le pipeline produit exactement ce que les
  éditrices PURH ont produit sur ce point, sur les 16 chapitres testés.
- **Remarques** : garde-fous techniques testés (`tests/unit/test_orthotypo_service_guardrails.py`).

### `R-ORTHO-LIGATURE-OE-001`

- **Titre** : Ligatures œ sur formes lexicales courantes
- **Description** : Remplace `oe`/`Oe`/`OE` par `œ`/`Œ` pour une liste fermée de mots
  courants (`boeuf`, `soeur`, `coeur`, `oeuvre`, `oeil`, `voeu`, `noeud`, `moeurs`, etc.),
  en respectant la casse d'origine.
- **Exemple fautif** : `boeuf boeufs oeuf oeufs`
- **Exemple attendu** : `bœuf bœufs œuf œufs`
- **Contre-exemple (ne doit pas toucher)** : `coelacanthe` → `coelacanthe` (mot hors liste).
- **Niveau** : 2 — correction locale automatique, volontairement bornée à une liste fermée
  (Niveau 3/abstention implicite pour tout mot hors liste — pas de règle générale sur `oe → œ`).
- **Source** : convention typographique française générale, non confrontée au guide PURH.
- **Remarques** : identifiant hérité, ne suit pas la nomenclature `purh.xxx.yyy` (voir §2).

### `purh.guillemets.espace_apres_ouvrant`

- **Titre** : Espace fine insécable après «
- **Description** : Absorbe tout espace (normal, insécable, fine insécable) suivant un
  guillemet ouvrant français et le remplace par une espace fine insécable (U+202F).
- **Exemple fautif** : `« Bonjour` (espace normale)
- **Exemple attendu** : `« Bonjour`
- **Niveau** : 2 — correction locale automatique
- **Source** : convention typographique française standard (Imprimerie nationale),
  cohérente avec le corpus H&P2 mais non vérifiée isolément de `purh.guillemets.droits`.

### `purh.guillemets.espace_avant_fermant`

- **Titre** : Espace fine insécable avant »
- **Description** : Symétrique de la règle précédente, côté guillemet fermant.
- **Exemple fautif** : `Bonjour »`
- **Exemple attendu** : `Bonjour »`
- **Niveau** : 2 — correction locale automatique
- **Source** : idem `purh.guillemets.espace_apres_ouvrant`.

### `purh.espaces.avant_ponct_forte`

- **Titre** : Espace fine insécable avant `: ; ? !`
- **Description** : Insère une espace fine insécable avant deux-points, point-virgule,
  point d'interrogation et point d'exclamation. Garde-fous explicites : URL (`http://`),
  chemins Windows (`C:\dossier`), ratios/heures numériques (`16:9`, `10:30`).
- **Exemple fautif** : `Voici: un cas`
- **Exemple attendu** : `Voici : un cas`
- **Contre-exemples (ne doit pas toucher)** : `http://exemple.org:8080/test`, `10:30`,
  `format 16:9`, `C:\dossier\fichier`.
- **Niveau** : 2 — correction locale automatique
- **Source** : **confirmée par observation directe** sur le corpus H&P2 — motif présent
  des centaines de fois dans les corrections réelles des éditrices.

### `purh.espaces.avant_ponct_faible`

- **Titre** : Suppression de l'espace avant `,` et `.`
- **Description** : Retire toute espace précédant une virgule ou un point (sauf devant
  un chiffre, pour ne pas casser les décimaux).
- **Exemple fautif** : `mot , suite`
- **Exemple attendu** : `mot, suite`
- **Niveau** : 2 — correction locale automatique
- **Source** : convention typographique française générale, non confrontée au guide PURH.

### `purh.espaces.double`

- **Titre** : Double espace → espace simple
- **Description** : Réduit toute séquence de deux espaces/tabulations normales
  consécutives à une seule espace. N'affecte pas les espaces insécables ou fines
  insécables adjacentes à une espace normale (protégées explicitement).
- **Exemple fautif** : `mot  mot`
- **Exemple attendu** : `mot mot`
- **Niveau** : 2 — correction locale automatique
- **Source** : convention typographique générale, non confrontée au guide PURH.

### `purh.civilite`

- **Titre** : Espace insécable après titre de civilité
- **Description** : Insère une espace insécable normale (U+00A0, pas la fine
  insécable) entre un titre de civilité (`M.`, `Mme`, `Mmes`, `Dr`, `Pr`, `Prof.`) et le
  nom propre qui suit.
- **Exemple fautif** : `M. Dupont arrive`
- **Exemple attendu** : `M. Dupont arrive`
- **Niveau** : 2 — correction locale automatique
- **Source** : convention typographique française générale, non confrontée au guide PURH.
- **Remarques** : aucune observation directe sur le corpus H&P2 (peu d'occurrences de
  civilités dans ce corpus) — à vérifier en priorité si un manuscrit avec davantage de
  civilités est disponible.

### `purh.siecles`

- **Titre** : Normalisation des siècles (XIXe)
- **Description** : Normalise les notations de siècle en chiffres romains suivies de
  « e »/« ème »/« ère » (`XIIème`, `xiiième`, `XIIe`…) vers la forme canonique
  `XIIe`, **uniquement si le mot « siècle(s) » ou « s. » suit immédiatement**
  (garde-fou ajouté en Phase 1 — voir ci-dessous). Cas particulier du chiffre romain
  « I » : produit `Ier` (jamais `Ie`, qui n'existe pas en français).
  Une étape séparée (comportement `R-SO-001`, non un `TypoRule`) stylise ensuite le
  chiffre romain en petites capitales et le suffixe en exposant, ce qui repasse le
  texte stocké en minuscules (l'apparence capitale vient du style Word/TEI, pas du texte).
- **Exemple fautif** : `pour le XVIIe siècle` (déjà correct) / `pour le XVIIème siècle`
- **Exemple attendu** : `pour le xviie siècle` (texte stocké, stylé petites capitales +
  exposant à l'affichage)
- **Contre-exemple (ne doit pas toucher)** : `prolonger la vie de l'homme` (le mot
  « vie » ressemble à un siècle « VI » + « e » mais n'est suivi d'aucun mot « siècle »)
  ni `Maximilien Ier` (ordinal de prénom, pas un siècle).
- **Niveau** : 2 — correction locale automatique
- **Source** : **confirmée par observation directe** sur le corpus H&P2 pour la
  normalisation elle-même. Le garde-fou de contexte (§ ci-dessus) corrige un défaut
  réel découvert en Phase 1 (`docs/PHASE1_FIABILITE_PIPELINE.md`, défaut 1 du même
  esprit) : sans lui, la règle corrompait « Maximilien Ier » en « Maximilien Ie » et le
  mot « vie » en « VIe ». Corrigé le 2026-07-24 (commit `e665399`).

### `purh.ordinaux`

- **Titre** : Normalisation prudente des ordinaux simples
- **Description** : `1ère`/`1ere` → `1re` ; `Nème`/`Neme` → `Ne` (N quelconque). Ne
  touche pas `1er` (déjà correct) ni les ordinaux non couverts par ce motif exact.
- **Exemple fautif** : `la 1ère partie`, `le 5ème chapitre`
- **Exemple attendu** : `la 1re partie`, `le 5e chapitre`
- **Contre-exemple (ne doit pas toucher)** : `le 1er chapitre` (déjà correct), `version 2.0`.
- **Niveau** : 2 — correction locale automatique
- **Source** : convention typographique française générale, non confrontée au guide PURH.
- **Remarques** : ne couvre pas l'abréviation « Ie » (sans r) après un prénom de
  souverain (ex. « Jules Ie » → « Jules Ier »), un motif recensé comme récurrent sur le
  corpus H&P2 (catégorie 2b de `docs/ANALYSE_CORPUS_HP2.md`, ~9 occurrences) mais non
  encore couvert par cette règle — candidate pour la Phase 4.

### `purh.tiret.double`

- **Titre** : Double tiret → tiret demi-cadratin
- **Description** : Remplace `--` par le tiret demi-cadratin `–` (U+2013).
- **Exemple fautif** : `Paris--Londres`
- **Exemple attendu** : `Paris–Londres`
- **Niveau** : 2 — correction locale automatique
- **Source** : convention typographique française générale, non confrontée au guide PURH.

### `purh.abreviations.etc`

- **Titre** : `etc…`/`etc...` → `etc.`
- **Description** : Normalise les variantes fautives de « etc. » (points de suspension
  ou points multiples) vers la forme correcte à un seul point.
- **Exemple fautif** : `etc...`, `etc…`
- **Exemple attendu** : `etc.`
- **Niveau** : 2 — correction locale automatique
- **Source** : convention typographique française générale, non confrontée au guide PURH.

### `purh.pagination.espace`

- **Titre** : Espace fine insécable après abréviations de pagination
- **Description** : Insère une espace fine insécable entre une abréviation de
  pagination/référence (`p.`, `pp.`, `vol.`, `t.`, `f.`, `fol.`, `fig.`, `chap.`, `cat.`,
  `pl.`, `ms.`, `Ms.`, `n°`, `N°`, `col.`) et le nombre ou chiffre romain qui suit.
- **Exemple fautif** : `voir p. 12`, `cf. vol. II`
- **Exemple attendu** : `voir p. 12`, `cf. vol. II`
- **Niveau** : 2 — correction locale automatique
- **Source** : convention typographique française standard (Imprimerie nationale),
  cohérente avec les usages observés dans les notes du corpus H&P2 sans avoir été isolée
  spécifiquement dans l'analyse déjà produite.
- **Remarques** : cette règle *reconnaît* `pp.` déjà présent pour l'espacement mais ne le
  *produit* jamais (pas de doublement automatique `p.` → `pp.`) — trou identifié par
  l'audit initial, à traiter en Phase 4.

### `purh.numero`

- **Titre** : Espace fine insécable après n°
- **Description** : Insère une espace fine insécable entre `n°`/`N°` et le chiffre qui suit.
- **Exemple fautif** : `n° 5`, `N° 12`
- **Exemple attendu** : `n° 5`, `N° 12`
- **Niveau** : 2 — correction locale automatique
- **Source** : convention typographique française générale, non confrontée au guide PURH.
- **Remarques** : recouvrement partiel avec `purh.pagination.espace` (qui couvre aussi
  `n°`) — règle distincte conservée pour le cas où `n°` apparaît hors contexte de
  pagination.

### `purh.nombres.milliers`

- **Titre** : Espace fine insécable dans les nombres (séparateur de milliers)
- **Description** : Insère une espace fine insécable entre groupes de trois chiffres
  dans un nombre d'au moins quatre chiffres. Ne touche pas une année isolée (`2025`) ni
  un numéro structuré du type ISBN (déjà séparé par des espaces simples entre groupes
  qui ne forment pas un nombre continu).
- **Exemple fautif** : `1 000`, `1 500 000`
- **Exemple attendu** : `1 000`, `1 500 000`
- **Contre-exemple (ne doit pas toucher)** : `en 2025`, `ISBN 978 2 1234 5678 9`.
- **Niveau** : 2 — correction locale automatique
- **Source** : convention typographique française générale, non confrontée au guide PURH.

### `purh.tiret.incise`

- **Titre** : Tiret cadratin pour les incises
- **Description** : Convertit un tiret simple ou demi-cadratin entouré d'espaces
  (` - ` ou ` – `) en tiret cadratin (` — `, U+2014) lorsqu'il relie deux mots.
- **Exemple fautif** : `une phrase - incise - continue`
- **Exemple attendu (production actuelle)** : `une phrase — incise — continue`
- **Niveau** : 2 — correction locale automatique
- **Source** : **contredite par observation directe** sur le corpus H&P2
  (`docs/ANALYSE_CORPUS_HP2.md`, catégorie 2c). Le manuscrit brut utilise
  systématiquement le tiret **cadratin** « — » pour les incises ; les éditrices PURH le
  remplacent systématiquement par le tiret **demi-cadratin** « – » (50 occurrences
  observées). Cette règle produit donc la convention **opposée** à la pratique éditoriale
  réelle. Elle ne s'est pas déclenchée sur le corpus H&P2 testé (le brut n'y contient pas
  le motif qu'elle cible), donc elle n'y a rien corrompu empiriquement — mais elle
  encoderait la mauvaise convention sur tout manuscrit utilisant déjà le tiret simple.
  **À corriger en priorité en Phase 4**, une fois le guide PURH réel consulté pour
  trancher la convention attendue (l'usage observé côté éditrices suggère le
  demi-cadratin, mais ce n'est qu'une observation sur un seul ouvrage).

---

## 5. Règles complémentaires hors `OrthotypoService` (diagnostics, Niveau 1)

Ces règles étaient déjà répertoriées dans les anciens documents ; elles ne font pas
partie des 17 règles de `OrthotypoService` mais partagent le même système de
`rule_id`/`Diagnostic` et méritent de rester documentées ici pour ne pas perdre
d'information par rapport aux anciens fichiers fusionnés.

### `R-GQ-004` — Ponctuation autour des guillemets fermants

- **Module** : `OrthotypoService.analyze_quote_punctuation`
- **Niveau** : 1 — diagnostic seul, ne modifie jamais le texte.
- **Description** : Signale un guillemet fermant `»` immédiatement suivi d'un point,
  quand le contenu cité se termine déjà par une ponctuation forte — cas ambigu où la
  ponctuation peut appartenir à la citation ou à la phrase englobante.
- **Source** : convention éditoriale prudente, non confrontée au guide PURH.

### `R-AN-002` / `R-AN-003` — Placement des appels de note

- **Module** : `FootnoteNormalizer.analyze_note_call_placement`
- **Niveau** : 1 — diagnostic seul.
- **R-AN-002** : place suspecte d'un appel de note par rapport à la ponctuation.
- **R-AN-003** : espace parasite avant un appel de note.
- **Source** : convention éditoriale prudente, non confrontée au guide PURH.

---

## 6. Ce qu'il reste à faire (Phase 4)

- Dépouiller `sources/editorial_rules/CONSIGNES_AUTEURS_PURH_2025 (1).pdf` et le
  *Lexique… Imprimerie nationale* pour remplacer, règle par règle, le champ Source
  « non confronté au guide PURH » par une référence précise (page, section) ou une
  correction de la règle si le guide contredit la pratique actuelle.
- Trancher la convention de tiret d'incise (`purh.tiret.incise`, cadratin vs
  demi-cadratin) — c'est la seule règle de ce catalogue en contradiction connue avec
  l'usage éditorial observé.
- Ajouter la règle manquante de redoublement d'abréviations déjà présentes
  (`pp.`, `vv.`, `ll.`, `§§`) normalisées vers la forme correcte, identifiée par l'audit
  initial et non couverte par `purh.pagination.espace`.
- Compléter `purh.ordinaux` (ou créer une règle dédiée) pour l'expansion de l'abréviation
  brute « Ie » → « Ier » après un prénom de souverain (catégorie 2b,
  `docs/ANALYSE_CORPUS_HP2.md`).
