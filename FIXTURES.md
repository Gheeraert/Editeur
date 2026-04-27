# FIXTURES.md

## 1. Objet

Ce document décrit les familles de fixtures à constituer pour permettre un développement fiable avec Codex.

Une fixture n'est pas un gros document réaliste ; c'est un **cas de test ciblé**.

Tu enregistreras éventuellement quelques fixtures dans le dossier, pour des cas précis, courts, limités, pertinents, utiles pour les tests, en complément des fichiers exemples complets qui se trouvent dans le dossier "sources"
---

## 2. Principe général

Les fixtures doivent être :
- courtes ;
- lisibles ;
- nommées explicitement ;
- reliées à un comportement attendu ;
- indépendantes autant que possible.

Les documents réels volumineux doivent d'abord être placés dans `sources/`, puis découpés en fixtures ciblées.

---

## 3. Grandes familles de fixtures

## 3.1 Orthotypography
But : tester une règle déterministe de surface.

### Exemples
- `quotes_french_spacing`
- `colon_spacing`
- `semicolon_spacing`
- `note_call_position`
- `italics_unbalanced`
- `double_spaces`
- `century_notation`
- `number_abbreviation`

### Fichiers attendus
- entrée brute (`.txt`, `.docx` ou JSON dérivé) ;
- sortie attendue (`.json`) ;
- éventuellement correction attendue locale.

---

## 3.2 Author vs styled
But : comparer un extrait auteur et sa version stylée.

### Exemples
- `chapter_heading_author_vs_styled`
- `note_call_author_vs_styled`
- `quotation_author_vs_styled`
- `bibliography_entry_author_vs_styled`

### Fichiers attendus
- version auteur ;
- version stylée ;
- JSON décrivant les écarts pertinents.

---

## 3.3 Style suggestions
But : vérifier qu'une suggestion IA reste prudente.

### Exemples
- `local_repetition_should_be_flagged`
- `dense_but_clear_sentence_should_not_be_rewritten`
- `ambiguous_pronoun_reference`
- `deliberate_literary_turn_should_be_left_alone`

### Attendu
- signalement ;
- suggestion locale ;
- ou abstention.

---

## 3.4 Structure recognition
But : reconnaître une structure documentaire.

### Exemples
- `chapter_title`
- `section_subtitle`
- `blockquote`
- `epigraph`
- `list_simple`
- `footnote_block`
- `bibliography_block`

### Attendu
- type de structure reconnu ;
- bloc(s) généré(s) ;
- ambiguïtés éventuelles.

---

## 3.5 Metopes XML
But : tester un comportement XML ciblé.

### Exemples
- `xml_simple_chapter`
- `xml_chapter_with_notes`
- `xml_quote_nested`
- `xml_bibliography_basic`

### Attendu
- structure lue correctement ;
- rendu ou extraction cohérente ;
- diagnostics si cas limite.

---

## 3.6 Rendering HTML
But : valider le rendu HTML d'un XML connu.

### Exemples
- `html_render_notes`
- `html_render_headings`
- `html_render_blockquote`
- `html_render_bibliography`

### Attendu
- HTML conforme à des critères ciblés ;
- pas nécessairement identité textuelle totale si le test porte sur des fragments significatifs.

---

## 3.7 Rendering PDF
But : vérifier des critères PDF ciblés.

### Remarque
Au début, on testera de préférence :
- présence d'éléments ;
- ordre ;
- titres ;
- notes ;
- non pas l'identité visuelle exhaustive.

---

## 3.8 Bibliography
But : tester la normalisation ou la reconnaissance de références.

À activer tôt seulement si la bibliographie entre dans le périmètre.

---

## 4. Nommage recommandé

Format conseillé :

```text
<famille>/<cas>_input.<ext>
<famille>/<cas>_expected.json
```

ou, pour les paires :

```text
author_vs_styled/<cas>_author.docx
author_vs_styled/<cas>_styled.docx
author_vs_styled/<cas>_expected.json
```

---

## 5. Format des attentes

Les attentes doivent être explicites.

### Pour l'orthotypographie
- diagnostics attendus ;
- rule ids ;
- correction locale éventuelle.

### Pour le style
- suggestion admise ou abstention attendue ;
- niveau de prudence.

### Pour la structure
- type(s) de blocs ou annotations attendus.

### Pour le XML / rendu
- structure ou fragments attendus.

---

## 6. Liste initiale de fixtures à préparer

## A. Orthotypographie — priorité absolue
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

## B. Author vs styled — priorité absolue
1. titre de chapitre ;
2. intertitre ;
3. paragraphe avec note ;
4. citation en bloc ;
5. entrée bibliographique.

## C. Style suggestions — priorité forte
1. répétition lexicale locale ;
2. lourdeur syntaxique réelle ;
3. phrase dense mais claire ;
4. style volontaire à respecter ;
5. ambiguïté pronominale.

## D. Structure recognition — priorité forte
1. titre ;
2. sous-titre ;
3. note ;
4. citation en bloc ;
5. liste ;
6. bibliographie simple.

## E. XML / rendu — priorité forte
1. chapitre simple XML ;
2. XML avec notes ;
3. XML avec citation ;
4. rendu HTML de notes ;
5. rendu HTML de hiérarchie ;
6. rendu PDF de base.

---

## 7. Ce qu'il faut éviter

- document entier comme unique fixture ;
- attente implicite non documentée ;
- fichier sans description de ce qu'il teste ;
- mélange de plusieurs difficultés dans un seul cas quand ce n'est pas nécessaire.

---

## 8. Fiche descriptive recommandée pour chaque fixture

Chaque famille peut comporter un petit `README.md` local indiquant :
- le but du cas ;
- la source d'origine ;
- la règle ou le comportement visé ;
- la raison du choix.

Cette pratique aidera fortement Codex et la maintenance du projet.
