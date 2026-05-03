# Checklist sources et fixtures

## Sources à déposer en premier

### 1. Normes éditoriales

- [ ] guide typographique PURH
- [ ] feuille de style
- [ ] consignes aux auteurs
- [ ] conventions bibliographiques, si disponibles
- [ ] CSL bibliographique, si la biblio entre vite dans le périmètre

### 2. Manuscrits

- [ ] 2 fichiers Word d'auteur représentatifs
- [ ] leurs 2 versions stylées par les éditrices
- [ ] si possible, une note rapide indiquant les corrections importantes

### 3. JSON pivot

- [ ] 2 JSON pivot correspondant à de courts extraits réels
- [ ] 1 JSON pivot minimal entièrement synthétique
- [ ] 1 JSON pivot volontairement incohérent pour tester les diagnostics
- [ ] 1 JSON pivot avec citation en vers
- [ ] 1 JSON pivot avec tableau

### 4. XML Métopes

- [ ] 2 XML réels
- [ ] si possible, une brève note expliquant leur statut ou leur provenance
- [ ] les extraits JSON pivot correspondant aux mêmes structures

### 5. Rendus

- [ ] 1 ou 2 HTML de référence
- [ ] 1 ou 2 PDF imprimeurs correspondants
- [ ] si possible, le pivot ou XML à l'origine du rendu

### 6. Références secondaires

- [ ] fichiers InDesign utiles à titre d'observation
- [ ] seulement si certains choix de rendu doivent être compris tôt

---

## Fixtures à fabriquer en premier

### Pivot contract

- [ ] pivot_roundtrip_minimal_document
- [ ] pivot_heading_requires_level
- [ ] pivot_poetry_requires_lineation
- [ ] pivot_protected_zone_is_not_semantics
- [ ] pivot_table_requires_preserved_structure
- [ ] pivot_unknown_block_diagnostic

### Orthotypographie

- [ ] quotes_french_spacing
- [ ] colon_spacing
- [ ] semicolon_spacing
- [ ] note_call_position
- [ ] italics_unbalanced
- [ ] double_spaces
- [ ] century_notation
- [ ] number_abbreviation

### Author vs styled

- [ ] heading_author_vs_styled
- [ ] note_author_vs_styled
- [ ] quotation_author_vs_styled
- [ ] poetry_author_vs_styled
- [ ] bibliography_author_vs_styled

### Style suggestions

- [ ] repetition_local
- [ ] heavy_sentence
- [ ] dense_but_clear_sentence
- [ ] deliberate_style_to_preserve
- [ ] ambiguous_reference

### Structure recognition

- [ ] chapter_title
- [ ] subtitle
- [ ] footnote
- [ ] blockquote
- [ ] poetry_sequence
- [ ] simple_list
- [ ] bibliography_block

### Canonicalization

- [ ] canonicalize_heading_level
- [ ] canonicalize_poetry_sequence
- [ ] canonicalize_quote_block_with_line_breaks
- [ ] canonicalize_table_block
- [ ] canonicalize_note_calls

### XML / rendu

- [ ] xml_simple_chapter
- [ ] xml_with_notes
- [ ] xml_with_quote
- [ ] xml_with_poetry_lg_l
- [ ] html_render_notes
- [ ] html_render_headings
- [ ] pdf_render_basic

### Export consistency

- [ ] pivot_poetry_docx_xml_agree
- [ ] pivot_heading_docx_xml_agree
- [ ] pivot_table_docx_xml_agree
