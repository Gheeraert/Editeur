# Catalogue des règles éditoriales

> Le nom de fichier `CATALOGUE_REGLES_TYPOGRAPHIQUES.md` est historique. Ce document couvre désormais toutes les familles déclarées dans le registre, et non les seules règles typographiques. Le fichier n'est pas renommé dans cette passe.

## Statut du document

Ce catalogue est la documentation humaine du registre. La source de vérité machine est [`src/purh_editorial/rules/registry.py`](../src/purh_editorial/rules/registry.py) : en cas de divergence, le registre prévaut. Les anciens catalogues et inventaires ne déterminent pas le statut courant d'une règle. Le présent document décrit également les règles `review_only`, `disabled`, `planned` et `dormant`.

## Synthèse calculée depuis le registre

| Famille | Nombre de règles |
|---|---:|
| `orthotypography` | 23 |
| `footnote` | 10 |
| `bibliography` | 7 |
| `structure` | 21 |
| **Total** | **61** |

| Nature | Nombre |
|---|---:|
| `deterministic` | 30 |
| `heuristic` | 31 |

| Type d'action | Nombre |
|---|---:|
| `text_transform` | 26 |
| `style_transform` | 2 |
| `structure_transform` | 21 |
| `diagnostic` | 8 |
| `pipeline_control` | 4 |

| Statut de déploiement | Nombre |
|---|---:|
| `active` | 40 |
| `review_only` | 18 |
| `disabled` | 3 |

| État d'implémentation | Nombre |
|---|---:|
| `legacy` | 55 |
| `planned` | 4 |
| `dormant` | 2 |

### Référentiel des sources normatives

Les identifiants cités dans les fiches renvoient aux objets `NormativeSource` définis dans le registre.

| Identifiant | Autorité | Titre | Localisateur | Statut |
|---|---|---|---|---|
| `purh.guide.p10` | PURH | Guide de préparation éditoriale | p. 10 | `purh_validated` |
| `purh.guide.p11` | PURH | Guide de préparation éditoriale | p. 11 | `purh_validated` |
| `purh.guide.p11-12` | PURH | Guide de préparation éditoriale | p. 11-12 | `purh_validated` |
| `purh.guide.p12` | PURH | Guide de préparation éditoriale | p. 12 | `purh_validated` |
| `typography.general` | Référence typographique générale | Convention typographique générale à confirmer pour les PURH | — | `documented_general` |
| `purh.corpus.observed` | PURH | Comportements observés dans le corpus de caractérisation | — | `corpus_observed` |

## Architecture des règles

Les `RuleDescriptor` sont des dataclasses gelées qui identifient une règle et portent ses métadonnées : identifiant, module propriétaire, famille, nature, action, déploiement, état d'implémentation, statut et sources normatives, politique de protection, famille de score éventuelle, alias historiques et tests.

- **Famille (`RuleFamily`)** : domaine de responsabilité. Valeurs : `orthotypography`, `footnote`, `bibliography`, `structure`.
- **Nature (`RuleNature`)** : mode d'évaluation. Valeurs : `deterministic`, `heuristic`. Une règle déterministe n'est pas nécessairement `active`.
- **Type d'action (`RuleActionType`)** : effet proposé. Valeurs : `text_transform`, `style_transform`, `structure_transform`, `diagnostic`, `pipeline_control`. Un `diagnostic` signale ; il n'est pas une transformation.
- **Statut de déploiement (`DeploymentStatus`)** : politique de décision. Valeurs : `active`, `review_only`, `disabled`. Il ne décrit ni la nature ni l'état d'implémentation.
- **État d'implémentation (`ImplementationState`)** : maturité technique. Valeurs définies : `legacy`, `planned`, `dormant`, `native` ; valeurs présentes dans ce registre : `legacy`, `planned`, `dormant`. Une règle recensée ou `planned` n'est pas nécessairement implémentée.
- **Statut normatif (`NormativeStatus`)** : qualité de l'ancrage déclaré. Valeurs : `purh_validated`, `documented_general`, `corpus_observed`, `internal_unsourced`, `not_applicable`.

Ces axes sont indépendants : une heuristique peut être `active`, une règle déterministe peut être `review_only`, et une règle `disabled` ne produit qu'une décision `ignore`.

## Principes d'exécution

Le registre central rassemble et valide les descripteurs. Le moteur reçoit un descripteur, une évaluation déterministe ou une proposition heuristique, les protections et le contexte de compatibilité, puis produit une décision `apply`, `review` ou `ignore` ; l'exécuteur matérialise ensuite l'action décidée. La description d'une règle, sa détection et son exécution sont donc séparées.

Pour une heuristique, les seuils de famille encadrent le passage entre revue et application (`0 <= review <= apply <= 1`). Le shadow compare l'observation legacy et la décision native, notamment les cibles, les actions et leurs ordres. Le legacy sert à la compatibilité et à la comparaison : il n'a pas de valeur normative.

## Catalogue exhaustif

Les fiches sont dans l'ordre du registre. « Aucune » signifie que le descripteur ne déclare pas cette information.

### Famille `orthotypography` — 23 règles

### `purh.apostrophe` — Apostrophe typographique
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Convertit l'apostrophe droite entre caractères alphabétiques en apostrophe typographique ; la règle reste soumise à revue.
- **Source normative :** `documented_general` — `typography.general`.
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`; `tests/unit/test_protection_asymmetry_characterization.py`.

### `purh.points_suspension` — Points de suspension
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Remplace trois points consécutifs par le caractère points de suspension ; la règle reste soumise à revue.
- **Source normative :** `documented_general` — `typography.general`.
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.guillemets.droits` — Guillemets droits
- **Nature :** `heuristic`; **Type d'action :** `diagnostic`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Signale les guillemets droits pour revue selon une analyse de structure de citation ; aucune transformation n'est décrite par le descripteur.
- **Source normative :** `purh_validated` — `purh.guide.p12` (p. 12).
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** `quote_structure`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.ligature.oe` — Ligatures OE
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise les ligatures OE sur des formes lexicales prévues par le comportement historique ; la description éditoriale détaillée est à compléter.
- **Source normative :** `documented_general` — `typography.general`.
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** `R-ORTHO-LIGATURE-OE-001` (ancien identifiant).
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.guillemets.espace_apres_ouvrant` — Espace après guillemet ouvrant
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise l'espace après un guillemet français ouvrant ; la règle reste soumise à revue.
- **Source normative :** `documented_general` — `typography.general`.
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.guillemets.espace_avant_fermant` — Espace avant guillemet fermant
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise l'espace avant un guillemet français fermant ; la règle reste soumise à revue.
- **Source normative :** `documented_general` — `typography.general`.
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.espaces.avant_ponct_forte` — Espace avant ponctuation forte
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise l'espace avant la ponctuation forte ; la règle reste soumise à revue.
- **Source normative :** `corpus_observed` — `purh.corpus.observed`.
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.espaces.avant_ponct_faible` — Espace avant ponctuation faible
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise l'espace avant la ponctuation faible ; la règle reste soumise à revue.
- **Source normative :** `documented_general` — `typography.general`.
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.espaces.double` — Espaces multiples
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Réduit les espaces multiples selon le comportement historique ; la règle reste soumise à revue.
- **Source normative :** `documented_general` — `typography.general`.
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.civilite` — Civilités
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise l'espacement associé aux civilités ; la règle reste soumise à revue.
- **Source normative :** `documented_general` — `typography.general`.
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.siecles` — Siècles
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise les notations de siècles en chiffres romains ; le stylage complémentaire est porté par `purh.siecles.style`.
- **Source normative :** `purh_validated` — `purh.guide.p10` (p. 10).
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`; `tests/unit/test_orthotypo_century_styling.py`.

### `purh.siecles.style` — Stylage des siècles
- **Nature :** `deterministic`; **Type d'action :** `style_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Applique le stylage associé aux siècles ; il complète `purh.siecles` sans être une transformation textuelle.
- **Source normative :** `purh_validated` — `purh.guide.p10` (p. 10).
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** `R-SO-001` (ancien identifiant).
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`; `tests/unit/test_orthotypo_century_styling.py`.

### `purh.ordinaux` — Ordinaux
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise les abréviations d'ordinaux couvertes par le comportement historique.
- **Source normative :** `purh_validated` — `purh.guide.p10` (p. 10).
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.tiret.double` — Double tiret
- **Nature :** `heuristic`; **Type d'action :** `diagnostic`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Signale les doubles tirets pour revue ; aucune transformation n'est produite par cette action diagnostique.
- **Source normative :** `documented_general` — `typography.general`.
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.abreviations.etc` — Abréviation « etc. »
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise les variantes de l'abréviation « etc. ».
- **Source normative :** `purh_validated` — `purh.guide.p10` (p. 10).
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.pagination.espace` — Espacement de pagination
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise l'espace après les abréviations de pagination et de référence couvertes par le comportement historique.
- **Source normative :** `purh_validated` — `purh.guide.p11-12` (p. 11-12).
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.numero` — Numéro
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise la forme textuelle des numéros ; le stylage complémentaire est porté par `purh.numero.style`.
- **Source normative :** `purh_validated` — `purh.guide.p12` (p. 12).
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`; `tests/unit/test_orthotypo_numero_styling.py`.

### `purh.numero.style` — Stylage du numéro
- **Nature :** `deterministic`; **Type d'action :** `style_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Applique le stylage associé à la forme de numéro produite par `purh.numero`.
- **Source normative :** `purh_validated` — `purh.guide.p12` (p. 12).
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** `R-NO-001` (ancien identifiant).
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`; `tests/unit/test_orthotypo_numero_styling.py`.

### `purh.abreviations.redoublement` — Abréviations redoublées
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Réduit les formes redoublées d'abréviations couvertes par la règle.
- **Source normative :** `purh_validated` — `purh.guide.p11` (p. 11).
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.nombres.milliers` — Séparateur de milliers
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise le séparateur de milliers ; la règle reste soumise à revue.
- **Source normative :** `documented_general` — `typography.general`.
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`.

### `purh.tiret.incise` — Tiret d'incise
- **Nature :** `heuristic`; **Type d'action :** `text_transform`; **Déploiement :** `disabled`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Règle de transformation du tiret d'incise enregistrée mais désactivée ; elle ne doit pas être présentée comme opérationnelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_orthotypo_deployment_characterization.py`; `tests/unit/test_orthotypo_incise_dash_abstention.py`.

### `purh.tiret.incise.diagnostic` — Diagnostic de tiret d'incise
- **Nature :** `deterministic`; **Type d'action :** `diagnostic`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Signale un tiret d'incise à vérifier ; aucune transformation n'est produite.
- **Source normative :** `corpus_observed` — `purh.corpus.observed`.
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** aucune; **Alias :** `R-TI-001` (ancien identifiant).
- **Tests associés :** `tests/unit/test_orthotypo_incise_dash_abstention.py`.

### `purh.guillemets.ponctuation_fermante` — Ponctuation de guillemet fermant
- **Nature :** `heuristic`; **Type d'action :** `diagnostic`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Signale la ponctuation autour d'un guillemet fermant pour revue ; aucune transformation n'est produite.
- **Source normative :** `purh_validated` — `purh.guide.p12` (p. 12).
- **Module propriétaire :** `purh_editorial.services.orthotypo_service`; **Protection :** `legacy.orthotypography`; **Score :** `quote_structure`; **Alias :** `R-GQ-004` (ancien identifiant).
- **Tests associés :** `tests/unit/test_quote_punctuation_diagnostics.py`.

### Famille `footnote` — 10 règles

### `purh.note.espace_initiale` — Espace initial d'une note
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise l'espace initial d'une note.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.footnote_normalizer`; **Protection :** `legacy.footnote`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_footnote_characterization_matrix.py`; `tests/unit/test_protection_asymmetry_characterization.py`.

### `purh.note.majuscule_initiale` — Majuscule initiale d'une note
- **Nature :** `heuristic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue puis normalise la majuscule initiale d'une note.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.footnote_normalizer`; **Protection :** `legacy.footnote`; **Score :** `footnote_form`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_footnote_characterization_matrix.py`.

### `purh.note.abreviation_latine` — Abréviation latine de note
- **Nature :** `heuristic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue puis normalise une abréviation latine de note.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.footnote_normalizer`; **Protection :** `legacy.footnote`; **Score :** `footnote_form`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_footnote_characterization_matrix.py`.

### `purh.note.espace_op_cit` — Espacement « op. cit. »
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise l'espacement de « op. cit. » dans une note.
- **Source normative :** `purh_validated` — `purh.guide.p11-12` (p. 11-12).
- **Module propriétaire :** `purh_editorial.services.footnote_normalizer`; **Protection :** `legacy.footnote`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_footnote_characterization_matrix.py`.

### `purh.note.espace_sans_lieu_date` — Espacement « sans lieu/date »
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise l'espacement de l'abréviation sans lieu ou date dans une note.
- **Source normative :** `purh_validated` — `purh.guide.p11-12` (p. 11-12).
- **Module propriétaire :** `purh_editorial.services.footnote_normalizer`; **Protection :** `legacy.footnote`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_footnote_characterization_matrix.py`.

### `purh.note.ponctuation_finale` — Ponctuation finale de note
- **Nature :** `heuristic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue puis normalise la ponctuation finale d'une note.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.footnote_normalizer`; **Protection :** `legacy.footnote`; **Score :** `footnote_form`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_footnote_characterization_matrix.py`.

### `purh.note.appel.placement` — Placement d'appel de note
- **Nature :** `deterministic`; **Type d'action :** `diagnostic`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Signale un placement suspect d'appel de note pour revue ; aucune transformation n'est produite.
- **Source normative :** `purh_validated` — `purh.guide.p11` (p. 11).
- **Module propriétaire :** `purh_editorial.services.footnote_normalizer`; **Protection :** `legacy.footnote`; **Score :** aucune; **Alias :** `R-AN-002` (ancien identifiant).
- **Tests associés :** `tests/unit/test_footnote_characterization_matrix.py`; `tests/unit/test_footnote_note_call_diagnostics.py`.

### `purh.note.appel.espace_avant` — Espace avant appel de note
- **Nature :** `deterministic`; **Type d'action :** `diagnostic`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Signale un espace parasite avant un appel de note pour revue ; aucune transformation n'est produite.
- **Source normative :** `purh_validated` — `purh.guide.p11` (p. 11).
- **Module propriétaire :** `purh_editorial.services.footnote_normalizer`; **Protection :** `legacy.footnote`; **Score :** aucune; **Alias :** `R-AN-003` (ancien identifiant).
- **Tests associés :** `tests/unit/test_footnote_characterization_matrix.py`; `tests/unit/test_footnote_note_call_diagnostics.py`.

### `purh.note.diagnostic.debut_minuscule` — Diagnostic de début de note en minuscule
- **Nature :** `heuristic`; **Type d'action :** `diagnostic`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Signale une note qui commence par une minuscule sans que ce soit une exception reconnue (URL, particule, abréviation latine) ; aucune transformation n'est produite.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.footnote_normalizer`; **Protection :** `legacy.footnote`; **Score :** `footnote_form`; **Alias :** `R-AN-004` (ancien identifiant).
- **Tests associés :** `tests/unit/test_footnote_characterization_matrix.py`.

### `purh.note.diagnostic.ponctuation_finale_ambigue` — Diagnostic de ponctuation finale ambiguë
- **Nature :** `heuristic`; **Type d'action :** `diagnostic`; **Déploiement :** `review_only`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Signale une fin de note dont la ponctuation est ambiguë (ex. item de liste) et où l'ajout automatique d'un point final serait risqué ; aucune transformation n'est produite.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.footnote_normalizer`; **Protection :** `legacy.footnote`; **Score :** `footnote_form`; **Alias :** `R-AN-005` (ancien identifiant).
- **Tests associés :** `tests/unit/test_footnote_characterization_matrix.py`.

### Famille `bibliography` — 7 règles

### `structure.bibliography.section.start` — Début de section bibliographique
- **Nature :** `heuristic`; **Type d'action :** `pipeline_control`; **Déploiement :** `active`; **Implémentation :** `planned`.
- **Fonction éditoriale :** Détecte un début de section bibliographique pour contrôler le pipeline. La règle est planifiée : elle n'est pas décrite comme fonctionnelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.bibliography_normalizer`; **Protection :** `legacy.bibliography`; **Score :** `bibliography_structure`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_bibliography_characterization_boundaries.py`.

### `structure.bibliography.section.end` — Fin de section bibliographique
- **Nature :** `heuristic`; **Type d'action :** `pipeline_control`; **Déploiement :** `active`; **Implémentation :** `planned`.
- **Fonction éditoriale :** Détecte une fin de section bibliographique pour contrôler le pipeline. La règle est planifiée : elle n'est pas décrite comme fonctionnelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.bibliography_normalizer`; **Protection :** `legacy.bibliography`; **Score :** `bibliography_structure`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_bibliography_characterization_boundaries.py`.

### `structure.bibliography.item.promote` — Promotion d'élément bibliographique
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `planned`.
- **Fonction éditoriale :** Prévoit de promouvoir un élément bibliographique dans la structure. La règle est planifiée : elle n'est pas décrite comme fonctionnelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.bibliography_normalizer`; **Protection :** `legacy.bibliography`; **Score :** `bibliography_structure`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_bibliography_characterization_boundaries.py`.

### `bibliography.entry.detect` — Détection d'entrée bibliographique
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `disabled`; **Implémentation :** `dormant`.
- **Fonction éditoriale :** Règle de détection d'entrée bibliographique enregistrée mais désactivée et dormante ; elle n'est pas opérationnelle.
- **Source normative :** `not_applicable` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.bibliography_normalizer`; **Protection :** `legacy.bibliography`; **Score :** `bibliography_structure`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_bibliography_characterization_boundaries.py`.

### `purh.biblio.pagination_nnbsp` — Espacement de pagination bibliographique
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise l'espace de pagination dans une bibliographie.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.bibliography_normalizer`; **Protection :** `legacy.bibliography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_bibliography_characterization_boundaries.py`; `tests/unit/test_protection_asymmetry_characterization.py`.

### `purh.biblio.numero_nnbsp` — Espacement de numéro bibliographique
- **Nature :** `deterministic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Normalise l'espace associé au numéro dans une bibliographie.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.bibliography_normalizer`; **Protection :** `legacy.bibliography`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_bibliography_characterization_boundaries.py`.

### `purh.biblio.ponctuation_finale` — Ponctuation finale bibliographique
- **Nature :** `heuristic`; **Type d'action :** `text_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue puis normalise la ponctuation finale d'une entrée bibliographique.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.bibliography_normalizer`; **Protection :** `legacy.bibliography`; **Score :** `bibliography_form`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_bibliography_characterization_boundaries.py`.

### Famille `structure` — 21 règles

### `structure.frontmatter.abstract` — Résumé de front matter
- **Nature :** `deterministic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Identifie et promeut la sémantique de résumé du front matter.
- **Source normative :** `corpus_observed` — `purh.corpus.observed`.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_frontmatter_semantics.py`; `tests/unit/test_structure_characterization_modes_and_protection.py`.

### `structure.frontmatter.keywords` — Mots-clés de front matter
- **Nature :** `deterministic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Identifie et promeut la sémantique de mots-clés du front matter.
- **Source normative :** `corpus_observed` — `purh.corpus.observed`.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_frontmatter_semantics.py`.

### `structure.frontmatter.acknowledgment` — Remerciements de front matter
- **Nature :** `deterministic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Identifie et promeut la sémantique de remerciements du front matter.
- **Source normative :** `corpus_observed` — `purh.corpus.observed`.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_frontmatter_semantics.py`.

### `structure.frontmatter.circuit_breaker` — Coupe-circuit de front matter
- **Nature :** `deterministic`; **Type d'action :** `pipeline_control`; **Déploiement :** `active`; **Implémentation :** `planned`.
- **Fonction éditoriale :** Prévoit de contrôler le pipeline après la détection du front matter. La règle est planifiée : elle n'est pas décrite comme fonctionnelle.
- **Source normative :** `corpus_observed` — `purh.corpus.observed`.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_frontmatter_semantics.py`.

### `structure.source_style.heading` — Titre par style source
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue le style source comme indice de titre et propose une transformation structurelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `heading`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_structure_characterization_modes_and_protection.py`.

### `structure.allcaps.heading` — Titre en capitales
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue les capitales comme indice de titre et propose une transformation structurelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `heading`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_structure_characterization_modes_and_protection.py`; `tests/unit/test_heading_heuristic_scoring.py`.

### `structure.bold.heading` — Titre en gras
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue le gras comme indice de titre et propose une transformation structurelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `heading`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_structure_characterization_modes_and_protection.py`; `tests/unit/test_heading_heuristic_scoring.py`.

### `structure.italic.author` — Auteur en italique
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue l'italique comme indice d'auteur et propose une transformation structurelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_structure_characterization_modes_and_protection.py`.

### `structure.italic.heading` — Titre en italique
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue l'italique comme indice de titre et propose une transformation structurelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `heading`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_structure_characterization_modes_and_protection.py`.

### `structure.epigraph.heuristic` — Épigraphe
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Recherche une épigraphe et propose une transformation structurelle. Description éditoriale détaillée à compléter.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** aucune; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_structure_characterization_modes_and_protection.py`.

### `structure.bibliography.section` — Section bibliographique
- **Nature :** `heuristic`; **Type d'action :** `pipeline_control`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Détecte une section bibliographique afin de contrôler le pipeline.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `bibliography_structure`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_structure_characterization_modes_and_protection.py`.

### `structure.bibliography.heuristic` — Élément bibliographique
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue un élément bibliographique et propose une transformation structurelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `bibliography_structure`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_structure_characterization_modes_and_protection.py`.

### `structure.indent.quote` — Citation indentée
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue un retrait comme indice de citation et propose une transformation structurelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `quote_structure`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_structure_characterization_modes_and_protection.py`.

### `structure.quote.guillemets` — Citation entre guillemets
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue les guillemets comme indice de citation et propose une transformation structurelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `quote_structure`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_structure_characterization_modes_and_protection.py`.

### `structure.heading.heuristic` — Heuristique de titre
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue des indices de titre et propose une transformation structurelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `heading`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_heading_heuristic_scoring.py`.

### `structure.heading.diagnostic` — Diagnostic structurel de titre
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue des indices de titre et propose une transformation structurelle. Description éditoriale détaillée à compléter.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `heading`; **Alias :** `R-STRUCT-HEADING-001` (ancien identifiant).
- **Tests associés :** `tests/unit/test_heading_heuristic_scoring.py`.

### `structure.lineated.blank_bounded.merge` — Fusion de séquence versifiée bornée par blancs
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue une séquence linéée bornée par des blancs et propose une fusion structurelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `poetry`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_structure_characterization_modes_and_protection.py`; `tests/unit/test_structure_service_poetry_detection.py`.

### `structure.lineated.short_sequence.merge` — Fusion de courte séquence linéée
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `disabled`; **Implémentation :** `dormant`.
- **Fonction éditoriale :** Règle de fusion de séquence linéée enregistrée mais désactivée et dormante ; elle n'est pas opérationnelle.
- **Source normative :** `not_applicable` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `poetry`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_structure_service_poetry_detection.py`.

### `structure.poetry.heuristique` — Heuristique de poésie
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue des indices de poésie et propose une transformation structurelle. Description éditoriale détaillée à compléter.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `poetry`; **Alias :** `R-CI-POETRY-001` (ancien identifiant).
- **Tests associés :** `tests/unit/test_poetry_heuristic_scoring.py`.

### `structure.lineated.group.annotate` — Annotation de groupe linéé
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue un groupe linéé et propose son annotation structurelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `poetry`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_poetry_heuristic_scoring.py`.

### `structure.lineated.stanza.merge` — Fusion de strophe
- **Nature :** `heuristic`; **Type d'action :** `structure_transform`; **Déploiement :** `active`; **Implémentation :** `legacy`.
- **Fonction éditoriale :** Évalue une strophe et propose une fusion structurelle.
- **Source normative :** `internal_unsourced` — aucune source déclarée.
- **Module propriétaire :** `purh_editorial.services.structure_service`; **Protection :** `legacy.structure`; **Score :** `poetry`; **Alias :** aucun.
- **Tests associés :** `tests/unit/test_poetry_heuristic_scoring.py`.

## Maintenance du catalogue

Toute création, suppression ou modification d'un `RuleDescriptor` doit entraîner la mise à jour de ce catalogue.

Commande de vérification reproductible (depuis la racine, avec `PYTHONPATH=src`) :

```powershell
$env:PYTHONPATH = 'src'; python -c "from collections import Counter; from purh_editorial.rules.registry import CANONICAL_RULE_REGISTRY as r; items=r.all(); print('total', len(items)); print('par_famille', dict(sorted(Counter(x.family.value for x in items).items()))); print('identifiants_uniques', len({x.rule_id for x in items}) == len(items))"
```
