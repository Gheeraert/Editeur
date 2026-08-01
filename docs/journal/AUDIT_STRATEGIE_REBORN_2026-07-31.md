# Audit du dépôt PURH Editorial Studio — 2026-07-31

Rapport de lecture seule. Aucune modification de code n'a été apportée à l'occasion de cet audit.

## 0. Résumé exécutif

Le dépôt contient **deux systèmes de correction complets et indépendants** :

| | Ancien système (« legacy ») | Nouveau système (« reborn ») |
|---|---|---|
| Entrée | `main.py` → `ui/step1_dialog.py` (Tk, 1739 lignes) | `corrector/cli.py` (argparse, pas d'UI) |
| Cœur | `pipeline/step1.py` (781 l.) + `services/orthotypo_service.py` (1087 l.) + `services/structure_service.py` (1846 l.) + `services/structure_ai_arbitrator.py` (759 l.) + IA, pivot JSON, TEI, LaTeX, seuils, profils | `corrector/word_document.py` (268 l.) + `corrector/rules/*.py` (≈1058 l.) |
| Philosophie | pivot Python-JSON, scoring, seuils, profils prudent/équilibré/exploratoire, IA structurelle + éditoriale, exports multiples (DOCX/TEI/LaTeX/JSON) | ouvrir une copie DOCX via COM Word, appliquer des règles déterministes/heuristiques simples, surligner, ressauvegarder — **exactement ce qui est demandé aujourd'hui** |
| Branché sur `main.py` ? | **Oui, c'est le seul point d'entrée actuel** | **Non — inaccessible sans ligne de commande** |

**Constat central : le produit visé (interface Tkinter → DOCX surligné) n'est pas ce que `main.py` lance aujourd'hui.** Un utilisateur qui exécute `python main.py` obtient l'ancienne architecture (pivot, IA, seuils, exports multiples), pas le correcteur `reborn`. Le correcteur `reborn` fonctionne mais n'a pas d'interface graphique et ne couvre qu'une fraction du catalogue de 61 règles.

Par ailleurs, le dernier commit (`d04f8e9`, *« Supprimer l'ancienne machinerie de correction »*) **n'a supprimé aucun code** — il a seulement ajouté un fichier d'avis (`avis_refactoring_regles.md`). Le message de commit est trompeur par rapport à son contenu réel.

---

## 1. Avis sur la stratégie actuelle (`reborn`)

**Sur le principe, la stratégie est la bonne et mérite d'être validée sans réserve** :

- Elle abandonne explicitement les notions qui ont fait échouer les tentatives précédentes (score, seuil, profils, moteur de décision générique, shadow/parité legacy-native) — `docs/REBORN_ARCHITECTURE.md` §3 et §7 l'écrivent noir sur blanc, en cohérence avec l'objectif affiché.
- Le mécanisme technique choisi (copie du DOCX, automatisation COM `Word.Application` via `pywin32`, modification de `Range` in place, `HighlightColorIndex` jaune pour les transformations / turquoise pour les diagnostics) est **simple, robuste vis-à-vis de la mise en page**, et répond exactement à l'impératif « toute intervention doit être surlignée, aucune intervention silencieuse ». C'est actuellement le seul mécanisme du dépôt qui tient réellement cette promesse.
- La forme minimale de règle (`rule_id`, `description`, `scope`, `detector`, `action`, `guards`, `exceptions`, pas de couche architecturale) est bien respectée dans `corrector/rules/orthotypography.py` et `footnotes.py` : ce sont des regex + tables de remplacement lisibles, testées, avec garde-fous locaux. C'est exactement le niveau de simplicité voulu pour un outil « corrigible facilement par la suite ».

**Réserves, par ordre d'importance :**

1. **Le chemin `reborn` est inachevé et surtout non branché.** Sur les 61 règles du catalogue, le nouveau moteur en couvre effectivement une partie via l'orthotypographie et les notes, mais :
   - `corrector/rules/bibliography.py` définit `BIBLIOGRAPHY_TEXT_RULES` (2 règles) — **jamais importé nulle part dans `word_document.py`**. Code mort, silencieusement inactif.
   - `corrector/rules/structure.py` définit `detect_frontmatter_rule`/`FRONTMATTER_PATTERNS` — **jamais appelé en dehors de son propre test unitaire**. Aucune des 21 règles de structure n'est réellement appliquée par le runner.
   - `runner.py` déclare pourtant ces `rule_id` dans `RULE_IDS` (donc dans le dictionnaire de comptage renvoyé à l'utilisateur), ce qui signifie que **l'outil rapporte « 0 correction » pour des familles entières de règles jamais exécutées**, sans distinction avec « 0 correction parce que le texte était déjà correct ». C'est risqué pour un outil dont la garantie centrale est « rien de silencieux ».
2. **Aucune interface graphique n'existe pour ce moteur.** `docs/REBORN_ARCHITECTURE.md` §11.7 prévoyait « ajouter éventuellement une interface simple après stabilisation » — cohérent avec l'esprit incrémental, mais `main.py` pointe aujourd'hui vers l'ancienne interface, ce qui rend le nouveau moteur invisible pour une éditrice qui lancerait le programme normalement.
3. **Aucun mécanisme de commentaire Word** n'est implémenté côté `reborn` (seul le surlignage l'est) — acceptable au vu du caractère facultatif exprimé pour les commentaires, mais à noter comme lacune si un commentaire minimal expliquant la nature de l'intervention est souhaité à terme.
4. Le document `avis_refactoring_regles.md` (ajouté par le dernier commit) contient un vrai point de fond à retenir : dans l'ancien `orthotypo_service.py`, l'axe « déterministe / heuristique » a historiquement été confondu avec l'axe « validé pour application automatique / laissé en diagnostic ». Si `reborn` continue d'être enrichi, il faudra trancher explicitement, règle par règle, laquelle des 31 règles dites « heuristiques » du catalogue est en réalité une regex sûre qu'on peut auto-appliquer, et laquelle nécessite un vrai jugement — plutôt que de laisser le doute filtrer dans l'implémentation au fil de l'eau.

**Verdict** : garder le cap `reborn`, ne pas revenir à la voie legacy. Les deux priorités techniques immédiates sont (a) brancher `main.py` / une UI Tkinter sur `corrector.correct_docx`, pas sur `ui/step1_dialog.py`, et (b) soit compléter, soit retirer honnêtement les règles bibliographie/structure déclarées mais non exécutées.

---

## 2. Scories des implémentations précédentes — inventaire et plan de suppression

### 2.1 Code mort ou orphelin (candidat à suppression pure)

| Élément | Taille | Constat |
|---|---|---|
| `src/purh_editorial/rules/model.py` + `rules/registry.py` | 1474 lignes | Registre « pur » et moteur de décision de la tentative *Passe 4A/4B* (« socle pur », « moteur de décision et politique de seuils »). **N'est importé par aucun autre module du dépôt** (seul `registry.py` s'auto-référence). Couvert uniquement par ses propres tests (`tests/unit/rules/test_rule_*.py`), qui ne testent donc rien d'utilisé en production. |
| `src/purh_editorial/services/structure_ai_arbitrator.py` | 759 lignes | Arbitrage IA à seuils/agressivité — dépendant de la voie legacy uniquement, hors périmètre `reborn` par construction (§7 de `REBORN_ARCHITECTURE.md` exclut explicitement ces notions). |
| `word_side_by_side_diagnostic.json` (racine, suivi par git) | — | Artefact de sortie d'un script de diagnostic (`tools/diagnose_word_side_by_side.py`), committé au lieu d'être ignoré. |
| `src/purh_editorial/rules/orthotypography/` | dossier vide + `__pycache__` | Résidu non suivi (déjà ignoré de fait) d'un module supprimé ; nettoyage local sans impact git. |
| `.idea/` (suivi par git : `Editeur.iml`, `misc.xml`, `modules.xml`, `vcs.xml`) | — | Config IDE personnelle committée ; n'a pas sa place dans un dépôt partagé. |

### 2.2 Code vivant mais appartenant à la voie abandonnée (à figer, puis retirer après validation de `reborn`)

Toute la chaîne suivante n'est utilisée que par `ui/step1_dialog.py`, elle-même seule voie branchée sur `main.py` :

- `src/purh_editorial/pipeline/step1.py` (781 l.)
- `src/purh_editorial/services/orthotypo_service.py` (1087 l.)
- `src/purh_editorial/services/structure_service.py` (1846 l.)
- `src/purh_editorial/services/ai_editorial_service.py` (322 l.)
- `src/purh_editorial/services/pivot_canonicalizer.py`, `pivot_validator.py`, `pivot_export_gate.py`
- `src/purh_editorial/services/word_review_service.py`, `word_review_annotation_service.py`, `word_workspace_service.py`
- `src/purh_editorial/latex/*` (export LaTeX), `src/purh_editorial/io/tei_xml_exporter.py`, `serialization/pivot_json.py`
- `src/purh_editorial/ui/step1_dialog.py` (1739 l.)

Soit environ **9000 lignes** représentant l'architecture « pivot JSON + scoring + seuils + IA multi-niveaux + exports multi-formats », l'architecture désignée comme échec de conception. `docs/REBORN_ARCHITECTURE.md` §10 prévoyait de garder ce code *temporairement*, le temps que la relève soit validée — mais ce garde-fou (« ne pas supprimer avant validation ») n'a ni date ni critère de sortie inscrit nulle part, d'où le risque qu'il reste indéfiniment.

Sur ce point, le commit `d04f8e9` intitulé *« Supprimer l'ancienne machinerie de correction »* **n'a rien supprimé** — il a ajouté un avis. L'étape de suppression réelle reste entièrement à faire.

### 2.3 Plan de suppression proposé (à valider avant exécution)

1. **Étape 0 (préalable, prioritaire)** : brancher `main.py` sur le moteur `reborn` avec une UI Tkinter minimale (sélection fichier → bouton « corriger » → chemin de sortie), pour que le produit livrable existe réellement avant de retirer quoi que ce soit.
2. **Étape 1 (sans risque, immédiat)** : supprimer `src/purh_editorial/rules/model.py`, `rules/registry.py` et leurs 3 fichiers de tests dédiés (`tests/unit/rules/test_rule_*.py`) — code prouvé orphelin, aucune dépendance ailleurs. Retirer `word_side_by_side_diagnostic.json` du suivi git et l'ignorer. Nettoyer `.idea/` du suivi git.
3. **Étape 2 (après étape 0)** : une fois l'UI `reborn` fonctionnelle et couvrant au moins les familles orthotypographie + notes + bibliographie (cf. §1), figer la voie legacy en lecture seule (déplacer dans un dossier `legacy/` ou une branche dédiée plutôt que la laisser mélangée dans `src/purh_editorial/`), pour qu'elle reste consultable (extraction de regex, listes lexicales, cas de test — comme le prévoit `REBORN_ARCHITECTURE.md` §3) sans polluer la recherche de code active.
4. **Étape 3 (après couverture complète des 61 règles par `reborn`, ou décision explicite d'abandonner certaines)** : suppression effective de `pipeline/step1.py`, `services/orthotypo_service.py`, `services/structure_service.py`, `services/structure_ai_arbitrator.py`, `services/ai_editorial_service.py`, `ui/step1_dialog.py`, l'export LaTeX/TEI/JSON pivot s'ils ne font pas partie du périmètre retenu, et les ~40 fichiers de tests qui ne couvrent qu'eux (`tests/unit/test_heuristic_profiles.py`, `test_orthotypo_service_guardrails.py`, `test_structure_service_*.py`, `test_pivot_*.py`, `test_latex_exporter_*.py`, `test_step1_options_modes.py`, etc. — à recenser précisément à ce moment-là).

Le chiffrage exact de l'étape 3 dépend d'une décision produit : conserver les exports TEI/LaTeX/JSON pivot comme fonctionnalités futures, ou viser uniquement un DOCX surligné en sortie ? Dans ce second cas, l'essentiel de `src/purh_editorial/latex/`, `io/tei_xml_exporter.py`, `serialization/pivot_json.py` et leurs tests associés (une quinzaine de fichiers) sont également candidats à suppression à terme.

---

## 3. État de la documentation et plan de mise à jour

### 3.1 Constat

Le dépôt compte **~30 fichiers Markdown** (racine + `docs/`). Sur cet ensemble :

- **Un seul document** (`docs/REBORN_ARCHITECTURE.md`) décrit la stratégie actuelle.
- **`docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md`** (523 lignes, 66 sous-sections) est l'actif solide identifié comme tel : catalogue structuré des 61 règles avec identifiants stables. Rien n'a été relevé qui appelle une remise en cause de fond — cohérent avec la consigne de ne pas y toucher sans forte raison.
- **Tout le reste décrit l'ancienne architecture comme si elle était toujours la cible actuelle**, en particulier :
  - `README.md` — décrit la chaîne « pivot Python-JSON → 4 sorties (JSON/DOCX/TEI/LaTeX) », les « régimes d'action » (déterministe / heuristique scorée / IA locale / IA exploratoire), les « zones protégées », c'est-à-dire très exactement le modèle de scoring/seuils abandonné. C'est le point d'entrée documentaire du dépôt et il contredit frontalement la stratégie actuelle.
  - `ARCHITECTURE.md`, `SPECS.md`, `DATA_MODEL.md`, `docs/EDITORIAL_DECISION_MODEL.md`, `docs/EDITORIAL_PIPELINE.md`, `docs/PIVOT_JSON_CONTRACT.md`, `docs/EXPORTERS_CONTRACT.md`, `docs/CONSERVATION_MATRIX.md`, `docs/ui.md`, `AI_STYLE_POLICY_V1.md`/`docs/AI_STYLE_POLICY.md` (doublon) — même problème.
  - `docs/RULES_CATALOG.md` est un **doublon partiel et périmé** de `docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md` (son en-tête indique lui-même « pour les 17 règles réellement implémentées dans `OrthotypoService` »), source de confusion sur la source de vérité.
  - `TYPO_RULES_PURH.md` existe **en double, à la racine et dans `docs/`**, chacun renvoyant l'un vers l'autre comme fusionné.
  - `docs/PASSE_1_INVENTAIRE_ARCHITECTURAL_REGLES.md`, `docs/PASSE_3_ARCHITECTURE_CIBLE_REGLES.md`, `docs/PHASE1_FIABILITE_PIPELINE.md`, `docs/PHASE4_EXTRACTION_REGLES_PURH.md`, `docs/PHASE5_CORPUS_CARACTERISATION.md`, `docs/PHASE6_TRACABILITE_OCCURRENCE.md`, `docs/DOCS_AUDIT_PIVOT.md`, `docs/WORD_REVIEW_PROTOTYPE.md`, `rapport.md`, `avis_refactoring_regles.md`, `NOTE_DE_CADRAGE.md`, `MANIFESTE.md`, `CHECKLIST_SOURCES_AND_FIXTURES.md` — sont des **rapports d'étape historiques** de refontes successives (légitimes comme journal, mais aucun n'indique clairement au lecteur qu'il est caduc par rapport à `reborn`).
  - `TEST_STRATEGY.md`, `FIXTURES.md`, `METOPES_MAPPING.md` décrivent la stratégie de test/fixtures de l'ancienne architecture (pivot, exports multiples) sans mention de `reborn`.
- **Aucun document n'explique, du point de vue d'une éditrice utilisatrice**, comment utiliser l'outil aujourd'hui (le `README.md` §8 « lancement rapide » pointe vers `python main.py`, qui lance l'ancienne UI complexe à seuils/IA — pas l'outil simple visé).

### 3.2 Plan de mise à jour proposé

1. **Créer un `README.md` unique, court, orienté utilisatrice finale** : que fait l'outil (ouvrir un DOCX, corriger, surligner, ressortir un DOCX), comment le lancer, quelles limites actuelles (règles encore non couvertes). Le README technique actuel devient un document d'archive (`docs/legacy/README_PIVOT_ARCHITECTURE.md` par ex.) plutôt que la porte d'entrée.
2. **Ajouter en tête de chaque document décrivant l'architecture pivot/scoring un bandeau explicite** (« Ce document décrit l'architecture legacy, remplacée par `docs/REBORN_ARCHITECTURE.md`. Conservé pour référence historique. ») plutôt que de les supprimer d'un coup — cela évite qu'un lecteur (humain ou IA) les prenne pour la cible actuelle.
3. **Résoudre les doublons** : fusionner définitivement les deux `TYPO_RULES_PURH.md`, trancher entre `docs/RULES_CATALOG.md` et `docs/CATALOGUE_REGLES_TYPOGRAPHIQUES.md` (le second est manifestement la source de vérité actuelle — le premier devrait soit être supprimé, soit explicitement redirigé).
4. **Faire vivre `docs/REBORN_ARCHITECTURE.md` comme document central** : y ajouter, au fur et à mesure, l'état réel de couverture des 61 règles (combien sont effectivement branchées dans `word_document.py` vs. seulement déclarées) — c'est l'écart le plus significatif identifié en §1, et il doit être visible dans la doc, pas seulement dans le code.
5. **Documenter l'UI Tkinter à venir** dans un nouveau document court (`docs/ui.md` actuel étant lui-même lié à l'ancienne UI, il faudra soit le remplacer soit le réécrire) une fois l'étape 0 du plan de suppression réalisée.
6. **Nettoyer les rapports d'étape historiques** (`PASSE_*`, `PHASE*`, `rapport.md`, `avis_refactoring_regles.md`, `DOCS_AUDIT_PIVOT.md`) en les déplaçant dans un dossier `docs/journal/` ou `docs/archive/` : ce sont des comptes-rendus utiles à l'archéologie du projet mais nuisibles s'ils restent au même niveau que la documentation active, exactement comme le code legacy mélangé au code actif.

### 3.3 Point annexe — environnement de développement

`pytest` n'est pas installé dans `.venv` alors que plusieurs fichiers de tests l'utilisent (`tests/unit/test_reborn_rule_logic.py` notamment — un des deux seuls fichiers de test du nouveau moteur). L'exécution via `unittest discover` fonctionne (509 tests, 1 échec sur un test de la voie legacy `R-GQ-004`, 6 erreurs d'import liées à l'absence de `pytest`, 8 skips) mais `requirements.txt` ne liste pas `pytest`. À corriger indépendamment de l'audit ci-dessus pour que toute la suite de tests (y compris celle du nouveau moteur) soit exécutable normalement.

---

## 4. Priorisation suggérée pour la suite

1. Brancher une UI Tkinter minimale sur `corrector.correct_docx` (fait exister réellement le produit visé).
2. Combler ou retirer honnêtement les règles bibliographie/structure déclarées mais non exécutées dans `reborn`.
3. Réécrire `README.md` pour refléter l'outil réel.
4. Nettoyage git immédiat (`rules/model.py` + `rules/registry.py` orphelins, `word_side_by_side_diagnostic.json`, `.idea/`).
5. Bandeaux de péremption sur la documentation legacy, puis archivage.
6. Suppression effective de la voie legacy une fois `reborn` validé sur corpus réel.
