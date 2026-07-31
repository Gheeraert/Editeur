# Audit ciblé — règles orthotypographiques, classification, niveaux de prudence

Périmètre : `src/purh_editorial/**`. Lecture seule, aucune modification apportée au code lors de cet audit.

## 1. Règles réellement prises en compte lors du traitement d'un DOCX

### 1.1 Orthotypographie (`services/orthotypo_service.py`) — 19 règles textuelles codées

| rule_id | Ce qu'elle détecte/corrige | Appliquée automatiquement ? |
|---|---|---|
| `purh.apostrophe` | Apostrophe droite → typographique (`'`→`’`) | non |
| `purh.points_suspension` | `...` → `…` | non |
| `purh.guillemets.droits` | Guillemets droits/anglais → `«…»` / `“…”` (avec exclusion des contextes techniques) | non |
| `R-ORTHO-LIGATURE-OE-001` | Ligatures œ sur table fermée (boeuf→bœuf, coeur→cœur…) | non |
| `purh.guillemets.espace_apres_ouvrant` | Espace fine insécable après `«` | non |
| `purh.guillemets.espace_avant_fermant` | Espace fine insécable avant `»` | non |
| `purh.espaces.avant_ponct_forte` | Espace fine insécable avant `: ; ? !` | non |
| `purh.espaces.avant_ponct_faible` | Suppression espace avant `,`/`.` | non |
| `purh.espaces.double` | Double espace → simple | non |
| `purh.civilite` | Espace insécable après civilité (M., Mme, Dr…) | non |
| `purh.siecles` | XIIème/xiiième → XIIe (whitelist chiffres romains) | **oui** |
| `purh.ordinaux` | 1ère/1ere → 1re ; nème/neme → ne | **oui** |
| `purh.tiret.double` | `--` → `–` | non |
| `purh.abreviations.etc` | etc…/etc.. → etc. | **oui** |
| `purh.pagination.espace` | Espace fine insécable après p./pp./vol./t./n°/fig./chap. + chiffre | **oui** |
| `purh.numero` | n°/N°/nº + chiffre → forme canonique (o en exposant) | **oui** |
| `purh.abreviations.redoublement` | pp./vv./ll./§§ → p./v./l./§ | **oui** |
| `purh.nombres.milliers` | Espace fine insécable dans 1 000, 1 500 000 | non |
| `purh.tiret.incise` | Tiret d'incise → cadratin | non (désactivée nativement) |

**Point central** : sur ces 19 règles codées, **seules 6 corrigent réellement le texte** (`purh.siecles`, `purh.ordinaux`, `purh.abreviations.etc`, `purh.pagination.espace`, `purh.numero`, `purh.abreviations.redoublement`) — filtre explicite `orthotypo_service.py:449-458` :

```python
# Only rules explicitly supported by a PURH source may alter the document.
# All other rules remain detectable review material until their source is
# documented; this is deliberately stricter than general French practice.
purh_validated_rule_ids = {"purh.siecles", "purh.ordinaux", "purh.abreviations.etc",
                            "purh.pagination.espace", "purh.numero", "purh.abreviations.redoublement"}
for rule in rules:
    rule.auto = rule.auto and rule.rule_id in purh_validated_rule_ids
```

Toutes les autres restent détectées mais deviennent des diagnostics à revue humaine (`analyze_unvalidated_rules`, catégorie `orthotypo_unvalidated_rule`).

Plus deux stylages Word directs (petites capitales/exposants) : `R-SO-001` (siècles), `R-NO-001` (n°).

Diagnostics purs (jamais de correction) : `R-GQ-004` (ponctuation autour de guillemets), `R-TI-001` (tiret d'incise, convention non tranchée).

### 1.2 Notes de bas de page (`footnote_normalizer.py`) — appliquées automatiquement

Espace de tête parasite, majuscule initiale (sauf URL/particule/abréviation latine), `Ibid./op. cit./art. cit.` en minuscule hors début, espaces fines dans « op. cit. »/« s. l. »/« s. d. », point final ajouté.

Diagnostics purs : `R-AN-002` à `R-AN-005` (placement d'appel de note, ponctuation ambiguë).

### 1.3 Bibliographie (`bibliography_normalizer.py`) — appliquées automatiquement

Espace fine après pagination/n°, point final d'entrée bibliographique.

### 1.4 Structure du document (`structure_service.py`)

Voir §2 et §3 ci-dessous.

### 1.5 IA éditoriale (`ai_editorial_service.py`)

`purh.ai.editorial` : jamais automatique, toujours `Suggestion` avec `caution_level="high"` → commentaire Word à décision humaine.

## 2. Classification déterministe / heuristique

Il n'existe **pas** d'enum `Deterministic`/`Heuristic` posé sur chaque règle orthotypographique individuelle. La dichotomie existe à deux autres niveaux :

- **Pipeline** (`pipeline/step1.py`) : `Step1Options.decision_mode` ∈ `{"deterministic", "heuristic", "heuristic_ai_local", "ai_exploratory"}`, défaut `"heuristic"`. Ce mode active/désactive l'IA structurelle et éditoriale.
- **Structure** (`structure_service.py`) : `StructurePreparationService.process(mode=...)` → `use_heuristics = mode != "deterministic"`. En `"deterministic"`, tous les blocs de scoring heuristique (gras, ALLCAPS, italique, indentation, score de titre, poésie) sont coupés ; seule reste la promotion de titre basée sur le **style Word source explicite**.

Au niveau orthotypo, l'équivalent fonctionnel de « déterministe vs heuristique » est le binaire `auto` (validé par source PURH documentée vs non validé) décrit en §1.

## 3. Niveaux prudent / équilibré / exploratoire

Ils existent, mais **uniquement pour la détection heuristique de structure**, pas pour l'orthotypo (qui reste binaire, §1).

`structure_service.py:110` :
```python
_ALLOWED_HEURISTIC_PROFILES = {"conservative", "balanced", "exploratory"}
```
avec alias français (`prudent`, `équilibré`, `exploratoire`). Seuils par défaut (`structure_service.py:159-161`) :

| Profil | seuil transform titre | seuil diagnostic titre | seuil transform poésie | seuil diagnostic poésie |
|---|---|---|---|---|
| conservative | 0.90 | 0.70 | 0.82 | 0.60 |
| balanced | 0.85 | 0.60 | 0.78 | 0.55 |
| exploratory | 0.75 | 0.50 | 0.72 | 0.48 |

**Critère de décision par candidat** (`HeuristicDecision`) : score composite pondéré → `"transform"` si style source ou signal fort + score ≥ seuil transform ; `"diagnostic"` si score ≥ seuil diagnostic ; sinon `"ignore"` (ou `"ignore"` immédiat si veto).

**Effet réel sur le document produit** :
- profil `exploratory` seul : `auto_apply_diagnostics=True` → les décisions `"diagnostic"` sont aussi appliquées automatiquement (pas seulement signalées) ;
- surlignage Word différencié : `structure_applied` (teal, transformation sûre appliquée), `exploratory_structure` (jaune foncé, appliqué en mode exploratoire — à vérifier), `suspect_unhandled` (rouge, détecté mais non appliqué → commentaire Word).

Configurable via `Step1Options.heuristic_profile` (défaut `"conservative"`) et sélecteur dans l'UI Tkinter, avec seuils individuellement surchageables.

**Système parallèle distinct**, à ne pas confondre avec le précédent : `structure_ai_arbitrator.py` régule l'agressivité de l'arbitrage IA structurel via `ALLOWED_AI_AGGRESSIVENESS = {"conservative", "balanced", "aggressive"}` (seuils de confiance 0.90/0.85/0.75), contrôlé séparément par `Step1Options.ai_aggressiveness`.

## Résumé opérationnel

1. 19 règles orthotypo codées, **6 seulement appliquées automatiquement** (liste ci-dessus) ; le reste = diagnostic/commentaire Word, par choix délibéré documenté dans le code (« deliberately stricter than general French practice »).
2. Déterministe/heuristique n'est pas un attribut par règle mais un mode global de pipeline et un paramètre de la couche structure, qui coupe entièrement les heuristiques scorées en mode déterministe.
3. Prudent/équilibré/exploratoire existe réellement, mais seulement pour la structure (titres, poésie), avec seuils numériques précis et effet visible (couleur de surlignage / auto-application des diagnostics en mode exploratoire). Un second triplet conservative/balanced/aggressive régule séparément l'IA structurelle.
