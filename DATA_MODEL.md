# Modèle de données

## 1. Objectif et statut

Le cœur métier repose sur des dataclasses Python. Ces dataclasses forment la représentation vivante du pivot éditorial.

La sérialisation JSON est la représentation stable, versionnée et testable de ce même pivot.

```text
Python dataclasses  <=>  JSON canonique
```

Le JSON ne doit pas être traité comme un export décoratif. Il sert à vérifier, comparer, rejouer et stabiliser les décisions éditoriales.

Le contrat détaillé du pivot est défini dans `docs/PIVOT_JSON_CONTRACT.md`.

---

## 2. Objets documentaires actuels

### `Document`

- `document_id`
- `source_path`
- `source_format`
- `metadata`
- `blocks`
- `notes`
- `bibliography`
- `annotations`
- `history`
- `original_text`

Note : dans la documentation fonctionnelle, ce pivot peut être désigné comme `EditorialDocument`. Dans le code actuel, la classe concrète est `Document`.

### `Metadata`

- `title`
- `subtitle`
- `authors`
- `language`
- `collection`
- `publication_type`
- `source_label`

### `InlineStyle`

- `bold`
- `italic`
- `small_caps`
- `subscript`
- `superscript`

Ces propriétés sont des faits de style, non des décisions éditoriales par elles-mêmes.

### `InlineSpan`

- `text`
- `style: InlineStyle`
- `kind` (`text`, `note_call`, `tab`, `line_break`, etc.)
- `note_ref`
- `attributes`

### `Block`

- `block_id`
- `block_type`
- `text`
- `inlines`
- `note_refs`
- `children`
- `attributes`
- `source_span`

Types courants : `paragraph`, `heading`, `quote_block`, `bibliography_item`, `author`, `epigraph`, `list_item`, `table`, `code_block`, `unknown`.

Le `block_type` est une décision ou annotation structurelle. Il ne doit pas être confondu avec le style Word source.

### `Note`

- `note_id`
- `label`
- `text`
- `inlines`
- `target_ref`
- `attributes`

### `BibliographyItem`

- `item_id`
- `raw_text`
- `parsed_fields`
- `item_type`
- `source_span`

---

## 3. Limite actuelle du modèle

Le modèle actuel utilise largement :

```python
attributes: dict[str, Any]
```

Cette souplesse a été utile pendant la phase exploratoire, mais elle crée un risque : le même dictionnaire peut contenir des faits source, des indices de mise en page, des décisions sémantiques, des choix de rendu et des traces de traitement.

Il faut donc progressivement distinguer :

```text
source      : faits issus du document source
layout      : indices matériels ou visuels
semantic    : décision éditoriale canonique
rendering   : projection vers DOCX, Métopes, LaTeX, HTML
processing  : scores, règles, vetos, diagnostics, historique
```

Tant que cette séparation n'est pas implémentée en dataclasses dédiées, les clés placées dans `attributes` doivent être documentées et testées.

---

## 4. Faits documentaires et attributs source

Les faits issus du document source doivent être conservés sans être confondus avec des décisions.

Exemples :

- `style_name`
- `style_id`
- `all_runs_bold`
- `all_runs_italic`
- `ind_left`
- `ind_first_line`
- `num_id`
- `numbering_level`
- `is_list`
- `table_position`
- `source_heading_level`
- `has_line_breaks`

Ces faits sont des indices. Ils ne suffisent pas toujours à décider.

---

## 5. Sémantique canonique attendue

Le pivot doit pouvoir dire explicitement ce qu'est un bloc.

### 5.1 Paragraphe ordinaire

```json
{
  "block_type": "paragraph",
  "attributes": {
    "semantic_role": "paragraph"
  }
}
```

### 5.2 Titre

```json
{
  "block_type": "heading",
  "attributes": {
    "semantic_role": "heading",
    "heading_level": 2
  }
}
```

Invariant : un titre doit avoir un niveau exploitable.

### 5.3 Citation en prose

```json
{
  "block_type": "quote_block",
  "attributes": {
    "semantic_role": "quote",
    "quote_kind": "prose",
    "lineation": "prose"
  }
}
```

### 5.4 Citation en vers

Contrat minimal transitoire :

```json
{
  "block_type": "quote_block",
  "text": "Premier vers\nDeuxième vers",
  "attributes": {
    "semantic_role": "quote",
    "quote_kind": "poetry",
    "lineation": "verse",
    "protected_zone": "poetry"
  }
}
```

Contrat cible :

```json
{
  "block_type": "quote_block",
  "attributes": {
    "semantic_role": "quote",
    "quote_kind": "poetry",
    "lineation": "verse"
  },
  "lines": [
    {"text": "Premier vers", "inlines": []},
    {"text": "Deuxième vers", "inlines": []}
  ]
}
```

Invariants :

```text
quote_kind == poetry  => lineation == verse
lineation == verse    => lignes exploitables
protected_zone poetry => bloc non promouvable en heading
```

---

## 6. Lignes et retours internes

Les retours internes peuvent provenir :

- d'un `\n` dans `Block.text` ;
- d'un `InlineSpan(kind="line_break")` ;
- d'une séquence de blocs successifs regroupés.

Le pivot doit choisir une représentation canonique avant export. L'export XML ne doit pas avoir à deviner si un retour à la ligne signifie vers, simple retour manuel ou accident.

---

## 7. ProtectedZone

Une zone protégée désigne un bloc ou une séquence qui ne doit pas subir certains traitements ordinaires.

Représentation minimale possible dans `Block.attributes` :

```json
{
  "protected_zone": "poetry",
  "protected_zone_score": 0.91,
  "protected_zone_rule": "structure.poetry.sequence"
}
```

Types initiaux recommandés : `poetry`, `quote`, `old_quote`, `code`, `linguistic_transcription`, `table`, `formula`, `bibliography`, `caption`.

Une zone protégée peut bloquer : promotion en heading, correction orthotypographique agressive, suggestion stylistique, normalisation d'espaces, suppression de ponctuation, transformation en liste.

Important : `protected_zone` n'est pas une sémantique complète. Elle doit conduire, si nécessaire, à une canonicalisation explicite.

---

## 8. Candidats concurrents

Un même bloc peut recevoir plusieurs interprétations possibles.

```json
{
  "target_ref": "block_42",
  "candidates": [
    {"type": "heading", "score": 0.74},
    {"type": "poetry_line", "score": 0.91}
  ],
  "decision": "poetry_line",
  "vetoed": ["heading"]
}
```

Cette logique peut d'abord être portée par `Diagnostic.attributes`, puis devenir une dataclass dédiée si le besoin se stabilise.

---

## 9. Annotations, diagnostics et transformations

### `Diagnostic`

- `diagnostic_id`
- `module`
- `severity`
- `category`
- `message`
- `target_ref`
- `evidence`
- `rule_id`
- `suggested_fix`
- `status`
- `attributes`

`attributes` peut contenir : `score`, `decision`, `candidate_type`, `veto_reasons`, `ai_candidate`, `protected_zone`, `source_signals`.

### `Suggestion`

- `suggestion_id`
- `module`
- `target_ref`
- `message`
- `rationale`
- `proposed_text`
- `confidence`
- `caution_level`
- `attributes`

Une suggestion n'est pas une transformation.

### `Transformation`

- `transformation_id`
- `module`
- `target_ref`
- `operation`
- `before`
- `after`
- `rule_id`
- `applied`
- `validated_by_human`
- `attributes`

Une transformation doit indiquer pourquoi elle a été appliquée : score, décision, indices, absence de veto.

---

## 10. Rapport

### `ModuleRun`

- `module_name`
- `version`
- `started_at`
- `finished_at`
- `parameters`
- `summary`
- `status`

### `ProcessingReport`

- `report_id`
- `document_id`
- `module_runs`
- `diagnostics`
- `suggestions`
- `transformations`
- `errors`
- `warnings`
- `metadata`

Le rapport doit permettre de reconstruire quel module a décidé quoi, avec quel score, quels vetos et quelle transformation ou abstention.

### `PipelineResult`

- `source_document`
- `styled_document`
- `report`
- `pivot_payload`
- `tei_xml`

À terme, `pivot_payload` doit être le JSON canonique du pivot, non un dictionnaire opportuniste.

---

## 11. Relation avec les sorties

- sortie JSON : représentation contractuelle du pivot ;
- sortie DOCX : vue de relecture humaine basée sur ce modèle ;
- sortie XML‑TEI Métopes : cible de production produite depuis ce modèle ;
- sortie LaTeX : projection typographique à rattacher au modèle ;
- sortie HTML/PDF : visualisation et contrôle.

Le modèle interne doit rester plus riche que la sortie DOCX.

---

## 12. Tests obligatoires liés au modèle

Le modèle doit être protégé par :

- tests de sérialisation ;
- tests de désérialisation ;
- tests de round‑trip Python -> JSON -> Python -> JSON ;
- tests d'invariants ;
- tests de cohérence entre pivot et exports.

Exemple critique :

```text
un bloc canonique quote_kind=poetry + lineation=verse
  -> JSON stable
  -> DOCX rendu comme vers
  -> XML <lg>/<l>
```
