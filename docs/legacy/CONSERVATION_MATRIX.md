> **Statut : document de l'architecture legacy (pivot Python-JSON / scoring / seuils / IA multi-niveaux), non utilisé par le point d'entrée actuel (`main.py`).**
> La stratégie actuelle est décrite dans [`docs/REBORN_ARCHITECTURE.md`](../REBORN_ARCHITECTURE.md). Conservé pour référence historique et récupération ponctuelle de code (voir `docs/REBORN_ARCHITECTURE.md` §10 « Politique de réutilisation »).

# Matrice de conservation documentaire (import/export DOCX)

Statut réel de ce qui est conservé lors de l'aller-retour DOCX → modèle interne →
DOCX, établi à partir de tests exécutables (cités) ou, à défaut, d'une inspection
directe du code d'import/export. Rien ici n'est une extrapolation.

| Objet | Statut | Preuve |
|---|---|---|
| Notes de bas de page (contenu, numérotation) | **conservé et testé** | `tests/unit/test_docx_importer_rich.py::test_import_docx_preserves_inline_styles_and_note_call`, `test_import_docx_note_keeps_inline_styles`, `test_footnote_with_id_zero_is_not_dropped_as_separator` |
| Styles de paragraphe (indentation 1re ligne, titres, citations) | **conservé et testé** | `tests/integration/test_docx_exporter_metopes_template.py::test_regular_paragraphs_are_first_line_indented`, `test_heading_not_indented_and_following_paragraph_is_indented`, `test_quote_block_is_not_indented` |
| Italique | **conservé et testé** | `test_docx_importer_rich.py::test_import_docx_preserves_inline_italic_span_for_poetry_like_line` ; `test_docx_exporter_century_styles.py::test_century_keeps_italic_in_exported_runs` |
| Petites capitales | **conservé et testé** | `test_docx_importer_rich.py::test_import_docx_preserves_inline_styles_and_note_call` (import) ; `test_docx_exporter_century_styles.py` (export, cas des siècles) |
| Exposant / indice (`vertAlign`) | **conservé et testé** | `test_docx_importer_rich.py::test_import_docx_preserves_inline_styles_and_note_call` (import, sub et sup) ; `test_docx_exporter_century_styles.py::test_century_is_exported_with_small_caps_and_superscript` et `tests/unit/test_orthotypo_numero_styling.py` (export, o de "no") |
| Tableau | **conservé et testé** (comme bloc protégé, structure préservée sans réinterprétation) | `test_docx_importer_rich.py::test_import_docx_preserves_table_as_protected_block` ; `test_docx_exporter_century_styles.py::test_export_preserves_table_and_body_order` |
| Saut de page | **conservé, testé indirectement** | Géré par `_add_page_break`/`page_break_before` (`docx_exporter.py`) ; pas de test dédié isolé à ce jour — écart identifié, pas comblé dans cette passe. |
| Hyperlien (texte visible) | **conservé sans garantie** | `tests/integration/test_docx_conservation_hyperlink.py::test_hyperlink_visible_text_is_preserved_on_import` — le texte du lien est importé comme texte normal parmi les runs. |
| Hyperlien (cible/URL) | **non pris en charge** | `tests/integration/test_docx_conservation_hyperlink.py::test_hyperlink_target_is_not_preserved_through_export` — `InlineSpan` n'a pas de champ dédié à une cible de lien ; l'URL n'est capturée nulle part et disparaît à l'export. |
| Saut de section | **non pris en charge (documents à plusieurs sections)** | `docx_exporter.py::_clear_body` ne préserve que le dernier `w:sectPr` du corps ; l'import ne modélise pas les sections comme un concept distinct. Un document à une seule section (cas normal d'un manuscrit académique) n'est pas affecté. |
| En-tête / pied de page | **non pris en charge** | Aucune lecture ni écriture de `word/header*.xml`/`word/footer*.xml` dans `docx_importer.py`/`docx_exporter.py` ; seul l'en-tête/pied du gabarit Métopes utilisé pour l'export s'applique, celui du manuscrit source n'est jamais lu. |
| Champ Word (`w:fldSimple`, TOC, numérotation auto., etc.) | **refusé explicitement** | `CONSIGNES_AUTEURS_PURH_2025.pdf` (guide PURH) demande déjà de ne pas utiliser l'indexation automatique ; le pipeline ne lit ni n'écrit de champs Word — un champ présent dans le manuscrit source est ignoré (son résultat mis en cache textuel, s'il existe dans `w:t`, peut survivre incidemment, mais le champ lui-même n'est jamais recréé). |
| Signet (`w:bookmarkStart`/`End`) | **non pris en charge** | Aucune référence à `bookmarkStart`/`bookmarkEnd` dans `docx_importer.py`/`docx_exporter.py`. |

## Ce que cette matrice ne couvre pas encore

- Saut de page : pas de test synthétique dédié isolé — le mécanisme existe
  (`page_break_before`) mais son round-trip n'est vérifié qu'incidemment via d'autres
  tests qui en contiennent.
- Toute combinaison de plusieurs de ces objets dans un même document n'a pas été testée
  spécifiquement au-delà des combinaisons déjà couvertes par les fixtures existantes
  (`tests/helpers/docx_factory.py`).

## Principe de mise à jour

Cette matrice doit être mise à jour à chaque fois qu'un test de conservation
documentaire est ajouté ou qu'un comportement change — ne jamais la laisser dériver du
code réel. Une ligne « conservé et testé » sans test cité est une régression de ce
document, pas seulement du code.
