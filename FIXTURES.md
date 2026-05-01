# FIXTURES.md

## 1. Objet

Ce document décrit les familles de fixtures à constituer pour permettre un développement fiable avec Codex.

Une fixture n'est pas un gros document réaliste. C'est un cas de test ciblé.

Les fichiers sources complets peuvent être conservés dans `sources/`, mais les tests doivent utiliser des extraits courts, lisibles et documentés.

---

## 2. Principe général

Les fixtures doivent être courtes, lisibles, nommées explicitement, reliées à un comportement attendu, indépendantes autant que possible, et accompagnées d'un attendu vérifiable.

Les documents réels volumineux doivent d'abord servir à comprendre les problèmes, puis être découpés en fixtures minimales.

---

## 3. Grandes familles de fixtures

### 3.1 Orthotypography

But : tester une règle déterministe de surface.

Exemples : `quotes_french_spacing`, `colon_spacing`, `semicolon_spacing`, `note_call_position`, `italics_unbalanced`, `double_spaces`, `century_notation`, `number_abbreviation`.

### 3.2 Author vs styled

But : comparer un extrait auteur et sa version stylée.

Exemples : `chapter_heading_author_vs_styled`, `note_call_author_vs_styled`, `quotation_author_vs_styled`, `bibliography_entry_author_vs_styled`.

### 3.3 Style suggestions

But : vérifier qu'une suggestion IA reste prudente.

Exemples : `local_repetition_should_be_flagged`, `dense_but_clear_sentence_should_not_be_rewritten`, `ambiguous_pronoun_reference`, `deliberate_literary_turn_should_be_left_alone`.

### 3.4 Structure recognition

But : reconnaître une structure documentaire.

Exemples : `chapter_title`, `section_subtitle`, `blockquote`, `epigraph`, `list_simple`, `footnote_block`, `bibliography_block`, `poetry_sequence`, `false_heading_in_poetry`, `code_block`, `linguistic_transcription`.

### 3.5 Protected zones

But : vérifier que certaines zones bloquent les transformations ordinaires.

Exemples : `poetry_blocks_heading`, `poetry_blocks_list_bullet`, `code_blocks_typography`, `linguistic_transcription_blocks_spacing`, `table_blocks_paragraph_flattening`, `old_quote_blocks_style_suggestion`.

### 3.6 Métopes XML

But : tester un comportement XML ciblé.

Exemples : `xml_simple_chapter`, `xml_chapter_with_notes`, `xml_quote_nested`, `xml_bibliography_basic`.

### 3.7 Rendering HTML

But : valider le rendu HTML d'un XML connu.

Exemples : `html_render_notes`, `html_render_headings`, `html_render_blockquote`, `html_render_bibliography`.

### 3.8 Rendering PDF

Au début, tester plutôt présence d'éléments, ordre, titres, notes, et non identité visuelle exhaustive.

### 3.9 Bibliography

À activer tôt seulement si la bibliographie entre dans le périmètre.

---

## 4. Nommage recommandé

```text
<famille>/<cas>_input.<ext>
<famille>/<cas>_expected.json
```

Pour les zones protégées :

```text
protected_zones/<cas>_input.json
protected_zones/<cas>_expected.json
```

---

## 5. Format des attentes

### Orthotypographie

Diagnostics attendus, rule ids, correction locale éventuelle.

### Style

Suggestion admise, abstention attendue, niveau de prudence.

### Structure

Types de blocs attendus, diagnostics attendus, transformations interdites, vetos attendus.

### Zones protégées

Type de zone, score éventuel, transformations bloquées, transformations autorisées.

### XML / rendu

Structure ou fragments attendus, diagnostics éventuels, rendu minimal vérifiable.

---

## 6. Liste initiale de fixtures à préparer

### A. Orthotypographie — priorité absolue

1. guillemets français et espaces ;
2. espace avant les deux-points ;
3. espace avant le point-virgule ;
4. appel de note et ponctuation ;
5. doubles espaces ;
6. italiques non refermés ;
7. siècles ;
8. abréviations fréquentes ;
9. numéros / `n°` ;
10. citation courte.

### B. Author vs styled — priorité absolue

1. titre de chapitre ;
2. intertitre ;
3. paragraphe avec note ;
4. citation en bloc ;
5. entrée bibliographique.

### C. Style suggestions — priorité forte

1. répétition lexicale locale ;
2. lourdeur syntaxique réelle ;
3. phrase dense mais claire ;
4. style volontaire à respecter ;
5. ambiguïté pronominale.

### D. Structure recognition — priorité forte

1. titre ;
2. sous-titre ;
3. note ;
4. citation en bloc ;
5. liste ;
6. bibliographie simple ;
7. poésie ;
8. faux titre ;
9. code ;
10. transcription linguistique.

### E. Protected zones — priorité forte

1. vers devenu titre ;
2. vers devenu liste à puce ;
3. code contenant ponctuation non française ;
4. transcription linguistique avec notation spécialisée ;
5. tableau à préserver ;
6. citation ancienne à ne pas moderniser.

### F. XML / rendu — priorité forte

1. chapitre simple XML ;
2. XML avec notes ;
3. XML avec citation ;
4. rendu HTML de notes ;
5. rendu HTML de hiérarchie ;
6. rendu PDF de base.

---

## 7. Fixtures prioritaires issues du problème poésie / titres

### `protected_zones/poetry_false_heading_input.json`

But : vérifier qu'un vers appartenant à une séquence poétique ne devient pas un titre.

Attendu : séquence reconnue comme poésie, bloc fautif non promu en `heading`, diagnostic ou transformation `quote_block` selon score, attribut `protected_zone = poetry` si implémenté.

### `protected_zones/poetry_false_bullet_input.json`

But : vérifier qu'une ligne de vers accidentellement importée comme puce ne reste pas une liste.

Attendu : séquence reconnue, attributs de liste ignorés ou nettoyés, pas de puce dans le DOCX de relecture.

### `protected_zones/poetry_source_heading_input.json`

But : vérifier qu'un faux style Word `Titre 2` ne casse pas la séquence poétique.

Attendu : `source_heading_count` conservé en evidence, pas de promotion en titre si la séquence poétique est prioritaire.

---

## 8. Ce qu'il faut éviter

Document entier comme unique fixture, attente implicite non documentée, fichier sans description, mélange de plusieurs difficultés dans un seul cas, fixture dépendante d'un rendu visuel complet si le test porte seulement sur une décision structurelle.

---

## 9. Fiche descriptive recommandée

Chaque famille peut comporter un petit `README.md` local indiquant le but du cas, la source, la règle visée, la raison du choix, les transformations interdites et les diagnostics attendus.
