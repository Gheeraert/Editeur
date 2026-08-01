# Catalogue des points scrutés par la couche IA

## Statut du document

Ce catalogue décrit les points que la couche IA (chantier `ia`, voir
[`proposition_architecture_ia.md`](../proposition_architecture_ia.md) à la racine) devra
scruter dans le manuscrit, au-delà de ce que couvrent déjà les règles déterministes et
heuristiques du moteur `reborn` (voir
[`CATALOGUE_REGLES_TYPOGRAPHIQUES.md`](CATALOGUE_REGLES_TYPOGRAPHIQUES.md)).

Ce document est le contrat de référence entre le prompt envoyé au modèle, le parsing de
sa réponse et le rapport d'intervention affiché à l'éditrice — tenu à jour à chaque
évolution du chantier `ia` (voir `src/purh_editorial/corrector/ai/` pour l'implémentation
et `docs/journal/VALIDATION_IA_CORPUS_REEL_2026-08-01.md` pour la validation sur corpus
réel).

## Principes qui s'appliquent à toutes les règles IA

- **Jamais de `text_transform` silencieux.** Toute règle de ce catalogue produit un
  `diagnostic` : surlignage + commentaire Word (`Comments.Add`), jamais une réécriture
  directe du texte. Voir la discussion validée avec l'utilisateur : distinction requise
  d'avec le jaune (correction automatique déterministe) et le turquoise (diagnostic
  déterministe/heuristique existant).
- **Couleur dédiée :** `wdDarkYellow` (code `14`), réservée exclusivement aux
  interventions de la couche IA — jamais utilisée par le moteur déterministe. À
  documenter dans `docs/NOTICE_COULEURS_WORD.md` lors de l'implémentation (étape 5 du
  plan).
- **Une suggestion sans validation de schéma est ignorée**, pas remontée comme erreur —
  voir le principe de tolérance aux pannes de la proposition d'architecture (§1.3).
- **Identifiants stables**, préfixés `ia.`, sur le modèle des identifiants `purh.*` /
  `structure.*` déjà en usage dans `runner.py`.
- **Score de sévérité (1 à 5) obligatoire**, attribué par le modèle lui-même à chaque
  suggestion (1 = préférence de style mineure et discutable, 5 = gêne sérieuse la
  lecture). Sert de curseur de sensibilité réglable par l'éditrice dans l'interface
  (`ai_min_severity`, `gui.py`) : une suggestion sous le seuil choisi n'est même pas
  localisée dans le texte. Choix délibéré plutôt que de compter sur l'auto-limitation du
  modèle par consigne de prompt seule, jugée peu efficace en pratique (voir l'addendum de
  `docs/journal/VALIDATION_IA_CORPUS_REEL_2026-08-01.md`).
- **Aucune analyse des paragraphes stylés « Citation » ou « Citation intense ».** Une
  citation reproduit un texte source verbatim ; ni son style ni son contenu n'appartient à
  l'éditrice PURH, et l'IA ne doit ni le juger ni le commenter (`_is_quote_style_paragraph`
  dans `word_document.py`).

## Table de synthèse

| Identifiant | Catégorie | Portée d'analyse | Fiabilité attendue |
|---|---|---|---|
| `ia.style.lourdeur` | Style | Paragraphe | Moyenne — dépend fortement du modèle |
| `ia.style.repetition` | Style | Paragraphe (avec fenêtre de contexte) | Moyenne |
| `ia.syntaxe.construction` | Syntaxe | Paragraphe | Moyenne |
| `ia.syntaxe.accord` | Syntaxe | Paragraphe | Faible — à valider prudemment sur corpus réel |
| `ia.morphologie.forme_douteuse` | Morphologie | Paragraphe | Faible |
| `ia.biblio.reference_incomplete` | Bibliographie | Entrée bibliographique | Élevée |
| `ia.biblio.structure_atypique` | Bibliographie | Entrée bibliographique | Moyenne |
| `ia.terminologie.incoherence` | Cohérence terminologique | Document entier | Moyenne — nécessite une passe d'agrégation |
| `ia.clarte.ambiguite` | Clarté | Paragraphe | Faible |

## Fiches détaillées

### `ia.style.lourdeur` — Lourdeur de style
- **Catégorie :** Style. **Portée :** un paragraphe à la fois.
- **Détecte :** pléonasmes, tournures passives excessives, lourdeurs de construction
  (« il s'avère avéré que », accumulation de subordonnées).
- **Sortie attendue :** commentaire Word citant la formulation proposée et
  l'explication brève du problème (cf. exemple JSON de la proposition, §4.1).
- **Risque de faux positifs :** modéré — les registres soutenus de l'édition
  universitaire peuvent être signalés à tort ; le prompt doit préciser le registre
  académique attendu.

### `ia.style.repetition` — Répétition rapprochée
- **Catégorie :** Style. **Portée :** paragraphe courant + un paragraphe de contexte
  avant/après (pour détecter une répétition à cheval sur deux paragraphes).
- **Détecte :** répétition d'un même mot ou d'une même tournure à faible distance,
  hors cas volontaires (anaphore rhétorique, terminologie technique répétée à dessein).
- **Sortie attendue :** commentaire signalant les occurrences et une piste de
  reformulation pour l'une d'elles.
- **Risque de faux positifs :** élevé sur le vocabulaire technique/terminologique
  répété à dessein — doit être croisé avec `ia.terminologie.incoherence` pour éviter
  de signaler une répétition qui est en fait une cohérence terminologique voulue.

### `ia.syntaxe.construction` — Rupture de construction
- **Catégorie :** Syntaxe. **Portée :** paragraphe.
- **Détecte :** anacoluthes, ruptures de construction grammaticale, incohérences de
  temps ou de mode dans une même phrase.
- **Sortie attendue :** commentaire citant la rupture identifiée, sans réécriture
  complète imposée (proposition de piste seulement).

### `ia.syntaxe.accord` — Accord douteux en contexte
- **Catégorie :** Syntaxe. **Portée :** paragraphe.
- **Détecte :** accords complexes que les correcteurs grammaticaux classiques
  (Word, LanguageTool) manquent car ils dépendent du sens (accord de participe passé
  avec un COD éloigné, accord par syllepse, etc.).
- **Fiabilité attendue :** faible à ce stade — à traiter en priorité basse et à valider
  sur corpus avant activation par défaut, car les modèles 7B locaux se trompent
  fréquemment sur ce type de jugement grammatical fin.

### `ia.morphologie.forme_douteuse` — Forme morphologique douteuse
- **Catégorie :** Morphologie. **Portée :** paragraphe.
- **Détecte :** formes fléchies douteuses ou archaïsantes non couvertes par le
  correcteur orthographique standard (par exemple des formes verbales rares
  employées de façon incorrecte).
- **Fiabilité attendue :** faible — catégorie à surveiller de près en phase de
  validation (étape 9 du plan), candidate à la désactivation par défaut si le taux
  de faux positifs est trop élevé sur corpus réel.

### `ia.biblio.reference_incomplete` — Référence bibliographique incomplète
- **Catégorie :** Bibliographie. **Portée :** une entrée bibliographique (paragraphe
  de la section bibliographie repérée par `BIBLIOGRAPHY_SECTION_HEADING_RE`, voir
  `runner.py`).
- **Détecte :** éléments manquants dans une référence (éditeur, ville, année, pages)
  à partir de l'extraction sémantique décrite en §2.1 de la proposition
  (`Référence brute → {auteur, prénom, titre, éditeur, année, ville}`).
- **Sortie attendue :** commentaire listant précisément l'élément manquant identifié,
  jamais une reconstruction automatique appliquée au texte.
- **Fiabilité attendue :** élevée — tâche d'extraction structurée, où les LLM (même
  7B locaux) sont généralement fiables.

### `ia.biblio.structure_atypique` — Bibliographie de forme non standard
- **Catégorie :** Bibliographie. **Portée :** une entrée bibliographique.
- **Détecte :** une entrée dont la forme s'écarte fortement du format canonique PURH
  (ordre auteur/titre inversé, ponctuation de séparation atypique) sans qu'un élément
  soit nécessairement manquant.
- **Sortie attendue :** commentaire proposant la reformulation canonique complète.

### `ia.terminologie.incoherence` — Incohérence terminologique
- **Catégorie :** Cohérence terminologique. **Portée :** **document entier**, à la
  différence de toutes les autres règles de ce catalogue.
- **Détecte :** variantes d'orthographe d'un même nom propre ou concept à travers le
  manuscrit (ex. « Foucauld » / « Foucault », une graphie de personnage historique
  incohérente d'un chapitre à l'autre).
- **Conséquence architecturale :** implique une **passe en deux temps** — une
  première passe de collecte des noms propres/termes candidats sur tout le document,
  puis une seconde passe de signalement des occurrences minoritaires. C'est la seule
  règle IA qui ne peut pas être traitée paragraphe par paragraphe isolément ; à
  concevoir en étape 6 du plan (stratégie de ciblage) comme un cas à part, pas comme
  une extension triviale des autres règles.
- **Sortie attendue :** commentaire sur chaque occurrence minoritaire, citant la forme
  majoritaire retenue ailleurs dans le document.

### `ia.clarte.ambiguite` — Formulation ambiguë
- **Catégorie :** Clarté. **Portée :** paragraphe.
- **Détecte :** une formulation dont le référent ou le sens est ambigu (pronom
  équivoque, rattachement syntaxique incertain d'une proposition).
- **Fiabilité attendue :** faible — catégorie la plus subjective du catalogue, à
  n'activer qu'après retour d'expérience des éditrices en étape 9.

## Catégories volontairement exclues à ce stade

- **Orthographe pure** : déjà couverte par le correcteur natif de Word ; l'IA ne doit
  pas la dupliquer.
- **Vérification factuelle du contenu scientifique** (exactitude d'une citation, d'une
  date historique) : hors périmètre — l'IA n'a pas accès à une source faisant autorité
  et le risque de fausse assurance (hallucination présentée avec confiance) est trop
  élevé pour un usage éditorial sans garde-fou supplémentaire.

## Maintenance du catalogue

Toute règle IA ajoutée, retirée ou dont le comportement change doit mettre à jour ce
document avant la mise à jour du code (`src/purh_editorial/corrector/ai/`), à l'inverse
du catalogue déterministe où le registre fait foi — ici, en l'absence de registre
machine pour la couche IA, ce fichier Markdown est la seule source de vérité tant que
l'étape 2 du plan de travail n'a pas produit d'équivalent structuré.
