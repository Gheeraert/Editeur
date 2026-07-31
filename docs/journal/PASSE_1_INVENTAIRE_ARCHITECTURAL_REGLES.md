# Passe 1 — Inventaire architectural complet des règles éditoriales

## Cadre de l’audit

Audit réalisé en lecture seule sur la branche `reclassement`.

- Aucun fichier de code n’a été modifié pendant l’audit.
- L’IA éditoriale et l’arbitrage IA structurel sont hors périmètre.
- Les constats décrivent le comportement effectivement observé dans le code ; ils ne constituent pas une proposition de refonte.

## Distinctions employées

Trois dimensions doivent rester indépendantes :

1. **Nature de la règle** : déterministe ou heuristique.
2. **Statut de déploiement** : `active`, `review_only` ou `disabled`.
3. **Comportement actuel** : transformation, diagnostic ou absence d’exécution.

Une règle déterministe peut légitimement rester `review_only` lorsqu’aucune source PURH ne l’autorise encore. À l’inverse, une règle heuristique peut être active dans le code actuel : cela décrit l’état présent, sans le valider éditorialement.

## Systèmes actuels de décision

| Système | Emplacement | Effet réel |
|---|---|---|
| `TypoRule.auto` | `services/orthotypo_service.py` | Garde l’application des règles orthotypographiques générales. |
| Liste blanche `purh_validated_rule_ids` | `services/orthotypo_service.py` | Autorise : siècles, ordinaux, `etc.`, espace de pagination, numéro, redoublement d’abréviations. Toutes les autres règles orthotypographiques deviennent des diagnostics. |
| Diagnostics de règles non validées | `OrthotypoService.analyze_unvalidated_rules()` | Produit un diagnostic `pending_human_review` pour chaque règle `auto=False` qui détecte un motif. |
| Protection transversale | `utils/protection.py` | Orthotypographie et notes ignorent blocs, notes et inlines protégés ; les diagnostics associés les ignorent aussi. |
| Profils structurels | `settings_for_heuristic_profile()` | `conservative`, `balanced`, `exploratory` règlent les seuils titre/poésie. |
| Seuils structurels | `HeuristicSettings` | Déterminent `transform`, `diagnostic` ou `ignore` pour les candidats titre et poésie. |
| `auto_apply_diagnostics` | Profil `exploratory` | Réapplique automatiquement certains candidats pourtant classés diagnostic. |
| `decision_mode="deterministic"` | `Step1Options` / pipeline | Désactive les heuristiques scorées, mais ne désactive pas tous les changements structurels : front matter, promotions par style source et suppressions de paragraphes vides subsistent. |
| `auto` des règles notes/bibliographie | `TypoRule` par défaut | Vaut implicitement `True`, mais n’est pas lu comme garde de déploiement : ces règles sont toutes appliquées. |
| Agressivité IA | `Step1Options.ai_aggressiveness` | Identifiée seulement comme contrôle hors périmètre ; aucun examen ni changement de l’IA éditoriale ou du pipeline IA n’a été réalisé. |

## Protections réellement appliquées

`is_protected_block()` protège les types `quote_block`, `lineated_block`, `bibliography_item`, `code`, `table`, `formula`, ainsi que les attributs `protected`, `is_protected`, `protected_zone` et les inlines protégés.

- Orthotypographie : respecte ces protections pour transformations et diagnostics.
- Notes : respecte les protections de la note, de ses inlines et du bloc cible.
- Bibliographie : respecte seulement les protections explicites par attribut/inline, volontairement pas son propre type `bibliography_item`.
- Structure : n’utilise pas le garde transversal ; elle possède des vetos locaux. Un paragraphe explicitement protégé n’est donc pas uniformément protégé contre toutes ses heuristiques structurelles.

## Inventaire orthotypographique

Sources principales : `src/purh_editorial/services/orthotypo_service.py` et `docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md`.

| Règle | Comportement actuel / `auto` | Source documentée | Classification proposée | Statut actuel / cas litigieux |
|---|---|---|---|---|
| `purh.apostrophe` | Diagnostic ; `auto=False` | Convention générale, non PURH | Déterministe local | `review_only` ; apostrophes en code, transcription, noms ou citations. |
| `purh.points_suspension` | Diagnostic ; `False` | Convention générale | Déterministe local | `review_only` ; ellipses intentionnelles, code, notations. |
| `purh.guillemets.droits` | Diagnostic ; `False` | Guide PURH p. 12 + corpus | Heuristique | `review_only` ; un guillemet droit peut être code, pouces, dialogue, citation, second niveau. Source documentée mais absente de la liste blanche. |
| `R-ORTHO-LIGATURE-OE-001` | Diagnostic ; `False` | Convention générale | Déterministe lexical fermé | `review_only` ; lexique fermé solide, mais absence de validation PURH. |
| `purh.guillemets.espace_apres_ouvrant` | Diagnostic ; `False` | Convention générale / cohérence guide | Déterministe conditionnel | `review_only` ; doit rester exclue des citations et zones protégées. |
| `purh.guillemets.espace_avant_fermant` | Diagnostic ; `False` | Idem | Déterministe conditionnel | `review_only` ; même réserve. |
| `purh.espaces.avant_ponct_forte` | Diagnostic ; `False` | Corpus privé, pas source PURH explicite | Heuristique bornée | `review_only` ; URL, chemins, heures et ratios gardés, autres syntaxes techniques possibles. |
| `purh.espaces.avant_ponct_faible` | Diagnostic ; `False` | Convention générale | Déterministe local | `review_only` ; décimales exclues, ponctuation technique à couvrir. |
| `purh.espaces.double` | Diagnostic ; `False` | Convention générale | Déterministe local | `review_only` ; espaces intentionnelles, alignements, transcription. |
| `purh.civilite` | Diagnostic ; `False` | Convention générale | Déterministe conditionnel | `review_only` ; titres étrangers, initiales, styles bibliographiques. |
| `purh.siecles` | Transformation + petites capitales/exposant ; `True` | Guide PURH p. 10 | Déterministe | `active` ; contexte `siècle` / `s.` indispensable ; protège notamment `Ier`. |
| `R-SO-001` | Stylage siècles ; sans champ `auto` | Même source que siècles | Déterministe | `active`, couplée à `purh.siecles` ; le texte peut rester identique mais le style change. |
| `purh.ordinaux` | Transformation ; `True` | Guide PURH p. 10 | Déterministe | `active` ; ne couvre pas le souverain `Ie → Ier`. |
| `purh.tiret.double` | Diagnostic ; `False` | Convention générale | Heuristique | `review_only` ; `--` peut relever du code, d’une plage ou d’une syntaxe source. |
| `purh.abreviations.etc` | Transformation ; `True` | Guide PURH p. 10 | Déterministe | `active` ; cas local fermé. |
| `purh.pagination.espace` | Transformation ; `True` | PURH p. 11–12, couverture partielle | Déterministe conditionnel | `active` ; inventaire d’abréviations plus large que la preuve PURH explicite. |
| `purh.numero` | Transformation + `o` exposé ; `True` | Guide PURH p. 12 | Déterministe | `active` ; interaction à caractériser avec pagination. |
| `R-NO-001` | Stylage du `o` ; sans champ `auto` | Même source | Déterministe | `active`, couplée à `purh.numero`. |
| `purh.abreviations.redoublement` | Transformation ; `True` | Guide PURH p. 11 | Déterministe | `active` ; formes exactes fermées : `pp.`, `vv.`, `ll.`, `§§`. |
| `purh.nombres.milliers` | Diagnostic ; `False` | Convention générale | Déterministe conditionnel | `review_only` ; ISBN, identifiants, tableaux et nombres stylisés. |
| `purh.tiret.incise` | Jamais appliquée ; `False` | Convention non tranchée | Heuristique éditoriale | `disabled` ; son ancien sens contredisait la pratique observée. |
| `R-TI-001` | Diagnostic | Catalogue / corpus | Heuristique éditoriale | `review_only` ; abstention actuelle cohérente. |
| `R-GQ-004` | Diagnostic ponctuation des guillemets | PURH + Imprimerie nationale | Heuristique structurelle | `review_only` ; dépend de citation fondue/non fondue. |

Tests existants : corpus normatif, caractérisation, garde-fous, offsets, traçabilité, siècles, numéro, tiret d’incise, guillemets et protections : `test_orthotypo_*`, `test_quote_punctuation_diagnostics.py`, `test_protected_zones_guardrails.py`.

## Inventaire des notes

Source : `src/purh_editorial/services/footnote_normalizer.py`.

| Règle | Comportement actuel / `auto` | Source | Classification proposée | Statut actuel / cas litigieux |
|---|---|---|---|---|
| `purh.note.espace_initiale` | Transformation ; `auto=True` implicite mais non contrôlé | Non documentée | Déterministe conditionnel | `active` ; dépend de la convention d’import/export des séparateurs de note. |
| `purh.note.majuscule_initiale` | Transformation ; implicite | Non documentée | Heuristique | `active` ; URL, DOI, particules et abréviations latines exclus, mais une note peut légitimement commencer par une minuscule. |
| `purh.note.abreviation_latine` | Minuscule hors début de note ; implicite | Non documentée explicitement | Heuristique | `active` ; sens bibliographique, langue, début effectif de note et séparateur exporté. |
| `purh.note.espace_op_cit` | NNBSP ; implicite | PURH p. 11–12 | Déterministe | `active` ; inclut `op.`, `art.`, `loc. cit.`. |
| `purh.note.espace_sans_lieu_date` | NNBSP ; implicite | PURH p. 11–12 | Déterministe | `active` ; `s. l.` et `s. d.`. |
| `purh.note.ponctuation_finale` | Ajout d’un point ; implicite | Non documentée | Heuristique | `active` ; URL, vers, listes et guillemets exclus, mais fragments bibliographiques ou légendes restent ambigus. |
| `R-AN-002` | Diagnostic appel après ponctuation/guillemet | PURH p. 11 | Déterministe de détection, décision de déplacement humaine | `review_only`. |
| `R-AN-003` | Diagnostic espace avant appel | PURH p. 11 | Déterministe de détection | `review_only` ; pas de déplacement automatique. |
| `R-AN-004` | Diagnostic abstention de majuscule | Règle interne | Heuristique | `review_only`. |
| `R-AN-005` | Diagnostic abstention de point final | Règle interne | Heuristique | `review_only`. |

Tests existants : `test_footnote_normalizer_abbreviations.py`, `test_footnote_normalizer_adversarial.py`, `test_footnote_note_call_diagnostics.py`, plus protections transversales.

## Inventaire bibliographique

Source : `src/purh_editorial/services/bibliography_normalizer.py`.

| Règle | Comportement actuel | Source | Classification proposée | Statut actuel / cas litigieux |
|---|---|---|---|---|
| Détection section bibliographique | Titre `heading` commençant par « Bibliographie », « Sources », etc. | Non documentée comme règle de code | Heuristique | `active` ; regex par préfixe : « Sources de… » peut ouvrir une section à tort. |
| Sortie de section | Prochain heading selon `style_id` | Aucun contrat canonique | Heuristique | `active` ; dépend de styles Word bruts. |
| Promotion des paragraphes de section | `paragraph → bibliography_item` + ajout `BibliographyItem` | Aucun contrat normatif | Heuristique | `active` ; transformation structurelle non explicitement journalisée par le normaliseur. |
| `_BIBLIO_ENTRY_RE` / `_looks_like_biblio_entry` | Helper défini, non utilisé dans le flux | — | Heuristique | `disabled` de fait ; code mort ou fonctionnalité inachevée. |
| `purh.biblio.pagination_nnbsp` | Transformation ; `auto=True` implicite | Non documentée | Déterministe conditionnel | `active` ; appliquée seulement aux items bibliographiques. |
| `purh.biblio.numero_nnbsp` | Transformation ; implicite | Non documentée | Déterministe conditionnel | `active` ; utilise `n°`, à aligner avec la règle PURH `no` exposé. |
| `purh.biblio.ponctuation_finale` | Ajout d’un point final ; implicite | Non documentée | Heuristique | `active` ; dépend du modèle bibliographique, du type d’entrée et de la langue. |

Tests existants : `test_bibliography_normalizer.py` couvre promotion, normalisations, `rule_id`, absence de transformation et protection explicite. Les frontières de section, modèles bibliographiques PURH et faux positifs de titre sont insuffisamment couverts.

## Inventaire structurel

Source : `src/purh_editorial/services/structure_service.py`.

| Règle / famille | Comportement actuel | Classification proposée | Statut actuel / risques |
|---|---|---|---|
| `structure.frontmatter.abstract` | Rôle canonique `abstract` sur étiquette stricte | Déterministe conditionnel | `active` ; idempotente, conserve rôle existant identique, diagnostique les conflits. |
| `structure.frontmatter.keywords` | Rôle `keywords` | Déterministe conditionnel | `active` ; mêmes garanties. |
| `structure.frontmatter.acknowledgment` | Rôle `acknowledgment` | Déterministe conditionnel | `active` ; mêmes garanties. |
| Coupe-circuit front matter | Arrête les heuristiques ultérieures dès une étiquette stricte reconnue | Déterministe de contrôle | `active` ; comportement important à préserver. |
| `structure.source_style.heading` | Promotion depuis `heading_level`, `style_id` ou `style_name` | Heuristique fondée sur fait Word | `active`, même en `decision_mode="deterministic"` ; conflit avec vetos seulement diagnostiqué. |
| `structure.allcaps.heading` | Promotion tout-capitales sous seuil | Heuristique | `active` selon score/profil ; risque sur références, acronymes, poésie. |
| `structure.bold.heading` | Promotion gras seul | Heuristique | `active` selon score/profil ; gras n’est pas une sémantique. |
| `structure.italic.author` | Italique seul → auteur | Heuristique | `active` ; texte italique peut être titre, citation ou emphase. |
| `structure.italic.heading` | Italique seul → titre | Heuristique | `active` selon score/profil. |
| `structure.epigraph.heuristic` | Premier paragraphe court non ponctué → épigraphe | Heuristique | `active` ; très contextuel. |
| `structure.bibliography.section` | Paragraphes sous titre bibliographique → bibliographie | Heuristique | `active` ; dépend du titre et des frontières. |
| `structure.bibliography.heuristic` | Motif auteur/titre/année hors section | Heuristique | `active` malgré `confidence="low"` ; produit aussi un diagnostic. |
| `structure.indent.quote` | Retrait gauche → citation longue | Heuristique | `active` ; retrait Word n’est qu’un indice. |
| `structure.quote.guillemets` | Guillemet + longueur → `quote_block` | Heuristique | `active`. |
| `structure.heading.heuristic` | Intertitre court/scoré | Heuristique scorée | `active` au-dessus du seuil ; diagnostic dans zone grise. |
| `R-STRUCT-HEADING-001` | Score titre, vetos et diagnostic | Heuristique scorée | `active` / `review_only` selon score. |
| `structure.lineated.blank_bounded.merge` | Fusion automatique de 3–20 lignes courtes encadrées de blancs en `lineated_block` | Heuristique structurelle forte | `active` ; supprime des blocs et modifie le pivot. |
| `structure.lineated.short_sequence.merge` | Ancien mécanisme de fusion de séquences courtes | Heuristique | `disabled` de fait : helper non appelé par `process()`. |
| `R-CI-POETRY-001` | Score poésie | Heuristique scorée | `active` / `review_only` selon seuil. |
| `structure.lineated.group.annotate` | Annote chaque ligne candidate ; peut produire une `Transformation` même au niveau diagnostic | Heuristique scorée | actif ; distinction diagnostic/transformation poreuse. |
| `structure.lineated.stanza.merge` | Fusion automatique des vers au-dessus du seuil | Heuristique scorée | `active` ; supprime des blocs. |

Vetos structurels existants : références de passages, légendes/références, listes, bibliographie, balisage technique, lignes de poésie, listes de noms, phrases, fragments très courts et connecteurs de phrase. Ils sont précieux, mais ne remplacent pas une protection transversale uniforme.

Tests existants : `test_frontmatter_semantics.py`, `test_heading_heuristic_scoring.py`, `test_structure_service_heading_guardrails.py`, `test_poetry_heuristic_scoring.py`, `test_structure_service_poetry_detection.py`, `test_structure_poetry_heading_confusion.py`, et intégrations de pipeline.

## Décisions éditoriales à prendre avant toute nouvelle activation

1. Confirmer si les règles documentées PURH mais aujourd’hui exclues de `purh_validated_rule_ids`, notamment les guillemets droits, doivent être actives ou rester en revue humaine.
2. Définir une politique distincte pour les règles déterministes mais non sourcées PURH : rester `review_only`, ou accepter une source Imprimerie nationale explicitement référencée.
3. Décider du statut de la ponctuation finale des notes et de bibliographie : ces corrections ne sont pas canoniques sans connaître modèle, langue et nature de l’entrée.
4. Décider si les règles de notes sourcées (`op. cit.`, `s. l.`, `s. d.`) peuvent rester automatiques indépendamment du modèle bibliographique choisi.
5. Définir si la reconnaissance d’une section bibliographique est une décision humaine, une heuristique à diagnostic, ou une décision canonique amont.
6. Décider si un style Word de titre peut encore promouvoir automatiquement un bloc, alors que les documents d’architecture qualifient le style Word d’indice.
7. Décider si toute fusion ou retypographie de poésie doit devenir `review_only` : elle est aujourd’hui automatique à certains seuils et modifie la structure.
8. Maintenir l’abstention sur le tiret d’incise tant qu’une consigne PURH explicite n’existe pas.
9. Définir une règle d’autorité cohérente entre catalogue historique, code et liste blanche ; ils divergent actuellement.

## Invariants à préserver lors d’un refactoring à comportement constant

- Une transformation conserve `rule_id`, `target_ref`, avant/après, offsets et ordre d’application.
- Les stylages seuls des siècles et numéros sont reconnus comme transformations, même si le texte brut ne change pas.
- Les zones protégées bloquent orthotypographie, notes et diagnostics associés.
- Les diagnostics de règles non validées n’altèrent jamais le texte.
- La reconnaissance front matter est idempotente, conserve le rôle préexistant et coupe les heuristiques de titre.
- Les vetos structurels empêchent notamment qu’une référence, une liste, un passage poétique ou une bibliographie devienne un titre.
- Les seuils et profils existants restent reproductibles tant que leur politique n’est pas explicitement redéfinie.
- Les règles bibliographiques appliquent leurs corrections localement avec leur propre `rule_id`.
- Notes et orthotypographie restent idempotentes sur leurs cas déjà caractérisés.

## Périmètre recommandé des tests de caractérisation

### Orthotypographie

- Un cas positif, négatif, protégé et idempotent par règle.
- Distinction stricte transformation / diagnostic pour chaque `auto=False`.
- Test de cohérence catalogue ↔ liste blanche.
- Cas de style seul pour siècles et numéros.

### Notes

- Matrice début de note : phrase, URL, DOI, particule, abréviation latine, citation.
- Matrice fin de note : phrase, URL, vers, liste, guillemet, entrée bibliographique.
- Protection d’une note liée à un bloc protégé.
- Réimport après export DOCX.

### Bibliographie

- Faux positifs de titres « Sources de… ».
- Sortie de section avec styles non normalisés.
- Modèle PURH 1 versus modèle auteur-date.
- Entrée sans point final dont l’absence est intentionnelle.
- Interaction `n°` bibliographique / règle PURH `no` exposé.

### Structure

- Une fixture minimale par transformation automatique.
- Une contre-fixture par veto.
- Vérification du nombre, de l’ordre et des identifiants des blocs après fusion.
- Tests explicitant les différences entre profils conservateur, équilibré et exploratoire.
- Tests prouvant que `decision_mode="deterministic"` n’exécute que les décisions réellement considérées déterministes.

### Transversal

- Même corpus exécuté sur bloc normal, citation, poésie, code, tableau, bibliographie, formule et protection explicite.
- Aucune transformation ni diagnostic contradictoire dans une zone protégée.

## Conclusion

Aucune architecture de remplacement n’est proposée dans cette première passe. L’inventaire établit les règles, leurs sources, leur mécanisme et leurs divergences de déploiement afin de préparer les passes de reclassification suivantes.
