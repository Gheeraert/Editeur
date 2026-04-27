# DATA_MODEL.md

## 1. Objectif

Ce document décrit le modèle métier minimal recommandé pour le projet.

La représentation interne doit être portée par des **dataclasses Python**.
Les mêmes objets doivent pouvoir être sérialisés en JSON.

---

## 2. Vue d'ensemble

Le modèle tourne autour de quatre familles d'objets :

1. **document et contenu** ;
2. **annotations de diagnostic** ;
3. **suggestions et transformations** ;
4. **rapport de traitement**.

---

## 3. Objets documentaires

## 3.1 Document
Représente l'unité de travail principale.

### Champs possibles
- `document_id`
- `source_path`
- `source_format`
- `metadata`
- `blocks`
- `notes`
- `bibliography`
- `annotations`
- `history`

### Invariants
- un `Document` doit toujours avoir un identifiant ;
- son contenu doit être ordonné ;
- ses blocs doivent être adressables.

---

## 3.2 Metadata
Métadonnées générales du document.

### Champs possibles
- `title`
- `subtitle`
- `authors`
- `language`
- `collection`
- `publication_type`
- `source_label`

Ces champs sont optionnels au départ, mais doivent être structurés dès que connus.

---

## 3.3 Block
Unité textuelle ou structurelle élémentaire.

### Champs possibles
- `block_id`
- `block_type`
- `text`
- `children`
- `attributes`
- `source_span`

### Exemples de `block_type`
- `paragraph`
- `heading`
- `subheading`
- `quote_block`
- `epigraph`
- `list`
- `list_item`
- `footnote`
- `bibliography_item`
- `unknown`

### Remarque
On peut choisir plus tard de spécialiser certains types en sous-dataclasses, mais un modèle simple avec `block_type` peut suffire au départ.

---

## 3.4 Note
Représente une note de bas de page ou de fin.

### Champs possibles
- `note_id`
- `label`
- `text`
- `target_ref`
- `attributes`

---

## 3.5 BibliographyItem
Entrée bibliographique structurée ou semi-structurée.

### Champs possibles
- `item_id`
- `raw_text`
- `parsed_fields`
- `item_type`
- `source_span`

### Remarque
Au début, `raw_text` peut suffire.
La structuration fine viendra ensuite.

---

## 4. Objets de diagnostic

## 4.1 Diagnostic
Signalement d'un point problématique ou notable.

### Champs possibles
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

### Valeurs utiles pour `severity`
- `info`
- `warning`
- `error`

### Exemples de `category`
- `spacing`
- `punctuation`
- `quotes`
- `note_call`
- `italics`
- `style_repetition`
- `structure_ambiguity`

### `status`
- `open`
- `accepted`
- `rejected`
- `ignored`

---

## 4.2 Evidence
Petit objet facultatif décrivant le contexte du diagnostic.

### Champs possibles
- `excerpt`
- `before`
- `after`
- `offset_start`
- `offset_end`

---

## 5. Suggestions et transformations

## 5.1 Suggestion
Proposition non obligatoire.

### Champs possibles
- `suggestion_id`
- `module`
- `target_ref`
- `message`
- `rationale`
- `proposed_text`
- `confidence`
- `caution_level`

### `caution_level`
- `high`
- `medium`
- `low`

Plus la prudence doit être forte, plus le système doit expliciter qu'il ne s'agit pas d'une correction certaine.

---

## 5.2 Transformation
Modification locale proposée ou appliquée.

### Champs possibles
- `transformation_id`
- `module`
- `target_ref`
- `operation`
- `before`
- `after`
- `rule_id`
- `applied`
- `validated_by_human`

### Exemples de `operation`
- `replace_text`
- `insert_space`
- `normalize_quotes`
- `annotate_structure`

---

## 6. Rapport de traitement

## 6.1 ProcessingReport
Agrégat des résultats produits par un module ou un pipeline.

### Champs possibles
- `report_id`
- `document_id`
- `module_runs`
- `diagnostics`
- `suggestions`
- `transformations`
- `errors`
- `warnings`
- `metadata`

---

## 6.2 ModuleRun
Trace d'exécution d'un module.

### Champs possibles
- `module_name`
- `version`
- `started_at`
- `finished_at`
- `parameters`
- `summary`
- `status`

---

## 7. Références de cible

Les diagnostics, suggestions et transformations doivent viser une cible stable.

### Options possibles
- id de bloc ;
- chemin logique ;
- note id ;
- plage d'offset ;
- combinaison de plusieurs repères.

### Recommandation
Ne pas dépendre exclusivement d'offsets bruts.
Préférer une référence sémantique stable.

---

## 8. Exemple JSON minimal

```json
{
  "document_id": "doc-001",
  "source_format": "docx",
  "metadata": {
    "title": "Chapitre 1"
  },
  "blocks": [
    {
      "block_id": "b1",
      "block_type": "paragraph",
      "text": "Voici un exemple :mal ponctué."
    }
  ]
}
```

Exemple de diagnostic associé :

```json
{
  "diagnostic_id": "d1",
  "module": "orthotypography",
  "severity": "warning",
  "category": "spacing",
  "message": "Absence d'espace insécable avant les deux-points.",
  "target_ref": "b1",
  "rule_id": "purh.spacing.colon",
  "status": "open"
}
```

---

## 9. Évolution prévue

Le modèle doit rester minimal au départ, mais prévoir une extension possible pour :
- variantes de blocs ;
- structure hiérarchique plus fine ;
- enrichissements bibliographiques ;
- liens vers XML ;
- validation humaine détaillée ;
- historique de décisions éditoriales.
