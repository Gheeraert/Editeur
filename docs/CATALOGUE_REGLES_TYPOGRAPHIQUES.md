# Catalogue des règles typographiques — document de référence unique

**Confidentialité** : le corpus privé cité en source de certaines règles est désigné par
l'identifiant générique `private_corpus_a` (voir `docs/CORPUS_ET_FIXTURES.md`), jamais par
un titre, un auteur ou un extrait de texte.

Ce document fusionne et remplace `/TYPO_RULES_PURH.md` (gabarit resté vide) et
`/docs/TYPO_RULES_PURH.md` (nomenclature `R-SP-xxx` incompatible avec le code). Les deux
anciens fichiers restent en place uniquement comme redirections courtes vers celui-ci.

## 1. Statut

Ce catalogue documente les règles **réellement implémentées et actives** dans
`OrthotypoService` (`src/purh_editorial/services/orthotypo_service.py`), telles
qu'elles fonctionnent aujourd'hui — pas des règles souhaitées ou à écrire.

**Mise à jour Phase 4** : `sources/editorial_rules/CONSIGNES_AUTEURS_PURH_2025 (1).pdf`
(le guide réel des PURH, 16 pages) et le chapitre « Citations » du *Lexique des règles
typographiques… Imprimerie nationale* ont été dépouillés — voir
`docs/PHASE4_EXTRACTION_REGLES_PURH.md` pour le détail de l'extraction. Les champs
Source ci-dessous ont été mis à jour en conséquence pour les règles concernées. Le reste
du guide PURH (bibliographie, index, citations) n'a pas encore été traduit en règles
automatisables : il s'agit de décisions structurelles (fondu/non fondu, langue, modèle
bibliographique choisi) qui dépassent la portée d'une substitution regex — voir le
rapport de Phase 4 pour le détail et les raisons de ne pas les avoir implémentées telles
quelles. Le champ **Source** de chaque fiche reflète honnêtement ce qui est validé
aujourd'hui : soit une confirmation dans le guide PURH réel (citée avec sa page), soit
une observation directe sur le corpus privé `private_corpus_a` (`docs/ANALYSE_CORPUS_HP2.md`), soit une
convention typographique générale non encore confrontée à une source PURH interne.

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
- **Source** : **confirmée par observation directe** sur le corpus privé `private_corpus_a`
  (`docs/ANALYSE_CORPUS_HP2.md`, catégorie 1) — le pipeline produit exactement ce que les
  éditrices PURH ont produit sur ce point, sur les 16 chapitres testés. **Confirmée aussi
  par le guide PURH réel** (`CONSIGNES_AUTEURS_PURH_2025.pdf`, p. 12, section « Guillemets
  français ou guillemets anglais ? ») : guillemets français exclusivement en texte courant,
  espace insécable après l'ouvrant et avant le fermant, guillemets anglais réservés à une
  citation de second niveau sans aucune espace interne — exactement le comportement de
  cette règle.
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
  cohérente avec le corpus privé `private_corpus_a` mais non vérifiée isolément de `purh.guillemets.droits`.

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
- **Source** : **confirmée par observation directe** sur le corpus privé `private_corpus_a` — motif présent
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
- **Remarques** : aucune observation directe sur le corpus privé `private_corpus_a` (peu d'occurrences de
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
- **Source** : **confirmée par observation directe** sur le corpus privé `private_corpus_a` pour la
  normalisation elle-même, et **confirmée par le guide PURH réel**
  (`CONSIGNES_AUTEURS_PURH_2025.pdf`, p. 10, tableau « Siècles, abréviations et
  symboles ») : « Les siècles sont toujours composés en chiffres romains et en petites
  capitales » ; le tableau donne explicitement `XIXème` → `XIXe` et surtout `Ier` → `Ier`
  (inchangé), qui valide directement le cas particulier ajouté en Phase 1. Le garde-fou
  de contexte (§ ci-dessus) corrige un défaut réel découvert en Phase 1
  (`docs/PHASE1_FIABILITE_PIPELINE.md`, défaut 1 du même esprit) : sans lui, la règle
  corrompait « Maximilien Ier » en « Maximilien Ie » et le mot « vie » en « VIe ».
  Corrigé le 2026-07-24 (commit `e665399`).

### `purh.ordinaux`

- **Titre** : Normalisation prudente des ordinaux simples
- **Description** : `1ère`/`1ere` → `1re` ; `Nème`/`Neme` → `Ne` (N quelconque). Ne
  touche pas `1er` (déjà correct) ni les ordinaux non couverts par ce motif exact.
- **Exemple fautif** : `la 1ère partie`, `le 5ème chapitre`
- **Exemple attendu** : `la 1re partie`, `le 5e chapitre`
- **Contre-exemple (ne doit pas toucher)** : `le 1er chapitre` (déjà correct), `version 2.0`.
- **Niveau** : 2 — correction locale automatique
- **Source** : **confirmée par le guide PURH réel** (`CONSIGNES_AUTEURS_PURH_2025.pdf`,
  p. 10) : « Pour les ordinaux, on abrège "e" et non pas "ème", "re" et non pas "ère" » —
  correspond exactement au comportement de cette règle.
- **Remarques** : ne couvre pas l'abréviation « Ie » (sans r) après un prénom de
  souverain (ex. « Jules Ie » → « Jules Ier »), un motif recensé comme récurrent sur le
  corpus privé `private_corpus_a` (catégorie 2b de `docs/ANALYSE_CORPUS_HP2.md`, ~9 occurrences) mais non
  encore couvert par cette règle — candidate pour une prochaine phase (voir
  `docs/PHASE4_EXTRACTION_REGLES_PURH.md`).

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
- **Source** : **confirmée par le guide PURH réel** (`CONSIGNES_AUTEURS_PURH_2025.pdf`,
  p. 10, tableau des abréviations) : « Et caetera : etc. Jamais en italique. Toujours
  suivi d'un point abréviatif, qui se substitue au point final si l'abréviation termine
  la phrase, et non de points de suspension. »

### `purh.pagination.espace`

- **Titre** : Espace fine insécable après abréviations de pagination
- **Description** : Insère une espace fine insécable entre une abréviation de
  pagination/référence (`p.`, `pp.`, `vol.`, `t.`, `f.`, `fol.`, `fig.`, `chap.`, `cat.`,
  `pl.`, `ms.`, `Ms.`, `n°`, `N°`, `col.`) et le nombre ou chiffre romain qui suit.
- **Exemple fautif** : `voir p. 12`, `cf. vol. II`
- **Exemple attendu** : `voir p. 12`, `cf. vol. II`
- **Niveau** : 2 — correction locale automatique
- **Source** : **confirmée par le guide PURH réel** (`CONSIGNES_AUTEURS_PURH_2025.pdf`,
  p. 11-12) pour les entrées listées avec « espace insécable entre les 2 éléments »
  (`loc. cit.`, `op. cit.`, `s. d.`, `s. l.`). Pour `p.`/`fig.`/`vol.`/etc., cohérent avec
  les usages observés dans les notes du corpus privé `private_corpus_a` sans avoir été isolé spécifiquement
  dans l'analyse déjà produite.
- **Remarques** : cette règle *reconnaît* `pp.` déjà présent pour l'espacement, mais la
  normalisation `pp.` → `p.` elle-même relève désormais de `purh.abreviations.redoublement`
  (ci-dessous), appliquée dans l'ordre des règles.
- **Écart identifié, non corrigé** : le guide (p. 12) abrège aussi « folio » en `fol.`/`fo`
  et « recto/verso » en `ro`/`vo`, avec, dans ces deux derniers cas, la lettre `o`
  **en exposant**, un style que cette règle ne produit pas (elle insère seulement une
  espace). Non traité dans cette phase : un exposant sélectif nécessiterait un
  éclatement en spans au même titre que le stylage des siècles (`R-SO-001`), hors
  périmètre d'une simple substitution regex — voir `docs/PHASE4_EXTRACTION_REGLES_PURH.md`.

### `purh.numero`

- **Titre** : Forme « no » avec o en exposant, plutôt que le symbole degré
- **Description** : Convertit `n°`/`N°` suivi d'un chiffre en la forme `no` (lettre `o`
  en exposant) avec une espace fine insécable avant le chiffre — la forme demandée par
  le guide PURH, pas le symbole degré `°`.
- **Exemple fautif** : `n° 5`, `N° 12`
- **Exemple attendu** : `no 5` (o en exposant), `No 12`
- **Niveau** : 2 — correction locale automatique, avec stylage en exposant
  (`_style_numero_in_inlines`, `rule_id` `R-NO-001`, éclatement en spans au même titre
  que le stylage des siècles, `R-SO-001`).
- **Source** : **confirmée par le guide PURH réel**
  (`CONSIGNES_AUTEURS_PURH_2025.pdf`, p. 12) : la forme demandée pour « numéro » est
  `no` avec la lettre `o` **en exposant** (comme pour `fo`/`ro`/`vo`), pas le symbole
  degré `n°`.
- **Historique** : jusqu'en Passe 6 bis, cette règle produisait par erreur le symbole
  degré (`n° 5`), contredisant le guide PURH réel — voir
  `docs/PHASE4_EXTRACTION_REGLES_PURH.md` pour le constat initial. Corrigée pour produire
  la forme exposant attendue, testée dans `tests/unit/test_orthotypo_numero_styling.py`.
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

### `purh.abreviations.redoublement`

- **Titre** : Abréviation redoublée → forme simple (`pp.`/`vv.`/`ll.`/`§§`)
- **Description** : Réduit une abréviation française redoublée pour marquer le pluriel
  (usage anglais) vers sa forme simple correcte en français : `pp.` → `p.`, `vv.` → `v.`,
  `ll.` → `l.`, `§§` → `§`. S'applique quel que soit le contenu qui suit (plage de pages,
  nombre unique, etc.) ; se compose avec `purh.pagination.espace` pour l'espacement fin
  qui suit `p.` devant un chiffre.
- **Exemple fautif** : `pp. 53-84`, `vv. 122-128`, `ll. 5 et 12`, `§§ 5-9`
- **Exemple attendu** : `p. 53-84`, `v. 122-128`, `l. 5 et 12`, `§ 5-9`
- **Contre-exemple (ne doit pas toucher)** : `supp. cit.` (« pp » n'est pas en début de
  mot, pas de redoublement d'abréviation).
- **Niveau** : 2 — correction locale automatique
- **Source** : **confirmée par le guide PURH réel** (`CONSIGNES_AUTEURS_PURH_2025.pdf`,
  p. 11) : « Ne jamais redoubler tout ou partie d'une abréviation française pour indiquer
  le pluriel », avec exactement ces quatre exemples (`pp.`→`p.`, `vv.`→`v.`, `ll.`→`l.`,
  `§§`→`§`).
- **Ajoutée en Phase 4** (2026-07-25) pour combler le trou identifié par l'audit initial :
  seule la *création* de nouveaux redoublements était jusqu'ici empêchée
  (`purh.pagination.espace` ne fait que reconnaître `pp.` déjà présent pour l'espacement,
  sans jamais le produire) ; les redoublements déjà présents dans un manuscrit n'étaient
  pas normalisés. Le prompt de `ai_editorial_service.py` (« Abréviations normalisées :
  p. XX (pas pp.) ») était déjà cohérent avec cette règle avant même son écriture — vérifié,
  aucune double source de vérité à corriger.

### `purh.tiret.incise`

- **Titre** : Tiret cadratin pour les incises — **abstention depuis Passe 6 bis**
- **Description (pattern conservé, jamais appliqué automatiquement)** : convertirait un
  tiret simple ou demi-cadratin entouré d'espaces (` - ` ou ` – `) en tiret cadratin
  (` — `, U+2014) lorsqu'il relie deux mots.
- **Statut actuel** : `auto=False` dans `OrthotypoService` — cette règle **ne s'applique
  plus jamais automatiquement**. Elle est remplacée par un diagnostic pur,
  `analyze_incise_dash` (`rule_id` `R-TI-001`, Niveau 1), qui signale la présence d'un
  tiret d'incise sans jamais le corriger : *« Convention du tiret d'incise à vérifier :
  aucune normalisation automatique n'a été appliquée. »*
- **Pourquoi** : observation directe sur le corpus privé `private_corpus_a`
  (`docs/ANALYSE_CORPUS_HP2.md`, catégorie 2c) : le manuscrit brut utilise
  systématiquement le tiret **cadratin** « — » pour les incises ; les éditrices PURH le
  remplacent systématiquement par le tiret **demi-cadratin** « – » (50 occurrences
  observées) — soit la convention **opposée** à ce que cette règle produisait. Le guide
  PURH réel ne tranche pas explicitement la question (il mentionne seulement le tiret
  cadratin pour un usage différent, p. 8), et l'observation ci-dessus ne porte que sur un
  seul ouvrage : appliquer automatiquement la convention inverse de la pratique observée
  aurait été un contresens plus risqué qu'une abstention. D'où le passage en diagnostic
  seul (voir `tests/unit/test_orthotypo_incise_dash_abstention.py`).

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
- **Source** : le principe même de cette règle (diagnostic prudent plutôt que correction
  automatique) est **confirmé comme nécessaire** par le guide PURH (p. 12, « Guillemet
  fermant et ponctuation finale ») et par le *Lexique Imprimerie nationale* (chapitre
  « Cit. », section « Guillemets et ponctuation ») : la position de la ponctuation finale
  par rapport au guillemet fermant dépend de si la citation est *fondue* dans la phrase
  ou en constitue une entière — une distinction structurelle que ni le guide ni le
  lexique ne réduisent à une règle mécanique, ce qui valide le choix de rester en
  diagnostic (Niveau 1) plutôt que de corriger automatiquement.

### `R-AN-002` / `R-AN-003` — Placement des appels de note

- **Module** : `FootnoteNormalizer.analyze_note_call_placement`
- **Niveau** : 1 — diagnostic seul.
- **R-AN-002** : place suspecte d'un appel de note par rapport à la ponctuation.
- **R-AN-003** : espace parasite avant un appel de note.
- **Source** : **confirmée par le guide PURH réel** (`CONSIGNES_AUTEURS_PURH_2025.pdf`,
  p. 11, « Appels de note ») : « L'appel de note se place toujours avant la ponctuation
  ou le guillemet fermant... Il ne doit pas être précédé d'une espace et ne peut être
  rejeté à la ligne suivante. » — correspond exactement à ce que ces deux diagnostics
  signalent.

### `R-TI-001` — Tiret d'incise à vérifier (ajoutée en Passe 6 bis)

- **Module** : `OrthotypoService.analyze_incise_dash`
- **Niveau** : 1 — diagnostic seul, ne modifie jamais le texte.
- **Description** : signale la présence d'un tiret d'incise (simple ou demi-cadratin
  entouré d'espaces reliant deux mots) sans jamais le corriger automatiquement.
  Remplace l'ancien comportement automatique de `purh.tiret.incise` (voir plus haut),
  désactivé (`auto=False`) car il encodait la convention opposée à celle observée côté
  éditrices sur le corpus privé `private_corpus_a`.
- **Source** : voir la fiche `purh.tiret.incise` ci-dessus.

### `R-NO-001` — Stylage exposant du « o » de `purh.numero` (ajoutée en Passe 6 bis)

- **Module** : `OrthotypoService._style_numero_in_inlines`
- **Niveau** : 2 — transformation stylistique automatique, appliquée en complément de
  `purh.numero` (même principe d'éclatement en spans que `R-SO-001` pour les siècles).
- **Description** : applique le style exposant à la lettre `o` produite par
  `purh.numero`, pour obtenir `no`/`No` avec `o` visuellement en exposant plutôt que le
  symbole degré.
- **Source** : voir la fiche `purh.numero` ci-dessus.

---

## 6bis. Passe 6 bis — corrections apportées à `purh.numero` et `purh.tiret.incise`

Les deux écarts identifiés en Phase 4 (`purh.numero` produisait le symbole degré au lieu
de la forme exposant demandée par le guide PURH ; `purh.tiret.incise` encodait la
convention opposée à celle observée côté éditrices) ont été traités : `purh.numero`
produit désormais la forme exposant attendue (`R-NO-001`), et `purh.tiret.incise` est
passée en abstention diagnostique (`R-TI-001`) plutôt que de continuer à appliquer une
correction dont le sens s'est révélé incertain. Voir les fiches correspondantes ci-dessus
et `docs/CORPUS_ET_FIXTURES.md` pour la terminologie corpus utilisée dans leur
justification.

## 6. Ce qui a été fait en Phase 4, et ce qui reste

Voir `docs/PHASE4_EXTRACTION_REGLES_PURH.md` pour le rapport complet. En bref :

**Fait** : dépouillement de `CONSIGNES_AUTEURS_PURH_2025.pdf` (intégral, 16 pages) et du
chapitre « Citations » du *Lexique Imprimerie nationale* ; sources mises à jour
ci-dessus pour 8 des 17 règles ; nouvelle règle `purh.abreviations.redoublement`
implémentée et testée ; cohérence du prompt `ai_editorial_service.py` vérifiée (déjà
cohérente, rien à corriger).

**Reste à faire**, par ordre de priorité suggéré :

1. Trancher la convention de tiret d'incise (`purh.tiret.incise`, cadratin vs
   demi-cadratin) — toujours la seule règle en contradiction connue avec l'usage
   éditorial observé ; le guide PURH ne tranche pas explicitement ce point précis.
2. Espace insécable entre un nom propre et le numéral dynastique qui le suit
   (« Louis XIV », « Léon X ») — **candidate la plus solide** pour une prochaine règle :
   confirmée à la fois par 784 occurrences sur le corpus privé `private_corpus_a` et par le *Lexique
   Imprimerie nationale* (règle de coupure : « les noms de souverains [ne seront pas
   séparés] de leur numéro dynastique »). Non implémentée dans cette phase (absente de
   la liste de gaps que cette phase devait traiter).
3. Composition des citations (4 cas fondu/non fondu × français/étranger), guillemets de
   second niveau (déjà couvert, confirmé), modèles bibliographiques, format des entrées
   d'index : identifiés et documentés dans le rapport de Phase 4, mais **non
   implémentés** — ce sont des décisions structurelles (détection de citation, langue,
   modèle bibliographique choisi par l'auteur) hors de portée d'une substitution regex
   isolée ; nécessitent une conception au niveau `structure_service`/zones protégées.
4. Deux écarts de style secondaires identifiés (numéro en `no` exposant plutôt que `n°` ;
   folio/recto/verso avec `o` exposant) — nécessitent le même mécanisme d'éclatement en
   spans que le stylage des siècles, non traités ici.
5. Compléter `purh.ordinaux` (ou créer une règle dédiée) pour l'expansion de l'abréviation
   brute « Ie » → « Ier » après un prénom de souverain (catégorie 2b,
   `docs/ANALYSE_CORPUS_HP2.md`).
