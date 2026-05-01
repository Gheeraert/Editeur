# DATA_MODEL.md

## 1. Objectif et statut

Le cœur métier repose sur des dataclasses Python. Ce modèle est le pivot réel du pipeline éditorial.

La sérialisation JSON est l'image transportable de ces objets : debug, traçabilité, tests, échanges techniques. Elle n'est pas le modèle souverain.

---

## 2. Objets documentaires

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

## 3. Faits documentaires et attributs source

Les faits issus du document source doivent être conservés dans `attributes` ou des structures dédiées.

Exemples : `style_name`, `style_id`, `all_runs_bold`, `all_runs_italic`, `ind_left`, `ind_first_line`, `num_id`, `numbering_level`, `is_list`, `table_position`, `source_heading_level`.

Ces faits sont des indices. Ils ne suffisent pas toujours à décider.

---

## 4. Annotations et décisions

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

### `Evidence`

- `excerpt`
- `before`
- `after`
- `offset_start`
- `offset_end`

Pour une décision structurelle, `Evidence` doit idéalement citer les indices : nombre de lignes, longueur moyenne, ratio de ponctuation, styles sources, etc.

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

## 5. HeuristicDecision

Le module de reconnaissance structurelle peut utiliser une dataclass de décision heuristique.

Champs recommandés :

- `rule_id`
- `category`
- `target_refs`
- `score`
- `decision`
- `evidence`
- `veto_reasons`
- `ai_candidate`

Valeurs possibles de `decision` : `ignore`, `diagnostic`, `transform`.

---

## 6. ProtectedZone

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

---

## 7. Candidats concurrents

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

## 8. Rapport

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

---

## 9. Relation avec les sorties

- sortie JSON : dérivée de ce modèle ;
- sortie DOCX : vue de relecture humaine basée sur ce modèle ;
- sortie XML-TEI Métopes : cible de production à produire depuis ce modèle.

Le modèle interne doit rester plus riche que la sortie DOCX.
