# DATA MODEL (etat reel V1 consolidee)

## 1. Objectif

Le coeur metier repose sur des dataclasses Python.
La serialisation JSON est l'image transportable de ces objets.

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

### `Metadata`
- `title`
- `subtitle`
- `authors`
- `language`
- `collection`
- `publication_type`
- `source_label`

### `InlineStyle` (nouveau)
- `bold`
- `italic`
- `small_caps`
- `subscript`
- `superscript`

### `InlineSpan` (nouveau)
- `text`
- `style: InlineStyle`
- `kind` (`text`, `note_call`, `tab`, `line_break`, ...)
- `note_ref` (si appel de note)
- `attributes`

### `Block`
- `block_id`
- `block_type`
- `text`
- `inlines` (liste de `InlineSpan`)
- `note_refs` (liste d'ids de notes appelees)
- `children`
- `attributes`
- `source_span`

Sous-types en place:
- `Paragraph`
- `Heading`
- `QuoteBlock`

### `Note`
- `note_id`
- `label`
- `text`
- `inlines` (liste de `InlineSpan`)
- `target_ref` (bloc d'appel principal, si connu)
- `attributes`

### `BibliographyItem`
- `item_id`
- `raw_text`
- `parsed_fields`
- `item_type`
- `source_span`

## 3. Annotations

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

### `Evidence`
- `excerpt`
- `before`
- `after`
- `offset_start`
- `offset_end`

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

## 4. Rapport

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

### `PipelineResult`
- `source_document`
- `styled_document`
- `report`
- `pivot_payload`
