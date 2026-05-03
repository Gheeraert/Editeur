# Catalogue de règles SHS — version opérationnelle

## 1. Statut

Ce catalogue organise les règles selon un mécanisme de décision éditoriale compatible avec le pivot Python‑JSON.

Une règle ne doit pas seulement produire un effet visible. Elle doit produire, selon son régime :

- un diagnostic ;
- une suggestion ;
- une transformation ;
- une décision structurelle ;
- une canonicalisation du pivot ;
- un veto.

---

## 2. Légende automatisation

- `A1` auto-correction sûre ;
- `A2` suggestion localisée ;
- `A3` diagnostic seulement ;
- `A4` hors périmètre initial ;
- `P1` invariant du pivot obligatoire ;
- `P2` canonicalisation requise avant export.

---

## 3. Niveaux de décision transversaux

### 3.1 Vetos structurels

Un veto bloque la transformation, même si le score est élevé.

Vetos types :

- `passage_reference`
- `caption_or_reference`
- `list_like`
- `bibliography_like`
- `technical_markup`
- `poetry_line_candidate`
- `table_zone`
- `heading_explicit` selon contexte

### 3.2 Déterministe sûr

Règles locales et testables, appliquées automatiquement quand le contexte est stable.

Exemples :

- `R-AB-001` (`etc...` -> `etc.`)
- `R-SO-002` ordinaux simples (`1re`, `5e`)
- `R-SP-002`, `R-SP-003` espaces locaux
- siècles stylés quand contexte robuste

### 3.3 Heuristique scorée

Utilisée quand plusieurs indices doivent être combinés.

Sortie attendue :

- score ;
- décision (`transform` / `diagnostic` / `ignore`) ;
- evidence ;
- veto_reasons ;
- ai_candidate.

Exemples :

- `R-STRUCT-HEADING-001` candidats heading ;
- `R-CI-POETRY-001` candidats citation poétique.

### 3.4 Canonicalisation du pivot

Une règle structurelle appliquée doit produire un état pivot stable.

Exemple :

```text
R-CI-POETRY-001 transform
  -> block_type=quote_block
  -> quote_kind=poetry
  -> lineation=verse
  -> protected_zone=poetry
```

### 3.5 IA locale

Usage cible :

- uniquement sur segments `ai_candidate` ;
- sortie structurée ;
- pas d'override des vetos ;
- pas de transformation sans passage par le pivot.

### 3.6 IA exploratoire future

Usage cible :

- désactivée par défaut ;
- suggestions uniquement ;
- niveau de liberté paramétrique.

---

## 4. Extraits de règles prioritaires

### Espaces et ponctuation

- `R-SP-001` espaces avant `: ; ? !` avec garde-fous (URL/heures/ratios/paths/refs)
- `R-SP-002` suppression espace avant `, .`
- `R-SP-003` réduction doubles espaces
- `R-SP-004` séparateur des milliers

### Guillemets

- `R-GQ-001` conversion prudente des guillemets droits (`A2` par défaut)
- `R-GQ-004` ponctuation autour des guillemets (`A3`)

### Notes

- `R-AN-002` placement appel de note vs ponctuation (`A3`)
- `R-AN-003` espace parasite avant appel de note (`A3`)

### Structuration

- `R-TI-001` hiérarchie de titres
- `R-STRUCT-HEADING-001` décision scorée heading + vetos
- `R-CI-POETRY-001` décision scorée candidats poésie + vetos
- `R-PIVOT-POETRY-001` invariant citation en vers (`P1`)
- `R-PIVOT-EXPORT-001` interdiction d'heuristique structurelle dans les exporteurs (`P1`)

---

## 5. Règles pivot prioritaires

### `R-PIVOT-ROUNDTRIP-001`

Un document pivot doit supporter le round‑trip :

```text
Python -> JSON -> Python -> JSON
```

### `R-PIVOT-POETRY-001`

Si `quote_kind=poetry`, alors `lineation=verse` et des lignes exploitables doivent exister.

### `R-PIVOT-HEADING-001`

Si `block_type=heading`, alors `heading_level` doit exister et être valide.

### `R-PIVOT-TABLE-001`

Si `block_type=table`, alors la structure tabulaire ou l'OOXML source doit être conservé. Pas d'aplatissement silencieux.

### `R-PIVOT-PROTECTED-ZONE-001`

Une zone protégée n'est pas une structure canonique complète. Elle doit bloquer ou déclencher une canonicalisation, mais non être directement interprétée par l'exporteur.

---

## 6. Points explicitement futurs

- IA locale active sur zones grises, sans généralisation automatique ;
- IA exploratoire, désactivée par défaut ;
- normalisation bibliographique exhaustive multi-modèles ;
- remplacement progressif des attributs non typés par des structures dédiées ;
- validation complète du JSON pivot par schéma.
